#!/bin/bash
# VoteChain V3 - Auto-start script for Raspberry Pi

# Wait for network to be ready
sleep 10

# Navigate to project directory
cd /home/cainepi/Desktop/FInal\ Year\ Project/blockchain-voting-dapp-v3

# Start Backend Server (Port 3000)
echo "Starting Backend Server..."
cd backend
node server.js > /home/cainepi/votechain-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
cd ..

# Wait for backend to initialize
sleep 3

# Start Frontend Server (Port 8000)
echo "Starting Frontend Server..."
python3 -m http.server 8000 > /home/cainepi/votechain-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Save PIDs for later reference
echo $BACKEND_PID > /home/cainepi/votechain-backend.pid
echo $FRONTEND_PID > /home/cainepi/votechain-frontend.pid

echo "VoteChain V3 is now running!"
echo "- Admin Dashboard: http://localhost:8000/admin.html"
echo "- Results Page: http://localhost:8000/index.html"
echo "- Backend API: http://localhost:3000"
echo ""
echo "Logs:"
echo "- Backend: /home/cainepi/votechain-backend.log"
echo "- Frontend: /home/cainepi/votechain-frontend.log"
