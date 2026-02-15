import sys
import os
import time
import serial
import adafruit_fingerprint

# Add kiosk to path to import config if needed
sys.path.append('/home/cainepi/Desktop/VoteChain - V3/blockchain-voting-dapp-v3/kiosk')

try:
    uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
    
    if finger.read_templates() == adafruit_fingerprint.OK:
        print("✅ Sensor found!")
        print(f"Templates stored: {finger.templates}")
        
        print("Testing image capture (place finger)...")
        start = time.time()
        while time.time() - start < 10:
            if finger.get_image() == adafruit_fingerprint.OK:
                print("✅ Image captured successfully!")
                break
            time.sleep(0.5)
        else:
            print("❌ No finger detected within 10s")
    else:
        print("❌ Sensor not found or communication error")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'uart' in locals():
        uart.close()
