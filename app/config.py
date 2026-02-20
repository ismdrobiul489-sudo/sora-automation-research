"""
Configuration — Loads settings from environment variables.
"""
import os

# Chrome DevTools Protocol endpoint
# linuxserver/chromium runs Chrome with --remote-debugging-port=9222
CDP_ENDPOINT = os.getenv("CDP_ENDPOINT", "http://localhost:9222")

# Videos are saved to this directory
VIDEO_DIR = os.getenv("VIDEO_DIR", "/app/videos")

# Optional API key (for security)
API_KEY = os.getenv("API_KEY", "")

# Sora URL
SORA_URL = os.getenv("SORA_URL", "https://sora.com")

# Maximum wait time for video generation (seconds)
MAX_WAIT_TIME = int(os.getenv("MAX_WAIT_TIME", "600"))  # 10 minutes

# Poll interval (seconds)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))
