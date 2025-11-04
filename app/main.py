from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .config import settings
from .crud import compute_weekly_average, list_trip_groups
from .db import get_sync_session, sync_engine
from .ingestion import schedule_ingestion
from .models import Base, IngestionJob
from .notifications import manager
from .schemas import TripGroupListResponse, WeeklyAverageResponse

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
async def startup() -> None:
    Base.metadata.create_all(bind=sync_engine)


@app.post("/ingest")
async def ingest_data(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV uploads are supported")
    destination = settings.data_dir / f"{uuid4().hex}_{Path(file.filename).name}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as buffer:
        await asyncio.to_thread(shutil.copyfileobj, file.file, buffer)
    job_id = await schedule_ingestion(destination)
    return JSONResponse({"job_id": job_id, "message": "Ingestion scheduled", "filename": destination.name})


@app.get("/jobs/{job_id}")
async def get_job(job_id: int) -> JSONResponse:
    with get_sync_session() as session:
        job = session.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        payload = {
            "id": job.id,
            "filename": job.filename,
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "total_rows": job.total_rows,
            "processed_rows": job.processed_rows,
            "message": job.message,
        }
    return JSONResponse(payload)


@app.websocket("/ws/ingestion/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: int) -> None:
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)


@app.get("/trip-groups", response_model=TripGroupListResponse)
def get_trip_groups(limit: int = 50) -> TripGroupListResponse:
    with get_sync_session() as session:
        rows = list_trip_groups(session, limit=limit)
    groups = [
        {
            "id": group.id,
            "region": group.region,
            "origin_geohash": group.origin_geohash,
            "destination_geohash": group.destination_geohash,
            "time_bucket_start": group.time_bucket_start,
            "time_bucket_minutes": group.time_bucket_minutes,
            "trip_count": count,
        }
        for group, count in rows
    ]
    return TripGroupListResponse(groups=groups)


@app.get("/analytics/weekly-average", response_model=WeeklyAverageResponse)
def weekly_average(
    region: Optional[str] = None,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lng: Optional[float] = None,
    max_lng: Optional[float] = None,
) -> WeeklyAverageResponse:
    bbox = None
    if None not in (min_lat, max_lat, min_lng, max_lng):
        if min_lat > max_lat or min_lng > max_lng:
            raise HTTPException(status_code=400, detail="Invalid bounding box coordinates")
        bbox = (min_lat, min_lng, max_lat, max_lng)
    with get_sync_session() as session:
        weekly_avg, total_trips, week_count = compute_weekly_average(session, region=region, bbox=bbox)
    if total_trips == 0:
        raise HTTPException(status_code=404, detail="No trips found for the specified filters")
    area_description = region or f"BBox({min_lat},{min_lng})-({max_lat},{max_lng})"
    return WeeklyAverageResponse(
        area_description=area_description,
        weekly_average=weekly_avg,
        total_trips=total_trips,
        week_count=week_count,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
