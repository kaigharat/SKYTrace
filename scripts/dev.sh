#!/usr/bin/env bash
# SkyTrace Development Launcher
# Starts both the FastAPI ML Backend and the Next.js Frontend concurrently.

set -e

cleanup() {
    echo ""
    echo "Shutting down SkyTrace services..."
    kill $(jobs -p) 2>/dev/null || true
    wait 2>/dev/null || true
    echo "All services stopped."
}

trap cleanup SIGINT SIGTERM EXIT

echo "=========================================================="
echo " Starting SkyTrace Repository Intelligence AI (Full-Stack)"
echo "=========================================================="

# Start Backend API
echo "Starting FastAPI Backend on http://localhost:8000..."
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend health
echo "Waiting for backend health check..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "Backend is healthy."
        break
    fi
    sleep 1
done

# Start Frontend
echo "Starting Next.js Frontend on http://localhost:3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "=========================================================="
echo " SkyTrace is running!"
echo " Frontend: http://localhost:3000"
echo " Backend API: http://localhost:8000"
echo " API Docs: http://localhost:8000/docs"
echo " Press Ctrl+C to stop all services."
echo "=========================================================="

wait
