from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TripGroup(Base):
    __tablename__ = "trip_groups"
    id = Column(Integer, primary_key=True, index=True)
    region = Column(String, index=True, nullable=False)
    origin_geohash = Column(String, index=True, nullable=False)
    destination_geohash = Column(String, index=True, nullable=False)
    time_bucket_start = Column(DateTime, index=True, nullable=False)
    time_bucket_minutes = Column(Integer, nullable=False)

    trips = relationship("Trip", back_populates="group")

    __table_args__ = (
        UniqueConstraint(
            "region",
            "origin_geohash",
            "destination_geohash",
            "time_bucket_start",
            name="uq_trip_group",
        ),
    )


class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True, index=True)
    region = Column(String, index=True, nullable=False)
    origin_lat = Column(Float, index=True, nullable=False)
    origin_lng = Column(Float, index=True, nullable=False)
    destination_lat = Column(Float, index=True, nullable=False)
    destination_lng = Column(Float, index=True, nullable=False)
    started_at = Column(DateTime, index=True, nullable=False)
    datasource = Column(String, index=True, nullable=False)
    group_id = Column(Integer, ForeignKey("trip_groups.id"), nullable=False)

    group = relationship("TripGroup", back_populates="trips")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, index=True, nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, nullable=True)
    message = Column(String, nullable=True)
