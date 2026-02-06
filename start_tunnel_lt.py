#!/usr/bin/env python3
"""
VoteChain V3 - Localtunnel Manager with Service Discovery

This script:
1. Starts a Localtunnel (loca.lt) for the backend
2. Extracts the public URL from tunnel logs
3. Updates Supabase system_config table with the new URL
4. Keeps tunnel alive and monitors for failures

Usage:
    python3 start_tunnel_lt.py
"""

import subprocess
import re
import time
import os
import sys
import signal
import threading

# Load environment variables from backend/.env
def load_env_file(filepath):
    """Load environment variables from .env file"""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip('"').strip("'")
                    os.environ[key] = value

# Load from backend/.env if exists
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, 'backend', '.env')
load_env_file(env_path)

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ ERROR: supabase library not installed")
    sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Missing Supabase credentials")
    sys.exit(1)

BACKEND_PORT = "3000"

# ============================================================
# GLOBAL STATE
# ============================================================
tunnel_process = None
supabase_client = None
current_url = None

def signal_handler(sig, frame):
    print("\n\n🛑 Shutdown signal received...")
    cleanup()
    sys.exit(0)

def cleanup():
    global tunnel_process
    if tunnel_process:
        print("🔒 Stopping tunnel...")
        tunnel_process.terminate()
        try:
            tunnel_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            tunnel_process.kill()

def init_supabase():
    global supabase_client
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to init Supabase: {e}")
        return False

def update_supabase_url(url):
    global supabase_client
    if not supabase_client:
        if not init_supabase():
            return

    try:
        print(f"💾 Updating Supabase with: {url}")
        data = supabase_client.table("system_config").upsert({
            "key": "backend_url",
            "value": url,
            "updated_at": "now()"
        }).execute()
        print("✅ Database sync complete!")
    except Exception as e:
        print(f"❌ Failed to update Supabase: {e}")

def start_tunnel():
    global tunnel_process, current_url
    
    print(f"🚀 Starting Localtunnel for port {BACKEND_PORT}")
    
    # Use npx localtunnel or local path
    cmd = ["npx", "localtunnel", "--port", BACKEND_PORT]
    
    # Start process
    tunnel_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # Read stdout for URL
    while True:
        line = tunnel_process.stdout.readline()
        if not line:
            break
        
        line = line.strip()
        print(f"[TUNNEL] {line}")
        
        # Check for URL
        # Output format: "your url is: https://..."
        match = re.search(r'your url is: (https://[a-zA-Z0-9-]+\.loca\.lt)', line)
        if match:
            url = match.group(1)
            print(f"\n✅ TUNNEL URL FOUND: {url}")
            current_url = url
            update_supabase_url(url)
            print("🔒 Tunnel is active. Monitoring for failures...")

    # If we get here, process ended
    print("⚠️ Tunnel process ended unexpectedly")
    return

def monitor_tunnel():
    while True:
        if tunnel_process and tunnel_process.poll() is not None:
            print("⚠️ Tunnel died! Restarting in 5 seconds...")
            cleanup()
            time.sleep(5)
            start_tunnel()
        time.sleep(5)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*60)
    print("VoteChain V3 - Localtunnel Manager")
    print("="*60)
    
    init_supabase()
    
    # Start tunnel in a separate thread to allow monitoring
    # Actually, start_tunnel blocks on readline, so we can just run it.
    # But we want to restart if it crashes.
    
    while True:
        try:
            start_tunnel()
        except Exception as e:
            print(f"💥 Error in tunnel loop: {e}")
        
        print("⚠️ Retrying in 5 seconds...")
        time.sleep(5)
