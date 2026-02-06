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
if sudo systemctl is-active --quiet votechain-kiosk.service; then
    echo "   ✅ RUNNING"
else
    echo "   ⚠️  STOPPED (may need fingerprint scanner connected)"
fi
echo ""

# Service Status
echo "📊 System Services:"
sudo systemctl status votechain.service --no-pager | grep "Active:"
sudo systemctl status votechain-frontend.service --no-pager | grep "Active:"
sudo systemctl status votechain-kiosk.service --no-pager | grep "Active:"
echo ""

# Access URLs
echo "🔗 Access Points:"
echo "   Results Page: http://localhost:8000/index.html"
echo "   Admin Panel:  http://localhost:8000/admin.html"
echo "   Backend API:  http://localhost:3000"
echo ""

# Log Files
echo "📝 Recent Logs:"
echo "   Backend:"
tail -3 /home/cainepi/votechain-backend.log 2>/dev/null || echo "   No logs yet"
echo ""
echo "   Kiosk:"
tail -3 /home/cainepi/votechain-kiosk.log 2>/dev/null || echo "   No logs yet"
echo ""

echo "========================================"
echo "Run 'sudo systemctl status votechain' for details"
echo "========================================"
