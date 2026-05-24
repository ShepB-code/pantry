#!/usr/bin/env bash
set -e

echo "Starting Pantry MVP..."

# Start backend
echo "Starting backend API (FastAPI)..."
cd backend

# Install dependencies and activate .venv
if [ ! -d "../.venv" ]; then
  python3 -m venv ../.venv
fi
source ../.venv/bin/activate
python3 -m pip install fastapi uvicorn pandas python-multipart google-generativeai python-dotenv pillow > /dev/null 2>&1 || true
python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Start frontend
echo "Starting frontend UI (Vite)..."
cd frontend
npm install --no-audit --no-fund > /dev/null 2>&1 || true
npm run dev &
FRONTEND_PID=$!
cd ..

echo "MVP is running!"
echo "Backend: http://127.0.0.1:8000"
echo "Frontend: Check Vite output for local URL (usually http://localhost:8080 or http://localhost:5173)"
echo "Press Ctrl+C to stop both servers."

# Handle shutdown
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID
