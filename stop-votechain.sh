#!/bin/bash
# VoteChain V3 - Stop script

echo "Stopping VoteChain services..."

# Stop backend
if [ -f /home/cainepi/votechain-backend.pid ]; then
    BACKEND_PID=$(cat /home/cainepi/votechain-backend.pid)
    kill $BACKEND_PID 2>/dev/null
    echo "Backend stopped (PID: $BACKEND_PID)"
    rm /home/cainepi/votechain-backend.pid
fi

# Stop frontend
if [ -f /home/cainepi/votechain-frontend.pid ]; then
    FRONTEND_PID=$(cat /home/cainepi/votechain-frontend.pid)
    kill $FRONTEND_PID 2>/dev/null
    echo "Frontend stopped (PID: $FRONTEND_PID)"
    rm /home/cainepi/votechain-frontend.pid
fi

# Fallback: Kill any remaining processes
pkill -f "node server.js"
pkill -f "python3 -m http.server 8000"

echo "VoteChain stopped."
