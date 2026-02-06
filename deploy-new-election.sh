#!/bin/bash
# VoteChain V3 - Deploy New Election
# This script helps you deploy a new election contract via the admin dashboard

echo "🗳️  VoteChain - New Election Deployment"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Guide you through the admin dashboard"
echo "  2. Wait for contract deployment"
echo "  3. Automatically restart backend to load new contract"
echo ""
echo "📋 Prerequisites:"
echo "  ✅ Backend must be running"
echo "  ✅ Admin dashboard accessible at http://localhost:8000/admin.html"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Check if backend is running
echo ""
echo "🔍 Checking backend status..."
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Backend is running"
else
    echo "❌ Backend is not responding!"
    echo "   Start it with: ./votechain.sh start"
    exit 1
fi

# Get current contract address
echo ""
echo "📝 Current configuration:"
CURRENT_ADDR=$(grep "VOTING_CONTRACT_ADDRESS" backend/.env | cut -d'"' -f2)
echo "   Contract: $CURRENT_ADDR"
echo ""

# Open admin dashboard
echo "🌐 Opening admin dashboard..."
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open "http://localhost:8000/admin.html" > /dev/null 2>&1 &
elif command -v open > /dev/null 2>&1; then
    open "http://localhost:8000/admin.html" > /dev/null 2>&1 &
else
    echo "   Please open: http://localhost:8000/admin.html"
fi

echo ""
echo "📋 Steps to deploy new election:"
echo "   1. Click 'New Election' button in admin dashboard"
echo "   2. Wait for deployment to complete (~30 seconds)"
echo "   3. Note the new contract address"
echo ""
read -p "Have you deployed the new contract? (y/n): " DEPLOYED

if [ "$DEPLOYED" != "y" ] && [ "$DEPLOYED" != "Y" ]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

# Wait a moment for .env to be written
sleep 2

# Check if contract address changed
NEW_ADDR=$(grep "VOTING_CONTRACT_ADDRESS" backend/.env | cut -d'"' -f2)

if [ "$NEW_ADDR" == "$CURRENT_ADDR" ]; then
    echo "⚠️  Contract address unchanged!"
    echo "   Make sure deployment completed successfully"
    exit 1
fi

echo ""
echo "✅ New contract detected: $NEW_ADDR"
echo ""
echo "🔄 Restarting backend to load new contract..."

# Check if running as systemd service
AUTO_RESTART=$(grep -E '^AUTO_RESTART' backend/.env 2>/dev/null | cut -d'=' -f2 | tr -d '"')

if [ "$AUTO_RESTART" = "true" ]; then
    if systemctl is-active --quiet votechain; then
        echo "   Using systemd service (AUTO_RESTART=true)..."
        sudo systemctl restart votechain
        sleep 3

        if systemctl is-active --quiet votechain; then
            echo "✅ Backend restarted successfully"
        else
            echo "❌ Backend failed to restart!"
            echo "   Check logs: sudo journalctl -u votechain -n 50"
            exit 1
        fi
    else
        echo "⚠️  Backend not running as systemd service"
        echo "   Please restart manually:" 
        echo "   1. Stop current backend process"
        echo "   2. Run: cd backend && node server.js"
    fi
else
    echo "AUTO_RESTART not enabled; will not restart systemd. Polling backend /api/active-contract for new address..."
    # Poll the backend for the active contract (timeout 60s)
    TIMEOUT=60
    INTERVAL=2
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        NEW_ACTIVE=$(curl -s http://localhost:3000/api/active-contract | python3 -c 'import sys,json;print(json.load(sys.stdin).get("contractAddress",""))' 2>/dev/null)
        if [ "$NEW_ACTIVE" = "$NEW_ADDR" ]; then
            echo "✅ Backend now reports the new contract address as active"
            break
        fi
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    done
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo "⚠️ Backend did not report the new address within ${TIMEOUT}s. You may need to restart the backend manually or enable AUTO_RESTART=true in backend/.env"
    fi
fi

echo ""
echo "🎉 New election deployment complete!"
echo ""
echo "📊 Summary:"
echo "   Old Contract: $CURRENT_ADDR"
echo "   New Contract: $NEW_ADDR"
echo ""
echo "✅ System ready for new election!"
echo "   - Voters can now vote again"
echo "   - All fingerprints preserved"
echo "   - Backend loaded new contract"
echo ""
echo "🌐 Access Points:"
echo "   Admin: http://localhost:8000/admin.html"
echo "   Results: http://localhost:8000/index.html"
echo ""
