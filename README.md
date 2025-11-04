# Trip Data Engineering Challenge

This repository implements an end-to-end data platform for processing mobility trip data. It fulfils the challenge requirements by providing:

* Automated CSV ingestion into a SQL database with background workers.
* Grouping of similar trips using geohash/time buckets.
* Weekly average analytics by region or bounding box.
* Real-time ingestion status updates delivered over WebSockets (no polling).
* Horizontal scalability for 100M+ records with documented benchmarks and a containerised deployment path.

## Project Layout

```
app/
  main.py              # FastAPI application & API definitions
  ingestion.py         # Background ingestion worker
  crud.py              # Database access helpers
  models.py            # SQLAlchemy models
  schemas.py           # Pydantic response/request models
  clustering.py        # Geohash and time bucket utilities
  notifications.py     # WebSocket connection manager
scripts/
  generate_data.py     # Synthetic data generator
  benchmark_ingest.py  # Ingestion benchmark harness
docs/SCALABILITY.md    # Scaling strategy and benchmark results
sql_queries.sql        # Answers to the bonus SQL questions
tests/                 # Automated QA coverage
```

## Running Locally (SQLite)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at <http://localhost:8000>. Visit `/docs` for interactive documentation.

### Example Workflow

1. **Upload data** – `POST /ingest` with a CSV file (see the sample CSV in the challenge prompt).
2. **Follow progress** – Connect to `ws://localhost:8000/ws/ingestion/{job_id}` to receive status updates such as processed row counts.
3. **Inspect trip groups** – `GET /trip-groups` lists the most populated geohash/time clusters.
4. **Weekly analytics** – `GET /analytics/weekly-average?region=Prague` returns aggregated KPIs for a region or by bounding box using `min_lat`, `max_lat`, `min_lng`, `max_lng` parameters.

## Containerised Setup (PostgreSQL)

The project ships with a Docker Compose stack:

```bash
docker compose up --build
```

This starts PostgreSQL and the FastAPI service (listening on port `8000`). In production you would typically push CSV files to object storage (S3/GCS) and trigger ingestion jobs by posting the object URL.

A reference AWS deployment would use:

* **Amazon RDS (PostgreSQL)** for the SQL database with partitioning enabled.
* **Amazon ECS/Fargate** to host the API and a pool of ingestion workers.
* **Amazon S3** for durable storage of incoming CSV files; workers stream data directly from S3.
* **Amazon SNS + API Gateway WebSockets** to broadcast ingestion status events.

## Scalability Proof

Details about database partitioning, ingestion throughput benchmarks and horizontal scaling considerations live in [`docs/SCALABILITY.md`](docs/SCALABILITY.md). Synthetic datasets and benchmarks can be reproduced with:

```bash
python scripts/generate_data.py --rows 1000000 --output data/synthetic.csv
python scripts/benchmark_ingest.py data/synthetic.csv
```

## Automated Quality Assurance

Automated tests cover ingestion and analytics logic:

```bash
pytest
```

## Bonus SQL Answers

The `sql_queries.sql` file contains ready-to-run SQL answering:

1. From the two most common regions, which is the latest datasource?
2. What regions has the `cheap_mobile` datasource appeared in?

## Environment Variables

| Variable             | Default Value                                         | Purpose                               |
|----------------------|-------------------------------------------------------|---------------------------------------|
| `DATABASE_URL`       | `sqlite+aiosqlite:///./tripdata.db`                   | Async SQLAlchemy URL                  |
| `SYNC_DATABASE_URL`  | `sqlite:///./tripdata.db`                             | Sync SQLAlchemy URL                   |
| `INGESTION_CHUNK_SIZE` | `1000`                                             | Rows processed per batch              |
| `GEOHASH_PRECISION`  | `5`                                                   | Controls grouping sensitivity         |
| `TIME_BUCKET_MINUTES` | `60`                                                | Time bucket duration                  |
| `DATA_DIR`           | `data/`                                               | Persistent storage for uploaded CSVs  |

## Manual QA Checklist

* `POST /ingest` accepts CSV uploads and responds with a job id.
* `ws://.../ws/ingestion/{job_id}` streams progress updates without polling.
* `GET /trip-groups` shows grouped trips with counts.
* `GET /analytics/weekly-average` returns averages for region or bounding box filters.
* Web interface at `/docs` documents the API and allows manual testing.

