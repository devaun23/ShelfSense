#!/bin/sh
# Start script for Railway deployment
# This ensures proper shell expansion of $PORT

# Default to 8000 if PORT not set
PORT="${PORT:-8000}"

echo "Starting uvicorn on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
