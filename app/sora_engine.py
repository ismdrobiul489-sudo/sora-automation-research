"""
Sora Engine — Controls the running Chrome via Playwright CDP to generate Sora videos.

This does NOT launch a new browser — it connects to the Chrome instance already
running inside the linuxserver/chromium container. You can see everything
happening in real-time via VNC at http://server:4100!
"""
import asyncio
import os
import uuid
import time
import logging
from typing import Dict, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from app.config import CDP_ENDPOINT, VIDEO_DIR, SORA_URL, MAX_WAIT_TIME, POLL_INTERVAL

logger = logging.getLogger("sora_engine")
logging.basicConfig(level=logging.INFO)


class TaskInfo:
    """Stores all information about a video generation task"""
    def __init__(self, task_id: str, prompt: str, orientation: str, size: str):
        self.task_id = task_id
        self.prompt = prompt
        self.orientation = orientation
        self.size = size
        self.status = "queued"
        self.progress = 0.0
        self.message = "Queued"
        self.video_path: Optional[str] = None
        self.video_url: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at = time.time()


class SoraEngine:
    """
    Controls the running Chromium via Playwright CDP.
    Does NOT launch a new browser — connects to the existing one!
    """

    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._is_connected = False
        self._lock = asyncio.Semaphore(1)  # Limit to 1 concurrent generation for 1GB RAM stability

    async def connect(self) -> bool:
        """Connect to running Chrome via CDP"""
        try:
            if self._is_connected and self._browser and self._browser.is_connected():
                return True

            logger.info(f"Connecting to Chrome: {CDP_ENDPOINT}")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.connect_over_cdp(CDP_ENDPOINT)
            self._is_connected = True
            logger.info("Successfully connected to Chrome!")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Chrome: {e}")
            self._is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from Chrome"""
        try:
            if self._playwright:
                await self._playwright.stop()
            self._is_connected = False
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._browser and self._browser.is_connected()

    async def check_session(self) -> bool:
        """Check if Sora login session is still valid"""
        if not await self.connect():
            return False
        try:
            contexts = self._browser.contexts
            if not contexts:
                context = await self._browser.new_context()
            else:
                context = contexts[0]

            page = await context.new_page()
            await page.goto(SORA_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # If redirected to login page, session is invalid
            is_logged_in = "login" not in page.url.lower() and "auth" not in page.url.lower()
            await page.close()

            if is_logged_in:
                logger.info("Sora session is valid — logged in!")
            else:
                logger.warning("Sora session invalid — login required!")

            return is_logged_in
        except Exception as e:
            logger.error(f"Session check error: {e}")
            return False

    def create_task(self, prompt: str, orientation: str = "landscape", size: str = "small") -> str:
        """Create a new video generation task"""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = TaskInfo(task_id, prompt, orientation, size)
        self.tasks[task_id] = task
        logger.info(f"New task created: {task_id} — '{prompt[:50]}...'")
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information"""
        return self.tasks.get(task_id)

    async def run_generation(self, task_id: str):
        """
        Generate a video — this is the main automation!
        Playwright controls the same Chrome: opens Sora -> types prompt -> clicks Generate -> waits -> downloads
        """
        task = self.tasks.get(task_id)
        if not task:
            return

        # Use semaphore to ensure only ONE video generates at a time (saves RAM)
        async with self._lock:
            page = None
            try:
                # 1. Connect to Chrome
                if not await self.connect():
                    task.status = "failed"
                    task.error = "Failed to connect to Chrome"
                    task.message = task.error
                    return

                task.status = "running"
                task.progress = 5.0
                task.message = "Connected to Chrome"

                # 2. Open a new tab (visible in VNC!)
                contexts = self._browser.contexts
                if not contexts:
                    context = await self._browser.new_context()
                else:
                    context = contexts[0]

                page = await context.new_page()
                task.progress = 10.0
                task.message = "Opening Sora..."

                # 3. Navigate to Sora
                logger.info(f"Opening Sora: {SORA_URL}")
                await page.goto(SORA_URL, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                # Check login status
                if "login" in page.url.lower() or "auth" in page.url.lower():
                    task.status = "failed"
                    task.error = "Not logged in to Sora! Please login via Chrome UI first."
                    task.message = task.error
                    logger.error(f"Error: {task.error}")
                    await page.close()
                    return

                task.progress = 20.0
                task.message = "Sora loaded, typing prompt..."

                # 4. Find prompt textarea and type
                logger.info(f"Typing prompt: '{task.prompt[:50]}...'")
                textarea = page.locator(
                    'textarea[placeholder*="Describe"], '
                    'textarea[placeholder*="What"], '
                    'textarea[placeholder*="prompt"], '
                    'textarea'
                ).first
                await textarea.wait_for(state="visible", timeout=15000)
                await textarea.click()
                await textarea.fill(task.prompt)
                await page.wait_for_timeout(1000)

                task.progress = 30.0
                task.message = "Prompt entered, clicking Generate..."

                # 5. Click Generate/Create button
                logger.info("Clicking Generate button...")
                create_btn = page.locator(
                    'button:has-text("Create"), '
                    'button:has-text("Generate"), '
                    'button[type="submit"]'
                ).first
                await create_btn.wait_for(state="visible", timeout=10000)
                await create_btn.click()

                task.progress = 35.0
                task.message = "Generation started! Video is being created..."
                logger.info("Video generation in progress...")

                # 6. Wait for video to be ready
                await page.wait_for_timeout(5000)  # initial wait

                start_time = time.time()
                video_ready = False

                while (time.time() - start_time) < MAX_WAIT_TIME:
                    elapsed = time.time() - start_time
                    # estimated progress (35% to 90% over MAX_WAIT_TIME)
                    task.progress = min(90.0, 35.0 + (elapsed / MAX_WAIT_TIME) * 55.0)

                    # Check for Download button or video element
                    download_btn = page.locator(
                        'button:has-text("Download"), '
                        'a:has-text("Download"), '
                        'button[aria-label*="download" i]'
                    )
                    if await download_btn.count() > 0:
                        logger.info("Video is ready!")
                        video_ready = True
                        break

                    # Video element check
                    video_el = page.locator('video source, video[src]')
                    if await video_el.count() > 0:
                        logger.info("Video element found!")
                        video_ready = True
                        break

                    # Progress text check (Sora UI shows percentage)
                    progress_text = await page.locator('[class*="progress"], [role="progressbar"]').all_text_contents()
                    if progress_text:
                        task.message = f"Generating video... {', '.join(progress_text)}"

                    await page.wait_for_timeout(POLL_INTERVAL * 1000)

                if not video_ready:
                    task.status = "failed"
                    task.error = f"Timeout exceeded ({MAX_WAIT_TIME}s)"
                    task.message = task.error
                    # Debug screenshot
                    await page.screenshot(path=f"/app/videos/{task_id}_timeout.png")
                    await page.close()
                    return

                # 7. Download the video
                task.progress = 90.0
                task.status = "downloading"
                task.message = "Downloading video..."

                os.makedirs(VIDEO_DIR, exist_ok=True)
                video_path = os.path.join(VIDEO_DIR, f"{task_id}.mp4")

                # Method A: Click download button and intercept file download
                try:
                    async with page.expect_download(timeout=60000) as download_info:
                        download_btn = page.locator(
                            'button:has-text("Download"), '
                            'a:has-text("Download"), '
                            'button[aria-label*="download" i]'
                        ).first
                        await download_btn.click()
                    download = await download_info.value
                    await download.save_as(video_path)
                    logger.info(f"Video saved: {video_path}")
                except Exception as dl_err:
                    logger.warning(f"Download button failed, trying video src: {dl_err}")
                    # Method B: Extract video URL from video element
                    try:
                        video_src = await page.locator('video source').first.get_attribute('src')
                        if not video_src:
                            video_src = await page.locator('video').first.get_attribute('src')

                        if video_src:
                            task.video_url = video_src
                            # Download via Playwright
                            response = await page.request.get(video_src)
                            with open(video_path, 'wb') as f:
                                f.write(await response.body())
                            logger.info(f"Video downloaded from src: {video_path}")
                        else:
                            raise Exception("Video URL not found")
                    except Exception as src_err:
                        task.status = "failed"
                        task.error = f"Failed to download video: {src_err}"
                        task.message = task.error
                        await page.screenshot(path=f"/app/videos/{task_id}_dl_error.png")
                        await page.close()
                        return

                # 8. Success!
                task.video_path = video_path
                task.status = "succeeded"
                task.progress = 100.0
                task.message = "Video generation complete!"
                logger.info(f"Task {task_id} completed successfully!")

            except Exception as e:
                logger.error(f"Generation error: {e}")
                task.status = "failed"
                task.error = str(e)
                task.message = f"Error: {e}"
                if page:
                    try:
                        await page.screenshot(path=f"/app/videos/{task_id}_error.png")
                    except Exception:
                        pass
            finally:
                if page:
                    try:
                        logger.info(f"Closing tab for task {task_id} to save RAM...")
                        await page.close()
                    except Exception:
                        pass


# Singleton engine instance
engine = SoraEngine()
