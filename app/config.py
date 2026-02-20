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

# === Storage Cleanup Settings ===
# Auto-delete video file from server after user downloads it (saves storage!)
AUTO_DELETE_AFTER_DOWNLOAD = os.getenv("AUTO_DELETE_AFTER_DOWNLOAD", "true").lower() == "true"

# Auto-delete videos older than this many hours (0 = disabled)
VIDEO_MAX_AGE_HOURS = int(os.getenv("VIDEO_MAX_AGE_HOURS", "2"))

# Cleanup check interval in minutes
CLEANUP_INTERVAL_MINUTES = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "30"))
