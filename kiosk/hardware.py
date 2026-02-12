import time
import sys

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
        self.device = None
        self.finger = None
        self.finger_present = False
        
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
            self._setup_gpio()
            self._setup_oled()
            self._setup_fingerprint()

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.PIN_LED_GREEN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.PIN_LED_RED, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.PIN_BUZZER, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.PIN_BTN_START, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BTN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.PIN_BTN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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
            GPIO.cleanup()
            self.set_leds(False, False)

    def set_leds(self, green=False, red=False):
        if IS_PI:
            GPIO.output(self.PIN_LED_GREEN, GPIO.HIGH if green else GPIO.LOW)
            GPIO.output(self.PIN_LED_RED, GPIO.HIGH if red else GPIO.LOW)
        else:
            print(f"[HW] LEDs -> Green:{green} Red:{red}")

    def beep(self, count=1, duration=0.1):
        if IS_PI:
            for _ in range(count):
                GPIO.output(self.PIN_BUZZER, GPIO.HIGH)
                time.sleep(duration)
                GPIO.output(self.PIN_BUZZER, GPIO.LOW)
                time.sleep(0.05)
        else:
            print(f"[HW] BEEP x{count}")

    def is_button_pressed(self, btn_name):
        if not IS_PI: return False
        pin_map = {'START': self.PIN_BTN_START, 'A': self.PIN_BTN_A, 'B': self.PIN_BTN_B}
        return GPIO.input(pin_map[btn_name]) == GPIO.LOW

    def show_msg(self, line1, line2="", line3="", big_text=False):
        print(f"[DISPLAY] {line1} | {line2} | {line3}")
        if not self.device: return

        with canvas(self.device) as draw:
            draw.rectangle(self.device.bounding_box, fill="black")
            try:
                if big_text and ImageFont:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                    draw.text((5, 20), str(line1), fill="white", font=font)
                else:
                    font = ImageFont.load_default() if ImageFont else None
                    draw.text((5, 5), str(line1), fill="white", font=font)
                    draw.text((5, 25), str(line2), fill="white", font=font)
                    draw.text((5, 45), str(line3), fill="white", font=font)
            except Exception:
                pass # Font loading fallback

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
