#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from app.crud import create_ingestion_job
from app.db import get_sync_session, sync_engine
from app.ingestion import ingest_file
from app.models import Base, IngestionJob


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark ingestion throughput")
    parser.add_argument("csv", type=Path, help="Path to the CSV file to ingest")
    return parser.parse_args()


async def run_benchmark(csv_path: Path) -> None:
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    with get_sync_session() as session:
        job = create_ingestion_job(session, filename=csv_path.name)
        job_id = job.id
    start = time.perf_counter()
    await ingest_file(job_id, csv_path)
    elapsed = time.perf_counter() - start
    with get_sync_session() as session:
        job = session.get(IngestionJob, job_id)
    if job is None:
        raise RuntimeError("Ingestion job missing after benchmark")
    print(f"Ingested {job.processed_rows} rows in {elapsed:.2f}s -> {job.processed_rows / elapsed:.2f} rows/s")


def main() -> None:
    args = parse_args()
    asyncio.run(run_benchmark(args.csv))


if __name__ == "__main__":
    main()
