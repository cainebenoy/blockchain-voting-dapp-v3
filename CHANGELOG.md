# Changelog

All notable changes to this project are documented in this file.

## [Unreleased] - 2025-11-29

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
