#!/usr/bin/env python3
"""
VoteChain Ngrok Discovery Service
Launches a static Ngrok tunnel and maintains heartbeat with Supabase
"""

import subprocess
import time
import sys
import logging
import os
from dotenv import load_dotenv
from datetime import datetime

try:
    from supabase import create_client
    import requests
except ImportError:
    print("❌ Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)

# ============================================================================
# CONFIGURATION - LOADED FROM .ENV
# ============================================================================

# Load .env file from the current directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print(f"⚠️ Warning: .env file not found at {env_path}")
    print("Please create it from .env.example")

# Supabase project details
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Permanent Ngrok static domain
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")

# Ngrok Authtoken
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN")

# Local backend port
PORT = int(os.getenv("PORT", 3000))

# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", 30))

# ============================================================================
# SETUP & VALIDATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Validate critical environment variables
missing_vars = []
if not SUPABASE_URL: missing_vars.append("SUPABASE_URL")
if not SUPABASE_KEY: missing_vars.append("SUPABASE_KEY")
if not NGROK_DOMAIN or "YOUR-STATIC-DOMAIN" in NGROK_DOMAIN: missing_vars.append("NGROK_DOMAIN")

if missing_vars:
    logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("   Check your pi/.env file.")
    sys.exit(1)

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error(f"Failed to connect to Supabase: {e}")
    sys.exit(1)

# ============================================================================
# FUNCTIONS
# ============================================================================

def update_supabase_config(url, status="online"):
    """Update Supabase with current backend URL and status"""
    try:
        # Update backend URL
        supabase.table("system_config").upsert({
            "key": "backend_url",
            "value": url
        }).execute()
        
        # Update status
        supabase.table("system_config").upsert({
            "key": "kiosk_status",
            "value": status
        }).execute()
        
        logger.info(f"📡 Supabase updated: {url} ({status})")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase update failed: {e}")
        return False


def send_heartbeat():
    """Ping backend health endpoint and update last_seen timestamp"""
    url = f"http://localhost:{PORT}"
    
    try:
        # Ping health endpoint
        resp = requests.get(
            f"{url}/api/health",
            timeout=5,
            headers={"ngrok-skip-browser-warning": "true"}
        )
        
        if resp.status_code == 200:
            # Update last seen timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            supabase.table("system_config").upsert({
                "key": "kiosk_last_seen",
                "value": timestamp
            }).execute()
            
            logger.info(f"💚 Heartbeat OK (Backend responding)")
            return True
        else:
            logger.warning(f"⚠️ Backend returned status {resp.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.warning("⚠️ Backend health check timeout")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Heartbeat failed: {e}")
        return False


def start_ngrok_tunnel():
    """Launch Ngrok tunnel with static domain"""
    logger.info(f"🚀 Launching Ngrok tunnel: {NGROK_DOMAIN}")
    
    # Validate configuration
    if "YOUR-STATIC-DOMAIN" in NGROK_DOMAIN:
        logger.error("❌ Please update NGROK_DOMAIN in the script!")
        logger.error("   Get your free static domain from: https://dashboard.ngrok.com/cloud-edge/domains")
        sys.exit(1)
    
    # Update Supabase before starting tunnel
    url = f"https://{NGROK_DOMAIN}"
    update_supabase_config(url, "starting")
    
    try:
        # Build ngrok command
        cmd = ['ngrok', 'http', '--domain', NGROK_DOMAIN, str(PORT)]
        
        # Use authtoken from .env if provided
        if NGROK_AUTHTOKEN:
            # Insert auth token at index 2 (after 'http')
            cmd.insert(2, '--authtoken')
            cmd.insert(3, NGROK_AUTHTOKEN)
            logger.info("🔑 Using authtoken from .env")
        else:
            logger.info("ℹ️ No authtoken found in .env, using system-wide config if available")
            
        subprocess.run(cmd, check=True)
        
    except FileNotFoundError:
        logger.error("❌ Ngrok not found! Install it from: https://ngrok.com/download")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ngrok failed: {e}")
        raise
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping tunnel...")
        update_supabase_config(url, "offline")
        sys.exit(0)


def heartbeat_loop():
    """Background heartbeat loop (runs in separate thread if needed)"""
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        send_heartbeat()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point with auto-restart on failure"""
    logger.info("=" * 60)
    logger.info("VoteChain Ngrok Discovery Service")
    logger.info("=" * 60)
    logger.info(f"Static Domain: {NGROK_DOMAIN}")
    logger.info(f"Local Port: {PORT}")
    logger.info(f"Heartbeat Interval: {HEARTBEAT_INTERVAL}s")
    logger.info("=" * 60)
    
    # Initial heartbeat to verify backend is running
    logger.info("Waiting 5 seconds for backend to start...")
    time.sleep(5)
    
    attempt = 0
    max_attempts = 3
    
    while attempt < max_attempts:
        attempt += 1
        logger.info(f"Heartbeat check (attempt {attempt}/{max_attempts})...")
        
        if send_heartbeat():
            logger.info("✅ Backend is healthy, starting tunnel...")
            break
        else:
            if attempt < max_attempts:
                logger.warning(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error("❌ Backend not responding. Is it running on port 3000?")
                logger.error("   Start it with: cd backend && npm start")
                sys.exit(1)
    
    # Start tunnel (this blocks until stopped)
    while True:
        try:
            start_ngrok_tunnel()
        except Exception as e:
            logger.error(f"Tunnel crashed: {e}")
            logger.info("Restarting in 5 seconds...")
            update_supabase_config(f"https://{NGROK_DOMAIN}", "reconnecting")
            time.sleep(5)


if __name__ == "__main__":
    main()
