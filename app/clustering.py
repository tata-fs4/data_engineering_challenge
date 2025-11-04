from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple

from .config import settings

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def parse_point(point: str) -> Tuple[float, float]:
    point = point.strip()
    if not point.startswith("POINT"):
        raise ValueError(f"Unsupported point format: {point}")
    coords = point[6:-1]
    lng_str, lat_str = coords.split()
    return float(lat_str), float(lng_str)


def encode_geohash(lat: float, lng: float, precision: int | None = None) -> str:
    precision = precision or settings.geohash_precision
    lat_interval = [-90.0, 90.0]
    lng_interval = [-180.0, 180.0]
    geohash = []
    bit = 0
    char = 0
    even = True

    while len(geohash) < precision:
        if even:
            mid = sum(lng_interval) / 2
            if lng > mid:
                char |= 1 << (4 - bit)
                lng_interval[0] = mid
            else:
                lng_interval[1] = mid
        else:
            mid = sum(lat_interval) / 2
            if lat > mid:
                char |= 1 << (4 - bit)
                lat_interval[0] = mid
            else:
                lat_interval[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(_BASE32[char])
            bit = 0
            char = 0
    return "".join(geohash)


def time_bucket(dt: datetime, minutes: int | None = None) -> datetime:
    minutes = minutes or settings.time_bucket_minutes
    bucket_start = dt - timedelta(minutes=dt.minute % minutes, seconds=dt.second, microseconds=dt.microsecond)
    return bucket_start
