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
        # Be tolerant: attempt to set mode and claim pins; raise if unrecoverable
        try:
            GPIO.setmode(GPIO.BCM)
        except Exception:
            # if mode already set or backend uses different mechanism, continue
            pass

        GPIO.setup(self.PIN_LED_GREEN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.PIN_LED_RED, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.PIN_BTN_START, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BTN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BTN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # mark GPIO as ready for use
        self._gpio_ready = True

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
        if (line1, line2, line3, big_text) == self._last_display and (now - self._last_display_time) < 0.5:
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
                        # SUPER BOLD: Size 32 for "Massive" impact
                        for y, txt in [(0, str(line1)), (32, str(line2))]:
                            size = 34
                            while size > 10:
                                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
                                try:
                                    w, h = draw.textsize(txt, font=font)
                                except AttributeError:
                                    w = draw.textlength(txt, font=font)
                                    h = size # Approximate height
                                
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
                        font = ImageFont.load_default() if ImageFont else None
                        draw.text((5, 5), str(line1), fill="white", font=font)
                        draw.text((5, 25), str(line2), fill="white", font=font)
                        draw.text((5, 45), str(line3), fill="white", font=font)
                except Exception:
                    pass # Font loading fallback
        except Exception:
            # If the display or GPIO used by the display errors during shutdown,
            # fallback to console-only behaviour and avoid raising.
            try:
                print(f"[DISPLAY-ERR] {line1} | {line2} | {line3}")
            except Exception:
                pass

    def scan_finger(self):
        # Provide detailed console diagnostics for each scan step to aid
        # debugging in the field when matching fails. Wait up to `wait_seconds`
        # for the user to place a finger so late placements are tolerated.
        # Allow configuration of wait time via environment for field tuning
        try:
            wait_seconds = int(os.getenv('FINGER_WAIT_SECONDS', '15'))
        except Exception:
            wait_seconds = 15
        poll_interval = 0.25

        if not self.finger:
            print("[FINGER] No fingerprint device attached.")
            return None

        deadline = time.time() + wait_seconds
        attempt = 0
        img_res = None
        # Poll for a readable image until timeout
        while time.time() < deadline:
            attempt += 1
            try:
                img_res = self.finger.get_image()
                print(f"[FINGER] get_image attempt={attempt} -> {repr(img_res)}")
            except Exception as e:
                print(f"[FINGER] get_image EXCEPTION: {e}")
                return None

            if img_res == adafruit_fingerprint.OK:
                break
            # brief UI hint (non-blocking) so user knows to press harder/hold
            try:
                # update display if available
                self.show_msg("Hi", "Place Finger", f"{int(deadline-time.time())}s")
            except Exception:
                pass
            time.sleep(poll_interval)

        if img_res != adafruit_fingerprint.OK:
            print("[FINGER] No readable finger image within timeout (NOFINGER or FAIL).")
            return None

        try:
            tz_res = self.finger.image_2_tz(1)
            print(f"[FINGER] image_2_tz -> {repr(tz_res)}")
        except Exception as e:
            print(f"[FINGER] image_2_tz EXCEPTION: {e}")
            return None

        if tz_res != adafruit_fingerprint.OK:
            print("[FINGER] Failed to convert image to template.")
            return None

        try:
            search_res = self.finger.finger_search()
            print(f"[FINGER] finger_search -> {repr(search_res)}")
        except Exception as e:
            print(f"[FINGER] finger_search EXCEPTION: {e}")
            return None

        if search_res != adafruit_fingerprint.OK:
            print("[FINGER] finger_search returned NOT FOUND")
            return None

        try:
            fid = self.finger.finger_id
            print(f"[FINGER] Match found: id={repr(fid)}")
            return fid
        except Exception as e:
            print(f"[FINGER] finger_id read EXCEPTION: {e}")
            return None

    def enroll_finger_logic(self, location_id):
        if not self.finger: return False
        # Deprecated placeholder — use `robust_enroll` instead for full flow
        return False

    def robust_enroll(self, target_id: int) -> bool:
        """Robust enrollment routine with retries, UX updates and logging.

        Waits up to `FINGER_WAIT_SECONDS` for each scan, retries template
        conversion a few times, and performs model creation + storage.
        """
        if not self.finger:
            print("[FINGER] ERROR: No sensor attached")
            return False
        # Typical R307/AS608 capacity; validate slot range conservatively
        try:
            slot_min, slot_max = 1, 162
            if target_id < slot_min or target_id > slot_max:
                print(f"[FINGER] ERROR: Invalid slot {target_id} (valid {slot_min}-{slot_max})")
                return False
        except Exception:
            pass

        try:
            wait_seconds = int(os.getenv('FINGER_WAIT_SECONDS', '40'))
        except Exception:
            wait_seconds = 40
        poll_interval = 0.5

        def attempt_scan(slot: int, label: str) -> bool:
            deadline = time.time() + wait_seconds
            print(f"[FINGER] {label}: hold finger flat and firm")
            while time.time() < deadline:
                try:
                    if self.is_button_pressed('START'):
                        return False
                except Exception:
                    pass
                try:
                    img = self.finger.get_image()
                except Exception as e:
                    print(f"[FINGER] get_image EXCEPTION: {e}")
                    img = None
                print(f"[FINGER] {label} get_image -> {repr(img)}")
                if img == adafruit_fingerprint.OK:
                    self.show_msg("Image OK", label, "Keep steady")
                    break
                self.show_msg("Place Finger", label, f"{int(deadline-time.time())}s")
                time.sleep(poll_interval)
            else:
                print(f"[FINGER] {label} FAILED: no OK image within {wait_seconds}s")
                return False

            # Retry image_2_tz a few times to overcome transient quality issues
            for retry in range(3):
                try:
                    tz = self.finger.image_2_tz(slot)
                except Exception as e:
                    print(f"[FINGER] image_2_tz EXCEPTION: {e}")
                    tz = None
                print(f"[FINGER] {label} image_2_tz retry={retry+1} -> {repr(tz)}")
                if tz == adafruit_fingerprint.OK:
                    return True
                # Give operator a moment to reposition/press harder
                time.sleep(1)
                try:
                    img2 = self.finger.get_image()
                except Exception:
                    img2 = None
                if img2 != adafruit_fingerprint.OK:
                    print(f"[FINGER] {label} re-capture returned {repr(img2)}")
            return False

        print(f"[FINGER] Starting enroll to slot {target_id}")
        self.show_msg("Enroll", f"ID {target_id}", "Scan 1/2")
        if not attempt_scan(1, "Scan1"):
            print("[FINGER] Scan1 failed")
            return False

        self.show_msg("Remove Finger", "", "Wait 2s")
        time.sleep(2)

        self.show_msg("Place Again", "Scan 2/2", "")
        if not attempt_scan(2, "Scan2"):
            print("[FINGER] Scan2 failed")
            return False

        try:
            model_res = self.finger.create_model()
        except Exception as e:
            print(f"[FINGER] create_model EXCEPTION: {e}")
            return False
        print(f"[FINGER] create_model -> {repr(model_res)}")
        if model_res != adafruit_fingerprint.OK:
            # 10 commonly ENROLLMISMATCH; treat as failure and advise retry
            print(f"[FINGER] create_model failed: {repr(model_res)}")
            return False

        try:
            store_res = self.finger.store_model(target_id)
        except Exception as e:
            print(f"[FINGER] store_model EXCEPTION: {e}")
            return False
        print(f"[FINGER] store_model({target_id}) -> {repr(store_res)}")
        success = store_res == adafruit_fingerprint.OK
        if success:
            self.show_msg("Enroll Success", f"ID {target_id}", "")
        else:
            self.show_msg("Enroll Failed", f"ID {target_id}", "")
        return success

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
