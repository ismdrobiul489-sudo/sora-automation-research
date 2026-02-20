"""
Sora Automation REST API — FastAPI

Runs inside the linuxserver/chromium container.
Controls the same Chrome via Playwright CDP to generate videos.
"""
import asyncio
import os
import time
import glob
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    GenerateRequest, GenerateResponse,
    StatusResponse, HealthResponse,
    TaskStatus
)
from app.sora_engine import engine
from app.config import (
    API_KEY, VIDEO_DIR,
    AUTO_DELETE_AFTER_DOWNLOAD,
    VIDEO_MAX_AGE_HOURS,
    CLEANUP_INTERVAL_MINUTES,
)

logger = logging.getLogger("sora_api")

# === API Key Security (Optional) ===
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key — skips if not configured"""
    if not API_KEY:
        return True
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True


# === Auto Cleanup Background Task ===
async def periodic_cleanup():
    """Background task: deletes old video files to save storage"""
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_MINUTES * 60)

            if VIDEO_MAX_AGE_HOURS <= 0:
                continue

            max_age_seconds = VIDEO_MAX_AGE_HOURS * 3600
            now = time.time()
            deleted_count = 0
            freed_mb = 0.0

            for filepath in glob.glob(os.path.join(VIDEO_DIR, "*")):
                if not os.path.isfile(filepath):
                    continue
                file_age = now - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    file_size = os.path.getsize(filepath) / (1024 * 1024)
                    os.remove(filepath)
                    deleted_count += 1
                    freed_mb += file_size

            if deleted_count > 0:
                logger.info(
                    f"Cleanup: deleted {deleted_count} old files, freed {freed_mb:.1f} MB"
                )
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


def delete_video_file(filepath: str):
    """Delete a single video file and log it"""
    try:
        if filepath and os.path.exists(filepath):
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            os.remove(filepath)
            logger.info(f"Auto-deleted after download: {filepath} ({size_mb:.1f} MB freed)")
    except Exception as e:
        logger.error(f"Failed to delete {filepath}: {e}")


def get_storage_info():
    """Get current video storage usage"""
    total_size = 0
    file_count = 0
    for filepath in glob.glob(os.path.join(VIDEO_DIR, "*")):
        if os.path.isfile(filepath):
            total_size += os.path.getsize(filepath)
            file_count += 1
    return {
        "file_count": file_count,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }


# === App Lifecycle ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown actions"""
    logger.info("Starting Sora Automation API...")
    os.makedirs(VIDEO_DIR, exist_ok=True)

    # Try connecting to Chrome (retry — Chrome takes time to boot)
    for attempt in range(5):
        if await engine.connect():
            break
        logger.info(f"Chrome connect retry {attempt + 1}/5...")
        await asyncio.sleep(5)

    # Start periodic cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info(
        f"Storage cleanup enabled: delete files older than {VIDEO_MAX_AGE_HOURS}h, "
        f"check every {CLEANUP_INTERVAL_MINUTES}min, "
        f"auto-delete on download: {AUTO_DELETE_AFTER_DOWNLOAD}"
    )

    yield

    logger.info("Shutting down Sora Automation API...")
    cleanup_task.cancel()
    await engine.disconnect()


# === FastAPI App ===
app = FastAPI(
    title="Sora Automation API",
    description="REST API for generating videos on Sora.com. "
                "Controls the Chrome browser inside linuxserver/chromium container via Playwright CDP.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow access from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Endpoints ===

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check server health and connection status"""
    chrome_ok = engine.is_connected
    session_ok = False

    if chrome_ok:
        try:
            session_ok = await engine.check_session()
        except Exception:
            pass

    return HealthResponse(
        status="ok" if chrome_ok else "chrome_disconnected",
        chrome_connected=chrome_ok,
        session_valid=session_ok,
    )


@app.post("/generate", response_model=GenerateResponse, tags=["Video"])
async def generate_video(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_api_key),
):
    """
    Start video generation.

    - Send a prompt -> get a task_id
    - Video generation runs in the background via Chrome automation
    - Watch it live at http://server:4100 (Chrome VNC UI)!
    """
    if not engine.is_connected:
        # Try reconnecting
        if not await engine.connect():
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to Chrome. Make sure the container is running."
            )

    task_id = engine.create_task(
        prompt=request.prompt,
        orientation=request.orientation.value,
        size=request.size.value,
    )

    # Start video generation in background
    background_tasks.add_task(engine.run_generation, task_id)

    return GenerateResponse(
        task_id=task_id,
        status="queued",
        message=f"Video generation started! prompt='{request.prompt[:80]}...'",
    )


@app.get("/status/{task_id}", response_model=StatusResponse, tags=["Video"])
async def get_status(task_id: str, _: bool = Depends(verify_api_key)):
    """
    Check video generation progress.

    - status: queued -> running -> downloading -> succeeded / failed
    - progress: 0-100%
    """
    task = engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    download_url = None
    if task.status == "succeeded" and task.video_path:
        download_url = f"/download/{task_id}"

    return StatusResponse(
        task_id=task.task_id,
        status=TaskStatus(task.status),
        progress=task.progress,
        message=task.message,
        video_url=task.video_url,
        download_url=download_url,
    )


@app.get("/download/{task_id}", tags=["Video"])
async def download_video(
    task_id: str,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_api_key),
):
    """
    Download the generated video.

    - Only available when status is 'succeeded'
    - Returns MP4 file
    - If AUTO_DELETE_AFTER_DOWNLOAD is enabled, the file is deleted from
      the server after you download it (saves storage!)
    """
    task = engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    if task.status != "succeeded":
        raise HTTPException(
            status_code=400,
            detail=f"Video not ready yet. Current status: {task.status}"
        )

    if not task.video_path or not os.path.exists(task.video_path):
        raise HTTPException(status_code=404, detail="Video file not found (may have been auto-deleted)")

    # Schedule auto-delete AFTER the file has been sent to the client
    if AUTO_DELETE_AFTER_DOWNLOAD:
        background_tasks.add_task(delete_video_file, task.video_path)
        task.message = "Downloaded and scheduled for auto-delete from server"

    return FileResponse(
        path=task.video_path,
        media_type="video/mp4",
        filename=f"sora_{task_id}.mp4",
        headers={"Content-Disposition": f'attachment; filename="sora_{task_id}.mp4"'},
    )


@app.get("/tasks", tags=["Video"])
async def list_tasks(_: bool = Depends(verify_api_key)):
    """List all tasks"""
    tasks = []
    for tid, task in engine.tasks.items():
        tasks.append({
            "task_id": task.task_id,
            "prompt": task.prompt[:100],
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
        })
    return {"tasks": tasks, "total": len(tasks)}


@app.post("/session/check", tags=["Session"])
async def check_session(_: bool = Depends(verify_api_key)):
    """
    Check if Sora login session is valid.

    - True: API is ready to generate videos
    - False: Login via Chrome UI (http://server:4100) first
    """
    if not engine.is_connected:
        if not await engine.connect():
            return {"valid": False, "message": "Cannot connect to Chrome"}

    valid = await engine.check_session()
    return {
        "valid": valid,
        "message": "Session valid — ready to generate!" if valid
                   else "Session expired — please login via Chrome UI (http://server:4100)"
    }


# === Storage Management Endpoints ===

@app.get("/storage", tags=["Storage"])
async def storage_info(_: bool = Depends(verify_api_key)):
    """
    Check how much storage is being used by videos.

    Returns file count and total size in MB.
    """
    info = get_storage_info()
    return {
        **info,
        "auto_delete_on_download": AUTO_DELETE_AFTER_DOWNLOAD,
        "max_age_hours": VIDEO_MAX_AGE_HOURS,
        "cleanup_interval_minutes": CLEANUP_INTERVAL_MINUTES,
    }


@app.post("/cleanup", tags=["Storage"])
async def cleanup_videos(
    max_age_hours: int = 0,
    _: bool = Depends(verify_api_key),
):
    """
    Manually delete old video files to free up storage.

    - max_age_hours=0 : Delete ALL video files
    - max_age_hours=1 : Delete files older than 1 hour
    - max_age_hours=2 : Delete files older than 2 hours
    """
    before = get_storage_info()
    max_age_seconds = max_age_hours * 3600 if max_age_hours > 0 else 0
    now = time.time()
    deleted = []

    for filepath in glob.glob(os.path.join(VIDEO_DIR, "*")):
        if not os.path.isfile(filepath):
            continue

        if max_age_seconds > 0:
            file_age = now - os.path.getmtime(filepath)
            if file_age < max_age_seconds:
                continue

        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        os.remove(filepath)
        deleted.append({"file": os.path.basename(filepath), "size_mb": round(size_mb, 2)})

    after = get_storage_info()
    freed_mb = before["total_size_mb"] - after["total_size_mb"]

    logger.info(f"Manual cleanup: deleted {len(deleted)} files, freed {freed_mb:.1f} MB")

    return {
        "deleted_count": len(deleted),
        "freed_mb": round(freed_mb, 2),
        "remaining": after,
        "deleted_files": deleted,
    }
