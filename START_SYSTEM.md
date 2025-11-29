
# 🚀 VoteChain V3 - System Startup Guide

## 🎉 Production Mode — Auto start on boot

**The system is now fully configured to auto-start!** All services will launch automatically when you power on the Raspberry Pi.

### Quick start (after boot)

```bash
# Check everything is running
./check-system.sh

# Or use master control
./votechain.sh status
```

**Expected startup time:** ~20 seconds after power-on

### Using headless (no monitor)

1. Power on Pi
2. Wait 20 seconds
3. Press START button on kiosk
4. Type Aadhaar on keyboard (appears on OLED)
5. Follow OLED prompts

**Press START button anytime to reset!**

---

## 📋 Manual control

### Start/stop all services

```bash
./votechain.sh start    # Start everything
./votechain.sh stop     # Stop everything
./votechain.sh restart  # Restart everything
./votechain.sh status   # Check status
```

### View logs

```bash
./votechain.sh logs backend   # Backend logs
./votechain.sh logs frontend  # Frontend logs
./votechain.sh logs kiosk     # Kiosk logs
```

---

## 🔧 Manual startup (development mode)

If you need to run services manually for testing, follow these steps.

## ✅ Pre-flight checklist

Your system is already configured correctly:

- ✅ `kiosk_main.py` → `BACKEND_URL = http://127.0.0.1:3000`
- ✅ `admin.html` → `BACKEND_URL = http://127.0.0.1:3000`
- ✅ Backend has all enrollment endpoints ready
- ✅ All files are on the same Pi (no network setup needed)

---

## 🎯 Step-by-step startup

### 1️⃣ Start the backend server

Open a terminal in VS Code (or press ``Ctrl+` ``):

```bash
cd backend
node server.js
```

**Expected output:**

```text
🔌 Connected to Supabase
🤖 VoteChain V3 Backend API listening on http://localhost:3000
```

> ⚠️ Leave this terminal running — do not close it.

---

### 2️⃣ Start the kiosk script

Open a **second terminal** in VS Code (click the `+` button):

```bash
python3 kiosk_main.py
```

**Expected output:**

```text
🔌 OLED Connected
🖐️ Fingerprint Scanner Ready
⏳ Polling backend for commands...
```

> ⚠️ Leave this terminal running too — the OLED should light up.

---

### 3️⃣ Open the admin dashboard

#### Option A: Quick open (recommended)

1. Press `Ctrl+O` in Chromium Browser
2. Navigate to your project folder
3. Select `admin.html`
4. Press Open

#### Option B: Direct path

Open Chromium and type in the address bar:

```text
file:///home/cainepi/Desktop/FInal%20Year%20Project/blockchain-voting-dapp-v3/admin.html
```

---

## 🧪 Test the remote enrollment

### In the admin dashboard

1. **Fill in the registration form:**
   - Aadhaar Number: `999999999999` (12 digits)
   - Name: `Test Pi User`
   - Constituency: `District 1` (optional)

2. **Click "Register Eligible Voter"**

3. **Watch the flow:**
   - 🔵 Browser shows "Waiting for Kiosk Scan..."
   - 💡 OLED wakes up and displays "PLACE FINGER ON SCANNER"
   - 🖐️ Place your finger on the R307 scanner
   - ✅ Browser shows "Voter Enrolled & Saved!"

---

## 🔍 Troubleshooting

### Backend won't start

```bash
# Check if port 3000 is already in use
sudo lsof -i:3000

# Kill the old process if needed
sudo kill -9 <PID>

# Restart backend
cd backend && node server.js
```

### Kiosk script errors

```bash
# Check if fingerprint scanner is connected
ls /dev/ttyAMA0

# Check OLED connections
# Make sure SPI is enabled: sudo raspi-config → Interface Options → SPI → Enable
```

### Admin page not connecting

- Make sure backend is running (check terminal #1)
- Check browser console for errors (F12)
- Verify `BACKEND_URL` is `http://127.0.0.1:3000` in the script

---

## 📊 View results

After testing enrollment, open the public results dashboard:

### Option 1: Press `Ctrl+O` and select `index.html`

### Option 2: Open in browser

```text
file:///home/cainepi/Desktop/FInal%20Year%20Project/blockchain-voting-dapp-v3/index.html
```

---

## 🎉 Success indicators

When everything works, you should see:

- ✅ Terminal 1: `🤖 Backend listening...`
- ✅ Terminal 2: `⏳ Polling backend...`
- ✅ OLED: Displaying messages
- ✅ Browser: "✅ Voter Enrolled & Saved!"

---

## 📝 Notes

- **MetaMask is optional** for testing the enrollment feature (it only uses the backend)
- The enrollment happens **entirely offline** on your Pi
- Fingerprint data is stored in Supabase (check the `voters` table)
- Each voter gets a unique `fingerprint_id` (1, 2, 3, etc.)

---

## 🚦 Next steps after successful test

1. Add real voters with actual fingerprints
2. Test the full voting flow (check-in → scan → vote)
3. Monitor blockchain transactions on Sepolia Etherscan
4. Set up PM2 for production (auto-restart on boot)

---

**Ready to test? Follow the steps above and verify the enrollment loop works!** 🎯
