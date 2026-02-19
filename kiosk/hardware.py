import time
import sys
import signal
import atexit
import logging
import os
import threading

# Mocks for non-Pi environments
try:
    import RPi.GPIO as GPIO
    import serial
    import adafruit_fingerprint
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106, ssd1306
    try:
        from PIL import ImageFont
    except ImportError:
        ImageFont = None
    IS_PI = True
except ImportError:
    print("⚠️ Hardware libraries not found. Running in EMULATION mode.")
    IS_PI = False
    GPIO = None
    serial = None
    adafruit_fingerprint = None
    spi = None
    canvas = None
    sh1106 = None
    ssd1306 = None
    ImageFont = None


class KioskHardware:
    def __init__(self):
        global IS_PI
        self.device = None
        self.finger = None
        self.finger_present = False
        # Track whether GPIO was successfully initialised
        self._gpio_ready = False
        
        # PIN CONFIG
        self.PIN_LED_GREEN = 17
        self.PIN_LED_RED = 27
        self.PIN_BUZZER = 18
        self.PIN_BTN_START = 4
        self.PIN_BTN_A = 22
        self.PIN_BTN_B = 23
        self.OLED_DC = 24
        self.OLED_RST = 25

        if IS_PI:
            try:
                self._setup_gpio()
            except Exception as e:
                logging.error(f"GPIO init failed: {e}")
            self._setup_oled()
            self._setup_fingerprint()
            # Optional: start button debug thread when enabled in environment
            try:
                if os.getenv('BUTTON_DEBUG') == '1':
                    self._start_button_debug()
            except Exception:
                pass
            # ensure cleanup on signals
            atexit.register(self._safe_cleanup)
            signal.signal(signal.SIGTERM, lambda s,f: self._safe_cleanup() or sys.exit(0))
            signal.signal(signal.SIGINT, lambda s,f: self._safe_cleanup() or sys.exit(0))
        # Last display cache to avoid rapid duplicate redraws
        self._last_display = (None, None, None, None)
        self._last_display_time = 0

    def _setup_gpio(self):
        GPIO.setwarnings(False)
        # Attempt to cleanup any stale configuration using a new handle context if possible
        print("[GPIO] Starting setup...")
        try:
            GPIO.cleanup()
            print("[GPIO] Cleanup success")
        except Exception as e:
            print(f"[GPIO] Cleanup warning: {e}")

        try:
            GPIO.setmode(GPIO.BCM)
            print("[GPIO] Mode set to BCM")
        except Exception as e:
            print(f"[GPIO] Setmode warning: {e}")

        # Setup pins one by one with logging
        pins = [
            (self.PIN_LED_GREEN, GPIO.OUT, GPIO.LOW, "LED_GREEN"),
            (self.PIN_LED_RED, GPIO.OUT, GPIO.LOW, "LED_RED"),
            (self.PIN_BUZZER, GPIO.OUT, GPIO.LOW, "BUZZER"),
            (self.PIN_BTN_START, GPIO.IN, None, "BTN_START"),
            (self.PIN_BTN_A, GPIO.IN, None, "BTN_A"),
            (self.PIN_BTN_B, GPIO.IN, None, "BTN_B")
        ]

        for pin, mode, initial, name in pins:
            try:
                print(f"[GPIO] Setting up {name} (Pin {pin})...")
                if mode == GPIO.OUT:
                    GPIO.setup(pin, mode, initial=initial)
                else:
                    GPIO.setup(pin, mode, pull_up_down=GPIO.PUD_UP)
                print(f"[GPIO] {name} OK")
            except Exception as e:
                print(f"[GPIO] FAILED to setup {name} (Pin {pin}): {e}")
                # We raise here to let the main handler know, or we could continue?
                # For now, let's Raise so we see the error in main logs properly
                raise e
        
        self._gpio_ready = True
        print("[GPIO] Setup Complete")

    def _setup_oled(self):
        try:
            serial_conn = spi(device=0, port=0, gpio_DC=self.OLED_DC, gpio_RST=self.OLED_RST)
            try:
                self.device = sh1106(serial_conn)
            except:
                self.device = ssd1306(serial_conn)
            print("✅ OLED initialized.")
        except Exception as e:
            print(f"❌ OLED Init Failed: {e}")

    def _setup_fingerprint(self):
        try:
            # Increase serial read timeout to reduce spurious FAIL responses
            uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=3)
            self.finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
            print("✅ Fingerprint Sensor initialized.")
        except Exception as e:
            print(f"❌ Fingerprint Init Failed: {e}")

    def cleanup(self):
        if IS_PI:
            # Try to turn LEDs off first while GPIO mode is still valid,
            # then release the GPIO resources. Ensure we clear the flag
            # so subsequent calls become no-ops.
            try:
                try:
                    self.set_leds(False, False)
                except Exception:
                    pass
            finally:
                try:
                    GPIO.cleanup()
                except Exception:
                    pass
                self._gpio_ready = False

    def _safe_cleanup(self):
        try:
            self.cleanup()
        except Exception:
            pass

    def set_leds(self, green=False, red=False):
        if IS_PI and self._gpio_ready:
            try:
                GPIO.output(self.PIN_LED_GREEN, GPIO.HIGH if green else GPIO.LOW)
                GPIO.output(self.PIN_LED_RED, GPIO.HIGH if red else GPIO.LOW)
            except Exception:
                # Ignore GPIO runtime errors during shutdown or transient I/O
                # Do NOT mark GPIO as not-ready here — that can disable button reads.
                return
        else:
            print(f"[HW] LEDs -> Green:{green} Red:{red}")

    def beep(self, count=1, duration=0.1):
        if IS_PI and self._gpio_ready:
            for _ in range(count):
                try:
                    GPIO.output(self.PIN_BUZZER, GPIO.HIGH)
                    time.sleep(duration)
                    GPIO.output(self.PIN_BUZZER, GPIO.LOW)
                    time.sleep(0.05)
                except Exception:
                    break
        else:
            print(f"[HW] BEEP x{count}")

    def is_button_pressed(self, btn_name):
        return self.is_button_pressed_debounced(btn_name)

    def is_button_pressed_debounced(self, btn_name, stable_ms=40):
        """Debounced read: require stable LOW for stable_ms milliseconds.

        Keeps compatibility with previous API but reduces missed presses from
        bounce or light taps.
        """
        if not IS_PI or not self._gpio_ready:
            return False
        pin_map = {'START': self.PIN_BTN_START, 'A': self.PIN_BTN_A, 'B': self.PIN_BTN_B}
        pin = pin_map.get(btn_name)
        if pin is None:
            return False

        # immediate check
        try:
            if GPIO.input(pin) != GPIO.LOW:
                return False
        except Exception:
            return False

        # require it remain LOW for stable_ms (sample every 10ms)
        # use slightly shorter debounce for responsiveness on light taps
        checks = max(1, max(1, (stable_ms // 10)))
        for _ in range(checks):
            time.sleep(stable_ms / (checks * 1000.0))
            try:
                if GPIO.input(pin) != GPIO.LOW:
                    return False
            except Exception:
                return False
        return True

    def show_msg(self, line1, line2="", line3="", big_text=False):
        # Avoid frequent duplicate updates to the OLED which can cause flicker
        now = time.time()
        if (line1, line2, line3, big_text) == self._last_display and (now - self._last_display_time) < 0.1:
            # skip redraw
            return
        self._last_display = (line1, line2, line3, big_text)
        self._last_display_time = now
        print(f"[DISPLAY] {line1} | {line2} | {line3}")
        if not self.device: return
        try:
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, fill="black")
                try:
                    if big_text and ImageFont:
                        # Reduced size to fit footer (Press START)
                        # Line 1 at y=0, Line 2 at y=28. Max height ~56px.
                        for y, txt in [(0, str(line1)), (28, str(line2))]:
                            size = 28
                            while size > 10:
                                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
                                try:
                                    w, h = draw.textsize(txt, font=font)
                                except AttributeError:
                                    w = draw.textlength(txt, font=font)
                                    h = size
                                
                                if w < 126: break
                                size -= 2
                            
                            x = (128 - w) // 2
                            draw.text((x, y), txt, fill="white", font=font)

                        if line3:
                             font3 = ImageFont.load_default() 
                             try: w3, h3 = draw.textsize(str(line3), font=font3)
                             except: w3 = draw.textlength(str(line3), font=font3)
                             x3 = (128 - w3) // 2
                             draw.text((x3, 54), str(line3), fill="white", font=font3)
                    else:
                        # Use Size 10 for guaranteed fit on 128x64
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                        
                        # Diagnostic: confirm what is actually hitting the drawing buffer
                        print(f"[DRAW] L1={line1} L2={line2} L3={line3}")

                        # Center aligned normal text
                        for i, line in enumerate([line1, line2, line3]):
                            txt = str(line)
                            if not txt: continue
                            try:
                                w, h = draw.textsize(txt, font=font)
                            except AttributeError:
                                w = draw.textlength(txt, font=font)
                            
                            x = (128 - w) // 2
                            # Even spacing: y=10, y=30, y=50
                            y = 10 + (i * 20)
                            draw.text((x, y), txt, fill="white", font=font)
                except Exception as e:
                    print(f"[DISPLAY] Font error: {e}")
                    pass # Font loading fallback
        except Exception:
            # If the display or GPIO used by the display errors during shutdown,
            # fallback to console-only behaviour and avoid raising.
            try:
                print(f"[DISPLAY-ERR] {line1} | {line2} | {line3}")
            except Exception:
                pass

    def set_sensor_led(self, color=1, mode=3, speed=0):
        """
        Control the fingerprint sensor's built-in LED.
        Color: 1=Red, 2=Blue/Green, 3=Purple
        Mode: 1=Breathing, 2=Flashing, 3=Solid, 4=Off, 5=Fade In, 6=Fade Out
        """
        if self.finger:
            try:
                self.finger.set_led(color=color, mode=mode, speed=speed)
            except Exception:
                pass

    def scan_finger(self):
        """
        Captures a fingerprint and searches the library for a match (1:N).
        Uses proven 2-second hold logic and LED feedback.
        """
        # Configuration
        try:
            wait_seconds = int(os.getenv('FINGER_WAIT_SECONDS', '15'))
        except Exception:
            wait_seconds = 15
        
        MANDATORY_HOLD_TIME = 2.0
        poll_interval = 0.25

        if not self.finger:
            print("[FINGER] No fingerprint device attached.")
            return None

        # Set LED to breathing red/blue (Mode 1, Color 1) for scanning
        self.set_sensor_led(color=1, mode=1)
        
        deadline = time.time() + wait_seconds
        found_finger = False

        # 1. Wait for finger & Hold
        while time.time() < deadline:
            # Allow cancellation from UI
            if self.is_button_pressed('START'):
                self.set_sensor_led(color=1, mode=4) # Off
                return None

            try:
                img_res = self.finger.get_image()
            except Exception as e:
                print(f"[FINGER] get_image EXCEPTION: {e}")
                img_res = adafruit_fingerprint.IMAGEFAIL

            if img_res == adafruit_fingerprint.OK:
                # Finger detected! Enforce 2-second hold.
                print(f"[FINGER] Finger detected. Holding 2s...")
                try:
                     self.show_msg("Keep Steady", "Hold Finger", "Capturing...")
                except: pass

                hold_start = time.time()
                while (time.time() - hold_start) < MANDATORY_HOLD_TIME:
                    try:
                        self.finger.get_image()
                    except Exception:
                        pass
                    time.sleep(0.1)
                
                found_finger = True
                break
            
            elif img_res == adafruit_fingerprint.NOFINGER:
                 # Update UI countdown if needed, but avoid spam
                 pass
            elif img_res == adafruit_fingerprint.IMAGEFAIL:
                print("[FINGER] Imaging error")
                self.set_sensor_led(color=1, mode=3) # Solid Red
                return None
            
            time.sleep(poll_interval)

        if not found_finger:
            print("[FINGER] Timeout: No finger detected.")
            self.set_sensor_led(color=1, mode=3) # Solid Red
            return None

        # 2. Template
        try:
            tz_res = self.finger.image_2_tz(1)
        except Exception as e:
            print(f"[FINGER] image_2_tz EXCEPTION: {e}")
            tz_res = adafruit_fingerprint.IMAGEFAIL

        if tz_res != adafruit_fingerprint.OK:
            print(f"[FINGER] Templating failed: {tz_res}")
            self.set_sensor_led(color=1, mode=3) # Solid Red
            return None

        # 3. Search
        try:
            search_res = self.finger.finger_search()
        except Exception as e:
            print(f"[FINGER] finger_search EXCEPTION: {e}")
            search_res = adafruit_fingerprint.IMAGEFAIL

        if search_res == adafruit_fingerprint.OK:
            # MATCH FOUND
            fid = self.finger.finger_id
            print(f"[FINGER] Match found: id={fid}, confidence={self.finger.confidence}")
            self.set_sensor_led(color=2, mode=3) # Solid Blue/Green (Success)
            return fid
        else:
            # NO MATCH
            print("[FINGER] No match found.")
            self.set_sensor_led(color=1, mode=3) # Solid Red (Failure)
            return None

    def enroll_finger_logic(self, location_id):
        if not self.finger: return False
        # Deprecated placeholder — use `robust_enroll` instead for full flow
        return False

    def robust_enroll(self, target_id: int) -> bool:
        """Robust enrollment routine using proven 2-second hold logic.

        1. Wait for finger.
        2. Force 2.0s hold while sampling.
        3. Convert image to template.
        4. Repeat for second scan.
        5. Create and store model.
        """
        if not self.finger:
            print("[FINGER] ERROR: No sensor attached")
            return False

        # Validate slot
        try:
            slot_min, slot_max = 1, 162
            if target_id < slot_min or target_id > slot_max:
                print(f"[FINGER] ERROR: Invalid slot {target_id}")
                return False
        except Exception:
            pass

        # Configuration
        # The user's script uses a shorter initial timeout (10s) but we'll stick to env or default
        try:
            timeout_seconds = int(os.getenv('FINGER_WAIT_SECONDS', '15'))
        except Exception:
            timeout_seconds = 15
        
        MANDATORY_HOLD_TIME = 2.0

        def get_image_with_hold(label: str) -> bool:
            """Waits for finger, then enforces 2s hold."""
            deadline = time.time() + timeout_seconds
            print(f"[FINGER] {label}: Waiting for finger...")
            self.show_msg("Place Finger", label, f"{timeout_seconds}s Timeout")

            # 1. Initial wait for finger placement
            while time.time() < deadline:
                # Allow user cancel
                if self.is_button_pressed('START'):
                    return False

                try:
                    i = self.finger.get_image()
                except Exception as e:
                    print(f"[FINGER] get_image exception: {e}")
                    i = adafruit_fingerprint.IMAGEFAIL

                if i == adafruit_fingerprint.OK:
                    # Finger detected! Enforce 2-second hold.
                    print(f"[FINGER] {label}: Finger detected. Holding 2s...")
                    self.show_msg("Keep Steady", "Hold Finger", "Capturing...")
                    
                    hold_start = time.time()
                    while (time.time() - hold_start) < MANDATORY_HOLD_TIME:
                        try:
                            self.finger.get_image()
                        except Exception:
                            pass
                        time.sleep(0.1)

                    print(f"[FINGER] {label}: Capture complete.")
                    return True
                
                elif i == adafruit_fingerprint.NOFINGER:
                    # blink dot or update timer?
                    # Minimal updates to avoid I/O spam
                    pass
                elif i == adafruit_fingerprint.IMAGEFAIL:
                    print(f"[FINGER] {label}: Imaging error")
                    return False
                else:
                    print(f"[FINGER] {label}: Error code {i}")
                    return False
                
                time.sleep(0.1)

            print(f"[FINGER] {label}: Timeout")
            self.show_msg("Enroll Failed", "Timeout", "Try Again")
            return False

        # --- SCAN 1 ---
        print(f"[FINGER] Starting enroll ID {target_id} - Scan 1")
        self.show_msg("Enroll Mode", f"ID #{target_id}", "Scan 1/2")
        
        if not get_image_with_hold("Scan 1"):
            return False

        print("[FINGER] Templating scan 1...")
        i = self.image_2_tz(1)
        if i != adafruit_fingerprint.OK:
            print(f"[FINGER] Templating failed: {i}")
            self.show_msg("Error", "Bad Image", "Try Again")
            return False

        print("[FINGER] Waiting for removal...")
        self.show_msg("Remove Finger", "", "To Continue")
        # specific wait logic from script
        while True:
            try:
                if self.finger.get_image() == adafruit_fingerprint.NOFINGER:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        print("[FINGER] Finger removed.")

        # --- SCAN 2 ---
        print("[FINGER] Starting Scan 2")
        self.show_msg("Place Again", "Scan 2/2", "")
        time.sleep(1) # small pause before sensing again

        if not get_image_with_hold("Scan 2"):
            return False

        print("[FINGER] Templating scan 2...")
        i = self.image_2_tz(2)
        if i != adafruit_fingerprint.OK:
            print(f"[FINGER] Templating failed: {i}")
            self.show_msg("Error", "Bad Image", "Try Again")
            return False

        # --- CREATE MODEL ---
        print("[FINGER] Creating model...")
        i = self.create_model()
        if i == adafruit_fingerprint.OK:
            print("[FINGER] Model created.")
        else:
            if i == adafruit_fingerprint.ENROLLMISMATCH:
                print("[FINGER] Mismatch!")
                self.show_msg("Enroll Failed", "Finger Mismatch", "Try Again")
            else:
                print(f"[FINGER] Model error: {i}")
                self.show_msg("Error", "Model Create", "Failed")
            return False

        # --- STORE MODEL ---
        print(f"[FINGER] Storing at {target_id}...")
        i = self.store_model(target_id)
        if i == adafruit_fingerprint.OK:
            print(f"[FINGER] Success! stored at {target_id}")
            self.show_msg("Success!", f"ID #{target_id}", "Enrolled")
            return True
        else:
            print(f"[FINGER] Store failed: {i}")
            self.show_msg("Storage Error", "Write Failed", "")
            return False

    # Low level access for complex flows
    def get_finger_image(self):
        if not self.finger: 
            # Simulation
            # time.sleep(1)
            # return adafruit_fingerprint.OK
            return adafruit_fingerprint.NOFINGER
        return self.finger.get_image()
    
    def image_2_tz(self, slot=1):
        if not self.finger: return adafruit_fingerprint.OK
        return self.finger.image_2_tz(slot)
    
    def create_model(self):
        if not self.finger: return adafruit_fingerprint.OK
        return self.finger.create_model()
    
    def store_model(self, location):
        if not self.finger: return adafruit_fingerprint.OK
        return self.finger.store_model(location)

    def wait_for_finger_release(self):
        if not self.finger: return
        # Avoid tight busy-loop; yield briefly between checks
        while self.finger.get_image() != adafruit_fingerprint.NOFINGER:
            time.sleep(0.1)

    def wipe_fingerprints(self) -> bool:
        """Danger Zone: Deletes all templates from the sensor."""
        if not self.finger: return False
        try:
            print("[FINGER] Wiping all fingerprints...")
            if self.finger.empty_library() == adafruit_fingerprint.OK:
                print("[FINGER] Library wiped successfully.")
                return True
            else:
                print("[FINGER] Failed to empty library.")
        except Exception as e:
            print(f"[FINGER] Wipe exception: {e}")
        return False

    def _start_button_debug(self):
        """Start a background thread that logs button pin values when they change.

        Enable by exporting `BUTTON_DEBUG=1` in the environment before starting
        the kiosk. This is non-intrusive and runs only when requested.
        """
        def _dbg():
            prev = {}
            pins = {'START': self.PIN_BTN_START, 'A': self.PIN_BTN_A, 'B': self.PIN_BTN_B}
            while True:
                for name, pin in pins.items():
                    try:
                        val = GPIO.input(pin) if IS_PI and self._gpio_ready else None
                    except Exception as e:
                        val = f"ERR:{e}"
                    if prev.get(name) != val:
                        logging.info(f"[BUTTON-DBG] {name} pin={pin} val={val}")
                        prev[name] = val
                time.sleep(0.2)

        t = threading.Thread(target=_dbg, daemon=True)
        t.start()

hardware = KioskHardware()
