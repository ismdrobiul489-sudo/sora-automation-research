# 🇧🇩 Sora Automation — বাংলা ডিপ্লয়মেন্ট গাইড

## এটা কি করে?

এই সিস্টেম USA-এর একটা ক্লাউড সার্ভারে Sora.com থেকে AI ভিডিও generate করে।
তুমি বাংলাদেশ থেকে REST API call দিয়ে ভিডিও বানাতে পারবে।

**যেহেতু Sora-এর কোনো official API নেই**, আমরা Playwright দিয়ে real Chrome
ব্রাউজার control করি — যেনো একজন মানুষ Chrome চালাচ্ছে!

---

## কিভাবে কাজ করে?

```
তুমি (বাংলাদেশ)                    US Cloud Server (Docker)
    │                                      │
    ├── http://server:4100 ──────→ Chrome UI (দেখতে পারবে!)
    │                                      │
    ├── POST /generate ──────────→ FastAPI → Playwright → same Chrome
    │                                      │
    ├── GET /status/{id} ────────→ progress কতটুকু?
    │                                      │
    └── GET /download/{id} ──────→ ভিডিও ডাউনলোড!
```

---

## ধাপ ১: US Cloud Server ভাড়া নাও

তোমার যেকোনো একটা ক্লাউড থেকে **US region**-এ একটা Ubuntu সার্ভার ভাড়া নিতে হবে।

### রিকমেন্ডেড প্রোভাইডার:

| প্রোভাইডার | সর্বনিম্ন প্ল্যান | মাসিক খরচ |
|---|---|---|
| [DigitalOcean](https://www.digitalocean.com) | 2 vCPU, 4GB RAM | ~$24/মাস |
| [Vultr](https://www.vultr.com) | 2 vCPU, 4GB RAM | ~$24/মাস |
| [Hetzner](https://www.hetzner.com/cloud) | 2 vCPU, 4GB RAM (US) | ~$7/মাস |
| [AWS Lightsail](https://aws.amazon.com/lightsail/) | 2 vCPU, 4GB RAM | ~$20/মাস |

> ⚠️ **গুরুত্বপূর্ণ:** অবশ্যই **US region** (New York, Virginia, San Francisco ইত্যাদি) সিলেক্ট করবে।
> Ubuntu **22.04 বা 24.04 LTS** ব্যবহার করবে।

### সার্ভারের ন্যূনতম specs:
- **RAM:** 4GB (Chrome চলবে, তাই 4GB+ দরকার)
- **CPU:** 2 vCPU
- **Disk:** 40GB+ (ভিডিও জমা হবে)
- **OS:** Ubuntu 22.04 / 24.04 LTS

---

## ধাপ ২: SSH দিয়ে সার্ভারে ঢোকো

সার্ভার তৈরি হলে তুমি একটি IP address পাবে। সেটা দিয়ে SSH connect করো:

```bash
ssh root@তোমার-সার্ভার-IP
```

> Windows-এ PowerShell / Terminal / MobaXterm ব্যবহার করতে পারো।

---

## ধাপ ৩: Docker ইনস্টল করো

```bash
# System update
sudo apt update && sudo apt upgrade -y

# Docker ইনস্টল
sudo apt install -y docker.io docker-compose-plugin

# Docker চালু ও enable
sudo systemctl start docker
sudo systemctl enable docker

# চেক করো Docker কাজ করছে কিনা
docker --version
```

---

## ধাপ ৪: প্রোজেক্ট আপলোড করো

### Option A: Git দিয়ে (যদি GitHub-এ আপলোড থাকে)
```bash
git clone https://github.com/তোমার-username/sora-automation-research.git
cd sora-automation-research
```

### Option B: SCP দিয়ে (তোমার PC থেকে সরাসরি)
```bash
# তোমার PC-র Terminal থেকে run করো:
scp -r ./sora-automation-research root@তোমার-সার্ভার-IP:/root/
```

তারপর সার্ভারে:
```bash
cd /root/sora-automation-research
```

---

## ধাপ ৫: Environment সেটআপ

```bash
# .env ফাইল তৈরি
cp .env.example .env

# .env edit করো — password সেট করো
nano .env
```

`.env` ফাইলে নিচেরগুলো সেট করো:
```
CHROME_USER=admin
CHROME_PASSWORD=তোমার-পাসওয়ার্ড

# (Optional) API Key — সেট করলে প্রতি API call-এ X-API-Key header দিতে হবে
API_KEY=তোমার-গোপন-কী
```

> `Ctrl+X` → `Y` → `Enter` দিয়ে সেভ করো।

---

## ধাপ ৬: Docker Container চালু করো! 🚀

```bash
# Image build ও container চালু (প্রথমবার কিছুক্ষণ সময় লাগবে)
docker compose up -d

# চেক করো container চলছে কিনা
docker ps
```

সফল হলে দেখতে পাবে:
```
CONTAINER ID   IMAGE      ...   PORTS                    NAMES
abc123         sora-...   ...   0.0.0.0:4100->3000/tcp   sora-automation
                                0.0.0.0:8000->8000/tcp
```

---

## ধাপ ৭: Chrome-এ Sora লগইন করো

1. তোমার ব্রাউজারে যাও: **`http://তোমার-সার্ভার-IP:4100`**
2. Username/Password দাও (ধাপ ৫-এ যা সেট করেছো)
3. Chrome ব্রাউজার দেখতে পাবে! 🎉
4. Chrome-এর address bar-এ যাও: **`https://sora.com`**
5. তোমার OpenAI অ্যাকাউন্ট দিয়ে **লগইন করো**
6. লগইন সফল হলে Sora dashboard দেখতে পাবে

> ✅ ব্যস! একবার লগইন করলেই হবে। এরপর API দিয়ে সব কাজ করতে পারবে।

---

## ধাপ ৮: API ব্যবহার করো! 🎬

### Health চেক:
```bash
curl http://তোমার-সার্ভার-IP:8000/health
```
Response:
```json
{"status": "ok", "chrome_connected": true, "session_valid": true}
```

### Session চেক (লগইন আছে কিনা):
```bash
curl -X POST http://তোমার-সার্ভার-IP:8000/session/check
```

### ভিডিও Generate:
```bash
curl -X POST http://তোমার-সার্ভার-IP:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cinematic drone shot of a futuristic city at sunset",
    "orientation": "landscape",
    "size": "small"
  }'
```
Response:
```json
{
  "task_id": "task_abc123def456",
  "status": "queued",
  "message": "ভিডিও তৈরি শুরু হয়েছে!"
}
```

> 🔥 **এই মুহূর্তে `http://server:4100`-এ গেলে দেখবে Chrome-এ Sora tab খুলেছে, prompt type হচ্ছে, Generate click হচ্ছে — সব real-time!**

### Status চেক:
```bash
curl http://তোমার-সার্ভার-IP:8000/status/task_abc123def456
```
Response:
```json
{
  "task_id": "task_abc123def456",
  "status": "running",
  "progress": 45.5,
  "message": "ভিডিও তৈরি হচ্ছে..."
}
```

### ভিডিও ডাউনলোড (status "succeeded" হলে):
```bash
curl -o my_video.mp4 http://তোমার-সার্ভার-IP:8000/download/task_abc123def456
```

### সব Task দেখো:
```bash
curl http://তোমার-সার্ভার-IP:8000/tasks
```

---

## 🔐 API Key ব্যবহার (Optional)

`.env`-এ `API_KEY=my-secret-key` সেট করলে প্রতি request-এ header দিতে হবে:

```bash
curl -X POST http://server:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-key" \
  -d '{"prompt": "A robot dancing"}'
```

---

## 🔧 ট্রাবলশুটিং

### সমস্যা: Chrome UI আসছে না (port 4100)
```bash
# Container চলছে কিনা দেখো
docker ps

# Log দেখো
docker logs sora-automation

# Firewall চেক/open
sudo ufw allow 4100
sudo ufw allow 8000
```

### সমস্যা: API response আসছে না (port 8000)
```bash
# API log দেখো
docker exec sora-automation cat /app/api.log

# Container-এ ঢুকে দেখো
docker exec -it sora-automation bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### সমস্যা: "Session নেই" error
Chrome UI-তে (`http://server:4100`) গিয়ে Sora-তে আবার লগইন করো।

### সমস্যা: ভিডিও generate হচ্ছে না
1. Chrome UI-তে দেখো কি হচ্ছে
2. Sora-এর quota/limit চেক করো
3. Screenshot দেখো: `docker exec sora-automation ls /app/videos/`

### Container restart:
```bash
docker compose restart
```

### সব মুছে শুরু করো:
```bash
docker compose down
docker compose up -d --build
```

---

## 🔄 সেশন Refresh

Sora-এর session expire হলে (সাধারণত কয়েক দিন পর):
1. `http://server:4100` যাও
2. Chrome-এ Sora-তে আবার লগইন করো
3. ব্যস! API আবার কাজ করবে

---

## 📋 Port তালিকা

| Port | কাজ | কখন ব্যবহার |
|---|---|---|
| 22 | SSH | সার্ভার manage করতে |
| 4100 | Chrome Web UI | লগইন ও monitoring |
| 8000 | FastAPI REST API | ভিডিও generate/download |

---

## 🐍 Python দিয়ে API Use (Example)

```python
import requests
import time

SERVER = "http://তোমার-সার্ভার-IP:8000"

# ১. ভিডিও Generate
response = requests.post(f"{SERVER}/generate", json={
    "prompt": "A cat playing piano in a jazz club",
    "orientation": "landscape"
})
task_id = response.json()["task_id"]
print(f"Task started: {task_id}")

# ২. Status poll
while True:
    status = requests.get(f"{SERVER}/status/{task_id}").json()
    print(f"Status: {status['status']} ({status['progress']:.1f}%)")
    
    if status["status"] == "succeeded":
        print("ভিডিও তৈরি হয়ে গেছে! ডাউনলোড করছি...")
        break
    elif status["status"] == "failed":
        print(f"Error: {status['message']}")
        break
    
    time.sleep(10)

# ৩. ভিডিও Download
video = requests.get(f"{SERVER}/download/{task_id}")
with open(f"sora_{task_id}.mp4", "wb") as f:
    f.write(video.content)
print("ভিডিও সেভ হয়ে গেছে!")
```
