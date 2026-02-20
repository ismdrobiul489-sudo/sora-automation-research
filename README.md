# Sora Automation — Cloud REST API

Sora.com ভিডিও generation automated — US cloud server থেকে REST API দিয়ে।

> **Sora-এর কোনো official API নেই।** আমরা Playwright দিয়ে real Chrome browser control করি — একটাই container, একটাই browser, সবকিছু ভিতরে!

## Architecture

```
Docker Container (linuxserver/chromium + FastAPI)
├── Chrome (KasmVNC) → http://server:4100 (দেখতে পারবে!)
├── FastAPI API → http://server:8000
└── Playwright → CDP দিয়ে same Chrome control করে
```

## Quick Start (One-Click Setup! 🚀)

SSH দিয়ে তোমার US VPS-এ ঢুকে এই একটা কমান্ড রান করো — ব্যস!

```bash
sudo apt update && sudo apt install curl -y
bash <(curl -sL https://raw.githubusercontent.com/ismdrobiul489-sudo/sora-automation-research/main/setup.sh)
```

এটা automatically:
- ✅ Docker ইনস্টল করবে
- ✅ সব ফাইল ডাউনলোড করবে
- ✅ Container build ও চালু করবে
- ✅ Firewall সেটআপ করবে

তারপর:
1. 🌐 `http://server-ip:4100` → Chrome UI → Sora লগইন
2. 🎬 `POST http://server-ip:8000/generate` → ভিডিও বানাও!
3. ⬇️ `GET http://server-ip:8000/download/{id}` → ডাউনলোড!

### Manual Setup (Alternative)

```bash
git clone <repo> && cd sora-automation-research
cp .env.example .env && nano .env
docker compose up -d
```

## API Endpoints

| Endpoint | Method | কাজ |
|---|---|---|
| `/health` | GET | System status |
| `/generate` | POST | ভিডিও generate শুরু |
| `/status/{task_id}` | GET | Progress check |
| `/download/{task_id}` | GET | ভিডিও download |
| `/tasks` | GET | সব task তালিকা |
| `/session/check` | POST | Login session check |

## Files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI REST API |
| `app/sora_engine.py` | Playwright CDP automation |
| `app/models.py` | Pydantic models |
| `app/config.py` | Environment config |
| `Dockerfile` | linuxserver/chromium + Python + FastAPI |
| `docker-compose.yml` | Container orchestration |
| `startup.sh` | Auto-start FastAPI on boot |
| `DEPLOY_GUIDE_BN.md` | বাংলায় deployment গাইড |

## বিস্তারিত গাইড

👉 **[বাংলায় সম্পূর্ণ ডিপ্লয়মেন্ট গাইড](DEPLOY_GUIDE_BN.md)**
