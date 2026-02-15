#!/usr/bin/env python3
"""
VoteChain V3 Kiosk - Main Entry Point
Biometric voting terminal with fingerprint authentication
"""

import time
import sys
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import uuid
import socket
import atexit
from hardware import hardware

# --- CONFIGURATION ---
import os
import logging
    # Delegate to hardware.robust_enroll which handles waiting, retries and UX
    try:
        success = hardware.robust_enroll(id)
    except Exception as e:
        logging.error(f"robust_enroll exception: {e}")
        success = False
    return success
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
# Ignore immediate re-trigger of START after cancel/return
IGNORE_START_UNTIL = 0

def cleanup():
    """Graceful shutdown handler"""
    logging.info("Kiosk shutting down...")
    try:
        hardware.set_leds(False, False)
    except Exception:
        pass
    try:
        hardware.show_msg("VOTECHAIN", "Offline", "System Shutdown")
    except Exception:
        pass
    try:
        hardware.cleanup()
    except Exception:
        pass

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
        # Diagnostic log for backend response body
        logging.debug(f"check_in_voter response status={response.status_code} body={response.text}")
        if response.status_code == 200:
            # prefer full JSON body for diagnosis
            try:
                data = response.json().get('data', {})
            except Exception:
                data = {}
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
            try:
                hardware.show_msg("Submitting...", frames[idx % 4], "Please Wait")
                idx += 1
            except Exception:
                pass # Prevent thread death on I2C hiccup
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
    # Enrollment LED Pattern: Green Blinking (Done in loop potentially, but static Green for now is safer)
    hardware.set_leds(green=True, red=False)
    
    # 1. First Scan — wait up to FINGER_WAIT_SECONDS for a readable image
    try:
        wait_seconds = int(os.getenv('FINGER_WAIT_SECONDS', '15'))
    except Exception:
        wait_seconds = 15
    deadline = time.time() + wait_seconds
    img = None
    while time.time() < deadline:
        if hardware.is_button_pressed('START'):
            return False
        img = hardware.get_finger_image()
        if img == 0:  # OK
            break
        # treat FAIL as transient; keep waiting until deadline
        time.sleep(0.1)

    if img != 0:
        return False

    if hardware.image_2_tz(1) != 0:
        return False
    
    hardware.show_msg("Remove Finger", "...", "...")
    hardware.beep(1)
    time.sleep(2)
    hardware.wait_for_finger_release()
    
    # 2. Second Scan
    hardware.show_msg("Place Again", "Verify...", "")
    enroll_start = time.time() # Reset timeout for second scan
    while True:
        # Timeout after 30s
        if time.time() - enroll_start > 30:
            hardware.show_msg("Timeout", "No Finger", "")
            return False

        if hardware.is_button_pressed('START'): return False
        
        try:
            img = hardware.get_finger_image()
            if img == 0: # OK
                break
            if img == 1: # NOFINGER
                pass
            elif img == 2: # IMAGE FAIL - Retry, don't abort!
                # hardware.show_msg("Bad Image", "Press Harder", "")
                pass
            else:
                # Other errors (communication error etc) might need abort, but let's retry for robustness
                time.sleep(0.1)
        except Exception:
            pass
            
        time.sleep(0.1) # Prevent CPU spinning
    
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
    # Try to read from sys.stdin and /dev/tty (if available). Use blocking reads
    # so this thread doesn't spin CPU; handle EOFs gracefully.
    tty_fd = None
    try:
        tty_fd = open('/dev/tty', 'rb', buffering=0)
    except Exception:
        tty_fd = None

    import select, os
    while True:
        rlist = []
        try:
            if not sys.stdin.closed:
                rlist.append(sys.stdin)
        except Exception:
            pass
        if tty_fd:
            rlist.append(tty_fd)

        try:
            if not rlist:
                time.sleep(0.1)
                continue
            # select on file objects; convert to filenos
            fds = [getattr(f, 'fileno')() for f in rlist]
            ready, _, _ = select.select(fds, [], [], 0.5)
            for fd in ready:
                try:
                    data = os.read(fd, 1)
                    if not data:
                        continue
                    char = data.decode(errors='ignore')
                    # Treat both newline and carriage return as input-ready
                    if char in ('\n', '\r'):
                        INPUT_READY = True
                    elif char in ('\x7f', '\b'):
                        # handle backspace/delete from some devices
                        INPUT_BUFFER = INPUT_BUFFER[:-1]
                    else:
                        INPUT_BUFFER += char
                except Exception:
                    continue
        except Exception:
            # recover from any unexpected I/O error
            time.sleep(0.1)
            continue


def start_evdev_listener():
    """Optional: listen to /dev/input/event* devices using python-evdev.
    This only runs if `evdev` is installed and the process has permission to read
    input devices. It maps simple KEY_* codes to characters and feeds the
    `INPUT_BUFFER` so scanners/keyboards work when running under systemd.
    """
    try:
        from evdev import InputDevice, list_devices, ecodes
    except Exception:
        return None

    import threading

    def _listener():
        dev_paths = list_devices()
        devices = []
        for path in dev_paths:
            try:
                d = InputDevice(path)
                caps = d.capabilities()
                if ecodes.EV_KEY in caps:
                    devices.append(d)
            except Exception:
                continue

        if not devices:
            return

        keymap = {}
        # basic mapping for letters and digits
        for c in range(ord('a'), ord('z')+1):
            keymap[getattr(ecodes, f'KEY_{chr(c).upper()}')] = chr(c)
        for n in range(0,10):
            keymap[getattr(ecodes, f'KEY_{n}')] = str(n)
        keymap[getattr(ecodes, 'KEY_ENTER')] = '\n'
        keymap[getattr(ecodes, 'KEY_SPACE')] = ' '
        keymap[getattr(ecodes, 'KEY_BACKSPACE')] = '\b'

        import select, os
        fds = [d.fd for d in devices]
        while True:
            try:
                r, _, _ = select.select(fds, [], [], 0.5)
                for fd in r:
                    for d in devices:
                        if d.fd != fd: continue
                        for event in d.read():
                            if event.type == ecodes.EV_KEY and event.value == 1:
                                code = event.code
                                ch = keymap.get(code)
                                if ch:
                                    global INPUT_BUFFER, INPUT_READY
                                    if ch == '\n':
                                        INPUT_READY = True
                                    elif ch == '\b':
                                        INPUT_BUFFER = INPUT_BUFFER[:-1]
                                    else:
                                        INPUT_BUFFER += ch
            except Exception:
                time.sleep(0.5)

    t = threading.Thread(target=_listener, daemon=True)
    t.start()
    return t

def get_input_non_blocking():
    global INPUT_BUFFER, INPUT_READY
    if INPUT_READY:
        val = INPUT_BUFFER.strip()
        INPUT_BUFFER = ""
        INPUT_READY = False
        return val
    return None

def fetch_active_candidates():
    """Robustly retrieve candidate list and election status from backend.

    Uses a session with retries, a timeout, and a small failure cache so brief
    backend hiccups don't immediately flip the UI to 'Election Closed'.
    Returns (candidates_list, election_active_bool)
    """
    global _LAST_CANDIDATES, _LAST_ELECTION_ACTIVE, _CONSECUTIVE_FAILURES

    try:
        _ = _LAST_CANDIDATES
    except NameError:
        _LAST_CANDIDATES = []
        _LAST_ELECTION_ACTIVE = False
        _CONSECUTIVE_FAILURES = 0

    try:
        res = _session.get(f"{BACKEND_URL}/api/results", headers={'ngrok-skip-browser-warning': 'true'}, timeout=POLL_TIMEOUT)
        res.raise_for_status()
        data = res.json().get('data', {}) if isinstance(res.json(), dict) else res.json()
        candidates = data.get('candidates', [])
        election_active = data.get('electionActive', data.get('active', False))

        _LAST_CANDIDATES = candidates
        _LAST_ELECTION_ACTIVE = election_active
        _CONSECUTIVE_FAILURES = 0
        return candidates, election_active

    except Exception as e:
        logging.warning(f"fetch_active_candidates failed: {e}")
        _CONSECUTIVE_FAILURES += 1

        if _CONSECUTIVE_FAILURES <= FAILURE_CACHE_MAX:
            logging.info(f"Using cached candidates (failures={_CONSECUTIVE_FAILURES})")
            return _LAST_CANDIDATES, _LAST_ELECTION_ACTIVE

        logging.error(f"Too many failures ({_CONSECUTIVE_FAILURES}); falling back to closed state")
        return [], False

def validate_aadhaar(val):
    """Local format check for Aadhaar (12 digits)"""
    if not val: return False
    # Remove spaces/hyphens
    # Keep only digits (strip carriage returns, control chars, etc.)
    clean = ''.join([c for c in val if c.isdigit()])
    return clean.isdigit() and len(clean) == 12

# --- MAIN LOOP ---

def main():
    print("🚀 Kiosk Started")
    # "Bubbly" Text Restoration -> big_text=True for the logo
    hardware.show_msg("VOTE", "CHAIN", "", big_text=True)
    time.sleep(2)
    
    # Start keyboard listener
    kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
    kb_thread.start()
    # Start optional evdev listener (if available and permitted)
    # DISABLED BY DEFAULT: Causes double inputs in many environments
    # Uncomment only if running as a service without TTY access
    # try:
    #     start_evdev_listener()
    # except Exception:
    #     pass

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

        # 4. Idle Screen — show closed but still poll buttons so START can get a user message
        if not election_active:
            hardware.show_msg("ELECTION", "CLOSED", "", big_text=True)
            # Idle/Closed LED Pattern: Red Only
            hardware.set_leds(False, True)
            # Poll buttons for up to POLL_INTERVAL seconds so START presses are acknowledged
            start_poll = time.time()
            while time.time() - start_poll < POLL_INTERVAL:
                if hardware.is_button_pressed('START'):
                    hardware.show_msg("Closed", "Use Admin Portal", "", big_text=False)
                    hardware.beep(1)
                    time.sleep(1)
                    break
                time.sleep(0.1)
            continue

        hardware.show_msg("VOTE", "CHAIN", "Press START", big_text=True)
        # Idle/Ready LED Pattern: Green Only (Welcoming)
        hardware.set_leds(green=True, red=False)
        
        # 5. Check Start Button — allow a short window to catch presses
        def wait_for_start(timeout=1.5):
            start_t = time.time()
            global IGNORE_START_UNTIL
            while time.time() - start_t < timeout:
                # ignore START presses for a short period after cancel/return
                if time.time() < IGNORE_START_UNTIL:
                    time.sleep(0.05)
                    continue
                if hardware.is_button_pressed('START'):
                    return True
                time.sleep(0.05)
            return False

        if wait_for_start(1.5):
            # Clear any buffered input before showing Aadhaar prompt
            INPUT_BUFFER = ""
            INPUT_READY = False
            hardware.show_msg("Voter Identity", "Enter Aadhaar ID", "On Keyboard/Scanner")
            hardware.beep(1)
            
            # Persistent Aadhaar entry prompt: wait until valid input or explicit cancel
            aadhaar = None
            start_time = time.time()
            MAX_WAIT = 30  # Reduced to 30s for faster queues
            last_feedback = time.time() # Delay first countdown update by 5s
            logging.info("Entered Aadhaar entry loop")
            while True:
                # debug trace for cancel/timeouts
                if int(time.time() - start_time) % 10 == 0:
                    logging.debug(f"Aadhaar loop tick, elapsed={int(time.time()-start_time)}s, buffer_len={len(INPUT_BUFFER)}")
                # Cancel if operator presses START (debounced)
                # Ignore immediate START state for a short window to avoid treating
                # residual/held presses as a cancel right after opening the prompt.
                if time.time() - start_time > 0.5 and hardware.is_button_pressed('START'):
                    aadhaar = "CANCEL"
                    # avoid immediate re-trigger of START when returning to idle
                    global IGNORE_START_UNTIL
                    IGNORE_START_UNTIL = time.time() + 1.5
                    logging.info("Aadhaar entry cancelled via START button")
                    break
                elif hardware.is_button_pressed('START'):
                    # If START is seen immediately, ignore it and log for diagnosis
                    logging.debug("Ignoring immediate START read at Aadhaar entry" )

                # Non-blocking check for keyboard input
                val = get_input_non_blocking()
                if val:
                    # Normalize and diagnose input
                    logging.info(f"Aadhaar input received: [{val}] (len={len(val)})")
                    clean = ''.join([c for c in val if c.isdigit()])
                    if validate_aadhaar(val):
                        aadhaar = clean
                        break
                    else:
                        hardware.show_msg("Invalid ID", "Must be 12 Digits", "Try Again")
                        logging.debug(f"validate_aadhaar raw=[{repr(val)}] clean=[{clean}] len={len(clean)}")
                        hardware.beep(1, 0.5)
                        time.sleep(1)
                        hardware.show_msg("Voter Identity", "Enter Aadhaar ID", "On Keyboard/Scanner")

                # Echo live buffer so user sees digits on the OLED
                try:
                    buf_snapshot = INPUT_BUFFER
                except Exception:
                    buf_snapshot = ''
                if buf_snapshot:
                    # show typed digits (trim to fit display)
                    display_val = buf_snapshot[-12:]
                    try:
                        hardware.show_msg("Voter Identity", display_val, "")
                    except Exception:
                        pass

                # Periodic countdown feedback
                if time.time() - last_feedback > 5:
                    remaining = MAX_WAIT - int(time.time() - start_time)
                    if remaining < 0:
                        remaining = 0
                    hardware.show_msg("Voter Identity", f"Enter Aadhaar ({remaining}s)", "")
                    last_feedback = time.time()

                # Timeout -> return to idle
                if time.time() - start_time > MAX_WAIT:
                    logging.info(f"Aadhaar entry timed out after {int(time.time()-start_time)}s")
                    hardware.show_msg("Timeout", "Returning to Idle", "")
                    time.sleep(1)
                    break

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
                    logging.debug(f"Fingerprint scan attempt={attempt} fid={repr(fid)} expected={repr(voter.get('fingerprint_id'))}")
                    if fid == voter.get('fingerprint_id'):
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

                    # Require double-press to confirm selection: first press selects,
                    # second press (same button within CONFIRM_WINDOW) confirms.
                    CONFIRM_WINDOW = 5
                    selected = None
                    confirm_deadline = 0

                    def show_select_screen():
                        hardware.show_msg("Select Candidate", 
                                         f"A: {candidates[0]['name'][:12]}" if len(candidates) > 0 else "",
                                         f"B: {candidates[1]['name'][:12]}" if len(candidates) > 1 else "")

                    show_select_screen()

                    while True:
                        if hardware.is_button_pressed('START'):
                            # Cancel vote selection
                            selected = None
                            break

                        # Button A
                        if len(candidates) > 0 and hardware.is_button_pressed('A'):
                            if selected == 'A' and time.time() <= confirm_deadline:
                                KIOSK_STATUS = "SUBMITTING"
                                submit_vote(aadhaar, candidates[0]['id'])
                                break
                            else:
                                selected = 'A'
                                confirm_deadline = time.time() + CONFIRM_WINDOW
                                hardware.show_msg("Confirm Vote", f"A: {candidates[0]['name'][:12]}", "Press A again to confirm")
                                hardware.beep(1)
                                time.sleep(0.3)

                        # Button B
                        elif len(candidates) > 1 and hardware.is_button_pressed('B'):
                            if selected == 'B' and time.time() <= confirm_deadline:
                                KIOSK_STATUS = "SUBMITTING"
                                submit_vote(aadhaar, candidates[1]['id'])
                                break
                            else:
                                selected = 'B'
                                confirm_deadline = time.time() + CONFIRM_WINDOW
                                hardware.show_msg("Confirm Vote", f"B: {candidates[1]['name'][:12]}", "Press B again to confirm")
                                hardware.beep(1)
                                time.sleep(0.3)

                        # If selection expired, return to select screen
                        if selected and time.time() > confirm_deadline:
                            selected = None
                            show_select_screen()

                        time.sleep(0.1)
                else:
                    logging.warning(f"Auth failed for voter {aadhaar}")
                    hardware.show_msg("Auth Failed", "Contact Polling", "Officer for Help")
                    hardware.beep(3, 0.2)
                    time.sleep(5)

        # Responsiveness Fix: Poll during the wait interval instead of hard sleeping
        # This prevents the "Sleep of Death" where button presses are ignored for seconds
        start_wait = time.time()
        while time.time() - start_wait < POLL_INTERVAL:
            if hardware.is_button_pressed('START'):
                break # Wake up immediately
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        hardware.cleanup()