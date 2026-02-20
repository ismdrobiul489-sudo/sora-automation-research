#!/bin/bash
# =========================================================
# Sora Automation — One-Click Setup Script
# 
# This script sets up everything automatically:
# - Docker installation
# - Sora Automation container build & launch
# - Firewall configuration
# - FastAPI REST API
#
# Usage:
#   bash <(curl -sL https://raw.githubusercontent.com/ismdrobiul489-sudo/sora-automation-research/main/setup.sh)
# =========================================================

set -e

# === Colors ===
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m"

# === Banner ===
echo -e "${CYAN}"
cat << 'BANNER'
 ____                       _         _                        _   _             
/ ___|  ___  _ __ __ _     / \  _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __  
\___ \ / _ \| '__/ _` |   / _ \| | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \ 
 ___) | (_) | | | (_| |  / ___ \ |_| | || (_) | | | | | | (_| | |_| | (_) | | | |
|____/ \___/|_|  \__,_| /_/   \_\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|

      Video Generation — Cloud Automation Setup
      FastAPI REST API + Playwright + Chrome (KasmVNC)
BANNER
echo -e "${NC}"

# === Step 1: System Dependencies ===
echo -e "${GREEN}[1/9] Installing system dependencies...${NC}"
sudo apt-get update && sudo apt-get install -y \
    curl wget git ufw ca-certificates gnupg lsb-release

# === Step 2: Credentials ===
echo ""
echo -e "${CYAN}====================================================${NC}"
echo -e "${BOLD}[2/9] Set Chrome Web UI Login Credentials${NC}"
echo -e "${YELLOW}(Use this username/password to login at http://server:4100)${NC}"
echo -e "${CYAN}====================================================${NC}"
read -p "Username [default: admin]: " CHROME_USER
CHROME_USER=${CHROME_USER:-admin}
read -s -p "Password: " CHROME_PASSWORD
echo ""

if [ -z "$CHROME_PASSWORD" ]; then
    echo -e "${RED}Error: Password is required!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}(Optional) Set an API Security Key (Press Enter to skip):${NC}"
read -p "API Key [optional]: " API_KEY
API_KEY=${API_KEY:-}

# === Step 3: Docker Installation ===
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}[3/9] Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | bash
    sudo systemctl start docker
    sudo systemctl enable docker
else
    echo -e "${YELLOW}[3/9] Docker already installed. Skipping.${NC}"
fi

# === Step 4: Docker Compose Check ===
if ! docker compose version &> /dev/null 2>&1; then
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${GREEN}[4/9] Installing Docker Compose...${NC}"
        COMPOSE_VERSION="v2.24.7"
        sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
else
    echo -e "${YELLOW}[4/9] Docker Compose already installed. Skipping.${NC}"
fi

# === Step 5: Project Directory ===
echo -e "${GREEN}[5/9] Creating project directory...${NC}"
PROJECT_DIR="$HOME/sora-automation"
mkdir -p "$PROJECT_DIR"/{data,videos,app}
cd "$PROJECT_DIR"

# === Step 6: Download Project Files from GitHub ===
echo -e "${GREEN}[6/9] Downloading project files from GitHub...${NC}"

REPO_RAW="https://raw.githubusercontent.com/ismdrobiul489-sudo/sora-automation-research/main"

# Download app files
curl -sL "$REPO_RAW/app/__init__.py"      -o app/__init__.py
curl -sL "$REPO_RAW/app/config.py"        -o app/config.py
curl -sL "$REPO_RAW/app/models.py"        -o app/models.py
curl -sL "$REPO_RAW/app/sora_engine.py"   -o app/sora_engine.py
curl -sL "$REPO_RAW/app/main.py"          -o app/main.py

# Download Docker & config files
curl -sL "$REPO_RAW/requirements.txt"     -o requirements.txt
curl -sL "$REPO_RAW/Dockerfile"           -o Dockerfile
curl -sL "$REPO_RAW/startup.sh"           -o startup.sh
chmod +x startup.sh

echo -e "${YELLOW}   All files downloaded successfully${NC}"

# === Step 7: Generate .env & docker-compose.yml ===
echo -e "${GREEN}[7/9] Generating configuration files...${NC}"

# .env file
cat > .env << ENVEOF
CHROME_USER=${CHROME_USER}
CHROME_PASSWORD=${CHROME_PASSWORD}
API_KEY=${API_KEY}
ENVEOF

# docker-compose.yml
cat > docker-compose.yml << 'COMPOSEEOF'
services:
  sora:
    build: .
    container_name: sora-automation
    security_opt:
      - seccomp:unconfined
    ports:
      - "4100:3000"
      - "4101:3001"
      - "8000:8000"
    volumes:
      - ./data:/config
      - ./videos:/app/videos
    environment:
      - CUSTOM_USER=${CHROME_USER:-admin}
      - PASSWORD=${CHROME_PASSWORD:-changeme}
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - CHROME_CLI=--remote-debugging-port=9222 --remote-debugging-address=0.0.0.0
      - API_KEY=${API_KEY:-}
    shm_size: "2gb"
    restart: unless-stopped
COMPOSEEOF

echo -e "${YELLOW}   .env and docker-compose.yml generated${NC}"

# === Step 8: Build & Start Container ===
echo -e "${GREEN}[8/9] Building Docker image and starting container...${NC}"
echo -e "${YELLOW}   (This may take a few minutes on first run — downloading image + building)${NC}"
sudo docker compose up -d --build

# === Step 9: Firewall Setup ===
echo -e "${GREEN}[9/9] Configuring firewall...${NC}"
if ! command -v ufw &> /dev/null; then
    sudo apt-get install -y ufw
fi

sudo ufw allow 22/tcp      # SSH
sudo ufw allow 4100/tcp    # Chrome Web UI
sudo ufw allow 4101/tcp    # HTTPS VNC
sudo ufw allow 8000/tcp    # FastAPI API
sudo ufw --force enable

echo -e "${YELLOW}   Ports 22, 4100, 4101, 8000 opened${NC}"

# === Get Public IP ===
VPS_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

# === DONE! ===
echo ""
echo -e "${CYAN}========================================================================${NC}"
echo -e "${GREEN}${BOLD}"
cat << 'DONE'

  Sora Automation setup completed successfully!

DONE
echo -e "${NC}"
echo -e "${CYAN}========================================================================${NC}"
echo ""
echo -e "${BOLD}Your Links:${NC}"
echo ""
echo -e "   Chrome Web UI:   ${GREEN}http://${VPS_IP}:4100${NC}"
echo -e "   REST API:        ${GREEN}http://${VPS_IP}:8000${NC}"
echo -e "   API Docs:        ${GREEN}http://${VPS_IP}:8000/docs${NC}"
echo ""
echo -e "${CYAN}========================================================================${NC}"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo ""
echo -e "   ${YELLOW}Step 1:${NC} Open browser -> ${GREEN}http://${VPS_IP}:4100${NC}"
echo -e "         Username: ${CYAN}${CHROME_USER}${NC} / Password: ${CYAN}(the one you set)${NC}"
echo ""
echo -e "   ${YELLOW}Step 2:${NC} In Chrome, go to ${GREEN}https://sora.com${NC} -> Login to your account"
echo ""
echo -e "   ${YELLOW}Step 3:${NC} Generate a video!"
echo -e "         ${CYAN}curl -X POST http://${VPS_IP}:8000/generate \\${NC}"
echo -e "         ${CYAN}  -H 'Content-Type: application/json' \\${NC}"
echo -e "         ${CYAN}  -d '{\"prompt\": \"A cat playing piano\", \"orientation\": \"landscape\"}'${NC}"
echo ""
echo -e "   ${YELLOW}Step 4:${NC} Check status -> ${CYAN}curl http://${VPS_IP}:8000/status/{task_id}${NC}"
echo ""
echo -e "   ${YELLOW}Step 5:${NC} Download video -> ${CYAN}curl -o video.mp4 http://${VPS_IP}:8000/download/{task_id}${NC}"
echo ""
echo -e "${CYAN}========================================================================${NC}"
echo ""
echo -e "${YELLOW}Project folder: ${PROJECT_DIR}${NC}"
echo -e "${YELLOW}Videos folder:  ${PROJECT_DIR}/videos${NC}"
echo -e "${YELLOW}Chrome login:   ${CHROME_USER} / (your password)${NC}"
if [ -n "$API_KEY" ]; then
    echo -e "${YELLOW}API Key:        Set (use header: X-API-Key)${NC}"
fi
echo ""
echo -e "${GREEN}All done! Login to Sora via Chrome UI, then use the API to generate videos!${NC}"
echo ""
