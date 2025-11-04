from __future__ import annotations

import asyncio
import csv
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from .clustering import parse_point
from .config import settings
from .crud import (
    bulk_insert_trips,
    create_ingestion_job,
    get_or_create_trip_group,
    update_ingestion_job,
)
from .db import get_sync_session
from .models import Trip
from .notifications import manager


class IngestionError(Exception):
    """Raised when an ingestion job fails."""


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.strip())


def _count_rows(file_path: Path) -> int:
    with file_path.open("r", encoding="utf-8") as csvfile:
        return max(sum(1 for _ in csvfile) - 1, 0)


def _persist_chunk(session: Session, records: List[dict]) -> None:
    trips: List[Trip] = []
    for record in records:
        origin_lat, origin_lng = parse_point(record["origin_coord"])
        destination_lat, destination_lng = parse_point(record["destination_coord"])
        started_at = parse_datetime(record["datetime"])
        datasource = record["datasource"]
        group = get_or_create_trip_group(
            session,
            region=record["region"],
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            started_at=started_at,
        )
        trip = Trip(
            region=record["region"],
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            started_at=started_at,
            datasource=datasource,
            group_id=group.id,
        )
        trips.append(trip)
    bulk_insert_trips(session, trips)


def _ingest_file(job_id: int, file_path: Path, loop: asyncio.AbstractEventLoop) -> None:
    def notify(message: dict) -> None:
        asyncio.run_coroutine_threadsafe(manager.send_update(job_id, message), loop)

    try:
        total_rows = _count_rows(file_path)
        with get_sync_session() as session:
            update_ingestion_job(session, job_id, status="running", total_rows=total_rows, processed_rows=0)
        notify({"status": "running", "processed_rows": 0, "total_rows": total_rows})

        processed = 0
        with file_path.open("r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            buffer: List[dict] = []
            for record in reader:
                buffer.append(record)
                if len(buffer) >= settings.ingestion_chunk_size:
                    with get_sync_session() as session:
                        _persist_chunk(session, buffer)
                        processed += len(buffer)
                        update_ingestion_job(session, job_id, processed_rows=processed)
                    notify({"status": "running", "processed_rows": processed, "total_rows": total_rows})
                    buffer.clear()
            if buffer:
                with get_sync_session() as session:
                    _persist_chunk(session, buffer)
                    processed += len(buffer)
                    update_ingestion_job(session, job_id, processed_rows=processed)
                notify({"status": "running", "processed_rows": processed, "total_rows": total_rows})
        with get_sync_session() as session:
            update_ingestion_job(session, job_id, status="completed", processed_rows=processed)
        notify({"status": "completed", "processed_rows": processed, "total_rows": total_rows})
    except Exception as exc:  # noqa: BLE001
        with get_sync_session() as session:
            update_ingestion_job(session, job_id, status="failed", message=str(exc))
        notify({"status": "failed", "message": str(exc)})
        raise IngestionError(str(exc)) from exc


async def ingest_file(job_id: int, file_path: Path) -> None:
    loop = asyncio.get_running_loop()
    bound_ingest = partial(_ingest_file, job_id, file_path, loop)
    await loop.run_in_executor(None, bound_ingest)


async def schedule_ingestion(file_path: Path) -> int:
    with get_sync_session() as session:
        job = create_ingestion_job(session, filename=file_path.name)
        job_id = job.id
    asyncio.create_task(ingest_file(job_id, file_path))
    return job_id
