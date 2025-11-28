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
try:
    uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1) 
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
    print("✓ Fingerprint sensor initialized")
except Exception as e:
    print(f"❌ FATAL: Fingerprint sensor unavailable: {e}")
    print("❌ Please check the wiring and connections.")
    print("❌ Cannot start kiosk without fingerprint scanner.")
    sys.exit(1)

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

def show_msg(line1, line2="", line3="", big_text=False):
    print(f"[DISPLAY] {line1} | {line2} | {line3}")
    if device:
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            if big_text:
                # Center large text with shadow effect
                from PIL import ImageFont
                try:
                    # Use a font size that fits the screen width
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
                except:
                    font = None
                
                # Calculate text position to center it
                if font:
                    bbox = draw.textbbox((0, 0), line1, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                else:
                    text_width = len(line1) * 10
                    text_height = 8
                
                x = (device.width - text_width) // 2
                y = (device.height - text_height) // 2
                
                # Draw shadow (offset by 2 pixels down and right)
                draw.text((x + 2, y + 2), line1, fill="white", font=font)
                # Draw main text
                draw.text((x, y), line1, fill="white", font=font)
            else:
                draw.text((5, 5), line1, fill="white")
                draw.text((5, 25), line2, fill="white")
                draw.text((5, 45), line3, fill="white")

def read_aadhaar_simple(max_len: int = 12) -> str:
    """Simple keyboard input that works on TTY - displays on OLED.
    This is the most reliable method for headless operation.
    """
    digits = ""
    show_msg("Manual Mode", "Enter Aadhaar:", "_")
    print("\n" + "="*40)
    print("ENTER AADHAAR NUMBER (press Enter when done):")
    print("="*40)
    
    while len(digits) < max_len:
        try:
            # Read one character at a time
            import sys
            import tty
            import termios
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                
                # Enter key
                if ch in ('\r', '\n'):
                    if digits:
                        print()  # Newline
                        return digits
                
                # Backspace
                elif ch in ('\x7f', '\x08'):
                    if digits:
                        digits = digits[:-1]
                        print('\b \b', end='', flush=True)
                
                # ESC to cancel
                elif ch == '\x1b':
                    print("\nCancelled")
                    return ""
                
                # Only accept digits
                elif ch.isdigit():
                    digits += ch
                    print(ch, end='', flush=True)
                
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
            # Update OLED after each character
            cursor = "_" if len(digits) < max_len else ""
            show_msg("Manual Mode", "Enter Aadhaar:", digits + cursor)
            
        except Exception as e:
            print(f"Input error: {e}")
            break
    
    print()  # Newline after input
    return digits

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
    """Find the main keyboard input device (not consumer control or system control)."""
    try:
        from evdev import list_devices
        candidates = []
        for dev_path in list_devices():
            try:
                dev = InputDevice(dev_path)
                name = (dev.name or '').lower()
                
                # Look for keyboard, but exclude consumer/system control variants
                if 'keyboard' in name:
                    # Prefer the base keyboard without "consumer" or "system" in name
                    if 'consumer' not in name and 'system' not in name:
                        print(f"✓ Found main keyboard: {dev.name} at {dev_path}")
                        return dev
                    else:
                        candidates.append((dev, dev_path))
            except Exception:
                continue
        
        # If no exact match, try any keyboard candidate
        if candidates:
            dev, dev_path = candidates[0]
            print(f"✓ Using keyboard: {dev.name} at {dev_path}")
            return dev
            
    except Exception as e:
        print(f"⚠️ Error finding keyboard: {e}")
    return None

def read_aadhaar_from_keyboard_device(max_len: int = 12, timeout_sec: int = 60) -> str:
    """Read Aadhaar directly from keyboard device with exclusive grab.
    Works completely headless - no terminal focus needed.
    """
    if InputDevice is None or ecodes is None:
        print("⚠️ evdev not available, falling back to simple input")
        return ""
    
    dev = _find_keyboard_device()
    if not dev:
        print("⚠️ No keyboard device found")
        return ""
    
    digits = ""
    deadline = time.time() + timeout_sec
    show_msg("Enter Aadhaar", "Type on keyboard", "_")
    
    grabbed = False
    try:
        # Grab exclusive access - prevents desktop/terminal from seeing keys
        dev.grab()
        grabbed = True
        print(f"✓ Keyboard grabbed: {dev.name}")
        
        # Use read_loop() instead of select + read()
        for event in dev.read_loop():
            # Check timeout
            if time.time() > deadline:
                print("\n⏱️ Input timeout")
                return ""
            
            # Check for reset button during input
            if GPIO.input(PIN_BTN_START) == GPIO.LOW:
                print("\n⚠️ Reset pressed during input")
                return "RESET"
            
            if event.type != ecodes.EV_KEY:
                continue
            
            # Only process key down events (value == 1)
            if event.value != 1:
                continue
            
            code = event.code
            print(f"[DEBUG] Key code: {code}", flush=True)
            
            # Enter key submits
            if code in (ecodes.KEY_ENTER, ecodes.KEY_KPENTER):
                if digits:
                    print(f"\n✓ Aadhaar entered: {digits}")
                    return digits
            
            # ESC cancels
            elif code == ecodes.KEY_ESC:
                print("⚠️ Input cancelled")
                show_msg("Cancelled", "", "")
                time.sleep(1)
                return ""
            
            # Backspace
            elif code == ecodes.KEY_BACKSPACE:
                if digits:
                    digits = digits[:-1]
                    print(f"\b \b", end='', flush=True)
            
            # Number keys (top row: KEY_1=2, KEY_2=3, ..., KEY_0=11)
            elif code >= ecodes.KEY_1 and code <= ecodes.KEY_0:
                if len(digits) < max_len:
                    # KEY_1 through KEY_9 are sequential, KEY_0 is after KEY_9
                    if code == ecodes.KEY_0:
                        digit = '0'
                    elif code == ecodes.KEY_1:
                        digit = '1'
                    elif code == ecodes.KEY_2:
                        digit = '2'
                    elif code == ecodes.KEY_3:
                        digit = '3'
                    elif code == ecodes.KEY_4:
                        digit = '4'
                    elif code == ecodes.KEY_5:
                        digit = '5'
                    elif code == ecodes.KEY_6:
                        digit = '6'
                    elif code == ecodes.KEY_7:
                        digit = '7'
                    elif code == ecodes.KEY_8:
                        digit = '8'
                    elif code == ecodes.KEY_9:
                        digit = '9'
                    else:
                        continue
                    digits += digit
                    print(digit, end='', flush=True)
                    if len(digits) >= max_len:
                        print()
                        return digits
            
            # Numpad keys (KEY_KP0=82, KEY_KP1=79, etc)
            elif code in (ecodes.KEY_KP0, ecodes.KEY_KP1, ecodes.KEY_KP2, ecodes.KEY_KP3,
                         ecodes.KEY_KP4, ecodes.KEY_KP5, ecodes.KEY_KP6, ecodes.KEY_KP7,
                         ecodes.KEY_KP8, ecodes.KEY_KP9):
                if len(digits) < max_len:
                    if code == ecodes.KEY_KP0:
                        digit = '0'
                    elif code == ecodes.KEY_KP1:
                        digit = '1'
                    elif code == ecodes.KEY_KP2:
                        digit = '2'
                    elif code == ecodes.KEY_KP3:
                        digit = '3'
                    elif code == ecodes.KEY_KP4:
                        digit = '4'
                    elif code == ecodes.KEY_KP5:
                        digit = '5'
                    elif code == ecodes.KEY_KP6:
                        digit = '6'
                    elif code == ecodes.KEY_KP7:
                        digit = '7'
                    elif code == ecodes.KEY_KP8:
                        digit = '8'
                    elif code == ecodes.KEY_KP9:
                        digit = '9'
                    else:
                        continue
                    digits += digit
                    print(digit, end='', flush=True)
                    if len(digits) >= max_len:
                        print()
                        return digits
            
            # Update OLED after each key
            cursor = "_" if len(digits) < max_len else ""
            show_msg("Enter Aadhaar", digits if digits else "Type on keyboard", cursor)
        
    except PermissionError:
        print("❌ Permission denied - run with sudo")
        show_msg("Permission Error", "Run with sudo", "")
        time.sleep(2)
        return ""
    except Exception as e:
        print(f"⚠️ Keyboard error: {e}")
        import traceback
        traceback.print_exc()
        return ""
    finally:
        # Always release the grab
        if grabbed:
            try:
                dev.ungrab()
                print("✓ Keyboard released")
            except:
                pass
    
    return ""

# --- FINGERPRINT LOGIC ---

def get_image_with_timeout(timeout_seconds=10.0):
    MANDATORY_HOLD_TIME = 1.5
    print(f"Waiting for finger...", end="", flush=True)
    
    start_time = time.time()
    
    while (time.time() - start_time) < timeout_seconds:
        # Check for reset button during fingerprint wait
        if GPIO.input(PIN_BTN_START) == GPIO.LOW:
            print("\n⚠️ Reset pressed")
            return "RESET"
            
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
    finger.set_led(color=1, mode=1) # Breathing
    result = get_image_with_timeout(10.0)
    if result == "RESET":
        finger.set_led(color=3, mode=3) # Off
        return "RESET"
    if not result:
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
            show_msg("Check-in Failed", "Not Found/Voted", "Press START")
            beep(count=1, duration=0.5)
            # Wait for reset button press
            while True:
                if GPIO.input(PIN_BTN_START) == GPIO.LOW:
                    time.sleep(0.2)
                    return "RESET"
                time.sleep(0.1)
    except:
        show_msg("Network Error", "Check Server", "Press START")
        # Wait for reset button press
        while True:
            if GPIO.input(PIN_BTN_START) == GPIO.LOW:
                time.sleep(0.2)
                return "RESET"
            time.sleep(0.1)

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
        # Check for reset button
        if GPIO.input(PIN_BTN_START) == GPIO.LOW:
            time.sleep(0.2)
            print("\n⚠️ Vote cancelled by reset")
            return "RESET"
            
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
    # Verify sensor is working
    if finger.read_sysparam() != adafruit_fingerprint.OK:
        print("❌ Sensor check failed. Please check the wiring.")
        sys.exit(1)
    
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
            show_msg("VOTECHAIN", big_text=True)
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
                # Use direct keyboard device reading (works headless, no terminal focus needed)
                aadhaar = read_aadhaar_from_keyboard_device()
                
                # Check for reset during input
                if aadhaar == "RESET":
                    print("🔄 Reset during Aadhaar input, returning to idle...")
                    idle_message_shown = False
                    continue
                
                # Fallback to simple TTY input if evdev fails
                if not aadhaar:
                    aadhaar = read_aadhaar_simple()
                
                if not aadhaar or aadhaar.strip() == "": 
                    idle_message_shown = False
                    continue # Loop back to check for commands

                # 3. VOTER CHECK-IN
                voter = check_in_voter(aadhaar)
                
                # Check for reset signal from check-in
                if voter == "RESET":
                    print("🔄 Resetting to idle...")
                    idle_message_shown = False
                    continue
                
                if voter:
                    # 4. VERIFY FINGERPRINT
                    show_msg("Verifying...", "Scan Finger", "Or Press START")
                    set_leds(green=False, red=True) 
                    
                    print(f"Expecting Finger ID #{voter['fingerprint_id']}")
                    scanned_id = scan_finger_and_get_id()
                    
                    # Check for reset signal
                    if scanned_id == "RESET":
                        print("🔄 Resetting to idle...")
                        idle_message_shown = False
                        continue
                    
                    if scanned_id == voter['fingerprint_id']:
                        # 5. VOTE INTERFACE
                        print("✅ Identity Verified.")
                        final_choice = run_voting_interface(voter['name'])
                        
                        # Check for reset signal
                        if final_choice == "RESET":
                            print("🔄 Resetting to idle...")
                            idle_message_shown = False
                            continue
                        
                        # 6. SUBMIT
                        submit_vote(aadhaar, final_choice)
                        time.sleep(4)
                    else:
                        print("⛔ Mismatch.")
                        show_msg("Access Denied", "Finger Mismatch", "Press START")
                        set_leds(green=False, red=True)
                        beep(count=3, duration=0.2)
                        # Wait for reset
                        while GPIO.input(PIN_BTN_START) == GPIO.HIGH:
                            time.sleep(0.1)
                        time.sleep(0.2)
                    
                    idle_message_shown = False  # Reset for next iteration
                else:
                    # No voter found but not a reset signal, just go back to idle
                    idle_message_shown = False
            
        except KeyboardInterrupt:
            GPIO.cleanup()
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)