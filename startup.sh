#!/bin/bash
# =========================================================
# FastAPI Startup Script
# Auto-runs when linuxserver/chromium container boots
# =========================================================

echo "Starting Sora Automation API..."

# Ensure videos directory exists
mkdir -p /app/videos

# Disable screen blanking and DPMS (Power Management) to prevent black screen
export DISPLAY=:1
xset s off || true
xset -dpms || true
xset s noblank || true

# Wait for Chrome to boot up first
sleep 10

# Start FastAPI server in background
cd /app && nohup python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    > /app/api.log 2>&1 &

echo "Sora API started on port 8000"
echo "Log file: /app/api.log"
