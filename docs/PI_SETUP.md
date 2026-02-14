# 🍓 Raspberry Pi Kiosk Setup Guide

Follow these steps to move your voting system from your laptop to the physical Raspberry Pi.

## 1. Access the Pi Terminal (SSH)
Before you start, you need to "log in" to your Pi from your laptop.
1.  Open PowerShell or Terminal on your laptop.
2.  Run: `ssh pi@raspberrypi.local` (replace `pi` with your username).
3.  Enter your password when prompted.


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

## 7. Enabling Auto-Start (Service)
To make the voting system start automatically every time the Pi boots:

1.  **Edit the Service File**: Open `pi/votechain.service` and ensure the `User` and `WorkingDirectory` paths are correct for your Pi.
    ```ini
    [Unit]
    Description=VoteChain Kiosk Startup (Backend + Ngrok)
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    User=pi
    WorkingDirectory=/home/pi/blockchain-voting-dapp-v3
    ExecStart=/bin/bash pi/start_kiosk.sh
    Restart=always
    RestartSec=10
    StandardOutput=journal
    StandardError=journal
    SyslogIdentifier=votechain

    [Install]
    WantedBy=multi-user.target
    ```
2.  **Copy to System**:
    ```bash
    sudo cp pi/votechain.service /etc/systemd/system/
    ```
3.  **Enable and Start**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable votechain
    sudo systemctl start votechain
    ```
4.  **Check Status**:
    ```bash
    sudo systemctl status votechain
    ```
    If everything is green, your kiosk is now fully automated!

## 9. ⚠️ Critical Tip: Laptop Cleanup
Before you start the Pi or enable the service:
> [!IMPORTANT]
> Stop the `node server.js` and any Ngrok tunnels running on your laptop. 

## 10. 📋 Command Cheat Sheet
Here is a quick reference for all the commands you might need:

### 🌐 Setup & Navigation
```bash
ssh pi@raspberrypi.local             # Connect to Pi
cd blockchain-voting-dapp-v3        # Enter project
```

### 🚀 Starting the App
```bash
./pi/start_kiosk.sh                 # One-click start (Backend + Tunnel)
```

### 🛠️ Manual Start (For Debugging)
```bash
cd backend && node server.js        # Run Backend only
python3 pi/ngrok_discovery.py       # Run Tunnel only
```

### ⚙️ System Management
```bash
sudo systemctl restart votechain    # Restart the auto-boot service
sudo journalctl -u votechain -f     # View live logs from the service
sudo raspi-config                   # Open Pi configuration menu
```



