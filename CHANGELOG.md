# Changelog

All notable changes to this project are documented in this file.

## [2025-12-04] - Service Discovery System (Complete)

### Added - Service Discovery & Hybrid Hosting

- **Cloudflare Tunnel integration**: `start_tunnel.py` manages tunnel lifecycle, extracts public URL from logs, and updates Supabase with the current backend address
- **Supabase service discovery**: `system_config` table stores dynamic backend URL with RLS policies (public read, service role write)
- **Frontend auto-discovery**: `admin.html` and `verify.html` query Supabase on load to dynamically discover backend URL
- **Zero-configuration hybrid hosting**: Frontend on GitHub Pages + Backend on Raspberry Pi via Cloudflare Tunnel with automatic URL resolution
- **Service discovery documentation**: Complete `docs/SERVICE_DISCOVERY.md` with setup steps, testing procedures, troubleshooting, and monitoring
- **PM2 integration**: Tunnel manager added to PM2 for automatic startup on Pi boot
- **DNS resilience**: Automatic DNS configuration for reliable Cloudflare API access
- **Environment variable loading**: `start_tunnel.py` automatically loads Supabase credentials from `backend/.env`

### Fixed

- **DNS resolution**: Set default DNS to Google 8.8.8.8 to resolve Cloudflare API connectivity issues

### Changed

- **Architecture**: Added service discovery layer for flexible, location-independent deployment
- **Frontend initialization**: Both HTML frontends now perform service discovery before initializing contract instances
- **Deployment model**: Supports GitHub Pages + Pi hybrid model without manual URL configuration

---

## [Unreleased] - Earlier Changes

### Added

- **Fingerprint retry logic**: Kiosk now allows one retry attempt during voting if the first fingerprint scan fails, improving user experience and reducing false rejections.
- **Deployment automation**: Backend now handles contract deployment via `/api/admin/deploy-contract` endpoint; deployment scripts updated to centralize deployment through backend API.
- **AUTO_RESTART configuration**: Added `AUTO_RESTART` environment variable to backend `.env` to control automatic systemd service restarts after deployment.
- **Active contract endpoint**: Added `/api/active-contract` to return current contract address and network info for frontend/admin UI synchronization.

### Fixed

- **Kiosk indentation error**: Corrected Python indentation in fingerprint verification block that prevented kiosk from starting on boot.
- **TypeScript type errors**: Fixed error handling in `scripts/deployV2.ts` to properly handle unknown exception types.
- **Backend syntax issues**: Removed duplicate `/api/verify-code` endpoint and fixed missing closing bracket in `app.listen()`.
- **ESLint warnings**: Renamed unused catch variables to `_e` convention to suppress warnings.

### Changed

- **Backend contract runtime updates**: Made contract instance mutable to allow hot-swapping after deployments without full server restart.
- **Deployment flow**: Centralized deployment to backend API; `scripts/deployV2.ts` now calls backend endpoint instead of deploying directly.
- **Admin UI improvements**: Enhanced deploy button to refresh config and reinitialize contract instance after successful deployment.

## [Previous] - 2025-11-29

- Commit `c464e3d` — kiosk: fix OLED rendering, hardware checks, idle font/shadow tweaks
  - Make the Raspberry Pi kiosk robust to hardware errors: persistent OLED error messages and guarded device access (no unexpected process exits on hardware faults).
  - Fix OLED rendering issues (safe ImageFont usage + fallback), remove white borders from screen clears, and fix the "invisible ink" bug in `show_msg()`.
  - Add `show_idle()` (idle screen), adjust title font to 17pt and tweak shadow offset for better readability.
  - Add `wait_for_reset()` for consistent reset behavior; improve fingerprint scan and check-in flows.
  - Add hardware health checks on boot (LEDs / Buttons / OLED) and small static-analysis stubs to avoid undefined-variable diagnostics.

---

### 2025-11-30 — Maintenance

- Removed duplicate `/api/verify-code` route handler in `backend/server.js` to avoid ambiguous routing and potential unexpected behavior.
  - Kept a single canonical `/api/verify-code` handler that normalizes codes to uppercase and returns the associated `tx_hash` from the `receipts` table.
  - Restarted the backend and verified `GET /api/health` and `POST /api/verify-code` (`FRN-GFG`) return expected responses.

This was a conservative cleanup to remove duplicated route definitions and prevent accidental future regressions.

### 2025-11-30 — Feature: Short-code receipt system

- Backend: generate and persist short, human-friendly receipt codes (`code`) mapped to on-chain `tx_hash` in a `receipts` Supabase table.
- Endpoints: added `/api/lookup-receipt` (tx_hash -> code) for kiosk polling and stabilized `/api/verify-code` (code -> tx_hash) for verify UI.
- Kiosk: poll backend for receipt codes after vote submission and fallback to showing truncated `tx_hash` if code not available.
- Docs: updated README and project docs with deployment, troubleshooting, and schema notes.
