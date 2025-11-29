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

**Download:** Raspberry Pi OS (64-bit) Bookworm
**Flash Tool:** Raspberry Pi Imager

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

EnvironmentFile=/home/pi/blockchain-voting-dapp-v3/.env
ExecStart=/usr/bin/python3 kiosk_main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

```bash

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

```python

## Testing Hardware

### Test OLED Display

```python

from luma.core.interface.serial import spi
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont
import RPi.GPIO as GPIO

## Initialize display

serial = spi(device=0, port=0, gpio_DC=24, gpio_RST=25)
device = sh1106(serial)

## Draw test text

with canvas(device) as draw:
    draw.text((0, 0), "VoteChain V3", fill="white")
    draw.text((0, 16), "Display Test", fill="white")
    draw.text((0, 32), "Success!", fill="white")

print("If you see text on OLED, display is working!")

```python

### Test Fingerprint Sensor

```python

import serial
import adafruit_fingerprint

## Initialize sensor

uart = serial.Serial("/dev/ttyAMA0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

## Test connection

if finger.read_templates() != adafruit_fingerprint.OK:
    print("Failed to communicate with fingerprint sensor!")
else:
    print(f"Fingerprint sensor detected! Templates: {finger.template_count}")
    print(f"Library capacity: {finger.library_size}")

```python

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

```bash

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

```python

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

```bash

### GPIO Permission Denied

**Symptoms:** `RuntimeError: Cannot export GPIO`

**Solution:**

```bash

## Run with sudo (required for GPIO access)

sudo -E python3 kiosk_main.py

## Or add user to gpio group (may not work on all Pi OS versions)

sudo usermod -aG gpio pi

```bash

### Backend Server Won't Start

**Symptoms:** Connection refused on port 3000

**Check logs:**

```bash

sudo journalctl -u votechain-backend.service -n 50

```python

- **Common issues:**

- Missing `.env` file → Create from template
- Wrong RPC URL → Test with curl: `curl $SEPOLIA_RPC_URL`
- Port 3000 already in use → `sudo lsof -i :3000`

### Kiosk Crashes on Startup

**Check logs:**

```bash

sudo journalctl -u votechain-kiosk.service -n 50

```bash

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

```bash

### Network Optimization

```bash

## Use static IP (faster than DHCP)

sudo nano /etc/dhcpcd.conf

```conf

Add at end:

```text

interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

```conf

### Increase RPC Timeout

If experiencing vote submission failures due to slow blockchain confirmation:

Edit `backend/server.js` line ~230:

```javascript

const timeoutPromise = new Promise((_, reject) => 
    setTimeout(() => reject(new Error('RPC_TIMEOUT')), 90000) // Increase to 90s
);

```python

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

```bash

### 2. Disable Unused Services

```bash

sudo systemctl disable bluetooth.service
sudo systemctl disable cups.service
sudo systemctl disable triggerhappy.service

```bash

### 3. Auto-update Security Patches

```bash

sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

```bash

### 4. Lock Down SSH

```bash

sudo nano /etc/ssh/sshd_config

```conf

Set:

```text

PermitRootLogin no
PasswordAuthentication no  # Use SSH keys only
X11Forwarding no

```bash

```bash

sudo systemctl restart ssh

```bash

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

```bash

### Log Rotation

```bash

sudo nano /etc/logrotate.d/votechain

```text

```conf

/var/log/votechain/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pi pi
}

```bash

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

```bash

Make executable and add to cron:

```bash

chmod +x /home/pi/backup.sh
crontab -e

## Add: 0 2 * * * /home/pi/backup.sh

```bash

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

```python

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

```python

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

```python

This script:
1. Checks system is running
2. Opens admin dashboard
3. Guides you through deployment
4. Auto-restarts backend service
5. Verifies new contract loaded

### Manual Deployment Steps

#### 1. Open Admin Dashboard

```bash

## From another device on same network

http://RASPBERRY_PI_IP:8000/admin.html

## Or locally with browser

chromium-browser http://localhost:8000/admin.html

```bash

#### 2. Click "New Election" Button

- Deploys new smart contract (~30 seconds)
- Auto-updates `backend/.env` with new address
- Resets voter eligibility (all `has_voted = false`)
- Preserves enrolled fingerprints

#### 3. Restart Backend Service

```bash

sudo systemctl restart votechain-backend.service

```bash

#### 4. Verify New Contract Loaded

```bash

## Check .env file was updated

grep VOTING_CONTRACT_ADDRESS ~/blockchain-voting-dapp-v3/backend/.env

## Verify backend API returns new address

curl http://localhost:3000/api/config | jq '.contractAddress'

```python

### What Happens Automatically

#### 1. Smart Contract Deployment
```javascript

// backend/server.js deploys new VotingV2 contract
const newContract = await ContractFactory.deploy();
const contractAddress = await newContract.getAddress();

```conf

#### 2. Environment Update
```javascript

// backend/.env automatically updated with regex replace
envContent = envContent.replace(
    /VOTING_CONTRACT_ADDRESS="0x[a-fA-F0-9]{40}"/,
    `VOTING_CONTRACT_ADDRESS="${contractAddress}"`
);

```python

#### 3. Database Reset
```javascript

// All voters reset to eligible status
await supabase
    .from('voters')
    .update({ has_voted: false })
    .neq('id', 0);

```python

#### 4. Authorization Setup
```javascript

// Backend wallet auto-authorized as official signer
await ensureAuthorizedSignerFor(contractAddress);

```conf

#### Expanded Signer Authorization Walkthrough

After a new contract is deployed the backend wallet must be authorized as the contract's `officialSigner` so the backend can submit votes. The backend attempts auto-authorization on deploy, but you can run and verify the steps manually:

1. Ensure the following are set in `backend/.env` (or exported in your shell):

```bash
export VOTING_CONTRACT_ADDRESS="0x..."
export SERVER_PRIVATE_KEY="0x..."   # backend signing wallet
export SEPOLIA_RPC_URL="https://..."
```

2. Run the helper script (preferred):

```bash
VOTING_CONTRACT_ADDRESS=$VOTING_CONTRACT_ADDRESS SERVER_WALLET_ADDRESS=$SERVER_WALLET_ADDRESS \
    npx hardhat run scripts/authorize-signer.ts --network sepolia
```

3. Verify on-chain (via Hardhat console or Etherscan):

```bash
npx hardhat console --network sepolia
> const v = await ethers.getContractAt('VotingV2', process.env.VOTING_CONTRACT_ADDRESS)
> await v.officialSigner()
```

The `officialSigner` getter should return the backend wallet address. If it does not:

- Confirm the wallet used has enough ETH to pay gas.
- Confirm `SEPOLIA_RPC_URL` is reachable from the deployment machine.
- Inspect backend logs: `sudo journalctl -u votechain-backend.service -n 200` for auto-authorization attempts.

Recovery: if authorization fails and you cannot call `setOfficialSigner` from the admin/deployer wallet, redeploy the contract with a known admin wallet and repeat the authorization steps above.

#### 5. Runtime Update
```javascript

// Current backend session updated (no restart needed for admin UI)
process.env.VOTING_CONTRACT_ADDRESS = contractAddress;

```python

### How Dynamic Loading Works

**Backend (`backend/server.js`):**
```javascript

// Always loads from environment variable
const contract = new ethers.Contract(
    process.env.VOTING_CONTRACT_ADDRESS,  // ← From .env
    ABI,
    wallet
);

// API endpoint provides current configuration
app.get('/api/config', async (req, res) => {
    res.json({
        contractAddress: process.env.VOTING_CONTRACT_ADDRESS
    });
});

```python

**Admin Dashboard (`admin.html`):**
```javascript

// Fetches contract address from backend API
const config = await fetch(`${BACKEND_URL}/api/config`).then(r => r.json());
contractAddress = config.contractAddress;  // ← Dynamic!

```python

**Results Dashboard (`index.html`):**
```javascript

// Fetches from backend API
const config = await fetch(`${API_BASE}/api/config`).then(r => r.json());
CONTRACT_ADDRESS = config.contractAddress;  // ← Dynamic!

```python

**Kiosk (`kiosk_main.py`):**
```python

## Backend API handles all blockchain interaction

response = requests.post(
    f"{BACKEND_URL}/api/vote",
    json={"aadhaar_id": aadhaar_id, "candidate_id": candidate_id}
)

```python

### No Hardcoding Anywhere

✅ **Contract Address**: `.env` → API → Frontend  
✅ **RPC URL**: From `.env` (`SEPOLIA_RPC_URL`)  
✅ **Private Keys**: From `.env` (encrypted in production)  
✅ **Supabase Config**: From `.env`

### Verification Commands

```bash

## Check current contract in .env

grep VOTING_CONTRACT_ADDRESS ~/blockchain-voting-dapp-v3/backend/.env

## Check backend API returns same address

curl http://localhost:3000/api/config | jq '.contractAddress'

## Check voter reset status

curl http://localhost:3000/api/config | jq '{total: .totalVoters, voted: .totalVoted}'

## After deployment, 'voted' should be 0

```bash

### Deployment Checklist

### Before Deployment
- [ ] Backup current `.env`: `cp backend/.env backend/.env.backup`
- [ ] Export results: `curl http://localhost:3000/api/results > backup.json`
- [ ] Verify backend running: `curl http://localhost:3000/api/health`
- [ ] Check wallet balance: `curl http://localhost:3000/api/signer-balance`

### During Deployment
- [ ] Click "New Election" in admin dashboard
- [ ] Wait for confirmation (~30 seconds)
- [ ] Note new contract address

### After Deployment
- [ ] Verify `.env` updated: `grep VOTING_CONTRACT backend/.env`
- [ ] Restart backend: `sudo systemctl restart votechain-backend.service`
- [ ] Check API: `curl http://localhost:3000/api/config`
- [ ] Test one vote with test voter
- [ ] Verify dashboards show new contract

### Troubleshooting Deployment

### Old Contract Still Showing

API returns old address after deployment:

```bash

## Check .env was updated

cat ~/blockchain-voting-dapp-v3/backend/.env | grep VOTING_CONTRACT

## Restart backend to reload .env

sudo systemctl restart votechain-backend.service

## Verify

curl http://localhost:3000/api/config | jq '.contractAddress'

```bash

### Frontend Cached Old Address

Dashboard shows old contract after refresh:

1. Hard refresh: `Ctrl+Shift+R`
2. Clear browser cache
3. Close and reopen browser

### Deployment Transaction Failed

"New Election" button fails:

```bash

## Check wallet balance

curl http://localhost:3000/api/signer-balance

## Should have >0.01 ETH for gas

## Check backend logs

sudo journalctl -u votechain-backend.service -n 100 | grep -i deploy

```bash

### Voters Still Marked as Voted

Database not reset:

```bash

## Check Supabase dashboard or logs

## Voters table: has_voted should all be false after deployment

```bash

### Multi-Election Support

Deploy **unlimited elections** without reconfiguration:

```bash

## Election 1 (e.g., Student Council)

./deploy-new-election.sh  # Contract: 0xAAA...

## Run voting, get results

## Election 2 (e.g., Club President)

./deploy-new-election.sh  # Contract: 0xBBB...

## Run voting, get results

## Election 3 (e.g., Sports Captain)

./deploy-new-election.sh  # Contract: 0xCCC...

## Run voting, get results

```bash

Each election:
- ✅ Independent smart contract on blockchain
- ✅ Separate immutable voting records
- ✅ Reuses voter database (same students)
- ✅ Keeps fingerprints enrolled
- ✅ Auto-updates everywhere

### Security Notes

🔒 ### Keep `.env` Secure
- Contains private keys and database credentials
- Never commit to git (already in `.gitignore`)
- Backup encrypted: `gpg -c backend/.env`

🔒 ### Server Wallet
- Keep funded for deployments (~0.01 ETH per deployment)
- Monitor balance: `curl http://localhost:3000/api/signer-balance`
- Use dedicated wallet (not personal funds)

### Files Auto-Updated on Deployment

When deploying new election, **only one file changes**:

```text

backend/.env  ← VOTING_CONTRACT_ADDRESS updated automatically

```python

Everything else pulls from API dynamically:
- ✅ `admin.html` fetches from `/api/config`
- ✅ `index.html` fetches from `/api/config`
- ✅ `kiosk_main.py` uses `/api/vote` endpoint

**No manual file editing required!**

## Support

For additional help:

- Check logs: `sudo journalctl -u votechain-backend.service -f`
- Test hardware with scripts above
- Verify network connectivity: `ping 8.8.8.8`
- Check Alchemy RPC status: `curl $SEPOLIA_RPC_URL`

---

**Last Updated:** November 29, 2025  
**Tested On:** Raspberry Pi 5 (8GB) with Raspberry Pi OS Bookworm (64-bit)
