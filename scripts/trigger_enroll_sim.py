import requests
import os
import time

# Configuration
BACKEND_URL = "http://localhost:3000"
ADMIN_SECRET = "votechain-v3-secret-2026" # Matching .env default or retrieved
AADHAAR_ID = "999999999999" # Virtual ID
NAME = "Simulation User"
CONST = "SimCity"

def trigger_enrollment():
    print(f"[*] triggering enrollment for {NAME} ({AADHAAR_ID})...")
    
    headers = {
        "x-admin-secret": ADMIN_SECRET,
        "Content-Type": "application/json"
    }
    
    payload = {
        "aadhaar_id": AADHAAR_ID,
        "name": NAME,
        "constituency": CONST
    }
    
    try:
        res = requests.post(f"{BACKEND_URL}/api/admin/add-voter", json=payload, headers=headers)
        if res.status_code == 200:
            data = res.json()
            print(f"[+] Success! Enrollment Queued.")
            print(f"    Target ID: {data.get('target_id')}")
            print(f"    Request ID: {data.get('request_id')}")
            print("\n[!] Check Kiosk Screen Now! It should be beeping.")
        else:
            print(f"[-] Failed: {res.status_code}")
            print(res.text)
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    trigger_enrollment()
