#!/bin/bash

# VoteChain V3 - One-Click Startup Script
# Run this after reboot to bring everything back online.

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SITE_DIR="/home/cainepi/Desktop/VoteChain - V3/blockchain-voting-dapp-v3"
BACKEND_DIR="$SITE_DIR/backend"
KIOSK_DIR="$SITE_DIR/kiosk"
VENV_PYTHON="$KIOSK_DIR/venv/bin/python3"

echo -e "${BLUE}🚀 Starting VoteChain V3 System...${NC}"

# 1. Start Backend
echo -e "${BLUE}[1/4] Starting Backend Server...${NC}"
cd "$BACKEND_DIR" || exit
# Kill any existing node server on port 3000 (optional, be careful)
# fuser -k 3000/tcp > /dev/null 2>&1
nohup node server.js > "$SITE_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend running (PID: $BACKEND_PID)${NC}"
sleep 3

# 2. Start Ngrok
echo -e "${BLUE}[2/4] Starting Ngrok Tunnel...${NC}"
# Kill existing ngrok
pkill ngrok > /dev/null 2>&1
nohup ngrok http --url=remunerable-rhiannon-noncleistogamous.ngrok-free.dev --config="/home/cainepi/.config/ngrok/ngrok.yml" 3000 > "$SITE_DIR/ngrok.log" 2>&1 &
NGROK_PID=$!
echo -e "${GREEN}✅ Ngrok running (PID: $NGROK_PID)${NC}"
sleep 5

# 3. Update Supabase with public URL
echo -e "${BLUE}[3/4] Updating Service Discovery...${NC}"
cd "$SITE_DIR" || exit
# We assume the hardcoded domain. If using dynamic, we'd fetch from localhost:4040
PUBLIC_URL="https://remunerable-rhiannon-noncleistogamous.ngrok-free.dev"

# Ensure env vars are loaded for the script
# Load env vars safely
set -a
if [ -f "$BACKEND_DIR/.env" ]; then
    source "$BACKEND_DIR/.env"
fi
set +a

# Run the update script
node scripts/update-backend-url.js "$PUBLIC_URL"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Service Discovery Updated: $PUBLIC_URL${NC}"
else
    echo -e "${RED}⚠️ Failed to update Service Discovery. Check logs.${NC}"
fi

# 4. Start Kiosk (Foreground)
echo -e "${BLUE}[4/4] Starting Kiosk Terminal...${NC}"
echo -e "${BLUE}PRESS CTRL+C TO STOP KIOSK AND SHUTDOWN SYSTEM${NC}"

cd "$KIOSK_DIR" || exit
sudo "$VENV_PYTHON" kiosk_main.py

# Cleanup on exit
echo -e "${BLUE}🛑 Shutting down background services...${NC}"
kill $BACKEND_PID
kill $NGROK_PID
echo -e "${GREEN}✅ System Shutdown Complete.${NC}"
