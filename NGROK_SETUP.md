# VoteChain Ngrok Setup Guide

## 🎯 Overview
This guide will help you set up permanent remote access to your Raspberry Pi kiosk using Ngrok's free static domain feature.

## 📋 Prerequisites
- Raspberry Pi with internet connection
- Ngrok account (free tier)
- VoteChain backend running on Pi

---

## Step 1: Get Your Ngrok Static Domain

1. **Sign up/Login** at [ngrok.com](https://ngrok.com)
2. Navigate to **Cloud Edge → Domains**
3. Click **"Create Domain"** or **"New Domain"**
4. Ngrok will assign you a free permanent domain like:
   ```
   shrimp-solid-mortal.ngrok-free.app
   ```
5. **Copy this domain** - you'll need it later

6. Go to **Your Authtoken** section
7. **Copy your authtoken** (looks like: `2abc...xyz`)

---

## Step 2: Install Ngrok on Raspberry Pi

```bash
# Download and install Ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok

# Verify installation
ngrok version
```

---

## Step 3: Get Your Authtoken

1. Go to your [Ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
2. Copy your **Authtoken** (e.g., `2Lp...`)
3. **Note**: You do NOT need to run the `ngrok config add-authtoken` command if you use the `.env` method in Step 5 (recommended for security).

---

## Step 4: Install Python Dependencies

```bash
# Navigate to your project
cd ~/blockchain-voting-dapp-v3-main

# Install Python requirements
pip3 install -r pi/requirements.txt
```

---

---

## Step 5: Configure Environment Variables

Instead of editing the script directly, create a `.env` file in the `pi/` directory:

1. **Create the file**:
   ```bash
   cd pi
   cp .env.example .env
   nano .env
   ```

2. **Update the values** in the editor:
   - `SUPABASE_URL`: Your project URL
   - `SUPABASE_KEY`: Your project service role key
   - `NGROK_DOMAIN`: `remunerable-rhiannon-noncleistogamous.ngrok-free.dev`
   - `NGROK_AUTHTOKEN`: Paste your token from Step 3 here

3. **Save and exit** (Ctrl+O, Enter, Ctrl+X)

---

## Step 6: Test the Setup

### Option A: Manual Test (Recommended First Time)

1. **Start backend manually**:
   ```bash
   cd ~/blockchain-voting-dapp-v3-main/backend
   node server.js &
   ```

2. **Wait 5 seconds, then start tunnel**:
   ```bash
   cd ..
   python3 pi/ngrok_discovery.py
   ```

You should see:
```
🚀 Launching Ngrok tunnel: your-domain.ngrok-free.app
📡 Supabase updated: https://your-domain.ngrok-free.app (starting)
💚 Heartbeat OK (Backend responding)
```

**Press Ctrl+C to stop when done testing.**

### Option B: Automated Startup Script

```bash
# Make script executable
chmod +x pi/start_kiosk.sh

# Run it
./pi/start_kiosk.sh
```

This will:
1. Start the backend server
2. Wait 5 seconds
3. Launch Ngrok tunnel
4. Send heartbeats every 30 seconds

---

## Step 7: Verify Remote Access

1. Open your laptop/phone browser
2. Go to any VoteChain page (e.g., `simulator.html`)
3. The page will automatically discover your Pi's URL from Supabase
4. You should see "🔗 Connected to Kiosk" in the browser console

---

## 🔄 Auto-Start on Boot (Optional)

To make the kiosk start automatically when Pi boots:

```bash
# Edit crontab
crontab -e

# Add this line at the end:
@reboot sleep 30 && cd /home/pi/blockchain-voting-dapp-v3-main && ./pi/start_kiosk.sh >> /home/pi/kiosk.log 2>&1
```

This will:
- Wait 30 seconds after boot (for network to connect)
- Start the kiosk automatically
- Log output to `~/kiosk.log`

---

## 🐛 Troubleshooting

### "Ngrok not found"
```bash
# Reinstall ngrok
sudo apt update && sudo apt install ngrok
```

### "Backend not responding"
```bash
# Check if backend is running
ps aux | grep node

# Check backend logs
cd backend
npm start
```

### "Tunnel keeps disconnecting"
- Check your internet connection
- Ngrok free tier has connection limits (~40/min)
- The script auto-restarts on failure

### "Websites can't find the Pi"
1. Check Supabase `system_config` table
2. Verify `backend_url` has your Ngrok domain
3. Check browser console for errors

---

## 📊 Monitoring

### Check Kiosk Status
```bash
# View live logs
tail -f ~/kiosk.log

# Check if tunnel is running
ps aux | grep ngrok
```

### Supabase Dashboard
Check the `system_config` table for:
- `backend_url`: Your Ngrok URL
- `kiosk_status`: Should be "online"
- `kiosk_last_seen`: Recent timestamp

---

## 🎓 For Your Demo

### Before Presentation:
1. Power on Raspberry Pi
2. Wait ~1 minute for auto-start
3. Check `kiosk_last_seen` in Supabase (should be recent)
4. Open `simulator.html` on your laptop to verify connection

### During Presentation:
- Your Ngrok domain **never changes**, so no URL updates needed
- All websites automatically find the Pi via Supabase
- Show the "Kiosk Online" indicator to prove live connection

### After Presentation:
- Just power off the Pi - no cleanup needed
- Next time you boot, everything auto-starts

---

## 🔐 Security Notes

- **Auth Token Warning**: You previously pasted your auth token in chat. If you ever share your screen or code, consider resetting it in the Ngrok dashboard (`Settings` -> `Update Authtoken`) to be safe.
- The Ngrok URL is public but requires your backend's admin secret for sensitive operations
- Rate limiting is enforced by Ngrok (free tier)
- For production, consider upgrading to Ngrok paid tier or Cloudflare Tunnel

---

## 📞 Need Help?

Common issues and fixes:
1. **Domain not updating**: Check Supabase credentials in `ngrok_discovery.py`
2. **Heartbeat failing**: Ensure backend is running on port 3000
3. **Tunnel won't start**: Run `ngrok config add-authtoken` again

For more help, check the Ngrok docs: https://ngrok.com/docs
