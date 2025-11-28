# Raspberry Pi 5 Migration Guide

This document describes how to migrate and run the `blockchain-voting-dapp-v3` project on a Raspberry Pi 5 (RPi5). It covers OS selection, system setup, required packages, hardware integration, deployment steps, common troubleshooting, performance tips, and security considerations. This guide assumes you will not change application code; it focuses on environment and runtime requirements.

---

## 1. Overview and Requirements

Target device: Raspberry Pi 5 (recommended with at least 4GB RAM, 8GB+ recommended)

Primary goals:

- Run the Node.js backend (Express) and optional frontend (static files / React/Electron)
- Allow hardware access for camera and fingerprint reader via Node.js or helper scripts
- Enable connectivity to the Ethereum Sepolia testnet (or your chosen network) via Alchemy/other RPC

Minimum disk: 16GB (32GB recommended)
Network: Ethernet or stable Wi‑Fi
Power supply: Official Raspberry Pi 5 power supply

---

## 2. Recommended OS and Image

- Use Raspberry Pi OS (64-bit) or Ubuntu Server 24.04 LTS (arm64). Either works; choose based on familiarity. For best compatibility with Node/Electron and hardware drivers, `Ubuntu Server 24.04 (arm64)` or the 64-bit Raspberry Pi OS is recommended.

Download and flash using Raspberry Pi Imager or `balenaEtcher`.

Recommended image options:

- `Ubuntu Server 24.04 LTS (arm64)` (recommended for server deployments)
- `Raspberry Pi OS 64-bit (bookworm)` (recommended if using GUI/Electron)

After flashing, enable SSH (via imager option or create `ssh` file on /boot) and boot.

---

## 3. System Update & Base Packages

Run these commands after first boot (use `sudo` where shown):

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y build-essential git curl ca-certificates gnupg lsb-release
```

Set timezone and locale as needed:

```bash
sudo timedatectl set-timezone "Asia/Kolkata"   # adjust to your timezone
sudo locale-gen en_US.UTF-8
```

---

## 4. Node.js and npm (Required)

The project requires Node.js (check `package.json` for target). We recommend Node.js 18.x or 20.x (LTS) — install via NodeSource or using the official distributions.

Install Node 20.x (arm64):

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v
```

If you prefer using `nvm` for per-user management, install `nvm` and use it to install Node.

---

## 5. Python (Optional - for hardware scripts)

Some fingerprint and camera helper scripts may use Python. Install Python 3 and `pip`:

```bash
sudo apt install -y python3 python3-pip python3-venv
python3 -m pip --version
```

Install commonly used packages (if the project uses them):

```bash
python3 -m pip install --user opencv-python-headless pyserial
```

Note: If you need native OpenCV with camera support, use OS packages or build from source cautiously.

---

## 6. Install Project Dependencies

Clone or copy your repository to the Pi. If using SSH remote, you can `git clone`.

```bash
# example
cd /home/ubuntu
git clone https://github.com/cainebenoy/blockchain-voting-dapp-v3.git
cd blockchain-voting-dapp-v3
```

Install Node dependencies:

```bash
npm ci    # or npm install
```

If the project uses `pnpm` or `yarn`, install that tool first and use it accordingly.

---

## 7. Hardware Dependencies: Camera & Fingerprint Reader

A. Camera (Raspberry Pi Camera Module or USB webcam)

- For the Raspberry Pi Camera Module (official), enable camera support and configure libcamera or the V4L2 driver depending on OS.
- On Raspberry Pi OS (64-bit): enable camera in `raspi-config` or ensure `libcamera` is installed.

Sample test:

```bash
# Test using libcamera (camera module)
libcamera-hello --duration 2000

# Or using ffmpeg/v4l2-ctl for USB cameras
v4l2-ctl --list-devices
```

B. Fingerprint Reader (example R307 / Zenel)

- Many fingerprint units communicate over serial (USB-serial) or GPIO; the project uses a Python script `read_fingerprint.py`.
- Ensure the device is visible under `/dev/serial/by-id` or `/dev/ttyUSB0` when connected.
- Install `pyserial` (see Python section) and test the script.

Common troubleshooting:

- Use `dmesg | tail` after plugging device to see kernel messages
- Adjust udev rules if permission issues occur (create `/etc/udev/rules.d/99-fingerprint.rules` to set group ownership or mode)

Example udev rule (adjust idVendor/idProduct from `lsusb`):

```text
# /etc/udev/rules.d/99-fingerprint.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", MODE="0660", GROUP="plugdev"
```

---

## 8. Environment Configuration

Copy or create `.env` according to the project's expectations. Example variables (adjust values):

```bash
REACT_APP_API_BASE_URL=http://localhost:3000
ALCHEMY_API_KEY=your_alchemy_key
PRIVATE_KEY=0x...   # account used to deploy/interact (use env secret management)
NODE_ENV=production
```

Keep private keys secure — do NOT commit `.env` to version control. Use systemd environment files or `direnv` for safer management.

---

## 9. Running Backend Service (Node.js)

Run locally for testing:

```bash
# from project root
npm run start   # or npm run dev depending on package.json scripts
```

For production, create a `systemd` service to run the server as a daemon.

Example `systemd` unit file `/etc/systemd/system/voting-backend.service`:

```ini
[Unit]
Description=Voting DApp Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/blockchain-voting-dapp-v3
EnvironmentFile=/home/ubuntu/blockchain-voting-dapp-v3/.env
ExecStart=/usr/bin/node ./backend/server.js
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable voting-backend.service
sudo systemctl start voting-backend.service
sudo journalctl -u voting-backend.service -f
```

---

## 10. Frontend (Static / Electron)

If the frontend is static (plain HTML/CSS/JS in `index.html`), the backend can serve it (static middleware). If the frontend is a React app, build it on a dev machine or on the Pi:

```bash
# build (if React)
npm run build
# serve via simple static server (serve, http-server) or by backend
npx http-server build -p 3001
```

For Electron (kiosk app): install `electron` and `electron-builder` and package for `arm64`. Note: packaging Electron for Pi may require cross-compilation; using `electron-forge` with `@electron-forge/maker-deb` on-device is simplest but resource-intensive.

---

## 11. Blockchain RPC & Wallet

- Ensure the Pi can reach your RPC provider (Alchemy, Infura, or own node).
- Set `ALCHEMY_API_KEY` or RPC URL in `.env`.
- If signing transactions on the Pi, store private keys securely. Prefer using an HSM or at least a file with strict permissions and system user access only.

---

## 12. Logging, Monitoring & Backups

- Use `pm2` (Node process manager) or `systemd` for managing Node service. `pm2` offers logs and restarts:

```bash
sudo npm i -g pm2
pm2 start backend/server.js --name voting-backend
pm2 save
pm2 startup
```

- Configure `logrotate` or use `pm2` logrotation module to prevent full disk
- Backup `.env`, database credentials and any local state (not PII) regularly

---

## 13. Security Recommendations

- Run services under a dedicated user (e.g., `voting`) with minimal privileges
- Use firewall (ufw) to restrict access to required ports (3000/80/443)

```bash
sudo apt install ufw
sudo ufw allow 22/tcp
sudo ufw allow 3000/tcp
sudo ufw enable
```

- Use HTTPS (reverse proxy with nginx and TLS). Example: use `nginx` as reverse proxy terminating TLS, forwarding to `localhost:3000`.

---

## 14. Performance Tuning

- Swap: avoid excessive swapping. Increase `vm.swappiness` only if necessary.
- If using SQLite or other file DB, move DB onto SSD if possible.
- Use `--max-old-space-size` for Node if memory pressure occurs:

```bash
node --max-old-space-size=1024 ./backend/server.js
```

---

## 15. Troubleshooting

- Service not starting: check `journalctl -u voting-backend.service` or `pm2 logs`
- Camera issues: check `dmesg` and `libcamera` docs
- Serial device permission: add user to `dialout`/`plugdev` groups and reload udev rules

```bash
sudo usermod -aG dialout,vide0k,plugdev ubuntu
# replace 'ubuntu' with your running user
```

- Node dependency builds: install `build-essential` and `python3` for native addon builds

---

## 16. Example Quick Start (Commands Summary)

```bash
# Update system
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl python3 python3-pip

# Node
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone project
git clone https://github.com/cainebenoy/blockchain-voting-dapp-v3.git
cd blockchain-voting-dapp-v3
npm ci

# Configure env
cp .env.example .env
# edit .env with keys

# Run
npm run start
```

---

## 17. Appendix: Useful Commands

- Check disk space: `df -h`
- Check memory: `free -h`
- View dmesg: `dmesg | tail -n 50`
- List USB devices: `lsusb`
- List serial devices: `ls /dev/ttyUSB* /dev/ttyACM*`

---

## 18. Next Steps / Optional

- Prepare an Ansible playbook for automated provisioning
- Create a Docker image for the backend (note: Docker on Pi needs arm64 builds)
- Automate backup and monitoring (Prometheus + Node exporter)

---

If you'd like, I can:

- create a `systemd` unit and `nginx` reverse proxy example adapted to your project's actual `server.js` path, or
- generate an Ansible playbook or Dockerfile for arm64 to automate provisioning on multiple RPi devices.
