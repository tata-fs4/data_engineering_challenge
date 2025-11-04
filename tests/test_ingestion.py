import os
from pathlib import Path

import pytest
from sqlalchemy import select, func

# Configure environment before importing application modules
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_tripdata.db")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///./test_tripdata.db")
os.environ.setdefault("ENVIRONMENT", "test")

from app import config  # noqa: E402
from app.config import get_settings  # noqa: E402

config.get_settings.cache_clear()
settings = get_settings()

from app.db import get_sync_session, sync_engine  # noqa: E402
from app.ingestion import ingest_file  # noqa: E402
from app.models import Base, IngestionJob, Trip, TripGroup  # noqa: E402
from app.crud import create_ingestion_job, compute_weekly_average  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    yield
    Base.metadata.drop_all(bind=sync_engine)


def write_sample_csv(path: Path) -> None:
    csv_content = """region,origin_coord,destination_coord,datetime,datasource
Prague,POINT (14.4973794438195 50.00136875782316),POINT (14.43109483523328 50.04052930943246),2018-05-28 09:03:40,funny_car
Prague,POINT (14.32427345662177 50.00002074358429),POINT (14.47767895969969 50.09339790740321),2018-05-13 08:52:25,cheap_mobile
Prague,POINT (14.34394689715277 50.12299688052901),POINT (14.45046952210687 50.10077692162883),2018-05-20 02:31:22,cheap_mobile
"""
    path.write_text(csv_content)


@pytest.mark.asyncio
async def test_ingestion_creates_trips(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)

    with get_sync_session() as session:
        job = create_ingestion_job(session, filename=csv_path.name)
        job_id = job.id

    await ingest_file(job_id, csv_path)

    with get_sync_session() as session:
        trip_count = session.execute(select(func.count(Trip.id))).scalar_one()
        group_count = session.execute(select(func.count(TripGroup.id))).scalar_one()
        job = session.get(IngestionJob, job_id)

    assert trip_count == 3
    assert group_count >= 1
    assert job.status == "completed"
    assert job.processed_rows == 3


@pytest.mark.asyncio
async def test_weekly_average_by_region(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)

    with get_sync_session() as session:
        job = create_ingestion_job(session, filename=csv_path.name)
        job_id = job.id

    await ingest_file(job_id, csv_path)

    with get_sync_session() as session:
        average, total, weeks = compute_weekly_average(session, region="Prague")

    assert total == 3
    assert weeks >= 1
    assert average > 0
