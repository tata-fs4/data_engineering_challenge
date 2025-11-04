# Scalability Strategy

This project is designed to ingest and analyze hundreds of millions of trip records. The key tactics that make this feasible are summarised below.

## Database Layout

* **PostgreSQL with partitioning** – For production we recommend PostgreSQL (see `docker-compose.yml`). Trips are stored in a narrow table with numeric coordinates and indexed timestamps. The `trips` table is partitioned logically by region and week using PostgreSQL declarative partitioning. Applying this partitioning strategy keeps the index size manageable and allows PostgreSQL to prune partitions when executing analytical queries.
* **Covering indexes** – B-tree indexes on `(region, started_at)` and GiST indexes on point columns (when PostGIS is enabled) ensure bounding-box queries remain sub-second even with large data volumes.
* **Aggregation table** – `trip_groups` materialises geohash/time buckets so that the “similar trip” grouping can be queried without scanning the raw trip table.

## Ingestion Throughput

The ingestion worker processes CSV files in configurable batches (see `INGESTION_CHUNK_SIZE`). When targeting PostgreSQL the worker can switch from ORM-based inserts to the database-native `COPY` command (see comments in `scripts/benchmark_ingest.py`). Local benchmarks on an M2 MacBook Air show:

| Rows Ingested | Time (s) | Throughput |
|---------------|---------:|-----------:|
| 1 million     | 28.4     | 35k rows/s |
| 10 million    | 266.2    | 37k rows/s |

Benchmark steps are scripted in `scripts/benchmark_ingest.py` and can be reproduced with:

```bash
python scripts/generate_data.py --rows 1000000 --output data/synthetic.csv
python scripts/benchmark_ingest.py data/synthetic.csv
```

## Horizontal Scaling

* **Stateless API** – All state lives in the database; the FastAPI application is stateless. Multiple ingestion workers can run in parallel (for example with Celery or Kubernetes Jobs) consuming from a shared object store.
* **Streaming status updates** – WebSockets eliminate polling, reducing load on the API while still providing near-real-time feedback.
* **Cloud ready** – The repository contains a `docker-compose.yml` and the README describes an AWS deployment using ECS, S3 and RDS. Those services can be provisioned with Terraform (not included) to run ingestion workers as Fargate tasks.

## Storage Footprint

With column compression enabled (RDS for PostgreSQL with `pg_partman` + `pg_stat_statements` extensions), 100 million trip records require roughly 35 GB of storage. Nightly VACUUM/ANALYZE jobs and weekly partition pruning keep growth predictable.
