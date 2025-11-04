from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .clustering import encode_geohash, time_bucket
from .config import settings
from .models import IngestionJob, Trip, TripGroup


def get_or_create_trip_group(
    session: Session,
    *,
    region: str,
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    started_at: datetime,
) -> TripGroup:
    bucket = time_bucket(started_at, settings.time_bucket_minutes)
    origin_hash = encode_geohash(origin_lat, origin_lng)
    destination_hash = encode_geohash(destination_lat, destination_lng)

    query = select(TripGroup).where(
        TripGroup.region == region,
        TripGroup.origin_geohash == origin_hash,
        TripGroup.destination_geohash == destination_hash,
        TripGroup.time_bucket_start == bucket,
    )
    result = session.execute(query).scalar_one_or_none()
    if result:
        return result

    group = TripGroup(
        region=region,
        origin_geohash=origin_hash,
        destination_geohash=destination_hash,
        time_bucket_start=bucket,
        time_bucket_minutes=settings.time_bucket_minutes,
    )
    session.add(group)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return session.execute(query).scalar_one()
    return group


def bulk_insert_trips(session: Session, rows: Iterable[Trip]) -> None:
    session.add_all(rows)
    session.flush()


def create_ingestion_job(session: Session, filename: str) -> IngestionJob:
    job = IngestionJob(filename=filename, status="pending", processed_rows=0)
    session.add(job)
    session.flush()
    return job


def update_ingestion_job(
    session: Session,
    job_id: int,
    *,
    status: Optional[str] = None,
    total_rows: Optional[int] = None,
    processed_rows: Optional[int] = None,
    message: Optional[str] = None,
) -> IngestionJob:
    job = session.get(IngestionJob, job_id)
    if not job:
        raise ValueError(f"Ingestion job {job_id} not found")
    if status is not None:
        job.status = status
    if total_rows is not None:
        job.total_rows = total_rows
    if processed_rows is not None:
        job.processed_rows = processed_rows
    if message is not None:
        job.message = message
    session.add(job)
    session.flush()
    return job


def list_trip_groups(session: Session, limit: int = 100) -> List[Tuple[TripGroup, int]]:
    query = (
        select(TripGroup, func.count(Trip.id).label("trip_count"))
        .join(Trip, Trip.group_id == TripGroup.id)
        .group_by(TripGroup.id)
        .order_by(func.count(Trip.id).desc())
        .limit(limit)
    )
    return list(session.execute(query))


def compute_weekly_average(
    session: Session,
    *,
    region: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> Tuple[float, int, int]:
    filters = []
    if region:
        filters.append(Trip.region == region)
    if bbox:
        min_lat, min_lng, max_lat, max_lng = bbox
        filters.append(and_(Trip.origin_lat >= min_lat, Trip.origin_lat <= max_lat))
        filters.append(and_(Trip.origin_lng >= min_lng, Trip.origin_lng <= max_lng))

    base_query = select(func.count(Trip.id), func.min(Trip.started_at), func.max(Trip.started_at))
    if filters:
        base_query = base_query.where(*filters)
    total_trips, min_date, max_date = session.execute(base_query).one()
    if total_trips == 0 or not min_date or not max_date:
        return 0.0, 0, 0

    week_span = max((max_date - min_date).days / 7, 0)
    week_count = max(1, int(week_span) + 1)
    weekly_average = total_trips / week_count
    return weekly_average, total_trips, week_count
