# VoteChain V3 - Service Discovery Deployment Guide

This guide walks you through setting up the complete "plug-and-play" service discovery system that allows your VoteChain frontend (hosted on GitHub Pages) to automatically find your Raspberry Pi backend, no matter where it's connected to the internet.

## 🏗️ Architecture Overview

```
Frontend (GitHub Pages)
        ↓
Supabase Config Table (system_config)
        ↓
Cloudflare Tunnel (on Raspberry Pi)
        ↓
Backend Server (localhost:3000)
```

## 📋 Prerequisites

- ✅ Raspberry Pi with VoteChain backend running
- ✅ Supabase project (already configured for voters/receipts)
- ✅ GitHub Pages hosting for frontend files
- ✅ Internet connection on Raspberry Pi

---

## Phase 1: Supabase Configuration

### Step 1: Create the Configuration Table

1. **Open Supabase SQL Editor:**
   - Go to your Supabase Dashboard → SQL Editor
   - Create a new query

2. **Run the Setup Script:**
   ```bash
   # The script is already in your repository
   cat supabase-setup.sql
   ```

3. **Execute in Supabase:**
   - Copy the entire contents of `supabase-setup.sql`
   - Paste into Supabase SQL Editor
   - Click "Run"

4. **Verify Setup:**
   ```sql
   SELECT * FROM public.system_config;
   ```
   You should see one row with key='backend_url' and value='https://waiting-for-tunnel.com'

---

## Phase 2: Install Cloudflare Tunnel (Raspberry Pi)

### Step 1: Install Cloudflared

```bash
# Download (ARM64 for Pi 5, armhf for older Pi)
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb

# Install
sudo dpkg -i cloudflared-linux-arm64.deb

# Verify
cloudflared --version
```

### Step 2: Install Python Dependencies

```bash
pip3 install supabase --break-system-packages
```

### Step 3: Configure the Tunnel Script

Edit the script to add your Supabase credentials:

```bash
nano start_tunnel.py
```

Update these lines (around line 33-34):
```python
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-SERVICE-ROLE-KEY-HERE"
```

**Important:** Use your **service role key** (not anon key) for write access.

Where to find these:
- Supabase Dashboard → Settings → API
- Copy "Project URL" and "service_role" secret key

Save and exit (`Ctrl+X`, `Y`, `Enter`)

### Step 4: Test the Tunnel Script

```bash
# Make sure backend is running first
cd backend
node server.js &

# In another terminal, test the tunnel script
cd ..
python3 start_tunnel.py
```

**Expected output:**
```
🚀 Starting Cloudflare Tunnel for http://localhost:3000
⏳ Waiting for Cloudflare tunnel URL...
[TUNNEL] 2025-12-04T...
✅ TUNNEL URL FOUND: https://abc123xyz.trycloudflare.com
💾 Updating Supabase with: https://abc123xyz.trycloudflare.com
✅ Database sync complete!
🔒 Tunnel is active. Monitoring for failures...
```

**Verify in Supabase:**
```sql
SELECT * FROM system_config WHERE key = 'backend_url';
```

The `value` should now show your Cloudflare tunnel URL!

Press `Ctrl+C` to stop the tunnel for now.

---

## Phase 3: Automate with PM2 (Production)

### Step 1: Install PM2 (if not already installed)

```bash
sudo npm install -g pm2
```

### Step 2: Add Tunnel to PM2

```bash
cd /home/cainepi/Desktop/FInal Year Project/blockchain-voting-dapp-v3

# Start tunnel manager
pm2 start start_tunnel.py \
    --name "auto-tunnel" \
    --interpreter python3 \
    --restart-delay 5000
```

### Step 3: Configure PM2 Ecosystem (Optional but Recommended)

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [
    {
      name: 'votechain-backend',
      cwd: './backend',
      script: 'server.js',
      interpreter: 'node',
      env: {
        NODE_ENV: 'production'
      },
      restart_delay: 5000,
      max_restarts: 10
    },
    {
      name: 'votechain-kiosk',
      script: 'kiosk_main.py',
      interpreter: 'python3',
      restart_delay: 10000,
      max_restarts: 5
    },
    {
      name: 'auto-tunnel',
      script: 'start_tunnel.py',
      interpreter: 'python3',
      restart_delay: 5000,
      max_restarts: 10
    }
  ]
};
```

Then manage all services together:

```bash
# Start everything
pm2 start ecosystem.config.js

# Check status
pm2 list

# View logs
pm2 logs auto-tunnel
pm2 logs votechain-backend
pm2 logs votechain-kiosk

# Save configuration
pm2 save

# Enable startup on boot
pm2 startup
# Follow the command it outputs
```

---

## Phase 4: Update GitHub Pages Frontend

### Step 1: Push Updated Frontend

The frontend files (`admin.html` and `verify.html`) have already been updated with service discovery logic. Just commit and push:

```bash
git add admin.html verify.html supabase-setup.sql start_tunnel.py
git commit -m "feat: add service discovery for automatic backend URL detection"
git push origin main
```

### Step 2: Enable GitHub Pages

1. Go to your repository on GitHub
2. Settings → Pages
3. Source: Deploy from branch `main` / `root`
4. Save

Wait ~60 seconds, then your site will be live at:
```
https://yourusername.github.io/blockchain-voting-dapp-v3/
```

---

## 🧪 Testing the Complete System

### Test 1: Local Discovery (Development)

1. Open `admin.html` locally (file:// or localhost)
2. Check browser console (F12)
3. Should see: `🔧 Running locally - using localhost backend`

### Test 2: Remote Discovery (Production)

1. Open your GitHub Pages URL: `https://yourusername.github.io/blockchain-voting-dapp-v3/admin.html`
2. Check browser console (F12)
3. Should see:
   ```
   🔄 Discovering backend URL from Supabase...
   ✅ Backend discovered: https://abc123xyz.trycloudflare.com
   ✅ Admin console initialized
   ```

4. Try clicking "Check Health" - should connect successfully!

### Test 3: Verify Receipt Code

1. Go to `https://yourusername.github.io/blockchain-voting-dapp-v3/verify.html`
2. Enter a receipt code (e.g., `ABC-123`)
3. Should discover backend and verify the transaction

---

## 🔧 Troubleshooting

### Issue: "Service discovery failed"

**Check 1: Is tunnel running?**
```bash
pm2 list
# Should show auto-tunnel: online
```

**Check 2: Is URL in Supabase?**
```sql
SELECT * FROM system_config WHERE key = 'backend_url';
```

**Check 3: Check tunnel logs:**
```bash
pm2 logs auto-tunnel
```

### Issue: "Backend URL not yet configured"

The Supabase table still has the placeholder value. Check:

1. Tunnel script is running
2. Supabase credentials are correct in `start_tunnel.py`
3. Service role key has write permission

### Issue: "CORS error" in browser

The tunnel URL changed but frontend cached the old one. Solution:
1. Hard refresh browser (Ctrl+Shift+R)
2. Check Supabase for current URL
3. Restart tunnel if needed: `pm2 restart auto-tunnel`

### Issue: Tunnel URL keeps changing

This is normal for free Cloudflare Tunnel. Each restart gets a new URL. The system handles this automatically, but:

**For stable demos:**
- Start tunnel 5 minutes before presentation
- Don't restart Pi during demo
- Consider upgrading to paid ngrok ($8/month) for fixed subdomain

---

## 🚀 Demo Day Checklist

**1 Hour Before:**
- [ ] Power on Raspberry Pi
- [ ] Wait 2 minutes for services to start
- [ ] Check PM2 status: `pm2 list` (all green?)
- [ ] Check Supabase for tunnel URL
- [ ] Open GitHub Pages and test discovery

**5 Minutes Before:**
- [ ] Open `admin.html` on your laptop
- [ ] Click "Check Health" (should be green)
- [ ] Have a test receipt code ready to verify

**During Demo:**
- Keep PM2 dashboard open: `pm2 monit`
- If tunnel crashes, it will auto-restart in 5 seconds
- If disaster strikes: `pm2 restart all`

---

## 🎯 Monitoring & Maintenance

### View Real-Time Logs

```bash
# All services
pm2 logs

# Specific service
pm2 logs auto-tunnel --lines 50

# Follow tunnel activity
pm2 logs auto-tunnel --follow
```

### Check System Health

```bash
# PM2 status
pm2 list

# Detailed info
pm2 info auto-tunnel

# Backend health
curl http://localhost:3000/api/health

# Current tunnel URL
curl -s https://YOUR-PROJECT.supabase.co/rest/v1/system_config?key=eq.backend_url \
  -H "apikey: YOUR-ANON-KEY" | jq
```

### Restart Services

```bash
# Restart tunnel only
pm2 restart auto-tunnel

# Restart everything
pm2 restart all

# Stop and start clean
pm2 stop all && pm2 start all
```

---

## 🔐 Security Considerations

1. **Service Role Key:** Stored in `start_tunnel.py` - keep this file secure
2. **RLS Policies:** Public can read `system_config`, only service role can write
3. **Tunnel URLs:** Publicly accessible but change frequently (security by obscurity)
4. **Rate Limiting:** Already configured in backend (`express-rate-limit`)

---

## 📖 How It Works

1. **On Pi Boot:**
   - PM2 starts `auto-tunnel`
   - Script runs `cloudflared tunnel --url http://localhost:3000`
   - Cloudflare assigns random URL like `https://abc-123.trycloudflare.com`
   - Script captures URL from tunnel logs
   - Script updates Supabase `system_config` table

2. **When User Opens Frontend:**
   - Browser loads `admin.html` from GitHub Pages
   - JavaScript checks if running locally (uses localhost) or remotely
   - If remote, queries Supabase for `backend_url`
   - Sets `BACKEND_URL` variable dynamically
   - All subsequent API calls use discovered URL

3. **On Tunnel Crash:**
   - PM2 auto-restarts `start_tunnel.py` in 5 seconds
   - New tunnel gets new URL
   - Script updates Supabase automatically
   - Frontend discovers new URL on next page load

---

## 🎓 Advanced: Using Ngrok Instead

If you prefer ngrok over Cloudflare:

1. Sign up at https://ngrok.com
2. Install: `sudo apt install ngrok`
3. Auth: `ngrok authtoken YOUR-TOKEN`
4. Modify `start_tunnel.py`:
   ```python
   # Replace cloudflared command with:
   process = subprocess.Popen(
       ["ngrok", "http", "3000"],
       # ... rest same
   )
   # Update regex to match ngrok URLs:
   url_pattern = re.compile(r'https://[a-zA-Z0-9-]+\.ngrok-free\.app')
   ```

---

## 📞 Support

- **Check logs first:** `pm2 logs auto-tunnel`
- **Verify Supabase:** Check SQL Editor for current URL
- **Test backend directly:** `curl http://localhost:3000/api/health`
- **Browser console:** Always check F12 developer tools

---

**You're all set! Your VoteChain system is now production-ready with automatic service discovery. 🎉**
