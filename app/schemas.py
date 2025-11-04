from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TripBase(BaseModel):
    region: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    started_at: datetime
    datasource: str


class TripCreate(TripBase):
    group_id: int


class TripRead(TripBase):
    id: int
    group_id: int

    class Config:
        orm_mode = True


class TripGroupBase(BaseModel):
    region: str
    origin_geohash: str
    destination_geohash: str
    time_bucket_start: datetime
    time_bucket_minutes: int


class TripGroupRead(TripGroupBase):
    id: int
    trip_count: int = Field(..., description="Number of trips in the group")

    class Config:
        orm_mode = True


class IngestionRequest(BaseModel):
    filename: str


class IngestionJobRead(BaseModel):
    id: int
    filename: str
    status: str
    created_at: datetime
    updated_at: datetime
    total_rows: Optional[int]
    processed_rows: Optional[int]
    message: Optional[str]

    class Config:
        orm_mode = True


class WeeklyAverageRequest(BaseModel):
    region: Optional[str] = None
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lng: Optional[float] = None
    max_lng: Optional[float] = None


class WeeklyAverageResponse(BaseModel):
    area_description: str
    weekly_average: float
    total_trips: int
    week_count: int


class TripGroupListResponse(BaseModel):
    groups: List[TripGroupRead]
