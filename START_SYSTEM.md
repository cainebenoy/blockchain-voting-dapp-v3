# 🚀 VoteChain V3 - System Startup Guide

## ✅ Pre-Flight Checklist

Your system is already configured correctly:
- ✅ `kiosk_main.py` → BACKEND_URL = `http://127.0.0.1:3000`
- ✅ `admin.html` → BACKEND_URL = `http://127.0.0.1:3000`
- ✅ Backend has all enrollment endpoints ready
- ✅ All files are on the same Pi (no network setup needed!)

---

## 🎯 Step-by-Step Startup

### 1️⃣ Start the Backend Server

Open a terminal in VS Code (or press `` Ctrl+` ``):

```bash
cd backend
node server.js
```

**Expected Output:**
```
🔌 Connected to Supabase
🤖 VoteChain V3 Backend API listening on http://localhost:3000
```

> ⚠️ Leave this terminal running! Don't close it.

---

### 2️⃣ Start the Kiosk Script

Open a **second terminal** in VS Code (click the `+` button):

```bash
python3 kiosk_main.py
```

**Expected Output:**
```
🔌 OLED Connected
🖐️ Fingerprint Scanner Ready
⏳ Polling backend for commands...
```

> ⚠️ Leave this terminal running too! The OLED should light up.

---

### 3️⃣ Open the Admin Dashboard

**Option A: Quick Open (Recommended)**
1. Press `Ctrl+O` in Chromium Browser
2. Navigate to your project folder
3. Select `admin.html`
4. Press Open

**Option B: Direct Path**
Open Chromium and type in the address bar:
```
file:///home/cainepi/Desktop/FInal%20Year%20Project/blockchain-voting-dapp-v3/admin.html
```

---

## 🧪 Test the Remote Enrollment

### In the Admin Dashboard:

1. **Fill in the Registration Form:**
   - Aadhaar Number: `999999999999` (12 digits)
   - Name: `Test Pi User`
   - Constituency: `District 1` (optional)

2. **Click "Register Eligible Voter"**

3. **Watch the Magic Happen:**
   - 🔵 Browser shows "Waiting for Kiosk Scan..."
   - 💡 OLED wakes up and displays "PLACE FINGER ON SCANNER"
   - 🖐️ Place your finger on the R307 scanner
   - ✅ Browser shows "Voter Enrolled & Saved!"

---

## 🔍 Troubleshooting

### Backend won't start?
```bash
# Check if port 3000 is already in use
sudo lsof -i:3000

# Kill the old process if needed
sudo kill -9 <PID>

# Restart backend
cd backend && node server.js
```

### Kiosk script errors?
```bash
# Check if fingerprint scanner is connected
ls /dev/ttyAMA0

# Check OLED connections
# Make sure SPI is enabled: sudo raspi-config → Interface Options → SPI → Enable
```

### Admin page not connecting?
- Make sure backend is running (check terminal #1)
- Check browser console for errors (F12)
- Verify BACKEND_URL is `http://127.0.0.1:3000` in the script

---

## 📊 View Results

After testing enrollment, open the public results dashboard:

**Option 1:** Press `Ctrl+O` and select `index.html`

**Option 2:** Open in browser:
```
file:///home/cainepi/Desktop/FInal%20Year%20Project/blockchain-voting-dapp-v3/index.html
```

---

## 🎉 Success Indicators

When everything works, you should see:

✅ Terminal 1: `🤖 Backend listening...`  
✅ Terminal 2: `⏳ Polling backend...`  
✅ OLED: Displaying messages  
✅ Browser: "✅ Voter Enrolled & Saved!"  

---

## 📝 Notes

- **MetaMask is optional** for testing the enrollment feature (it only uses the backend)
- The enrollment happens **entirely offline** on your Pi
- Fingerprint data is stored in Supabase (check the `voters` table)
- Each voter gets a unique `fingerprint_id` (1, 2, 3, etc.)

---

## 🚦 Next Steps After Successful Test

1. Add real voters with actual fingerprints
2. Test the full voting flow (check-in → scan → vote)
3. Monitor blockchain transactions on Sepolia Etherscan
4. Set up PM2 for production (auto-restart on boot)

---

**Ready to test? Follow the steps above and verify the enrollment loop works!** 🎯
