# VoteChain V3 - Public Hosting Guide

This guide explains how to host VoteChain with public internet access, allowing voters and administrators to participate from anywhere without running a local server.

## 🎯 Overview

VoteChain supports a **hybrid hosting model**:

```
┌─────────────────────────────────────────────────────────┐
│ VOTERS / ADMINISTRATORS (Anywhere)                      │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     ▼
         ┌───────────────────────┐
         │   GitHub Pages CDN    │
         │  (Frontend: Static)   │
         │  admin.html, etc.     │
         └───────────┬───────────┘
                     │ Queries Supabase for URL
                     ▼
    ┌────────────────────────────┐
    │  Supabase system_config    │
    │   (Service Discovery)      │
    │   Key: backend_url         │
    │   Value: https://...       │
    └────────────────┬───────────┘
                     │ Contains tunnel URL
                     ▼
   ┌─────────────────────────────┐
   │  Cloudflare Tunnel          │
   │  (Free HTTPS proxy)         │
   │  https://xxx.trycloudflare │
   └────────────┬────────────────┘
                │ Port 3000
                ▼
   ┌──────────────────────────────┐
   │  Raspberry Pi Backend        │
   │  Node.js Server              │
   │  http://localhost:3000       │
   └──────────────────────────────┘
```

## 📋 Prerequisites

- ✅ Raspberry Pi running VoteChain backend
- ✅ Supabase project (free tier OK)
- ✅ GitHub account for Pages hosting
- ✅ Internet connection on both Pi and your workstation

## 🚀 Step 1: Frontend - GitHub Pages

### 1.1 Create Repository

```bash
# Already done if you forked: cainebenoy/blockchain-voting-dapp-v3
cd blockchain-voting-dapp-v3
git remote -v  # Verify origin points to your fork
```

### 1.2 Enable GitHub Pages

1. Go to **GitHub** → **Your Repository** → **Settings**
2. Click **Pages** (left sidebar)
3. Set:
   - **Source**: `Deploy from branch`
   - **Branch**: `main`
   - **Folder**: `/ (root)`
4. Click **Save**

Wait 60 seconds, then your site is live at:
```
https://yourusername.github.io/blockchain-voting-dapp-v3/
```

Test it:
- Frontend: `https://yourusername.github.io/blockchain-voting-dapp-v3/admin.html`
- Verification: `https://yourusername.github.io/blockchain-voting-dapp-v3/verify.html`

### 1.3 Commit & Push Updates

Whenever you update the frontend files, commit and push to deploy:

```bash
git add admin.html verify.html results.html
git commit -m "feat: update voting interface"
git push origin main
```

---

## 🔧 Step 2: Backend - Cloudflare Tunnel (On Raspberry Pi)

### 2.1 Install Cloudflared

```bash
# Download latest ARM64 release
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb

# Install
sudo dpkg -i cloudflared-linux-arm64.deb

# Verify
cloudflared --version
```

### 2.2 Install Python Dependencies

```bash
# Supabase client for database updates
sudo pip3 install supabase requests --break-system-packages
```

### 2.3 Verify Cloudflare Connectivity

```bash
# Test DNS resolution
ping -c 2 api.trycloudflare.com

# If DNS fails, set Google DNS:
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

---

## 📡 Step 3: Service Discovery - Supabase

### 3.1 Create Configuration Table

Go to **Supabase Dashboard** → **SQL Editor** → **New Query**

Paste and run this SQL:

```sql
-- Create the configuration table
CREATE TABLE IF NOT EXISTS public.system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Insert the placeholder row
INSERT INTO public.system_config (key, value)
VALUES ('backend_url', 'https://pending-setup.com')
ON CONFLICT (key) DO NOTHING;

-- Enable Row Level Security
ALTER TABLE public.system_config ENABLE ROW LEVEL SECURITY;

-- Allow Frontend to READ the URL
CREATE POLICY "Public Read URL" ON public.system_config FOR SELECT USING (true);

-- Allow Backend to UPDATE the URL
CREATE POLICY "Backend Update URL" ON public.system_config FOR UPDATE USING (true) WITH CHECK (true);
CREATE POLICY "Backend Insert URL" ON public.system_config FOR INSERT WITH CHECK (true);

-- Auto-update timestamp on changes
CREATE OR REPLACE FUNCTION update_system_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_system_config_timestamp_trigger ON public.system_config;
CREATE TRIGGER update_system_config_timestamp_trigger
    BEFORE UPDATE ON public.system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_system_config_timestamp();
```

Verify in **Table Editor**: You should see `system_config` table with one row.

### 3.2 Get Your Supabase Credentials

1. Go to **Supabase Dashboard** → **Project Settings** → **API**
2. Copy:
   - **Project URL**: `https://YOUR-PROJECT.supabase.co`
   - **Service Role Key** (secret): Start with `eyJhbG...`
   - **Anon Key** (public): Same format but different value

Note: Service Role Key is SECRET—only put it in `backend/.env`, not in HTML!

### 3.3 Update Tunnel Script

Edit `start_tunnel.py`:

```bash
nano start_tunnel.py
```

The script should already read credentials from `backend/.env`. Verify that your `backend/.env` has:

```bash
SUPABASE_URL="https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY="eyJhbGc..."  # Service role key
```

### 3.4 Update Frontend Files

Both `admin.html` and `verify.html` should already have your credentials. Verify the `<script>` section (around line 310 in admin.html):

```javascript
const CONFIG_SUPABASE_URL = "https://YOUR-PROJECT.supabase.co";
const CONFIG_SUPABASE_KEY = "eyJhbGc...";  // Service role key
```

---

## ✅ Step 4: Test the System

### 4.1 Verify Backend is Running

```bash
curl http://localhost:3000/api/health
# Should return: {"status":"ok","service":"VoteChain Backend","time":"..."}
```

### 4.2 Test Tunnel Script Manually

```bash
# Start the tunnel script
python3 start_tunnel.py

# Watch for output:
# ✅ TUNNEL URL FOUND: https://something.trycloudflare.com
# ✅ Database sync complete!
```

Check Supabase to verify URL was saved:
- **Table Editor** → **system_config**
- **value** column should show: `https://something.trycloudflare.com`

Press `Ctrl+C` to stop.

### 4.3 Test Public Backend Access

```bash
# Get the URL from Supabase or tunnel output
curl https://something.trycloudflare.com/api/health
# Should return the same health response
```

### 4.4 Test Frontend Discovery

Open your GitHub Pages site in a browser:
```
https://yourusername.github.io/blockchain-voting-dapp-v3/admin.html
```

Open **Browser Developer Tools** (F12) → **Console**

You should see:
```
✅ Backend discovered: https://something.trycloudflare.com
✅ Admin console initialized
```

Try clicking "Check Health" — should show green status.

---

## 🤖 Step 5: Automate with PM2 (Production)

### 5.1 Add to PM2

```bash
# Start the tunnel script as a PM2 service
pm2 start start_tunnel.py --name "auto-tunnel" --interpreter python3

# Save configuration
pm2 save

# Enable auto-start on boot
pm2 startup
```

Follow the output of `pm2 startup` to enable auto-launch.

### 5.2 Verify All Services

```bash
pm2 list

# Should show:
# ┌─────────────────────┬──────────┐
# │ auto-tunnel         │ online ✓ │
# │ votechain-backend   │ online ✓ │ (if using systemd, use: sudo systemctl status)
# │ votechain-kiosk     │ online ✓ │
# └─────────────────────┴──────────┘
```

### 5.3 Monitor Logs

```bash
# Watch tunnel output
pm2 logs auto-tunnel --follow

# Watch all services
pm2 monit
```

---

## 🔄 How It Works - The "Magic"

1. **Pi Boot**: PM2 starts `start_tunnel.py`
2. **Tunnel Starts**: `cloudflared tunnel --url http://localhost:3000`
3. **URL Assigned**: Cloudflare assigns `https://random-words.trycloudflare.com`
4. **URL Captured**: Script grabs URL from logs via regex
5. **Supabase Updated**: Script writes URL to `system_config.backend_url`
6. **Voter Opens Site**: GitHub Pages loads `admin.html`
7. **Discovery Runs**: JavaScript queries Supabase for `backend_url`
8. **Backend Found**: Frontend gets the tunnel URL and stores in `BACKEND_URL`
9. **All API Calls**: Use the discovered URL automatically

### No Manual Configuration Needed!

Every time the tunnel restarts (e.g., after power cycle), steps 1-5 happen automatically, and voters always get the current URL.

---

## 🛠️ Troubleshooting

### Problem: "Cannot find URL in logs"

**Causes**: DNS issues, network disconnected, cloudflared not installed

**Fix**:
```bash
# Check DNS
ping api.trycloudflare.com

# If fails, set to Google DNS:
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# Check cloudflared
which cloudflared
cloudflared --version

# Retry tunnel
python3 start_tunnel.py
```

### Problem: "Database Update Failed"

**Cause**: `system_config` table doesn't exist

**Fix**: Run the SQL script in Supabase SQL Editor (see Step 3.1)

### Problem: "Service discovery failed" in browser console

**Cause**: Wrong Supabase URL or key in HTML file

**Fix**:
1. Check `admin.html` line ~310 for correct credentials
2. Verify credentials match `backend/.env`
3. Hard refresh browser: `Ctrl+Shift+R`
4. Check browser console for exact error message

### Problem: Tunnel URL keeps changing

**Expected**: Free Cloudflare Tunnel gets a new URL on each restart

**Not a Problem**: Service discovery automatically detects new URL and frontend adapts

**If you need a stable URL**: Upgrade to paid Cloudflare plan or use Ngrok ($8/month for fixed subdomain)

### Problem: "Backend connection timeout"

**Check**:
1. Is backend running? `curl http://localhost:3000/api/health`
2. Is tunnel active? `pm2 logs auto-tunnel` should show "Tunnel is active"
3. Is the tunnel URL correct? Check Supabase `system_config` table
4. Try accessing tunnel directly: `curl https://xxx.trycloudflare.com/api/health`

### Problem: "Mixed Content" error (https frontend + http backend)

**This should NOT happen** because we use HTTPS tunnel: `https://xxx.trycloudflare.com`

**If it occurs**:
1. Verify Supabase shows `https://` URL, not `http://`
2. Check tunnel output logs: `pm2 logs auto-tunnel | grep "https://"`
3. Force browser cache clear: `Ctrl+Shift+R`

---

## 📊 Monitoring & Maintenance

### Daily Checks

```bash
# Tunnel status
pm2 logs auto-tunnel --lines 20

# Backend status
curl -s http://localhost:3000/api/health | python3 -m json.tool

# Current public URL
# Check browser console when visiting GitHub Pages site
# Or query directly:
curl -s "https://YOUR-PROJECT.supabase.co/rest/v1/system_config?key=eq.backend_url" \
  -H "apikey: YOUR_ANON_KEY"
```

### Weekly Maintenance

```bash
# Check disk space
df -h

# Check log file sizes
du -sh ~/.pm2/logs/*

# Update packages
sudo apt update && sudo apt upgrade -y
sudo pip3 install --upgrade supabase requests

# Cloudflared version
cloudflared --version
```

### Permanent DNS Configuration (Optional)

To make DNS changes persist across reboots:

```bash
# Edit netplan config (Ubuntu/Debian)
sudo nano /etc/netplan/01-netcfg.yaml

# Add this section:
# dhcp4-overrides:
#   use-dns: false
# nameservers:
#   addresses: [8.8.8.8, 8.8.4.4]

# Apply
sudo netplan apply

# Verify
cat /etc/resolv.conf
```

---

## 🔐 Security Considerations

### RLS Policies

- ✅ **Public read** of `system_config` (frontend needs this)
- ✅ **Service role only** can write (tunnel script key is secret)
- ✅ Tunnel URL is public (changes frequently, no sensitive data)

### API Keys

| Key | Used By | Access | Sensitive |
|-----|---------|--------|-----------|
| Service Role | `start_tunnel.py` | Read/Write system_config | ⚠️ **YES** |
| Anon Key | Frontend JS | Read system_config only | ✅ No |

Keep service role key **ONLY** in `backend/.env` (server-side), never in frontend code.

### CORS

Backend allows all origins (CORS is permissive). For production tightening:

```javascript
// In backend/server.js
const cors = require('cors');
app.use(cors({
    origin: 'https://yourusername.github.io'
}));
```

---

## 🎓 Advanced: Using Ngrok Instead of Cloudflare

If you prefer ngrok for a stable fixed subdomain:

```bash
# Install
curl https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Authenticate with token from https://dashboard.ngrok.com/auth
ngrok config add-authtoken YOUR_TOKEN

# Start tunnel
ngrok http 3000

# For fixed subdomain ($8/month):
ngrok http 3000 --domain=YOUR-FIXED-DOMAIN.ngrok-free.app

# Modify start_tunnel.py to use ngrok instead of cloudflared
```

---

## 📞 Support & Feedback

- Check `docs/TROUBLESHOOTING.md` for common issues
- Review `docs/SERVICE_DISCOVERY.md` for detailed technical architecture
- See `SECURITY.md` for security best practices

---

**Your VoteChain system is now ready for public voting! 🎉**
