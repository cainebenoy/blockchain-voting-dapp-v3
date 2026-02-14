# 🍓 Raspberry Pi Kiosk Setup Guide

Follow these steps to move your voting system from your laptop to the physical Raspberry Pi.

## 1. Prerequisites
- **Raspberry Pi 5** (recommended) with Raspberry Pi OS.
- **Node.js** (v18+) installed.
- **Python 3** installed.
- **Ngrok** installed and authenticated (`ngrok config add-authtoken <your-token>`).

## 2. Transfer the Code
You can use `git` or `scp` to move the project to the Pi.
```bash
# Example if using git
git clone <your-repo-url>
cd blockchain-voting-dapp-v3
```

## 3. Environment Variables
You MUST copy your current `.env` files to the Pi.
1.  Copy `backend/.env` to the Pi's `backend/` directory.
2.  Copy `.env` from the project root to the Pi's root.

## 4. Run the Kiosk
We've provided a one-click startup script.
```bash
# 1. Give execution permission
chmod +x pi/start_kiosk.sh

# 2. Run the script
./pi/start_kiosk.sh
```

### What the script does:
- Installs all `npm` and `python` dependencies automatically.
- Starts the **Backend Server** on `localhost:3000`.
- Starts the **Ngrok Tunnel** and broadcasts the URL to Supabase.
- The Admin Portal will automatically "see" your Pi once the tunnel is live.

## 5. Hardware Interfacing (R307 Fingerprint)
The backend is already configured to look for the fingerprint sensor on `/dev/ttyUSB0` or `/dev/ttyAMA0`. 
> [!NOTE]
> If your sensor is connected via UART (Direct Pi pins), you may need to enable Serial in `raspi-config` first.

## 6. Accessing the UI
Once the script is running:
1.  **Voters**: Point the Kiosk's browser (or a tablet) to the Ngrok URL displayed in the terminal.
2.  **Admins**: Use the Admin Portal on your laptop. It will dynamically connect to the Pi via the cloud.
