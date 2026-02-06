#!/usr/bin/env python3
"""
VoteChain V3 Kiosk - Main Entry Point
Biometric voting terminal with fingerprint authentication
"""

import time
import sys
import tty
import termios
import select
import atexit
import threading

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

# Pre-declare globals to satisfy static analysis (will be initialized later)
device = None

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


# --- HARDWARE HEALTH CHECK ---

def hardware_health_check(device):
    status = {}
    # Test LEDs
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PIN_LED_GREEN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(PIN_LED_RED, GPIO.OUT, initial=GPIO.LOW)
        GPIO.output(PIN_LED_GREEN, GPIO.HIGH)
        GPIO.output(PIN_LED_RED, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(PIN_LED_GREEN, GPIO.LOW)
        GPIO.output(PIN_LED_RED, GPIO.LOW)
        status['LEDs'] = 'OK'
    except Exception as e:
        status['LEDs'] = f"FAIL: {e}"
    # Test Buttons
    try:
        GPIO.setup(PIN_BTN_START, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PIN_BTN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PIN_BTN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        btns = [GPIO.input(PIN_BTN_START), GPIO.input(PIN_BTN_A), GPIO.input(PIN_BTN_B)]
        status['Buttons'] = 'OK' if all(x in [0,1] for x in btns) else 'FAIL: Bad read'
    except Exception as e:
        status['Buttons'] = f"FAIL: {e}"
    # Test OLED
    try:
        if 'device' in globals() and device:
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
                draw.text((10, 10), "OLED OK", fill="white")
            status['OLED'] = 'OK'
        else:
            status['OLED'] = 'FAIL: Not initialized'
    except Exception as e:
        status['OLED'] = f"FAIL: {e}"
    print("Hardware Health Check:")
    for k,v in status.items():
        print(f"  {k}: {v}")
    # Show status on OLED
    try:
        lines = [f"{k}: {v}" for k,v in status.items()]
        if 'device' in globals() and device:
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
                for i, line in enumerate(lines):
                    draw.text((5, 8 + i*14), line, fill="white")
            time.sleep(2)
    except Exception:
        pass
    return status

# Initialize OLED once


# --- 1. SENSOR SETUP ---
finger = None
finger_error = None
try:
    uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
    print("✓ Fingerprint sensor initialized")
except Exception as e:
    finger_error = str(e)
    print(f"❌ FATAL: Fingerprint sensor unavailable: {e}")
    print("❌ Please check the wiring and connections.")
    print("❌ Cannot start kiosk without fingerprint scanner.")
    try:
        if 'device' in globals() and device:
            from luma.core.render import canvas
            from PIL import ImageFont
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except:
                font = None
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
                msg1 = "FINGERPRINT ERROR"
                msg2 = "Check wiring & restart"
                msg3 = f"{finger_error}" if finger_error else ""
                if font:
                    draw.text((10, 10), msg1, fill="white", font=font)
                    draw.text((10, 32), msg2, fill="white", font=font)
                    draw.text((10, 54), msg3[:device.width//8], fill="white", font=font)
                else:
                    draw.text((10, 10), msg1, fill="white")
                    draw.text((10, 32), msg2, fill="white")
                    draw.text((10, 54), msg3[:device.width//8], fill="white")
        # Set red LED directly (set_leds not defined yet)
        try:
            GPIO.output(PIN_LED_RED, GPIO.HIGH)
        except:
            pass
    except Exception as ex:
        print(f"Error displaying fingerprint error: {ex}")
    # Do not exit, just wait for manual intervention
    while True:
        time.sleep(10)

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

if device is None:
    print("❌ SCREEN INITIALIZATION FAILED: Check SPI wiring!")
else:
    print("✅ Screen initialized successfully.")

# --- HELPER FUNCTIONS ---

def beep(count=1, duration=0.1):
    for _ in range(count):
        GPIO.output(PIN_BUZZER, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(PIN_BUZZER, GPIO.LOW)
        time.sleep(0.05)

def beep_success():
    beep(2, 0.08)

def beep_error():
    beep(1, 0.5)
    time.sleep(0.1)
    beep(1, 0.2)

def beep_prompt():
    beep(1, 0.05)

def wait_for_reset():
    """Wait for the START button to be pressed, then return 'RESET'."""
    while True:
        if GPIO.input(PIN_BTN_START) == GPIO.LOW:
            time.sleep(0.2)
            return "RESET"
        time.sleep(0.1)

def set_leds(green=False, red=False):
    GPIO.output(PIN_LED_GREEN, GPIO.HIGH if green else GPIO.LOW)
    GPIO.output(PIN_LED_RED, GPIO.HIGH if red else GPIO.LOW)

def show_msg(line1, line2="", line3="", big_text=False):
    print(f"[DISPLAY] {line1} | {line2} | {line3}")
    # Try to import ImageFont once; if not available, leave as None and fall back to default rendering
    try:
        from PIL import ImageFont
    except Exception:
        ImageFont = None
    # LED Logic
    l1 = str(line1).lower()
    l2 = str(line2).lower()
    if "idle" in l1 or "votechain" in l1 or "enter aadhaar" in l1:
        set_leds(green=True, red=False)
    elif "submitting" in l1 or "waiting" in l2:
        set_leds(green=True, red=True)
    elif "confirmed" in l1 or "success" in l2:
        set_leds(green=True, red=False)
    elif "rejected" in l1 or "fail" in l2 or "denied" in l2 or "mismatch" in l2:
        set_leds(green=False, red=True)
    # Screen Logic
    if device:
        try:
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
                if big_text:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                    except:
                        font = ImageFont.load_default()
                    draw.text((5, 20), str(line1), fill="white", font=font)
                else:
                    font = ImageFont.load_default()
                    draw.text((5, 5), str(line1), fill="white", font=font)
                    draw.text((5, 25), str(line2), fill="white", font=font)
                    draw.text((5, 45), str(line3), fill="white", font=font)
        except Exception as e:
            print(f"⚠️ Screen Draw Error: {e}")
    else:
        print("⚠️ Screen not initialized (device is None)")


def show_idle():
    """Display the idle screen: two-line centered title "VOTE" / "CHAIN" with larger font and shadow.

    This rendering is only used for the idle screen; other screens still use `show_msg()`.
    """
    # If device not ready, fall back to basic message
    if not ('device' in globals() and device):
        try:
            show_msg("VOTE", "CHAIN", "")
        except Exception:
            pass
        return

    try:
        from PIL import ImageFont
    except Exception:
        ImageFont = None

    try:
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, fill="black")

            line1 = "VOTE"
            line2 = "CHAIN"

            # Preferred larger font for idle title; fallback to default if unavailable
            preferred_size = 28
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", preferred_size)
            except Exception:
                try:
                    font = ImageFont.load_default() if ImageFont else None
                except Exception:
                    font = None

            if font:
                bbox1 = draw.textbbox((0, 0), line1, font=font)
                tw1 = bbox1[2] - bbox1[0]
                th1 = bbox1[3] - bbox1[1]
                bbox2 = draw.textbbox((0, 0), line2, font=font)
                tw2 = bbox2[2] - bbox2[0]
                th2 = bbox2[3] - bbox2[1]
            else:
                tw1 = len(line1) * 7
                th1 = 8
                tw2 = len(line2) * 7
                th2 = 8

            total_h = th1 + th2 + 4  # small spacing between lines
            y_start = max(0, (device.height - total_h) // 2)

            # Center each line horizontally
            x1 = max(0, (device.width - tw1) // 2)
            x2 = max(0, (device.width - tw2) // 2)

            # Draw a more prominent layered shadow for visual depth
            # Two layered offsets: a larger darker shadow, then a lighter one closer to the text
            shadow_layers = [ (2, -2, "dimgray"), (1, -1, "gray") ]
            for ox, oy, col in shadow_layers:
                draw.text((x1 + ox, y_start + oy), line1, fill=col, font=font)
                draw.text((x2 + ox, y_start + th1 + 4 + oy), line2, fill=col, font=font)

            # Draw main (foreground) text on top
            draw.text((x1, y_start), line1, fill="white", font=font)
            draw.text((x2, y_start + th1 + 4), line2, fill="white", font=font)
    except Exception as e:
        print(f"⚠️ Idle Draw Error: {e}")
def read_aadhaar_simple(max_len: int = 12) -> str:
    """This is the most reliable method for headless operation."""
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
    """
    Read Aadhaar digits from keyboard, reflecting input on OLED line 3.
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
        # Return None to allow retry logic to handle this
        return None
    print("Templating...", end="")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        finger.set_led(color=1, mode=3)
        # Return None to allow retry logic to handle this
        return None
    print("Searching...", end="")
    if finger.finger_search() == adafruit_fingerprint.OK:
        finger.set_led(color=2, mode=3) # Green success
        return finger.finger_id
    else:
        finger.set_led(color=1, mode=3) # Red fail
        # Return None to allow retry logic to handle this
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
            return wait_for_reset()
    except:
        show_msg("Network Error", "Check Server", "Press START")
        return wait_for_reset()

def submit_vote(aadhaar_id, candidate_id):
    show_msg("Submitting...", "Waiting for confirmation", "May take up to 90s")
    set_leds(green=True, red=True)

    stop_event = threading.Event()

    def spinner_animation(stop_evt, max_seconds=90):
        if not device:
            return
        start = time.time()
        frames = ['|','/','-','\\']
        idx = 0
        bar_x = 6
        bar_y = device.height - 12
        bar_w = device.width - 12
        while not stop_evt.is_set():
            elapsed = time.time() - start
            progress = min(1.0, elapsed / float(max_seconds)) if max_seconds > 0 else 0
            fill_w = int(bar_w * progress)
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
                # Title
                draw.text((5, 8), "Submitting...", fill="white")
                # Spinner
                draw.text((device.width - 12, 6), frames[idx % len(frames)], fill="white")
                # Progress bar outline
                draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + 6), outline="white", fill=None)
                # Progress fill
                if fill_w > 0:
                    draw.rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + 6), outline="white", fill="white")
            idx += 1
            time.sleep(0.12)

    spinner_thread = threading.Thread(target=spinner_animation, args=(stop_event, 90), daemon=True)
    spinner_thread.start()

    try:
        response = requests.post(f"{BACKEND_URL}/api/vote", 
                                 json={"aadhaar_id": aadhaar_id, "candidate_id": candidate_id}, timeout=90)
        # Stop spinner
        stop_event.set()
        spinner_thread.join(timeout=1)

        if response.status_code == 200:
            data = response.json().get('data', {})
            tx_hash = data.get('transaction_hash')
            # backend may return 'receipt_code' or 'short_code' depending on implementation
            short_code = data.get('receipt_code') or data.get('short_code')

            # Show confirmed screen and animation (we wait for code before final receipt)
            show_msg("Vote Confirmed!", "Finalizing...", "", big_text=True)
            tick_animation()
            set_leds(green=True, red=False)
            print(f"TX: {tx_hash}")
            beep_success()

            # If backend already returned a short code, display immediately
            if short_code:
                receipt_code = short_code
            else:
                # Poll backend lookup endpoint for receipt code (gives backend time to insert)
                receipt_code = None
                poll_start = time.time()
                poll_timeout = 60  # seconds
                poll_interval = 1.0
                show_msg("Finalizing...", "Waiting for receipt code", "")
                while time.time() - poll_start < poll_timeout:
                    try:
                        r = requests.post(f"{BACKEND_URL}/api/lookup-receipt", json={"tx_hash": tx_hash}, timeout=5)
                        if r.status_code == 200:
                            j = r.json()
                            receipt_code = j.get('code')
                            if receipt_code:
                                break
                    except Exception:
                        pass
                    time.sleep(poll_interval)

            # If we still don't have a receipt code, fall back to placeholder and instruct manual verify
            if not receipt_code:
                receipt_display = "------"
                # Show fallback screen with tx hash for manual verification
                cand_name = "CANDIDATE A" if candidate_id == 1 else "CANDIDATE B"
                show_msg("Vote Receipt:", f"Code: {receipt_display}", f"{cand_name}")
                # Also show instruction to verify via tx hash
                show_msg("Verify Manually:", tx_hash[:12] + "...", "Use verify.html")
            else:
                receipt_display = receipt_code
                cand_name = "CANDIDATE A" if candidate_id == 1 else "CANDIDATE B"
                show_msg("Vote Receipt:", f"Code: {receipt_display}", f"{cand_name}")

            # Wait for admin/start button to be pressed before continuing
            while GPIO.input(PIN_BTN_START) != GPIO.LOW:
                time.sleep(0.1)
            time.sleep(0.2)  # Debounce
            show_msg("Vote Submitted!", "Thank you", "")
            time.sleep(2)
            return True
        else:
            # Stop spinner already requested
            try:
                err = response.json()
                msg = err.get('message', '')
                if 'not active' in msg.lower() or 'inactive' in msg.lower() or 'election' in msg.lower():
                    show_msg("Vote Rejected", "Election Not Active", "Start election in admin")
                elif 'timeout' in msg.lower():
                    show_msg("Network Timeout", "Retry", "Blockchain slow")
                else:
                    show_msg("Vote Rejected", msg or "Error")
            except Exception:
                show_msg("Vote Rejected", "Error")
            set_leds(green=False, red=True)
            beep_error()
            return False
    except Exception as e:
        # Ensure spinner stops
        stop_event.set()
        try:
            spinner_thread.join(timeout=0.5)
        except Exception:
            pass
        show_msg("Connection Fail", "Retry")
        print(f"Vote error: {e}")
        beep_error()
        return False

def tick_animation():
    set_leds(green=True, red=False)
    if device:
        from PIL import ImageDraw
        # Progressive draw: first segment, then second
        x0, y0 = 40, 40  # Start
        x1, y1 = 55, 55  # Middle
        x2, y2 = 85, 25  # End
        steps1 = 8
        steps2 = 10
        # Draw first segment progressively
        for i in range(1, steps1 + 1):
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
                # Interpolate point
                xi = x0 + (x1 - x0) * i / steps1
                yi = y0 + (y1 - y0) * i / steps1
                draw.line((x0, y0, xi, yi), fill="white", width=6)
            time.sleep(0.02)
        # Draw second segment progressively
        for i in range(1, steps2 + 1):
            with canvas(device) as draw:
                draw.rectangle(device.bounding_box, fill="black")
                # Draw full first segment
                draw.line((x0, y0, x1, y1), fill="white", width=6)
                # Interpolate second segment
                xi = x1 + (x2 - x1) * i / steps2
                yi = y1 + (y2 - y1) * i / steps2
                draw.line((x1, y1, xi, yi), fill="white", width=6)
            time.sleep(0.02)
        # Hold final tick
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, fill="black")
            draw.line((x0, y0, x1, y1), fill="white", width=6)
            draw.line((x1, y1, x2, y2), fill="white", width=6)
        time.sleep(0.18)

def run_voting_interface(voter_name):
    show_msg(f"Hi {voter_name}", "Select Candidate:", "A (Btn1) | B (Btn2)")
    set_leds(green=True, red=False)
    beep(count=1)
    
    selected_candidate = None
    start_time = time.time()
    while True:
        if time.time() - start_time > 60:
            show_msg("Session timed out", "Returning to idle", "")
            time.sleep(2)
            return "RESET"
        # Check for reset button
        if GPIO.input(PIN_BTN_START) == GPIO.LOW:
            time.sleep(0.2)
            print("\n⚠️ Vote cancelled by reset")
            return "RESET"
        # 1. Wait for input
        if GPIO.input(PIN_BTN_A) == GPIO.LOW:
            new_selection = 1
            beep(count=1, duration=0.05)
            start_time = time.time()  # Reset the timer on input
            time.sleep(0.3)
        elif GPIO.input(PIN_BTN_B) == GPIO.LOW:
            new_selection = 2
            beep(count=1, duration=0.05)
            start_time = time.time()  # Reset the timer on input
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
    # Run hardware health check on boot
    hardware_health_check(device)
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
            show_idle()
            print("\n⏳ Polling for commands... (Press Ctrl+C to exit)")
            idle_message_shown = True
        # Small delay to prevent CPU spinning, then poll again
        time.sleep(0.5)
        
        # Check if START button is pressed to begin voting
        if GPIO.input(PIN_BTN_START) == GPIO.LOW:
            try:
                time.sleep(0.2)  # Debounce
                # Use direct keyboard device reading (works headless, no terminal focus needed)
                aadhaar = read_aadhaar_from_keyboard_device()
                # Check for reset during input
                if aadhaar == "RESET" or not aadhaar or aadhaar.strip() == "":
                    print("🔄 Reset during Aadhaar input or empty, returning to idle...")
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
                    # 4. VERIFY FINGERPRINT (allow one retry)
                    show_msg("Verifying...", "Scan Finger", "Or Press START")
                    set_leds(green=True, red=False)
                    print(f"Expecting Finger ID #{voter['fingerprint_id']}")

                    verified = False
                    max_attempts = 2
                    attempt = 0
                    while attempt < max_attempts:
                        scanned_id = scan_finger_and_get_id()
                        # Check for reset signal
                        if scanned_id == "RESET":
                            print("🔄 Resetting to idle...")
                            idle_message_shown = False
                            verified = False
                            break
                        # Successful match
                        if scanned_id == voter['fingerprint_id']:
                            verified = True
                            break
                        
                        # Failed scan (None) or wrong fingerprint ID
                        attempt += 1
                        if attempt < max_attempts:
                            if scanned_id is None:
                                print("⚠️ Scan failed — prompting retry")
                                show_msg("Scan Failed", "Try again", "Attempt 2 of 2")
                            else:
                                print(f"⚠️ Wrong finger (got ID #{scanned_id}) — prompting retry")
                                show_msg("Wrong Finger", "Try again", "Attempt 2 of 2")
                            # Audible prompt
                            try:
                                beep(count=1, duration=0.05)
                            except Exception:
                                pass
                            time.sleep(1)
                            # loop to allow next scan
                            continue
                        else:
                            # Exhausted attempts
                            verified = False
                            break

                    if not verified:
                        # Deny access and return to idle (do not block waiting for START)
                        if scanned_id is None:
                            print("⛔ Scan failed after retries.")
                            show_msg("Access Denied", "Scan Failed", "Press START")
                        else:
                            print("⛔ Mismatch after retries.")
                            show_msg("Access Denied", "Finger Mismatch", "Press START")
                        set_leds(green=False, red=True)
                        try:
                            beep(count=3, duration=0.2)
                        except Exception:
                            pass
                        # Wait for START button to reset
                        while True:
                            if GPIO.input(PIN_BTN_START) == GPIO.LOW:
                                time.sleep(0.2)
                                idle_message_shown = False
                                break
                            time.sleep(0.1)
                        continue

                    # 5. VOTE INTERFACE (identity verified)
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
                    idle_message_shown = False  # Reset for next iteration
                else:
                    # No voter found but not a reset signal, just go back to idle
                    idle_message_shown = False
            except KeyboardInterrupt:
                GPIO.cleanup()
                break
            except Exception as e:
                print(f"Error: {e}")
                idle_message_shown = False
                time.sleep(2)