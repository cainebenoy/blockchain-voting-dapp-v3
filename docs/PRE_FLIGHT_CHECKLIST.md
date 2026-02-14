# 🛫 Pi Pre-flight Checklist

Before you unplug your laptop and move to the Pi, go through this final checklist to ensure everything works on the hardware kiosk.

## 1. Hardware Permissions (Critical)
The fingerprint sensor uses the Serial UART port (`/dev/ttyAMA0`). By default, the Pi might have this reserved for the console.
- **Action**: Run `sudo raspi-config`.
- **Path**: Interface Options -> Serial Port.
- **Setting**: 
    - Would you like a login shell to be accessible over serial? **NO**
    - Would you like the serial port hardware to be enabled? **YES**
- **Reboot** the Pi after changing this.

## 2. Environment Variable Sync
Ensure the `.env` on your Pi matches your laptop exactly for these keys:
- `AADHAAR_SALT`: Must be identical so Aadhaar IDs generate the same "voterHash".
- `SERVER_PRIVATE_KEY`: Must be identical so the session tokens match.
- `VOTING_CONTRACT_ADDRESS`: Ensure it points to your latest Sepolia deployment.

## 3. Ngrok Authtoken
The Pi needs its own Ngrok authentication to use the static domain.
- **Action**: Run `ngrok config add-authtoken <YOUR_TOKEN>` on the Pi.

## 4. Port Conflict
Ensure no other web servers (like Apache or Nginx) are running on port 3000 or 80 on the Pi.

## 5. Clean Slate Strategy
Once the Pi is online and the Admin Portal shows "Kiosk: Connected via Ngrok":
- **Action**: Go to the Admin Portal and click **"Deploy New Election"**. 
- **Why**: This resets the database and the blockchain at the same time, ensuring the Pi is talking to a fresh, synchronized contract.

## 6. Monitoring the Pi
If the simulator doesn't connect, you can "watch" the Pi's logs in real-time:
```bash
# Watch the service logs
sudo journalctl -u votechain -f
```

## 7. Shutdown the Laptop Server
> [!WARNING]
> Close any `node server.js` windows and Ngrok terminals on your laptop **BEFORE** starting the Pi service. 
> Only one heart-beat should be active at a time to avoid confusing the Admin dashboard.
