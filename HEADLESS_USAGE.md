# VoteChain Headless Operation Guide

## How It Works

The kiosk terminal uses **direct keyboard device capture (evdev)**, which means:
- ✅ Works **completely headless** (no monitor needed)
- ✅ Keyboard input captured directly from hardware
- ✅ Aadhaar input displays on **OLED screen** in real-time
- ✅ Auto-starts on boot
- ✅ **START button resets at any time** - cancels and returns to idle

## Using Without Monitor

1. **Power on the Pi** - Everything starts automatically (wait 15-20 seconds)
2. **Press the START button** on the kiosk
3. **Type Aadhaar number** on USB keyboard (any keyboard plugged into Pi)
   - Each digit appears on OLED screen
   - Press **Enter** when done (or after 12 digits auto-submits)
   - Press **START button** anytime to cancel and reset to idle
4. **Follow fingerprint prompt** on OLED
   - Press **START button** to cancel fingerprint scan
5. **Vote using buttons** A or B
   - Press **START button** to cancel vote

## Reset Functionality

The **START button** acts as a reset button throughout the entire flow:

- **During Aadhaar input** → Cancels input, returns to idle screen
- **On "Check-in Failed"** screen → Returns to idle screen
- **During fingerprint scan** → Cancels scan, returns to idle screen
- **During vote selection** → Cancels vote, returns to idle screen
- **On any error screen** → Returns to idle screen

Simply press START anytime to reset!

## Auto-Start on Boot

The system automatically starts three services:

1. **Backend API** (port 3000) - Blockchain interaction
2. **Frontend Dashboard** (port 8000) - Web interface
3. **Kiosk Terminal** - Physical voting station

All services start automatically when Pi boots - no manual intervention needed!

## Viewing with Monitor (Optional)

If you connect a monitor:
- Desktop will show normally
- Kiosk runs in background (headless mode)
- Check status: `./check-system.sh`
- View logs: `sudo journalctl -u votechain-kiosk -f`

## Service Management

```bash
# Check all services status
./check-system.sh

# Or use master control script
./votechain.sh status

# Restart kiosk only
sudo systemctl restart votechain-kiosk

# View kiosk logs
sudo journalctl -u votechain-kiosk -f

# Stop all services
./votechain.sh stop

# Start all services
./votechain.sh start
```

## Technical Details

- **Service**: votechain-kiosk.service (runs as root for device access)
- **Input Method**: Direct evdev keyboard capture with exclusive grab
- **Display**: 128x64 OLED shows all prompts and input
- **Auto-restart**: Service restarts if crashed (15s delay)
- **No TTY needed**: Works completely headless via device events

## Troubleshooting

**No keyboard response?**
- Ensure keyboard is plugged into Pi USB port
- Check service running: `sudo systemctl status votechain-kiosk`
- Restart: `sudo systemctl restart votechain-kiosk`
- Check logs: `sudo journalctl -u votechain-kiosk -n 50`

**Stuck on a screen?**
- Press the **START button** to reset to idle

**Can't see what's happening?**
- OLED shows all status messages
- Check logs: `sudo journalctl -u votechain-kiosk -f`
- Or run manually: `sudo python3 kiosk_main.py`

**Services not starting on boot?**
```bash
# Check if services are enabled
sudo systemctl is-enabled votechain votechain-frontend votechain-kiosk

# Enable if needed
sudo systemctl enable votechain votechain-frontend votechain-kiosk

# Check status
./check-system.sh
```

## Production Deployment Checklist

- ✅ Backend auto-starts (votechain.service)
- ✅ Frontend auto-starts (votechain-frontend.service)  
- ✅ Kiosk auto-starts (votechain-kiosk.service)
- ✅ Keyboard input works headless (evdev with exclusive grab)
- ✅ OLED displays all prompts
- ✅ START button resets at any point
- ✅ Auto-restart on failure (all services)
- ✅ Logging configured (systemd journal)
- ✅ No demo mode (requires actual hardware)

System is **production-ready** for headless operation!
