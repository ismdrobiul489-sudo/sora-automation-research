# =========================================================
# Sora Automation — Single Container
# linuxserver/chromium + Python + FastAPI + Playwright
# =========================================================
# 
# This image extends linuxserver/chromium:
# - Chrome web UI (KasmVNC) = port 3000 -> host 4100
# - FastAPI REST API = port 8000
#
# Chrome runs with --remote-debugging-port=9222
# Playwright connects to the same Chrome via CDP
# =========================================================

FROM lscr.io/linuxserver/chromium:latest

# Install Python 3 + pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /app/requirements.txt

# Install Playwright dependencies (Chromium is already present, just need deps)
RUN pip3 install --break-system-packages playwright && \
    playwright install-deps chromium

# Copy application code
COPY app/ /app/

# Startup script — auto-starts FastAPI when container boots
COPY startup.sh /custom-cont-init.d/99-start-api.sh
RUN chmod +x /custom-cont-init.d/99-start-api.sh

# Create videos directory
RUN mkdir -p /app/videos

# Expose FastAPI port
EXPOSE 8000

# Volume mount points
VOLUME ["/config", "/app/videos"]
