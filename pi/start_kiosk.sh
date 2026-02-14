#!/bin/bash
# VoteChain Kiosk Startup Script
# This script starts both the backend server and Ngrok tunnel

set -e  # Exit on error

echo "=========================================="
echo "VoteChain Kiosk Startup"
echo "=========================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if backend dependencies are installed
if [ ! -d "backend/node_modules" ]; then
    echo "📦 Installing backend dependencies..."
    cd backend
    npm install
    cd ..
fi

# Check if Python dependencies are installed
if ! python3 -c "import supabase" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r pi/requirements.txt
fi

# Start backend in background
echo "🚀 Starting backend server..."
cd backend
node server.js &
BACKEND_PID=$!
cd ..

echo "✅ Backend started (PID: $BACKEND_PID)"
echo "⏳ Waiting 5 seconds for backend to initialize..."
sleep 5

# Start Ngrok tunnel (this will block)
echo "🌐 Starting Ngrok tunnel..."
python3 pi/ngrok_discovery.py

# If we get here, tunnel was stopped
echo "🛑 Tunnel stopped, shutting down backend..."
kill $BACKEND_PID 2>/dev/null || true

echo "✅ Kiosk shutdown complete"
