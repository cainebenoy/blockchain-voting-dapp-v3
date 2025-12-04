# VoteChain V3 - Deployment Status

**Last Updated**: December 4, 2025, 22:39 IST

## 🎉 System Status: FULLY OPERATIONAL

### Frontend (GitHub Pages)
- **URL**: https://cainebenoy.github.io/blockchain-voting-dapp-v3/
- **Admin UI**: https://cainebenoy.github.io/blockchain-voting-dapp-v3/admin.html
- **Verify UI**: https://cainebenoy.github.io/blockchain-voting-dapp-v3/verify.html
- **Status**: ✅ Live and accessible globally

### Backend (Raspberry Pi)
- **Local**: http://localhost:3000
- **Public Tunnel**: https://destination-payments-amongst-machine.trycloudflare.com
- **Status**: ✅ Running via systemd service
- **Service**: `votechain.service`

### Service Discovery
- **Method**: Cloudflare Tunnel + Supabase
- **Tunnel Manager**: Running in PM2 as `auto-tunnel`
- **Database**: Supabase `system_config` table
- **Current URL**: https://destination-payments-amongst-machine.trycloudflare.com
- **Auto-Update**: ✅ Enabled (updates Supabase on tunnel restart)
- **Status**: ✅ Fully functional

### Kiosk Terminal
- **Status**: ✅ Running via systemd service
- **Service**: `votechain-kiosk.service`
- **PID**: 5543

### Auto-Start Configuration
- **PM2 Systemd**: ✅ Configured (`pm2-cainepi.service`)
- **Backend Service**: ✅ Enabled (starts on boot)
- **Kiosk Service**: ✅ Enabled (starts on boot)

## How It Works

1. **User visits**: https://cainebenoy.github.io/blockchain-voting-dapp-v3/admin.html
2. **Frontend queries Supabase**: Fetches current `backend_url` from `system_config` table
3. **Dynamic connection**: Frontend automatically connects to the current tunnel URL
4. **No manual config**: System adapts when tunnel restarts (new URL auto-synced)

## Quick Commands

### Check System Status
```bash
# Backend service
systemctl status votechain.service

# Kiosk service
systemctl status votechain-kiosk.service

# Tunnel manager
pm2 status
pm2 logs auto-tunnel
```

### Get Current Tunnel URL
```bash
pm2 logs auto-tunnel --lines 20 | grep "TUNNEL URL FOUND"
```

### Test Backend
```bash
# Local
curl http://localhost:3000/api/health

# Public
curl https://destination-payments-amongst-machine.trycloudflare.com/api/health
```

### Restart Services
```bash
# Backend
sudo systemctl restart votechain.service

# Kiosk
sudo systemctl restart votechain-kiosk.service

# Tunnel
pm2 restart auto-tunnel
```

## Important Notes

1. **Tunnel URL Changes**: The Cloudflare free tunnel URL changes on each restart - this is normal. Service discovery handles this automatically.

2. **DNS Configuration**: System uses Google DNS (8.8.8.8) for reliable Cloudflare API access.

3. **PM2 Process List**: Saved with `pm2 save` - tunnel will auto-start on Pi reboot.

4. **GitHub Pages**: Hosted on branch `main`, root directory. Any push to main auto-deploys.

## Troubleshooting

### Frontend can't connect to backend
1. Check tunnel is running: `pm2 status`
2. Verify Supabase has correct URL: See `start_tunnel.py` logs
3. Hard refresh browser: `Ctrl+Shift+R`

### Tunnel keeps restarting
1. Check DNS: `cat /etc/resolv.conf` (should have 8.8.8.8)
2. Check backend is running: `systemctl status votechain.service`
3. View tunnel logs: `pm2 logs auto-tunnel`

### Services not starting on boot
1. Verify systemd services: `systemctl list-unit-files | grep votechain`
2. Verify PM2 startup: `systemctl status pm2-cainepi`
3. Check service logs: `journalctl -u votechain.service -n 50`

## Monitoring

- **PM2 Dashboard**: `pm2 monit`
- **Backend Logs**: `journalctl -u votechain.service -f`
- **Kiosk Logs**: `journalctl -u votechain-kiosk.service -f`
- **Tunnel Logs**: `pm2 logs auto-tunnel`

## Security Notes

- Service role keys are used in both frontend and tunnel script for Supabase write access
- RLS policies protect the `system_config` table (public read, service role write)
- CORS is configured in backend to accept GitHub Pages origin

---

**Deployment Complete**: All systems operational and configured for production use! 🚀
