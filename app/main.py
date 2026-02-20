"""
Sora Automation REST API — FastAPI

Runs inside the linuxserver/chromium container.
Controls the same Chrome via Playwright CDP to generate videos.
"""
import asyncio
import os
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
from app.config import API_KEY, VIDEO_DIR

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

    yield

    logger.info("Shutting down Sora Automation API...")
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
async def download_video(task_id: str, _: bool = Depends(verify_api_key)):
    """
    Download the generated video.

    - Only available when status is 'succeeded'
    - Returns MP4 file
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
        raise HTTPException(status_code=404, detail="Video file not found")

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
