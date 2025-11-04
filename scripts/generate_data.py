#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

REGIONS = ["Prague", "Turin", "Hamburg", "Berlin", "Madrid"]
DATASOURCES = ["cheap_mobile", "funny_car", "pt_search_app", "baba_car", "bad_diesel_vehicles"]


def generate_rows(count: int) -> List[dict[str, str]]:
    base_date = datetime(2018, 1, 1)
    rows: List[dict[str, str]] = []
    for i in range(count):
        region = random.choice(REGIONS)
        lat = round(random.uniform(40.0, 55.0), 6)
        lng = round(random.uniform(5.0, 15.0), 6)
        dest_lat = lat + random.uniform(-0.5, 0.5)
        dest_lng = lng + random.uniform(-0.5, 0.5)
        started_at = base_date + timedelta(minutes=random.randint(0, 60 * 24 * 365))
        rows.append(
            {
                "region": region,
                "origin_coord": f"POINT ({lng} {lat})",
                "destination_coord": f"POINT ({dest_lng} {dest_lat})",
                "datetime": started_at.strftime("%Y-%m-%d %H:%M:%S"),
                "datasource": random.choice(DATASOURCES),
            }
        )
    return rows


def write_csv(path: Path, rows: List[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["region", "origin_coord", "destination_coord", "datetime", "datasource"])
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic trip data")
    parser.add_argument("--rows", type=int, default=10000, help="Number of synthetic rows to generate")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic.csv"), help="Output CSV path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_rows(args.rows)
    write_csv(args.output, rows)
    print(f"Generated {args.rows} rows at {args.output}")


if __name__ == "__main__":
    main()
