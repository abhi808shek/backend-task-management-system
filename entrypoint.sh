#!/bin/bash

# Wait for postgres to be ready (optional but recommended)
echo "Waiting for postgres..."

# Run migrations
echo "Running alembic migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000