#!/bin/bash
# =========================================================
# FastAPI Startup Script
# Auto-runs inside linuxserver/chromium container on boot
# Installs Python deps (first run) then starts the API
# =========================================================

echo "=========================================="
echo "  Sora Automation API — Starting..."
echo "=========================================="

# Ensure directories exist
mkdir -p /app/videos

# Install Python dependencies (only if not already installed)
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "First run — installing Python dependencies..."
    apt-get update && apt-get install -y --no-install-recommends python3-pip
    pip3 install --break-system-packages --no-cache-dir -r /app/requirements.txt
    pip3 install --break-system-packages playwright
    echo "Dependencies installed successfully!"
else
    echo "Python dependencies already installed."
fi

# Wait for Chrome to fully boot up
echo "Waiting for Chrome to start..."
sleep 15

# Start FastAPI server in background
# Run from / so Python resolves "from app.xxx import ..." correctly
cd / && nohup python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    > /app/api.log 2>&1 &

echo "=========================================="
echo "  Sora API running on port 8000"
echo "  Log: /app/api.log"
echo "=========================================="
