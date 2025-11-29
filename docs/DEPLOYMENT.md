# Raspberry Pi Deployment Guide

Complete guide for deploying VoteChain V3 on Raspberry Pi 5.

## Recent Changes (Nov 29 2025)

- Kiosk display & robustness updates (commit `c464e3d`): added boot-time hardware
    health checks, fixed OLED rendering and font fallbacks, removed border outlines
    from screen clears, added `show_idle()` and `wait_for_reset()`, and made
    persistent OLED error messaging on hardware faults. See `CHANGELOG.md` for
    details.

## Hardware Requirements

### Required Components

- **Raspberry Pi 5** (4GB or 8GB RAM recommended)
- **Power Supply** (Official Raspberry Pi 5 USB-C power adapter)
- **Internet Connection** (Ethernet recommended for stability)
- **LEDs** (Green/Red for status indicators)
- **Buzzer** (Audio feedback)

For a step-by-step hardware wiring guide and emulation notes, see `docs/HARDWARE.md`.

```text
START Button    → BCM 4  (Physical Pin 7)
Candidate A     → BCM 22 (Physical Pin 15)
Candidate B     → BCM 23 (Physical Pin 16)
```

### OLED Display (SPI)

```text
VCC → 3.3V (Pin 1)
GND → Ground (Pin 6)
CLK → GPIO 11 / SCLK (Pin 23)
MOSI → GPIO 10 / MOSI (Pin 19)
DC → GPIO 24 (Pin 18)
RST → GPIO 25 (Pin 22)
CS → GPIO 8 / CE0 (Pin 24)
```

### R307 Fingerprint Sensor (UART)

```text
VCC (Red)    → 5V (Pin 2)
GND (Black)  → Ground (Pin 14)
TX (White)   → RX / GPIO 15 (Pin 10)
RX (Green)   → TX / GPIO 14 (Pin 8)
```

## Operating System Setup

### 1. Install Raspberry Pi OS

**Download:** [Raspberry Pi OS (64-bit) Bookworm](https://www.raspberrypi.com/software/operating-systems/)
**Flash Tool:** [Raspberry Pi Imager](https://www.raspberrypi.com/software/)

#### Settings in Imager

- Enable SSH
- Set username/password
- Configure Wi-Fi (if not using Ethernet)
- Set hostname: `votechain-kiosk`

### 2. First Boot Configuration

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Set timezone
```

Create the `systemd` unit files as described in the repo (example shown in the repo under `votechain-backend.service` and `votechain-kiosk.service`).

#### 3. Enable and Start Services

```bash
## Reload systemd
sudo systemctl daemon-reload

## Enable services (start on boot)
sudo systemctl enable votechain-backend.service
sudo systemctl enable votechain-kiosk.service

## Start services
sudo systemctl start votechain-backend.service
sudo systemctl start votechain-kiosk.service

## Check status
sudo systemctl status votechain-backend.service
sudo systemctl status votechain-kiosk.service

## View logs
sudo journalctl -u votechain-backend.service -f
sudo journalctl -u votechain-kiosk.service -f
```

## Testing Hardware

### Test OLED Display

```python
from luma.core.interface.serial import spi
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont
import RPi.GPIO as GPIO

serial = spi(device=0, port=0, gpio_DC=24, gpio_RST=25)
device = sh1106(serial)

with canvas(device) as draw:
    draw.text((0, 0), "VoteChain V3", fill="white")
    draw.text((0, 16), "Display Test", fill="white")
    draw.text((0, 32), "Success!", fill="white")

print("If you see text on OLED, display is working!")
```

### Test Fingerprint Sensor

```python
import serial
import adafruit_fingerprint

uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

if finger.read_templates() != adafruit_fingerprint.OK:
    print("Failed to communicate with fingerprint sensor!")
else:
    print(f"Fingerprint sensor detected! Templates: {finger.template_count}")
    print(f"Library capacity: {finger.library_size}")
```

### Test GPIO Buttons

```python
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)   # START
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Candidate A
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Candidate B

print("Press buttons to test (Ctrl+C to exit)")
try:
    while True:
        if GPIO.input(4) == GPIO.LOW:
            print("START button pressed")
            time.sleep(0.3)
        if GPIO.input(22) == GPIO.LOW:
            print("Candidate A button pressed")
            time.sleep(0.3)
        if GPIO.input(23) == GPIO.LOW:
            print("Candidate B button pressed")
            time.sleep(0.3)
except KeyboardInterrupt:
    GPIO.cleanup()
```

## Troubleshooting

### Fingerprint Sensor Not Detected

**Symptoms:** `/dev/ttyAMA0` doesn't exist or sensor not responding

**Solutions:**

```bash
## Check if serial port is enabled
ls -la /dev/ttyAMA0

## Verify in boot config
grep "enable_uart" /boot/firmware/config.txt

## Should show: enable_uart=1

## Add user to dialout group (if not using sudo)
sudo usermod -aG dialout pi

## Reboot and test again
sudo reboot
```

### OLED Display Not Working

**Symptoms:** Screen stays blank or shows garbage

**Solutions:**

```bash
## Verify SPI is enabled
lsmod | grep spi

## Should show: spi_bcm2835

## Check wiring:

## - DC pin must be GPIO 24 (Physical Pin 18)

## - RST pin must be GPIO 25 (Physical Pin 22)

## - Check all connections are secure

## Test with luma.oled examples
pip3 install --break-system-packages luma.examples
cd $(python3 -c "import luma.examples; print(luma.examples.__path__[0])")
python3 ../examples/sys_info.py -d sh1106
```

### GPIO Permission Denied

**Symptoms:** `RuntimeError: Cannot export GPIO`

**Solution:**

```bash
## Run with sudo (required for GPIO access)
sudo -E python3 kiosk_main.py

## Or add user to gpio group (may not work on all Pi OS versions)
sudo usermod -aG gpio pi
```

### Backend Server Won't Start

**Symptoms:** Connection refused on port 3000

**Check logs:**

```bash
sudo journalctl -u votechain-backend.service -n 50
```

- **Common issues:**

  - Missing `.env` file → Create from template
  - Wrong RPC URL → Test with curl: `curl $SEPOLIA_RPC_URL`
  - Port 3000 already in use → `sudo lsof -i :3000`

### Kiosk Crashes on Startup

**Check logs:**

```bash
sudo journalctl -u votechain-kiosk.service -n 50
```

- **Common issues:**

  - Fingerprint sensor disconnected → Check wiring
  - Display not detected → Verify SPI enabled
  - Backend not running → Start backend first

## Performance Optimization

### Reduce Boot Time

```bash
## Disable unnecessary services
sudo systemctl disable bluetooth.service
sudo systemctl disable avahi-daemon.service

## Enable faster boot
sudo nano /boot/firmware/cmdline.txt

## Add: quiet splash plymouth.ignore-serial-consoles
```

### Network Optimization

```bash
## Use static IP (faster than DHCP)
sudo nano /etc/dhcpcd.conf
```

```conf
Add at end:

interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

### Increase RPC Timeout

If experiencing vote submission failures due to slow blockchain confirmation:

Edit `backend/server.js` line ~230:

```javascript
const timeoutPromise = new Promise((_, reject) => 
    setTimeout(() => reject(new Error('RPC_TIMEOUT')), 90000) // Increase to 90s
);
```

## Security Hardening

### 1. Firewall Configuration

```bash
## Install ufw
sudo apt install -y ufw

## Allow SSH (if needed)
sudo ufw allow 22/tcp

## Allow backend (only from localhost)
sudo ufw allow from 127.0.0.1 to any port 3000

## Enable firewall
sudo ufw enable
```

### 2. Disable Unused Services

```bash
sudo systemctl disable bluetooth.service
sudo systemctl disable cups.service
sudo systemctl disable triggerhappy.service
```

### 3. Auto-update Security Patches

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 4. Lock Down SSH

```bash
sudo nano /etc/ssh/sshd_config
```

```conf
Set:

PermitRootLogin no
PasswordAuthentication no  # Use SSH keys only
X11Forwarding no
```

```bash
sudo systemctl restart ssh
```

## Monitoring

### System Health Check

```bash
## CPU temperature (should be < 70°C under load)
vcgencmd measure_temp

## Memory usage
free -h

## Disk space
df -h

## Service status
sudo systemctl status votechain-backend.service
sudo systemctl status votechain-kiosk.service
```

### Log Rotation

```bash
sudo nano /etc/logrotate.d/votechain
```

```text
/var/log/votechain/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pi pi
}
```

## Backup Strategy

### Daily Backup Script

```bash
#!/bin/bash

## /home/pi/backup.sh

BACKUP_DIR="/home/pi/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

## Backup database export
pg_dump -h YOUR_SUPABASE_HOST -U postgres votechain > $BACKUP_DIR/db_$DATE.sql

## Backup .env files
cp /home/pi/blockchain-voting-dapp-v3/.env $BACKUP_DIR/env_$DATE

## Remove backups older than 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "env_*" -mtime +7 -delete
```

Make executable and add to cron:

```bash
chmod +x /home/pi/backup.sh
crontab -e

## Add: 0 2 * * * /home/pi/backup.sh
```

## Maintenance

### Update Application

```bash
cd ~/blockchain-voting-dapp-v3
git pull origin main
npm install
cd backend && npm install && cd ..

## Restart services
sudo systemctl restart votechain-backend.service
sudo systemctl restart votechain-kiosk.service
```

### Clean Fingerprint Database

If sensor runs out of template slots:

```python
import serial
import adafruit_fingerprint

uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

## Clear all templates
if finger.empty_library() == adafruit_fingerprint.OK:
    print("All fingerprints deleted!")
```

## Deploying New Elections

### 🎯 Fully Dynamic - No Hardcoded Values

The system automatically updates contract addresses everywhere when you deploy
a new election:

- ✅ Backend reads from `.env` file
- ✅ Admin/results dashboards fetch from backend API
- ✅ No manual editing required
- ✅ Deploy unlimited elections

### Quick Deploy (Automated)

```bash
cd ~/blockchain-voting-dapp-v3
./deploy-new-election.sh
```

This script:

1. Checks system is running
2. Opens admin dashboard
3. Guides you through deployment
4. Auto-restarts backend service
5. Verifies new contract loaded

### Manual Deployment Steps

1. Open Admin Dashboard at [http://RASPBERRY_PI_IP:8000/admin.html](http://RASPBERRY_PI_IP:8000/admin.html) or locally.
2. Click "New Election" button — deploys contract and updates `.env`.
3. Restart backend service: `sudo systemctl restart votechain-backend.service`.
4. Verify: `curl http://localhost:3000/api/config | jq '.contractAddress'`

### What Happens Automatically

1. Smart contract deployed via backend.
1. `backend/.env` updated with new `VOTING_CONTRACT_ADDRESS`.
1. Voter eligibility reset in Supabase.
1. Backend attempts to authorize the server wallet as `officialSigner`.

### Expanded Signer Authorization Walkthrough

After a new contract is deployed the backend wallet must be authorized as the contract's `officialSigner` so the backend can submit votes. The backend attempts auto-authorization on deploy, but you can run and verify the steps manually:

1. Ensure the following are set in `backend/.env` (or exported in your shell):

```bash
export VOTING_CONTRACT_ADDRESS="0x..."
export SERVER_PRIVATE_KEY="0x..."   # backend signing wallet
export SEPOLIA_RPC_URL="https://..."
```

1. Run the helper script (preferred):

```bash
VOTING_CONTRACT_ADDRESS=$VOTING_CONTRACT_ADDRESS SERVER_WALLET_ADDRESS=$SERVER_WALLET_ADDRESS \
    npx hardhat run scripts/authorize-signer.ts --network sepolia
```

1. Verify on-chain (via Hardhat console or Etherscan):

```bash
npx hardhat console --network sepolia
> const v = await ethers.getContractAt('VotingV2', process.env.VOTING_CONTRACT_ADDRESS)
> await v.officialSigner()
```

If the getter does not return the backend wallet address: ensure the wallet has ETH to pay gas, confirm RPC reachability, and inspect backend logs (`sudo journalctl -u votechain-backend.service -n 200`).

## Support

For additional help, check logs (`sudo journalctl -u votechain-backend.service -f`), test hardware with the provided scripts, and verify network connectivity.

---

**Last Updated:** November 29, 2025
