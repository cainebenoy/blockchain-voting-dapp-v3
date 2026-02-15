import time
import sys
import signal
import atexit
import logging

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
            # ensure cleanup on signals
            atexit.register(self._safe_cleanup)
            signal.signal(signal.SIGTERM, lambda s,f: self._safe_cleanup() or sys.exit(0))
            signal.signal(signal.SIGINT, lambda s,f: self._safe_cleanup() or sys.exit(0))

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
            uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
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
                # On GPIO runtime errors (mode unset, backend issues) mark GPIO as not ready
                # so further calls become no-ops and avoid repeated tracebacks.
                try:
                    self._gpio_ready = False
                except Exception:
                    pass
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
        checks = max(1, stable_ms // 10)
        for _ in range(checks):
            time.sleep(stable_ms / (checks * 1000.0))
            try:
                if GPIO.input(pin) != GPIO.LOW:
                    return False
            except Exception:
                return False
        return True

    def show_msg(self, line1, line2="", line3="", big_text=False):
        print(f"[DISPLAY] {line1} | {line2} | {line3}")
        if not self.device: return
        try:
            with canvas(self.device) as draw:
                draw.rectangle(self.device.bounding_box, fill="black")
                try:
                    if big_text and ImageFont:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20) # Increased to 20 for "Thick" look
                        # Center roughly for 128x64
                        draw.text((10, 5), str(line1), fill="white", font=font)
                        draw.text((10, 32), str(line2), fill="white", font=font)
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
        if not self.finger: return None
        if self.finger.get_image() != adafruit_fingerprint.OK: return None
        if self.finger.image_2_tz(1) != adafruit_fingerprint.OK: return None
        if self.finger.finger_search() != adafruit_fingerprint.OK: return None
        return self.finger.finger_id

    def enroll_finger_logic(self, location_id):
        if not self.finger: return False
        # Logic roughly matches original enroll_finger
        # This is simplified; the main loop usually handles UI for enrollment steps
        # We might need to expose lower level primitive if we want UI feedback *during* enrollment
        # For now, let's just expose the primitive blocking function? 
        # Or keep it in main and just use `get_image` from here?
        # Better to expose `get_image()` and `create_model()`.
        pass 

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
        while self.finger.get_image() != adafruit_fingerprint.NOFINGER:
            pass

hardware = KioskHardware()
