import time
import sys
import tty
import termios
import select
import atexit

# Optional global keyboard capture (works without terminal focus)
try:
    from evdev import InputDevice, ecodes, list_devices
except Exception:
    InputDevice = None
    ecodes = None
    list_devices = lambda: []
import serial
import adafruit_fingerprint
import requests
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import sh1106, ssd1306 

# --- CONFIGURATION ---
# ⚠️ UPDATE THIS IP IF YOUR LAPTOP IP CHANGES ⚠️
BACKEND_URL = "http://127.0.0.1:3000"

# --- PIN LAYOUT (BCM) ---
PIN_LED_GREEN = 17
PIN_LED_RED = 27
PIN_BUZZER = 18
PIN_BTN_START = 4  # The Admin/Start Button
PIN_BTN_A = 22     # Candidate A
PIN_BTN_B = 23     # Candidate B

# OLED (SPI)
OLED_DC = 24
OLED_RST = 25

# --- 1. SENSOR SETUP ---
finger = None
try:
    uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1) 
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
    print("✓ Fingerprint sensor initialized")
except Exception as e:
    print(f"⚠️  Fingerprint sensor unavailable: {e}")
    print("⚠️  Continuing in demo mode (fingerprint checks will be skipped)")
    finger = None

# --- 2. GPIO & OLED SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Always release GPIO on exit/crash
def _cleanup_gpio():
    try:
        GPIO.output(PIN_LED_GREEN, GPIO.LOW)
        GPIO.output(PIN_LED_RED, GPIO.LOW)
    except Exception:
        pass
    try:
        GPIO.cleanup()
    except Exception:
        pass

atexit.register(_cleanup_gpio)

# Outputs (set initial LOW to avoid pre-read on lgpio backend)
GPIO.setup(PIN_LED_GREEN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_LED_RED, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)

# Inputs (Internal Pull-up)
GPIO.setup(PIN_BTN_START, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_BTN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_BTN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize OLED
try:
    serial_conn = spi(device=0, port=0, gpio_DC=OLED_DC, gpio_RST=OLED_RST)
    try:
        device = sh1106(serial_conn)
    except:
        device = ssd1306(serial_conn)
except:
    device = None

# --- HELPER FUNCTIONS ---

def beep(count=1, duration=0.1):
    for _ in range(count):
        GPIO.output(PIN_BUZZER, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(PIN_BUZZER, GPIO.LOW)
        time.sleep(0.05)

def set_leds(green=False, red=False):
    GPIO.output(PIN_LED_GREEN, GPIO.HIGH if green else GPIO.LOW)
    GPIO.output(PIN_LED_RED, GPIO.HIGH if red else GPIO.LOW)

def show_msg(line1, line2="", line3=""):
    print(f"[DISPLAY] {line1} | {line2} | {line3}")
    if device:
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((5, 5), line1, fill="white")
            draw.text((5, 25), line2, fill="white")
            draw.text((5, 45), line3, fill="white")

def read_aadhaar_on_oled(max_len: int = 12) -> str:
    """Read Aadhaar digits from keyboard, reflecting input on OLED line 3.
    Character-by-character input with instant OLED updates.
    """
    digits = ""
    show_msg("Manual Mode", "Enter Aadhaar:", "_")
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        # Raw mode: get characters instantly without echo
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            
            # Enter submits (both \n and \r)
            if ch in ("\n", "\r", "\x0d", "\x0a"):
                if digits:  # Only submit if we have input
                    print()  # New line in logs
                    return digits
            
            # Ctrl+C exits
            elif ch == "\x03":
                print("\n⚠️ Cancelled by user")
                GPIO.cleanup()
                sys.exit(0)
            
            # ESC cancels input
            elif ch == "\x1b":
                digits = ""
                show_msg("Manual Mode", "Cancelled", "")
                time.sleep(1)
                return ""
            
            # Backspace/delete
            elif ch in ("\x08", "\x7f", "\x17"):  # \x17 is Ctrl+W
                digits = digits[:-1]
            
            # Accept only digits up to max_len
            elif ch.isdigit() and len(digits) < max_len:
                digits += ch
            
            # Update OLED immediately after every key
            cursor = "_" if len(digits) < max_len else ""
            show_msg("Manual Mode", "Enter Aadhaar:", digits + cursor)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return digits

def _find_keyboard_device():
    try:
        for dev_path in list_devices():
            try:
                dev = InputDevice(dev_path)
                caps = dev.capabilities(verbose=True)
                if ('EV_KEY', ecodes.EV_KEY) in caps:
                    name = (dev.name or '').lower()
                    phys = (dev.phys or '').lower()
                    if 'kbd' in name or 'key' in name or 'keyboard' in name or 'event-kbd' in phys:
                        return dev
            except Exception:
                continue
    except Exception:
        pass
    return None

def read_aadhaar_from_evdev(max_len: int = 12, timeout_sec: int = 60) -> str:
    """Capture digits from any keyboard globally via evdev, mirror to OLED.
    Requires permission to read /dev/input/event* (run with sudo or set udev rules).
    Returns empty string on cancel/timeout.
    """
    if InputDevice is None:
        return ""
    dev = _find_keyboard_device()
    if not dev:
        return ""
    digits = ""
    deadline = time.time() + timeout_sec
    show_msg("Manual Mode", "Enter Aadhaar:", "_")
    try:
        while time.time() < deadline:
            r, _, _ = select.select([dev.fd], [], [], 0.3)
            if not r:
                continue
            for event in dev.read():
                if event.type != ecodes.EV_KEY:
                    continue
                # value: 1 = keydown
                if event.value != 1:
                    continue
                code = event.code
                if code in (ecodes.KEY_ENTER, getattr(ecodes, 'KEY_KPENTER', 0)):
                    return digits
                if code == ecodes.KEY_BACKSPACE:
                    digits = digits[:-1]
                elif code in (
                    ecodes.KEY_0, ecodes.KEY_1, ecodes.KEY_2, ecodes.KEY_3, ecodes.KEY_4,
                    ecodes.KEY_5, ecodes.KEY_6, ecodes.KEY_7, ecodes.KEY_8, ecodes.KEY_9,
                    getattr(ecodes, 'KEY_KP0', 0), getattr(ecodes, 'KEY_KP1', 0), getattr(ecodes, 'KEY_KP2', 0),
                    getattr(ecodes, 'KEY_KP3', 0), getattr(ecodes, 'KEY_KP4', 0), getattr(ecodes, 'KEY_KP5', 0),
                    getattr(ecodes, 'KEY_KP6', 0), getattr(ecodes, 'KEY_KP7', 0), getattr(ecodes, 'KEY_KP8', 0),
                    getattr(ecodes, 'KEY_KP9', 0)
                ):
                    # Map keycode -> digit char
                    key_to_digit = {
                        ecodes.KEY_0: '0', ecodes.KEY_1: '1', ecodes.KEY_2: '2', ecodes.KEY_3: '3', ecodes.KEY_4: '4',
                        ecodes.KEY_5: '5', ecodes.KEY_6: '6', ecodes.KEY_7: '7', ecodes.KEY_8: '8', ecodes.KEY_9: '9',
                    }
                    if code not in key_to_digit:
                        # Keypad mapping
                        try:
                            if code == ecodes.KEY_KP0: ch = '0'
                            elif code == ecodes.KEY_KP1: ch = '1'
                            elif code == ecodes.KEY_KP2: ch = '2'
                            elif code == ecodes.KEY_KP3: ch = '3'
                            elif code == ecodes.KEY_KP4: ch = '4'
                            elif code == ecodes.KEY_KP5: ch = '5'
                            elif code == ecodes.KEY_KP6: ch = '6'
                            elif code == ecodes.KEY_KP7: ch = '7'
                            elif code == ecodes.KEY_KP8: ch = '8'
                            elif code == ecodes.KEY_KP9: ch = '9'
                            else: ch = ''
                        except Exception:
                            ch = ''
                    else:
                        ch = key_to_digit[code]
                    if ch and len(digits) < max_len:
                        digits += ch
                        if len(digits) >= max_len:
                            return digits
                # Update OLED after any key
                cursor = '_' if len(digits) < max_len else ''
                show_msg("Manual Mode", "Enter Aadhaar:", digits + cursor)
    except PermissionError:
        # No permission to read input device
        show_msg("Keyboard blocked", "Run with sudo", "or set udev perms")
        time.sleep(2)
        return ""
    except Exception:
        return ""
    return digits

# --- FINGERPRINT LOGIC ---

def get_image_with_timeout(timeout_seconds=10.0):
    if finger is None:
        print("[DEMO MODE] Simulating finger scan...")
        time.sleep(2)
        return True
    MANDATORY_HOLD_TIME = 1.5
    print(f"Waiting for finger...", end="", flush=True)
    
    start_time = time.time()
    
    while (time.time() - start_time) < timeout_seconds:
        i = finger.get_image()
        if i == adafruit_fingerprint.OK:
            print("\nDetected. Holding...", end="", flush=True)
            beep(count=1, duration=0.05)
            time.sleep(MANDATORY_HOLD_TIME) # Hold for clarity
            finger.get_image() # Grab fresh image
            return True
        if i == adafruit_fingerprint.NOFINGER:
            pass
        elif i == adafruit_fingerprint.IMAGEFAIL:
            return False
    return False

def scan_finger_and_get_id():
    if finger is None:
        print("[DEMO MODE] Returning fingerprint ID 1")
        return 1  # Demo mode: always return ID 1
    finger.set_led(color=1, mode=1) # Breathing
    if not get_image_with_timeout(10.0):
        finger.set_led(color=1, mode=3) # Red error
        return None
        
    print("Templating...", end="")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        finger.set_led(color=1, mode=3)
        return None
    
    print("Searching...", end="")
    if finger.finger_search() == adafruit_fingerprint.OK:
        finger.set_led(color=2, mode=3) # Green success
        return finger.finger_id
    else:
        finger.set_led(color=1, mode=3) # Red fail
        return None

# --- NEW: ENROLLMENT LOGIC ---

def enroll_finger(location_id):
    """Captures a new finger and saves it to the specified ID"""
    if finger is None:
        print(f"[DEMO MODE] Simulating enrollment for ID #{location_id}")
        show_msg("DEMO ENROLL", f"ID #{location_id}", "Success!")
        time.sleep(3)
        return True
    show_msg("ENROLL MODE", f"ID #{location_id}", "Place Finger...")
    set_leds(green=True, red=True) # Both LEDs ON for Enroll Mode
    
    # 1. First Scan
    if not get_image_with_timeout(15.0): return False
    if finger.image_2_tz(1) != adafruit_fingerprint.OK: return False
    
    show_msg("Remove Finger", "...", "...")
    beep(1)
    time.sleep(2)
    while finger.get_image() != adafruit_fingerprint.NOFINGER: pass
    
    # 2. Second Scan
    show_msg("Place Again", "Verify...", "")
    if not get_image_with_timeout(15.0): return False
    if finger.image_2_tz(2) != adafruit_fingerprint.OK: return False
    
    # 3. Model & Store
    if finger.create_model() != adafruit_fingerprint.OK: return False
    if finger.store_model(location_id) != adafruit_fingerprint.OK: return False
    
    return True

def perform_remote_enrollment(target_id, voter_name):
    print(f"\n🔵 ADMIN COMMAND: Enroll {voter_name} as ID #{target_id}")
    beep(3, 0.1)
    
    success = enroll_finger(target_id)
    
    if success:
        show_msg("Enrollment", "SUCCESS!", "Saved.")
        set_leds(green=True, red=False)
        beep(2, 0.1)
    else:
        show_msg("Enrollment", "FAILED", "Try Again")
        set_leds(green=False, red=True)
        beep(3, 0.5)
        
    return success

# --- BACKEND API ---

def check_in_voter(aadhaar_id):
    show_msg("Checking DB...", aadhaar_id)
    try:
        response = requests.post(f"{BACKEND_URL}/api/voter/check-in", 
                                 json={"aadhaar_id": aadhaar_id}, timeout=5)
        if response.status_code == 200:
            return response.json()['data']
        else:
            show_msg("Check-in Failed", "Not Found/Voted")
            beep(count=1, duration=0.5)
            return None
    except:
        show_msg("Network Error", "Check Server")
        return None

def submit_vote(aadhaar_id, candidate_id):
    show_msg("Submitting...", "Please Wait")
    set_leds(green=True, red=True)
    try:
        response = requests.post(f"{BACKEND_URL}/api/vote", 
                                 json={"aadhaar_id": aadhaar_id, "candidate_id": candidate_id}, timeout=30)
        if response.status_code == 200:
            tx_hash = response.json()['transaction_hash']
            set_leds(green=True, red=False)
            show_msg("VOTE CONFIRMED!", "Success", "Thank You")
            print(f"TX: {tx_hash}")
            beep(count=2, duration=0.1)
            return True
        else:
            show_msg("Vote Rejected", "Error")
            set_leds(green=False, red=True)
            beep(count=1, duration=1.0)
            return False
    except:
        show_msg("Connection Fail", "Retry")
        return False

def run_voting_interface(voter_name):
    show_msg(f"Hi {voter_name}", "Select Candidate:", "A (Btn1) | B (Btn2)")
    set_leds(green=True, red=False)
    beep(count=1)
    
    selected_candidate = None
    
    while True:
        # 1. Wait for input
        if GPIO.input(PIN_BTN_A) == GPIO.LOW:
            new_selection = 1
            beep(count=1, duration=0.05)
            time.sleep(0.3)
        elif GPIO.input(PIN_BTN_B) == GPIO.LOW:
            new_selection = 2
            beep(count=1, duration=0.05)
            time.sleep(0.3)
        else:
            new_selection = None

        # 2. Handle Selection logic
        if new_selection is not None:
            if selected_candidate == new_selection:
                return selected_candidate
            else:
                selected_candidate = new_selection
                cand_name = "CANDIDATE A" if selected_candidate == 1 else "CANDIDATE B"
                show_msg("CONFIRM VOTE:", cand_name, "Press Again ->")

        time.sleep(0.05)

# --- MAIN APP LOOP ---

if __name__ == '__main__':
    if finger.read_sysparam() != adafruit_fingerprint.OK:
        print("❌ Sensor check failed.")
        exit()
    
    print("--- VOTECHAIN KIOSK LIVE (V3) ---")
    beep(count=2)
    
    # Track idle state
    idle_message_shown = False
    
    while True:
        # 1. POLL FOR ADMIN COMMANDS (Remote Enrollment)
        try:
            res = requests.get(f"{BACKEND_URL}/api/kiosk/poll-commands", timeout=0.5)
            cmd = res.json()
            
            if cmd.get('command') == 'ENROLL':
                # --- SWITCH TO ENROLLMENT MODE ---
                print(f"\n🔔 [REMOTE ENROLL] Command received for {cmd['name']}")
                success = perform_remote_enrollment(cmd['target_finger_id'], cmd['name'])
                
                # Report result back to server
                requests.post(f"{BACKEND_URL}/api/kiosk/enrollment-complete", 
                              json={"success": success, "fingerprint_id": cmd['target_finger_id']})
                
                time.sleep(2)
                idle_message_shown = False  # Reset idle state
                continue # Skip voting loop, check for commands again
        except: 
            pass # Ignore network blips during polling

        # 2. VOTING MODE (Idle) - Show idle message once
        if not idle_message_shown:
            set_leds(green=False, red=False)
            show_msg("   VOTECHAIN   ", "   SECURE EVM   ", "Enter Aadhaar ->")
            print("\n⏳ Polling for commands... (Press Ctrl+C to exit)")
            idle_message_shown = True
        
        # Small delay to prevent CPU spinning, then poll again
        time.sleep(0.5)
        
        # Check for keyboard input (non-blocking would be better, but this works)
        # For now, we'll use button input instead
        try:
            # Check if START button is pressed (replaces keyboard input)
            if GPIO.input(PIN_BTN_START) == GPIO.LOW:
                time.sleep(0.2)  # Debounce
                # Use terminal-based input with live OLED updates
                aadhaar = read_aadhaar_on_oled()
                
                if not aadhaar or aadhaar.strip() == "": 
                    idle_message_shown = False
                    continue # Loop back to check for commands

                # 3. VOTER CHECK-IN
                voter = check_in_voter(aadhaar)
                
                if voter:
                    # 4. VERIFY FINGERPRINT
                    show_msg("Verifying...", "Scan Finger")
                    set_leds(green=False, red=True) 
                    
                    print(f"Expecting Finger ID #{voter['fingerprint_id']}")
                    scanned_id = scan_finger_and_get_id()
                    
                    if scanned_id == voter['fingerprint_id']:
                        # 5. VOTE INTERFACE
                        print("✅ Identity Verified.")
                        final_choice = run_voting_interface(voter['name'])
                        
                        # 6. SUBMIT
                        submit_vote(aadhaar, final_choice)
                        time.sleep(4)
                    else:
                        print("⛔ Mismatch.")
                        show_msg("Access Denied", "Finger Mismatch")
                        set_leds(green=False, red=True)
                        beep(count=3, duration=0.2)
                        time.sleep(3)
                    
                    idle_message_shown = False  # Reset for next iteration
            
        except KeyboardInterrupt:
            GPIO.cleanup()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)