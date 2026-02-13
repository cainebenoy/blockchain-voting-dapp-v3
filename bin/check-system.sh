#!/bin/bash
# VoteChain V3 - System Status Check

echo "========================================"
echo "    VOTECHAIN V3 SYSTEM STATUS"
echo "========================================"
echo ""

# Check Backend
echo "🔧 Backend Server (Port 3000):"
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "   ✅ ONLINE"
else
    echo "   ❌ OFFLINE"
fi
echo ""

# Check Frontend
echo "🌐 Frontend Server (Port 8000):"
if curl -s http://localhost:8000/index.html > /dev/null 2>&1; then
    echo "   ✅ ONLINE"
else
    echo "   ❌ OFFLINE"
fi
echo ""

# Check Kiosk
echo "🖥️  Kiosk Terminal:"
if systemctl is-active --quiet votechain-kiosk.service; then
    echo "   ✅ RUNNING"
else
    echo "   ❌ STOPPED (Check journalctl -u votechain-kiosk)"
fi
echo ""

# Check Tunnel
echo "🔒 Cloudflare Tunnel:"
if systemctl is-active --quiet votechain-tunnel.service; then
    echo "   ✅ ACTIVE"
else
    echo "   ⚠️  INACTIVE (Remote access disabled)"
fi
echo ""

# Service Status
echo "📊 System Services:"
for svc in votechain-backend votechain-tunnel votechain-kiosk; do
    printf "   %-20s " "$svc:"
    systemctl is-active --quiet "$svc" && echo "✅" || echo "❌"
done
echo ""

# Hardware Diagnostics
echo "🌡️  Hardware Telemetry:"
if command -v vcgencmd >/dev/null; then
    echo "   CPU Temp: $(vcgencmd measure_temp | cut -d "=" -f2)"
else
    echo "   CPU Temp: EMULATION (No vcgencmd)"
fi
echo "   Uptime:   $(uptime -p)"
echo ""

# Access URLs
echo "🔗 Access Points:"
echo "   Results Page: http://localhost:8000/index.html"
echo "   Admin Panel:  http://localhost:8000/admin.html"
echo "   Backend API:  http://localhost:3000"
echo ""

# Log Files
echo "📝 Recent Journal Logs (Journald):"
echo "   Backend: $(sudo journalctl -u votechain-backend --no-pager -n 3 | tail -n 1)"
echo "   Kiosk:   $(sudo journalctl -u votechain-kiosk --no-pager -n 3 | tail -n 1)"
echo ""

echo "========================================"
echo "Run 'sudo systemctl status votechain' for details"
echo "========================================"
