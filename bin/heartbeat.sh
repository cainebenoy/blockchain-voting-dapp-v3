#!/bin/bash
# VoteChain V3 - Kiosk Heartbeat & Telemetry Script
# Reports system health to a log file (for journald) or backend API

# Load configuration if exists
[ -f /etc/votechain/backend.env ] && source /etc/votechain/backend.env

LOG_FILE="/var/log/votechain_heartbeat.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 1. Gather Telemetry
CPU_TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d "=" -f2 || echo "N/A")
UPTIME=$(uptime -p)
LOAD=$(cat /proc/loadavg | awk '{print $1" "$2" "$3}')
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}')
MEM_FREE=$(free -m | awk 'NR==2 {print $4"MB"}')

# 2. Check Service Status
BACKEND_ALIVE=$(curl -s --connect-timeout 2 http://localhost:3000/api/health > /dev/null && echo "YES" || echo "NO")
TUNNEL_ALIVE=$(pgrep cloudflared > /dev/null && echo "YES" || echo "NO")

# 3. Format Output for Journald
echo "------------------------------------------------"
echo "VoteChain Heartbeat: $TIMESTAMP"
echo "CPU Temp: $CPU_TEMP | Uptime: $UPTIME"
echo "Load: $LOAD | Mem Free: $MEM_FREE | Disk: $DISK_USAGE"
echo "Backend Active: $BACKEND_ALIVE | Tunnel Active: $TUNNEL_ALIVE"
echo "------------------------------------------------"

# 4. Optional: Post to Backend Metrics (if backend is alive)
if [ "$BACKEND_ALIVE" == "YES" ]; then
    # Payload for future centralized monitoring
    # curl -s -X POST -H "Content-Type: application/json" \
    #      -d "{\"temp\":\"$CPU_TEMP\", \"load\":\"$LOAD\", \"disk\":\"$DISK_USAGE\"}" \
    #      http://localhost:3000/api/kiosk/heartbeat > /dev/null
    :
fi
