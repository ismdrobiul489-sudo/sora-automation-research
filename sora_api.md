# Sora API Documentation (Reverse Engineered)

> **Disclaimer:** This is an unofficial, reverse-engineered API specification for OpenAI's Sora. It is subject to change at any time. Use responsibly.

## 1. Authentication
Sora requires a valid `Bearer Token` and specific `Cookies` that must be extracted from a logged-in browser session.

- **Source:** `sora.chatgpt.com`
- **Method:** Open Developer Tools (F12) > Network Tab > Filter by `create` > Look at Request Headers.
- **Critical Headers:**
  - `Authorization`: `Bearer <eyJxbGciOi...>` (JWT Token)
  - `Cookie`: `oai-did=...; _cfuvid=...;` (Session Cookies)
  - `oai-device-id`: Device UUID
  - `openai-sentinel-token`: Security token

---

## 2. API Endpoints

### A. Generate Video (Create Task)
**URL:** `https://sora.chatgpt.com/backend/nf/create`
**Method:** `POST`
**Content-Type:** `application/json`

#### Request Headers
```http
Host: sora.chatgpt.com
Authorization: Bearer <YOUR_ACCESS_TOKEN>
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36
Origin: https://sora.chatgpt.com
Referer: https://sora.chatgpt.com/profile
Priority: u=1, i
```

#### Request Body (JSON)
```json
{
  "kind": "video",
  "prompt": "A cinematic drone shot of a futuristic city at sunset...",
  "title": null,
  "orientation": "portrait",
  "size": "small",
  "audio_caption": null,
  "audio_transcript": null,
  "cameo_ids": null,
  "cameo_replacements": null,
  "inpaint_items": [],
  "metadata": null,
  "model": "sy_8",
  "n_frames": 300,
  "project_id": null,
  "remix_target_id": null,
  "storyboard_id": null,
  "style_id": null,
  "video_caption": null
}
```
**Key Parameters:**
- `prompt`: The text description of the video.
- `model`: `sy_8` (Seems to be the current model ID).
- `orientation`: `portrait` (9:16), `landscape` (16:9), or `square` (1:1).
- `n_frames`: `300` (Approx 10 seconds).

#### Response (Success)
```json
{
  "id": "task_01kg7sn8rmf7fvy3gacs5g8ahf",
  "status": "pending",
  "prompt": "..."
}
```

---

### B. Check Status (Polling)
**URL:** `https://sora.chatgpt.com/backend/nf/pending/v2`
**Method:** `GET`

#### Response (JSON Array)
Returns a list of active/recent tasks. You need to find your Task ID in this list.

```json
[
  {
    "id": "task_01kg7sn8rmf7fvy3gacs5g8ahf",
    "task_type": "video_gen",
    "status": "running", 
    "progress_pct": 0.45,
    "failure_reason": null,
    "generations": []
  }
]
```

**Statuses:**
- `running`: In progress. Check `progress_pct` (0.0 to 1.0).
- `succeeded` / `complete`: Finished. Check `generations` array.
- `failed`: Check `failure_reason`.

---

### C. Get Video URL (Download)
When `status` is `succeeded`, the `generations` array will contain the video details.

```json
{
  "id": "task_01kg7sn8rmf7fvy3gacs5g8ahf",
  "status": "succeeded",
  "generations": [
    {
      "id": "gen_...",
      "url": "https://videos.openai.com/az/files/...?se=...",
      "video_url": "https://videos.openai.com/az/files/...?se=...",
      "download_url": "..."
    }
  ]
}
```
**Access:** The URL is a Signed Azure Blob URL. It is publicly accessible but expires (Time-limited).

---

## 3. Workflow Logic (Pseudocode)

```javascript
async function createAndDownloadSoraVideo(prompt) {
    // 1. Send Create Request
    const task = await post('/backend/nf/create', { prompt, model: 'sy_8' });
    const taskId = task.id;

    // 2. Poll for Completion
    let videoUrl = null;
    while (!videoUrl) {
        await sleep(5000); // Wait 5s
        
        const tasks = await get('/backend/nf/pending/v2');
        const myTask = tasks.find(t => t.id === taskId);

        if (myTask.status === 'succeeded') {
            videoUrl = myTask.generations[0].url;
        } else if (myTask.status === 'failed') {
            throw new Error(myTask.failure_reason);
        }
    }

    // 3. Download
    downloadFile(videoUrl, `sora_${taskId}.mp4`);
}
```

## 4. Troubleshooting
- **401 Unauthorized:** Your Bearer Token has expired. Refresh the page in various browsers and copy the new token.
- **403 Forbidden:** Missing `Cookie` or `User-Agent` headers. Sora checks for browser consistency.

---

## 5. How to Use (Step-by-Step Guide)

### Step 1: Extract Credentials
1.  Open Chrome/Edge on your computer.
2.  Go to `https://sora.chatgpt.com/` and log in.
3.  Press `F12` to open Developer Tools.
4.  Go to the **Network** tab.
5.  Type a prompt and hit **Generate**.
6.  Look for a request named `create` (Method: POST).
7.  Click on it, go to **Headers**, and copy:
    - `Authorization` (The value starting with `Bearer ...`)
    - `Cookie` (The entire string)

### Step 2: Run via cURL (Terminal)

**Create Video:**
```bash
curl -X POST "https://sora.chatgpt.com/backend/nf/create" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Cookie: <YOUR_COOKIE_STRING>" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36" \
  -d '{
    "kind": "video",
    "prompt": "Cyberpunk city rain",
    "model": "sy_8",
    "orientation": "landscape",
    "n_frames": 300
  }'
```

**Check Status:**
```bash
curl "https://sora.chatgpt.com/backend/nf/pending/v2" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Cookie: <YOUR_COOKIE_STRING>"
```

### Step 3: Run via Python
Use this script to automate the process on your desktop.

```python
import requests
import time
import json

# CONFIG
TOKEN = "YOUR_BEARER_TOKEN_HERE"
COOKIE = "YOUR_COOKIE_STRING_HERE"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Cookie": COOKIE,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
}

def create_video(prompt):
    url = "https://sora.chatgpt.com/backend/nf/create"
    payload = {
        "kind": "video",
        "prompt": prompt,
        "model": "sy_8",
        "orientation": "portrait", 
        "n_frames": 300
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 200:
        task_id = response.json().get("id")
        print(f"Task Started: {task_id}")
        return task_id
    else:
        print(f"Error: {response.text}")
        return None

def poll_status(task_id):
    url = "https://sora.chatgpt.com/backend/nf/pending/v2"
    while True:
        print("Polling status...")
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            tasks = response.json()
            my_task = next((t for t in tasks if t["id"] == task_id), None)
            
            if my_task:
                status = my_task.get("status")
                print(f"Status: {status}")
                
                if status == "succeeded":
                    video_url = my_task["generations"][0]["url"]
                    print(f"\nVIDEO READY: {video_url}\n")
                    return video_url
                elif status == "failed":
                    print("Generation Failed.")
                    return None
            else:
                print("Task not found in pending list (check history?)")
        
        time.sleep(10)

# EXECUTE
tid = create_video("A happy robot dancing in the rain")
if tid:
    poll_status(tid)
```

### Step 4: Run via Node.js
```javascript
const fetch = require('node-fetch'); // npm install node-fetch

const TOKEN = "YOUR_TOKEN";
const COOKIE = "YOUR_COOKIES";

// ... (Logic is effectively the same as Python, using fetch)
```

