#!/usr/bin/env python3
"""
VoteChain V3 Kiosk - Main Entry Point
Biometric voting terminal with fingerprint authentication
"""

import time
import sys
import threading
import requests
import uuid
import socket
from hardware import hardware

# --- CONFIGURATION ---
import os
import logging
from dotenv import load_dotenv
from requests.exceptions import RequestException

# Load environment variables
load_dotenv()

# Configure Logging (Hardened)
log_path = '/var/log/votechain_kiosk.log'
if not os.access('/var/log', os.W_OK) if os.path.exists('/var/log/..') else False:
    # Fallback to local dir if /var/log is not writable (e.g. running without sudo or on Windows)
    log_path = 'kiosk.log'

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def discover_backend():
    """Discover backend URL via Supabase (Service Discovery)"""
    global BACKEND_URL
    logging.info("Attempting service discovery...")
    
    # Retry up to 3 times
    for attempt in range(1, 4):
        try:
            url = f"{SUPABASE_URL}/rest/v1/system_config?key=eq.backend_url&select=value"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and data[0].get('value'):
                    BACKEND_URL = data[0]['value']
                    logging.info(f"Discovered backend: {BACKEND_URL}")
                    return True
        except Exception as e:
            logging.error(f"Discovery attempt {attempt} failed: {e}")
            time.sleep(2)
    return False

def get_friendly_error(e):
    """Map technical exceptions to user-friendly messages"""
    if "timeout" in str(e).lower():
        return "Network Busy", "Please Wait..."
    if "connection" in str(e).lower():
        return "Server Offline", "Contact Admin"
    return "System Error", "Try Later"

# Session State
SESSION_TOKEN = None
KIOSK_ID = f"KIOSK-{socket.gethostname()}"
KIOSK_STATUS = "BOOTING"
START_TIME = time.time()

def cleanup():
    """Graceful shutdown handler"""
    logging.info("Kiosk shutting down...")
    hardware.set_leds(False, False)
    hardware.show_msg("VOTECHAIN", "Offline", "System Shutdown")
    hardware.cleanup()

atexit.register(cleanup)

# --- HELPER FUNCTIONS ---

def check_backend_connection():
    try:
        requests.get(f"{BACKEND_URL}/api/health", timeout=2)
        return True
    except:
        return False

def check_in_voter(aadhaar_id):
    global SESSION_TOKEN
    hardware.show_msg("Checking DB...", aadhaar_id)
    try:
        response = requests.post(f"{BACKEND_URL}/api/voter/check-in", 
                                 json={"aadhaar_id": aadhaar_id}, timeout=5)
        if response.status_code == 200:
            data = response.json().get('data', {})
            SESSION_TOKEN = data.get('session_token')
            return data
        else:
            hardware.show_msg("Check-in Failed", "Not Found/Voted", "Press START")
            hardware.beep(count=1, duration=0.5)
            wait_for_reset()
            return None
    except Exception as e:
        logging.error(f"Check-in network error: {e}")
        line1, line2 = get_friendly_error(e)
        hardware.show_msg(line1, line2, "Press START")
        wait_for_reset()
        return None

def submit_vote(aadhaar_id, candidate_id):
    hardware.show_msg("Submitting...", "Waiting Confirmation", "May take 90s")
    hardware.set_leds(green=True, red=True)

    # Spinner thread
    stop_event = threading.Event()
    def spinner():
        frames = ['|','/','-','\\']
        idx = 0
        while not stop_event.is_set():
            hardware.show_msg("Submitting...", frames[idx % 4], "Please Wait")
            idx += 1
            time.sleep(0.2)
    
    t = threading.Thread(target=spinner, daemon=True)
    t.start()

    # Generate unique transaction nonce (P0 Security)
    kiosk_nonce = str(uuid.uuid4())

    try:
        response = requests.post(f"{BACKEND_URL}/api/vote", 
                                 json={
                                     "aadhaar_id": aadhaar_id, 
                                     "candidate_id": candidate_id,
                                     "session_token": SESSION_TOKEN,
                                     "kiosk_nonce": kiosk_nonce
                                 }, timeout=90)
        stop_event.set()
        t.join()

        if response.status_code == 200:
            data = response.json().get('data', {})
            tx_hash = data.get('transaction_hash')
            short_code = data.get('receipt_code')

            hardware.show_msg("Vote Confirmed!", "Recording...", "", big_text=True)
            hardware.set_leds(green=True, red=False)
            hardware.beep(2, 0.1)

            if short_code:
                # Instant Success Screen (Like Simulator)
                hardware.show_msg("VOTE RECORDED", "Receipt Code:", short_code, big_text=False)
                # Let them see it, but they can press START to clear and leave
                logging.info(f"Vote confirmed instantly. Code: {short_code}")
                # Wait for dismissal or 10s auto-clear
                start_dismiss = time.time()
                while time.time() - start_dismiss < 10:
                    if hardware.is_button_pressed('START'): break
                    time.sleep(0.1)
            else:
                # Receipt was slow/failed in DB, poll as fallback
                hardware.show_msg("Confirmed!", "Getting Code...", "")
                poll_receipt(tx_hash)

        else:
            hardware.show_msg("Vote Failed", "Error", "Press START")
            hardware.set_leds(green=False, red=True)
            # ERROR BUZZER PATTERN: 3 long pulses
            hardware.beep(3, 0.5)
            time.sleep(15) # Auto-clear

    except Exception as e:
        stop_event.set()
        if t.is_alive(): t.join()
        logging.error(f"Vote submission error: {e}")
        line1, line2 = get_friendly_error(e)
        hardware.show_msg(line1, line2, "Check Receipt Later")
        time.sleep(15) # Auto-clear

def show_receipt(code):
    hardware.show_msg("Vote Recorded", "Receipt Code:", code, big_text=False)
    # This is now only used by the poll_receipt fallback
    time.sleep(5) 

def poll_receipt(tx_hash):
    for _ in range(30):
        try:
            res = requests.post(f"{BACKEND_URL}/api/lookup-receipt", json={"tx_hash": tx_hash}, timeout=2)
            if res.status_code == 200:
                show_receipt(res.json().get('code'))
                return
        except:
            pass
        time.sleep(1)
    hardware.show_msg("Vote Recorded", "No Receipt Code", "")
    time.sleep(5)

def wait_for_reset():
    while not hardware.is_button_pressed('START'):
        time.sleep(0.1)

def enroll_finger(id):
    hardware.show_msg("ENROLL MODE", f"ID #{id}", "Place Finger...")
    hardware.set_leds(green=True, red=True)
    
    # 1. First Scan
    while True:
        if hardware.is_button_pressed('START'): return False
        img = hardware.get_finger_image()
        if img == 0: # OK
            break
        if img == 1: # NOFINGER
            pass
        elif img == 2: # FAIL
            return False
            
    if hardware.image_2_tz(1) != 0: return False
    
    hardware.show_msg("Remove Finger", "...", "...")
    hardware.beep(1)
    time.sleep(2)
    hardware.wait_for_finger_release()
    
    # 2. Second Scan
    hardware.show_msg("Place Again", "Verify...", "")
    while True:
        if hardware.is_button_pressed('START'): return False
        img = hardware.get_finger_image()
        if img == 0: break
    
    if hardware.image_2_tz(2) != 0: return False
    
    if hardware.create_model() != 0: return False
    if hardware.store_model(id) != 0: return False
    
    return True

POLL_INTERVAL = 1
MAX_POLL_INTERVAL = 16

def poll_admin_commands():
    global POLL_INTERVAL, KIOSK_STATUS
    
    # Prepare Telemetry
    telemetry = {
        "kiosk_id": KIOSK_ID,
        "status": KIOSK_STATUS,
        "uptime": int(time.time() - START_TIME),
        "version": "3.2"
    }

    try:
        # POST heartbeat with telemetry
        res = requests.post(f"{BACKEND_URL}/api/kiosk/poll-commands", 
                             json=telemetry, timeout=2)
        
        if res.status_code == 200:
            POLL_INTERVAL = 1 # Reset on success
            data = res.json()
            if data.get('command') == 'ENROLL':
                voter_name = data.get('name')
                target_id = data.get('target_finger_id')
                
                hardware.show_msg("Enrollment", f"Voter: {voter_name}", "ID: " + str(target_id))
                hardware.beep(3)
                time.sleep(2)
                
                success = enroll_finger(target_id)
                
                # Report back
                try:
                    requests.post(f"{BACKEND_URL}/api/kiosk/enrollment-complete", 
                                  json={"success": success, "fingerprint_id": target_id},
                                  timeout=5)
                except Exception as e:
                    logging.error(f"Failed to report enrollment: {e}")
                
                if success:
                    hardware.show_msg("Enrollment", "SUCCESS", "")
                else:
                    hardware.show_msg("Enrollment", "FAILED", "")
                time.sleep(2)
        else:
            # Slower backoff for missing commands, but capped for UX
            POLL_INTERVAL = min(POLL_INTERVAL + 1, 5) 

    except Exception as e:
        POLL_INTERVAL = min(POLL_INTERVAL + 1, 5)

# --- INPUT HANDLING (NON-BLOCKING) ---
INPUT_BUFFER = ""
INPUT_READY = False

def keyboard_listener():
    """Background thread to capture keyboard input without blocking main loop"""
    global INPUT_BUFFER, INPUT_READY
    while True:
        try:
            char = sys.stdin.read(1)
            if char == '\n':
                INPUT_READY = True
            elif char:
                INPUT_BUFFER += char
        except EOFError:
            break

def get_input_non_blocking():
    global INPUT_BUFFER, INPUT_READY
    if INPUT_READY:
        val = INPUT_BUFFER.strip()
        INPUT_BUFFER = ""
        INPUT_READY = False
        return val
    return None

def fetch_active_candidates():
    """Retrieve candidate list and election status from blockchain via backend"""
    try:
        res = requests.get(f"{BACKEND_URL}/api/results", headers={'ngrok-skip-browser-warning': 'true'}, timeout=5)
        if res.status_code == 200:
            data = res.json().get('data', {})
            return data.get('candidates', []), data.get('electionActive', False)
    except Exception as e:
        logging.error(f"Failed to fetch candidates: {e}")
    return [], False

def validate_aadhaar(val):
    """Local format check for Aadhaar (12 digits)"""
    if not val: return False
    # Remove spaces/hyphens
    clean = val.replace(" ", "").replace("-", "")
    return clean.isdigit() and len(clean) == 12

# --- MAIN LOOP ---

def main():
    print("🚀 Kiosk Started")
    hardware.show_msg("Booting...", "VoteChain V3", "")
    time.sleep(1)
    
    # Start keyboard listener
    kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
    kb_thread.start()

    # Health Check
    hardware.set_leds(green=True, red=True)
    time.sleep(0.5)
    hardware.set_leds(False, False)

    candidates = []
    election_active = False

    while True:
        KIOSK_STATUS = "IDLE"
        # 1. Background State Sync
        if not check_backend_connection():
            KIOSK_STATUS = "SEARCHING"
            hardware.show_msg("Connecting...", "Checking Server", "")
            if not discover_backend():
                logging.warning("Backend unreachable and discovery failed.")
                time.sleep(5)
            continue
            
        # 2. Check Admin Commands (Enrollment) - Done even when idle
        poll_admin_commands()

        # 3. Fetch Candidates and Status
        new_candidates, active_now = fetch_active_candidates()
        if active_now != election_active or len(new_candidates) != len(candidates):
            candidates = new_candidates
            election_active = active_now
            logging.info(f"Kiosk updated: Election Active={election_active}, Candidates={len(candidates)}")

        # 4. Idle Screen
        if not election_active:
            hardware.show_msg("VOTECHAIN", "Election Closed", "Admin Portal Only", big_text=False)
            hardware.set_leds(False, True)
            time.sleep(POLL_INTERVAL)
            continue

        hardware.show_msg("VOTE", "CHAIN", "Press START", big_text=True)
        hardware.set_leds(green=True, red=False)
        
        # 5. Check Start Button
        if hardware.is_button_pressed('START'):
            hardware.show_msg("Voter Identity", "Enter Aadhaar ID", "On Keyboard/Scanner")
            hardware.beep(1)
            
            # Wait for Aadhaar with timeout and "Cancel" button support
            start_time = time.time()
            aadhaar = None
            while time.time() - start_time < 30: # 30s timeout
                # Check for Reset/Cancel
                if hardware.is_button_pressed('START'): 
                    aadhaar = "CANCEL"
                    break
                
                # Non-blocking check for keyboard input
                val = get_input_non_blocking()
                if val:
                    if validate_aadhaar(val):
                        aadhaar = val
                        break
                    else:
                        hardware.show_msg("Invalid ID", "Must be 12 Digits", "Try Again")
                        hardware.beep(1, 0.5)
                        time.sleep(2)
                        hardware.show_msg("Voter Identity", "Enter Aadhaar ID", "On Keyboard/Scanner")
                time.sleep(0.1)

            if not aadhaar or aadhaar == "CANCEL":
                continue # Back to idle
            
            KIOSK_STATUS = "CHECKING_IN"
            voter = check_in_voter(aadhaar)
            if voter:
                # Fingerprint Verification Loop (Hardened: Max 2 attempts)
                KIOSK_STATUS = "VERIFYING_BIO"
                verified = False
                for attempt in range(1, 3):
                    hardware.show_msg(f"Hi {voter['name'].split()[0]}", f"Scan Finger... ({attempt}/2)", "")
                    fid = hardware.scan_finger()
                    if fid == voter['fingerprint_id']:
                        verified = True
                        logging.info(f"Voter {aadhaar} verified on attempt {attempt}")
                        break
                    elif fid:
                        hardware.show_msg("Mismatch", "Try Again", f"Attempt {attempt}/2")
                        hardware.beep(1, 0.5)
                        time.sleep(1)
                    
                    if hardware.is_button_pressed('START'): break # Manual cancel

                if verified:
                    # Select Candidate (Dynamic Mapping)
                    if not candidates:
                        hardware.show_msg("Ballot Error", "No Candidates", "Contact Admin")
                        time.sleep(3)
                        continue

                    # Mapping logic for A, B, C buttons
                    hardware.show_msg("Select Candidate", 
                                     f"A: {candidates[0]['name'][:12]}" if len(candidates) > 0 else "",
                                     f"B: {candidates[1]['name'][:12]}" if len(candidates) > 1 else "")
                    
                    while True:
                        if hardware.is_button_pressed('START'): break # Cancel vote

                        if len(candidates) > 0 and hardware.is_button_pressed('A'):
                            KIOSK_STATUS = "SUBMITTING"
                            submit_vote(aadhaar, candidates[0]['id'])
                            break
                        elif len(candidates) > 1 and hardware.is_button_pressed('B'):
                            KIOSK_STATUS = "SUBMITTING"
                            submit_vote(aadhaar, candidates[1]['id'])
                            break
                        # Future: Add Button C support if hardware supports it
                        time.sleep(0.1)
                else:
                    logging.warning(f"Auth failed for voter {aadhaar}")
                    hardware.show_msg("Auth Failed", "Contact Polling", "Officer for Help")
                    hardware.beep(3, 0.2)
                    time.sleep(5)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        hardware.cleanup()