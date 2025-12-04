#!/usr/bin/env python3
"""
VoteChain V3 - Cloudflare Tunnel Manager with Service Discovery

This script:
1. Starts a Cloudflare Tunnel (trycloudflare.com) for the backend
2. Extracts the public URL from tunnel logs
3. Updates Supabase system_config table with the new URL
4. Keeps tunnel alive and monitors for failures

Usage:
    python3 start_tunnel.py

Requirements:
    - cloudflared binary installed
    - supabase-py library: pip3 install supabase
    - Backend running on localhost:3000
"""

import subprocess
import re
import time
import os
import sys
import signal

# Load environment variables from backend/.env
def load_env_file(filepath):
    """Load environment variables from .env file"""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
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
    print("   Run: pip3 install supabase --break-system-packages")
    sys.exit(1)

# ============================================================
# CONFIGURATION - Loaded from backend/.env
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Service role key from .env

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Missing Supabase credentials")
    print(f"   Checked: {env_path}")
    print("   Required: SUPABASE_URL and SUPABASE_KEY")
    sys.exit(1)

# Backend configuration
BACKEND_HOST = "localhost"
BACKEND_PORT = "3000"

# Tunnel configuration
TUNNEL_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# ============================================================
# GLOBAL STATE
# ============================================================
tunnel_process = None
supabase_client = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Shutdown signal received...")
    cleanup()
    sys.exit(0)

def cleanup():
    """Clean up tunnel process"""
    global tunnel_process
    if tunnel_process:
        print("🔒 Stopping tunnel...")
        tunnel_process.terminate()
        try:
            tunnel_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            tunnel_process.kill()

def init_supabase():
    """Initialize Supabase client"""
    global supabase_client
    
    if SUPABASE_URL == "YOUR_SUPABASE_URL" or SUPABASE_KEY == "YOUR_SUPABASE_SERVICE_ROLE_KEY":
        print("❌ ERROR: Please configure SUPABASE_URL and SUPABASE_KEY")
        print("   Edit this script or set environment variables:")
        print("   export SUPABASE_URL='https://your-project.supabase.co'")
        print("   export SUPABASE_KEY='your-service-role-key'")
        sys.exit(1)
    
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized")
        return True
    except Exception as e:
        print(f"❌ Supabase initialization error: {e}")
        return False

def update_backend_url(new_url):
    """Update the backend URL in Supabase"""
    print(f"💾 Updating Supabase with: {new_url}")
    
    try:
        response = supabase_client.table('system_config')\
            .update({'value': new_url})\
            .eq('key', 'backend_url')\
            .execute()
        
        print("✅ Database sync complete!")
        print(f"   Updated at: {response.data[0]['updated_at'] if response.data else 'now'}")
        return True
    except Exception as e:
        print(f"❌ Database update failed: {e}")
        return False

def extract_tunnel_url(process):
    """
    Monitor tunnel process output and extract public URL
    Returns: URL string or None
    """
    print("⏳ Waiting for Cloudflare tunnel URL...")
    
    # Regex pattern for trycloudflare.com URLs
    url_pattern = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    
    start_time = time.time()
    timeout = 30  # 30 second timeout
    
    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            print("❌ Timeout: No URL found in 30 seconds")
            return None
        
        # Check if process died
        if process.poll() is not None:
            print(f"❌ Tunnel process exited with code: {process.returncode}")
            return None
        
        try:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            line = line.strip()
            
            # Print log for debugging (comment out in production)
            if line:
                print(f"[TUNNEL] {line}")
            
            # Search for URL
            match = url_pattern.search(line)
            if match:
                url = match.group(0)
                print(f"\n✅ TUNNEL URL FOUND: {url}")
                return url
                
        except Exception as e:
            print(f"⚠️ Error reading tunnel output: {e}")
            time.sleep(0.1)

def start_tunnel():
    """
    Start Cloudflare tunnel and return the public URL
    Returns: (process, url) tuple or (None, None) on failure
    """
    global tunnel_process
    
    print(f"🚀 Starting Cloudflare Tunnel for {TUNNEL_URL}")
    print(f"   (Make sure backend is running on port {BACKEND_PORT})")
    
    try:
        # Start cloudflared process
        tunnel_process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", TUNNEL_URL],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Extract URL from output
        public_url = extract_tunnel_url(tunnel_process)
        
        if public_url:
            return tunnel_process, public_url
        else:
            cleanup()
            return None, None
            
    except FileNotFoundError:
        print("❌ ERROR: cloudflared not found")
        print("   Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
        return None, None
    except Exception as e:
        print(f"❌ Failed to start tunnel: {e}")
        cleanup()
        return None, None

def monitor_tunnel(process):
    """Keep tunnel alive and monitor for crashes"""
    print("🔒 Tunnel is active. Monitoring for failures...")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            # Check if process is still running
            if process.poll() is not None:
                print(f"\n⚠️ Tunnel died with exit code: {process.returncode}")
                return False
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
        return True

def main():
    """Main execution loop with auto-restart"""
    global tunnel_process
    
    print("=" * 60)
    print("VoteChain V3 - Tunnel Manager with Service Discovery")
    print("=" * 60)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize Supabase
    if not init_supabase():
        sys.exit(1)
    
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            # Start tunnel
            process, public_url = start_tunnel()
            
            if not process or not public_url:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"❌ Failed after {max_retries} attempts. Giving up.")
                    sys.exit(1)
                
                print(f"⚠️ Retrying in 10 seconds... (Attempt {retry_count}/{max_retries})")
                time.sleep(10)
                continue
            
            # Reset retry counter on success
            retry_count = 0
            
            # Update Supabase
            if not update_backend_url(public_url):
                print("⚠️ Warning: Failed to update database, but tunnel is active")
            
            # Monitor tunnel
            clean_exit = monitor_tunnel(process)
            
            if clean_exit:
                # User stopped it
                cleanup()
                print("👋 Tunnel manager stopped cleanly")
                break
            else:
                # Tunnel crashed, restart
                print("🔄 Restarting tunnel in 5 seconds...")
                cleanup()
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            cleanup()
            print("🔄 Restarting in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    main()
