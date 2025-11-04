FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/tripdata
ENV SYNC_DATABASE_URL=postgresql://postgres:postgres@db:5432/tripdata

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
