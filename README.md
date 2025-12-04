# VoteChain V3 — Blockchain Voting DApp

## Overview

VoteChain V3 is a secure, cyber-physical voting system that combines biometric authentication, blockchain transparency, and a user-friendly kiosk interface. It is designed for real-world elections with emphasis on privacy, auditability, and resilient operation in constrained environments.

## Features

- Biometric voter authentication (fingerprint) with retry logic for improved reliability
- Immutable blockchain vote ledger
- Real-time public dashboard
- Server-signed transactions (no voter wallet required)
- API endpoints for results, health, and configuration
- Modular architecture: kiosk, backend, database, blockchain
- Security: double-vote prevention, rate limiting, CORS, audit logging
- Automated deployment and contract management via backend API
- Auto-restart capability for production environments

## System Architecture

1. **Smart Kiosk (Edge Layer):** Raspberry Pi, fingerprint scanner, OLED display, physical buttons
2. **Backend Server (Trust Layer):** Node.js, Express, ethers.js, API, transaction signing
3. **Voter Database (Data Layer):** Supabase (Postgres), biometric mappings, voter status
4. **Blockchain Ledger (Verification Layer):** Ethereum Sepolia (testnet), VotingV2 smart contract

## Quick Start

### Prerequisites

- Node.js (v18+)
- npm
- Python 3 (for kiosk)
- Supabase project (service_role key for backend)
- Sepolia RPC provider (Alchemy/Infura) and a backend wallet with testnet ETH

### Install

```bash
git clone https://github.com/cainebenoy/blockchain-voting-dapp-v3.git
cd blockchain-voting-dapp-v3
npm install
cd backend
npm install
```

### Configuration

1. Copy `backend/.env.example` to `backend/.env` and set required variables:

   - `SUPABASE_URL` — your Supabase project URL
   - `SUPABASE_KEY` — Supabase `service_role` key (server-only secret)
   - `SEPOLIA_RPC_URL` — Alchemy/Infura RPC endpoint
   - `SERVER_PRIVATE_KEY` — backend signing wallet (authorize as contract `officialSigner`)
   - `VOTING_CONTRACT_ADDRESS` — deployed VotingV2 address (optional if deploying via backend API)
   - `AUTO_RESTART` — (optional) set to `true` to enable automatic systemd service restart after contract deployment

2. Deploy the smart contract:

**Option A: Via Backend API (Recommended for Production)**

Use the admin UI at `http://localhost:3000/admin.html` and click "Deploy New Election". The backend will:
- Deploy a new VotingV2 contract
- Update the backend `.env` file with the new contract address
- Authorize the backend wallet as the official signer
- Optionally restart the systemd service (if `AUTO_RESTART=true`)

**Option B: Manual Deployment via Scripts**

```bash
npx hardhat run scripts/deployV2.ts --network sepolia
```

Note: When using Option A, the backend handles all post-deployment steps automatically.

### Run the system (local testnet)

1. Start backend:

```bash
cd backend
node server.js
```

2.Start kiosk (on Raspberry Pi with hardware):

```bash
sudo -E python3 ../kiosk_main.py
```

3.Open admin UI: `http://localhost:3000/admin.html`
4.Open verify UI: `http://localhost:3000/verify.html`

## Core API Endpoints (summary)

### Public Endpoints

- `GET /api/health` — health check
- `GET /api/config` — contract and RPC information
- `GET /api/results` — on-chain results proxy
- `GET /api/metrics` — combined on-chain + DB metrics
- `GET /api/active-contract` — returns current contract address and network (useful after deployments)

### Voting Endpoints

- `POST /api/voter/check-in` — validate Aadhaar; returns fingerprint_id for kiosk verification
- `POST /api/vote` — cast vote (body: `{ aadhaar_id, candidate_id }`)
  - Response includes `data.transaction_hash` and, when available, `data.receipt_code`.

### Receipt Verification

- `POST /api/verify-code` — resolve short code to `tx_hash` (body: `{ code }`)
- `POST /api/lookup-receipt` — given `tx_hash` return `code` (used by kiosk polling)

### Admin & Enrollment Endpoints

  - `POST /api/admin/deploy-contract` — deploy new VotingV2 contract and update backend configuration
  - `POST /api/admin/add-voter` — queue remote enrollment for kiosk
  - `GET /api/admin/enrollment-status` — admin UI polls for status
  - `GET /api/kiosk/poll-commands` — kiosk polls for ENROLL commands
  - `POST /api/kiosk/enrollment-complete` — kiosk reports enrollment result and backend persists `voters` row

## Short-code Receipt System (how it works)

1. After the backend sends a vote transaction, it waits for confirmation with a 60s timeout.
2. The backend generates a short, human-friendly receipt code (e.g., `ABC-123`) and inserts `{ code, tx_hash }` into the `receipts` table in Supabase.
3. The backend returns the `receipt_code` in the `/api/vote` response when the DB insert succeeds; the kiosk displays it on the OLED.
4. Voters can verify a code at `verify.html`, which calls `/api/verify-code` to resolve the transaction and then checks the blockchain for confirmation.

## Notes on robustness

- If the DB insert for the receipt fails, the backend returns `receipt_code: null`. The kiosk falls back to showing a truncated transaction hash and instructions to verify manually.
- Kiosk will poll `/api/lookup-receipt` for a short period (e.g., 60s) after vote submission to discover a late-inserted code.
- Short codes and lookups are normalized to uppercase.

## Kiosk Features & Behavior

### Fingerprint Verification with Retry

The kiosk implements a user-friendly fingerprint verification process:

- **First Attempt**: When a voter provides their Aadhaar ID, the kiosk prompts for fingerprint scan
- **Retry Logic**: If the first scan fails or doesn't match, the voter gets ONE additional attempt
- **User Feedback**: Clear OLED messages ("Scan Failed - Please try again") and audio beep
- **Security**: After two failed attempts, the kiosk returns to the idle screen (no indefinite retries)
- **Reset Option**: Voters can press the START button at any time to return to the beginning

This retry mechanism reduces false rejections due to scanning issues while maintaining security.

### Receipt Display

After submitting a vote to the backend, the kiosk will:

1. Read `receipt_code` from the `/api/vote` response if present and display it on the OLED.
2. If `receipt_code` is not returned immediately, the kiosk will poll `/api/lookup-receipt` (with the `tx_hash`) for a short window (default ~60s) to discover a late-inserted code.
3. If no short code is found within the poll window, the kiosk shows a fallback receipt composed of the truncated transaction hash (e.g., first 10 characters) and instructions to verify on the admin/verify UI.

Ensure the kiosk can reach the backend (default `http://127.0.0.1:3000` on local deployments). If the kiosk is remote, set the backend URL in `kiosk_main.py` or via environment variable.

## Database & Supabase notes

- `voters` table: `{ aadhaar_id, name, fingerprint_id, constituency, has_voted }`.
- `receipts` table: `{ id, code, tx_hash, inserted_at }` — ensure `code` and `tx_hash` are unique.

Suggested minimal SQL for `receipts`:

```sql
create table if not exists receipts (
  id bigserial primary key,
  code varchar(32) not null unique,
  tx_hash varchar(66) not null unique,
  inserted_at timestamptz default now()
);
```

Ensure Supabase RLS policies permit the backend service role to `INSERT` and `SELECT` on these tables.

## E2E smoke test (manual)

A non-hardware smoke test can script the following API calls:

1. `POST /api/admin/add-voter` — queue enrollment
1. Poll `GET /api/kiosk/poll-commands` — kiosk receives ENROLL
1. `POST /api/kiosk/enrollment-complete` — simulate kiosk reporting success (inserts `voters` row)
1. `POST /api/vote` — cast vote (returns tx hash and maybe receipt code)
1. `POST /api/verify-code` — verify receipt code resolves to tx hash

> Tip: `POST /api/vote` submits a real transaction when using a real RPC/provider.

## Testing & CI

- Smart contract unit tests: `npx hardhat test` (in `test/`).
- For CI, stub Supabase or use a test Supabase project and a mock provider to avoid sending real transactions.

## Troubleshooting & common issues

- `Database save failed` on `/api/kiosk/enrollment-complete`: check Supabase policies, table schema, and that `SUPABASE_KEY` is a service role key.
- `Double voting detected!`: indicates the `voters` row already exists with `has_voted = true`; inspect DB and audit logs.
- `RPC_TIMEOUT` during `tx.wait()`: network or RPC slowness; check Etherscan for the transaction and logs.

## Deployment & production notes

- Use `systemd` to manage backend and kiosk processes on Raspberry Pi.
- Protect Supabase keys and backend private keys with a secrets manager.
- Enable HTTPS and firewall rules to restrict access to the backend.
- Regularly backup Supabase or configure scheduled exports.

Example `systemd` unit (backend):

```ini
[Unit]
Description=VoteChain Backend
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/blockchain-voting-dapp-v3/backend
Environment=NODE_ENV=production
ExecStart=/usr/bin/node server.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Contributing & development

- Keep backend as ESM and follow existing layout.
- Add tests for new behavior (short-code mapping and verify endpoints).
- Open PRs against `main` and add a short changelog entry for notable changes.

## Changelog (short)

- 2025-11-30 — Added short-code receipt system, `/api/verify-code`, `/api/lookup-receipt`, kiosk polling improvements, and verify UI updates.

## Contact

Open an issue on GitHub or contact the project owner for questions or deployment guidance.

If you'd like, I can also:

- Open a PR with this README update, or
- Add a small integration test for the `verify-code` endpoint, or
- Add a `docs/README-DEPLOY.md` with step-by-step Raspberry Pi setup.
