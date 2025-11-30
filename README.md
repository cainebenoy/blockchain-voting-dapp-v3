
# VoteChain V3 – Blockchain Voting DApp

## Overview

VoteChain V3 is a secure, cyber-physical voting system that combines biometric authentication, blockchain transparency, and a user-friendly kiosk interface. Designed for real-world elections, it ensures privacy, auditability, and ease of use for both voters and administrators.

## Features

- Biometric voter authentication (fingerprint)
- Immutable blockchain vote ledger
- Real-time public dashboard
- Server-signed transactions (no wallet required)
- API endpoints for results, health, and configuration
- Modular architecture: Kiosk, Backend, Database, Blockchain
- Security: double-vote prevention, rate limiting, CORS, audit logging

## System Architecture

1. **Smart Kiosk (Edge Layer):** Raspberry Pi 5, fingerprint scanner, OLED display, physical buttons
2. **Backend Server (Trust Layer):** Node.js, Express, Ethers.js, API, transaction signing
3. **Voter Database (Data Layer):** Supabase (PostgreSQL), biometric data, voter status
4. **Blockchain Ledger (Verification Layer):** Ethereum Sepolia, VotingV2 smart contract

## Quick Start

### System Prerequisites

- Node.js (v18+)
- npm
- Raspberry Pi 5 (for kiosk)
- Supabase account
- Ethereum Sepolia testnet access

### Installation (Quick Start)

```bash
# Clone the repository
git clone https://github.com/cainebenoy/blockchain-voting-dapp-v3.git
cd blockchain-voting-dapp-v3

# VoteChain V3 — Blockchain Voting DApp

## Overview

VoteChain V3 is a secure, cyber-physical voting system that combines biometric authentication, blockchain transparency, and a user-friendly kiosk interface. It is designed for real-world elections with emphasis on privacy, auditability, and resilient operation in constrained environments.

## Features

- Biometric voter authentication (fingerprint)
- Immutable blockchain vote ledger
- Real-time public dashboard
- Server-signed transactions (no voter wallet required)
- API endpoints for results, health, and configuration
- Modular architecture: kiosk, backend, database, blockchain
- Security: double-vote prevention, rate limiting, CORS, audit logging

## System Architecture

1. **Smart Kiosk (Edge Layer):** Raspberry Pi, fingerprint scanner, OLED display, physical buttons
1. **Backend Server (Trust Layer):** Node.js, Express, ethers.js, API, transaction signing
1. **Voter Database (Data Layer):** Supabase (Postgres), biometric mappings, voter status
1. **Blockchain Ledger (Verification Layer):** Ethereum Sepolia (testnet), VotingV2 smart contract

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
   - `VOTING_CONTRACT_ADDRESS` — deployed VotingV2 address (optional if deploying via scripts)

2. (Optional) Deploy the smart contract using Hardhat:

```bash
npx hardhat run scripts/deployV2.ts --network sepolia
```

### Run the system (local testnet)

1. Start backend:

```bash
cd backend
node server.js
```

1. Start kiosk (on Raspberry Pi with hardware):

```bash
sudo -E python3 ../kiosk_main.py
```

1. Open admin UI: `http://localhost:3000/admin.html`
1. Open verify UI: `http://localhost:3000/verify.html`

## Core API Endpoints (summary)

- `GET /api/health` — health check
- `GET /api/config` — contract and RPC information
- `GET /api/results` — on-chain results proxy
- `GET /api/metrics` — combined on-chain + DB metrics

- `POST /api/voter/check-in` — validate Aadhaar; returns fingerprint_id for kiosk verification
- `POST /api/vote` — cast vote (body: `{ aadhaar_id, candidate_id }`)

  - Response includes `data.transaction_hash` and, when available, `data.receipt_code`.

- `POST /api/verify-code` — resolve short code to `tx_hash` (body: `{ code }`)
- `POST /api/lookup-receipt` — given `tx_hash` return `code` (used by kiosk polling)

- Admin / enrollment endpoints:

  - `POST /api/admin/add-voter` — queue remote enrollment for kiosk
  - `GET /api/admin/enrollment-status` — admin UI polls for status
  - `GET /api/kiosk/poll-commands` — kiosk polls for ENROLL commands
  - `POST /api/kiosk/enrollment-complete` — kiosk reports enrollment result and backend persists `voters` row

## Short-code Receipt System (how it works)

1. After the backend sends a vote transaction, it waits for confirmation with a 60s timeout.
1. The backend generates a short, human-friendly receipt code (e.g., `ABC-123`) and inserts `{ code, tx_hash }` into the `receipts` table in Supabase.
1. The backend returns the `receipt_code` in the `/api/vote` response when the DB insert succeeds; the kiosk displays it on the OLED.
1. Voters can verify a code at `verify.html`, which calls `/api/verify-code` to resolve the transaction and then checks the blockchain for confirmation.

### Notes on robustness

- If the DB insert for the receipt fails, the backend returns `receipt_code: null`. The kiosk falls back to showing a truncated transaction hash and instructions to verify manually.
- Kiosk will poll `/api/lookup-receipt` for a short period (e.g., 60s) after vote submission to discover a late-inserted code.
- Short codes and lookups are normalized to uppercase.

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

## License

MIT

## Contact

Open an issue on GitHub or contact the project owner for questions or deployment guidance.

If you'd like, I can also:

- Open a PR with this README update, or
- Add a small integration test for the `verify-code` endpoint, or
- Add a `docs/README-DEPLOY.md` with step-by-step Raspberry Pi setup.
  ```

1. Verify on-chain: visit Etherscan for the deployed contract and check `officialSigner` (public view) or call the contract getter:

  ```bash
  npx hardhat console --network sepolia
  > const v = await ethers.getContractAt('VotingV2', process.env.VOTING_CONTRACT_ADDRESS)
  > await v.officialSigner()
  ```

Troubleshooting: if authorization fails, check that the wallet used has sufficient ETH to pay for the transaction, and ensure `SEPOLIA_RPC_URL` is reachable. If auto-authorization in `backend/server.js` reports an error, inspect `backend/server.log` for details.

## 📖 Usage Guide

### Admin Dashboard (`admin.html`)

Access at `http://localhost:3000/admin.html`

- **Connect Wallet**: MetaMask required, auto-switches to Sepolia
# VoteChain V3 — Blockchain Voting DApp (Renovated)

This repository implements VoteChain V3: a cyber-physical blockchain voting system built for real-world field deployment. It combines biometric authentication (fingerprint kiosks), a trusted backend that signs and submits votes, and a public verification flow using short-code receipts mapped to on-chain transactions.

This README has been renovated to reflect recent feature additions (short-code receipt system, kiosk polling/lookup, improved backend endpoints, and E2E testing guidance).

Overview
--------

VoteChain V3 is designed to be audit-friendly, privacy-conscious, and resilient in low-connectivity environments. Key ideas:

- Voters authenticate at a local kiosk using fingerprint + Aadhaar number.
- The backend signs and submits votes to a VotingV2 smart contract (server-authorized signer model).
- After a successful vote, a short alphanumeric receipt (e.g., ABC-123) is generated and displayed on the kiosk.
- The receipt maps to the transaction hash in a `receipts` table (Supabase). Voters can verify their vote using the short code or transaction hash on `verify.html`.

Highlights / New Features
------------------------

- Short-code receipt system: kiosk displays a human-friendly code after voting; backend persists mapping to `tx_hash` in `receipts`.
- Receipt lookup endpoints: `/api/verify-code` (code -> tx_hash) and `/api/lookup-receipt` (tx_hash -> code).
- Kiosk polling & enrollment: kiosks poll `/api/kiosk/poll-commands` for enrollment commands and report results to `/api/kiosk/enrollment-complete`.
- Robust vote submission: backend waits for confirmation with a timeout and still records vote status on timeout; audit logs are kept and rate limiting is enforced.
- Verify UI (`verify.html`) accepts both codes and tx hashes and queries the backend for resolution.
- Improved logging and conservative route cleanup to prevent duplicate handlers.

Quick Start (summary)
---------------------

Prerequisites

- Node.js (v18+)
- npm
- Python 3 (for kiosk)
- Supabase project (service_role key for backend)
- Sepolia RPC provider (Alchemy/Infura) + backend wallet with some ETH for gas (testnet)

Install

```bash
# Clone
git clone https://github.com/cainebenoy/blockchain-voting-dapp-v3.git
cd blockchain-voting-dapp-v3

# Install root & backend dependencies
npm install
cd backend
npm install
```

Configuration
-------------

Copy `.env.example` (or `backend/.env.example`) and set these core variables:

- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_KEY` — Supabase service_role key (server-only secret)
- `SEPOLIA_RPC_URL` — Alchemy/Infura RPC endpoint
- `SERVER_PRIVATE_KEY` — backend signing wallet (authorize as contract `officialSigner`)
- `VOTING_CONTRACT_ADDRESS` — deployed VotingV2 address (optional if deploying via scripts)

Recommended: load secrets via environment variables or a secrets manager in production; do not commit keys.

Run the system (local testnet)
-----------------------------

1) Start backend

```bash
cd backend
node server.js
```

2) Start kiosk (on Raspberry Pi with hardware)

```bash
sudo -E python3 ../kiosk_main.py
```

3) Open admin UI: `http://localhost:3000/admin.html`
4) Open verify UI: `http://localhost:3000/verify.html`

Core API Endpoints (summary)
----------------------------

- `GET /api/health` — health check
- `GET /api/config` — contract and RPC config
- `GET /api/results` — on-chain results proxy
- `GET /api/metrics` — combined on-chain + DB metrics

- `POST /api/voter/check-in` — validate Aadhaar; returns fingerprint_id for kiosk verification
- `POST /api/vote` — cast vote (body: `{ aadhaar_id, candidate_id }`)
  - Response includes `{ data: { transaction_hash, receipt_code } }` when available

- `POST /api/verify-code` — resolve short code to `tx_hash` (body: `{ code }`)
- `POST /api/lookup-receipt` — given `tx_hash` return `code` (used by kiosk polling)

- Admin / enrollment endpoints:
  - `POST /api/admin/add-voter` — queue remote enrollment for kiosk
  - `GET /api/admin/enrollment-status` — admin UI polls for status
  - `GET /api/kiosk/poll-commands` — kiosk polls for ENROLL commands
  - `POST /api/kiosk/enrollment-complete` — kiosk reports enrollment result and backend persists `voters` row

Receipt & Verification Flow (how it works)
-----------------------------------------

1. After a vote is signed and the transaction is sent, backend attempts `tx.wait(1)` with a 60s timeout.
2. Backend generates a short code via `generateShortCode()` and inserts `{ code, tx_hash }` into Supabase `receipts`.
3. Backend returns the `receipt_code` in the `/api/vote` response when the DB insert succeeds.
4. Kiosk displays the code on the OLED and prints/shows the voter.
5. Later, a user visits `/verify.html` and enters the code; the page calls `POST /api/verify-code` to get the `tx_hash` and then queries the blockchain to show confirmation.

Notes on robustness
-------------------

- If DB insertion of the receipt fails, the backend logs an error and returns `receipt_code: null` — the kiosk will fallback to showing the truncated `tx_hash` and instruct the voter to verify via transaction hash.
- Kiosk code polls `/api/lookup-receipt` for up to 60s after vote submission in case the short code is written slightly later by asynchronous processes.
- All short codes are normalized to uppercase by the backend and the verify UI.

Database & Supabase Notes
-------------------------

- `voters` table — stores `{ aadhaar_id, name, fingerprint_id, constituency, has_voted }`.
- `receipts` table — stores `{ code, tx_hash, inserted_at }` (ensure `code` is unique).
- Ensure Supabase RLS and policies allow the backend service role to `INSERT` and `SELECT` on these tables. Using the `service_role` key from Supabase is recommended for server-only operations (store it securely).

Suggested minimal SQL for `receipts` table

```sql
create table if not exists receipts (
  id bigserial primary key,
  code varchar(32) not null unique,
  tx_hash varchar(66) not null unique,
  inserted_at timestamptz default now()
);
```

E2E Smoke Test (how to run locally)
-----------------------------------

This repository contains a manual E2E flow that exercises enrollment and voting. A minimal script for smoke testing the API (non-hardware) can be created with curl/python to:

1. `POST /api/admin/add-voter` — queue enrollment
2. Poll `GET /api/kiosk/poll-commands` — kiosk receives ENROLL
3. `POST /api/kiosk/enrollment-complete` — simulate kiosk reporting success (inserts `voters` row)
4. `POST /api/vote` — cast vote (returns tx hash and maybe receipt code)
5. `POST /api/verify-code` — verify receipt code resolves to tx hash

Tip: when running a vote in live networks, be aware `POST /api/vote` will submit an actual blockchain transaction.

Testing & CI
------------

- Smart contract unit tests: `npx hardhat test` (in `test/`).
- Consider adding an integration test that stubs Supabase (or uses a test project) and a mock provider to avoid sending real transactions during CI.

Troubleshooting & Common Issues
--------------------------------

- `Database save failed` on `/api/kiosk/enrollment-complete`: check Supabase policies, table schema, and that the `SUPABASE_KEY` is set to a service role key.
- `Double voting detected!`: indicates the `voters` row exists and `has_voted` is true — verify DB state and audit logs. Use `supabase` SQL editor or the API to inspect the row.
- `RPC_TIMEOUT` during `tx.wait()` — network/rpc slowness. Backend will still proceed and update DB; check Etherscan for tx presence.

Deployment & Production Considerations
------------------------------------

- Use systemd units to manage backend and kiosk processes on Raspberry Pi.
- Protect Supabase keys and backend private keys using a secrets manager.
- Enable HTTPS and firewall rules to restrict access to the backend.
- Regularly backup Supabase (or set up scheduled exports).

Systemd example (backend)

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

Contributing & Development
--------------------------

- Code style: keep Node.js backend as ESM; follow the existing project layout.
- Add tests for new behavior (short-code mapping, verify endpoints).
- Open PRs against `main` and include a small changelog entry for significant changes.

Changelog (short)
-----------------

- 2025-11-30 — Added short-code receipt system, `/api/verify-code`, `/api/lookup-receipt`, kiosk polling improvements, and verify UI updates.

License
-------

MIT

Contact
-------

Open an issue on GitHub or contact the project owner for questions or deployment guidance.

---

If you'd like, I can also:

- Open a PR with this README update, or
- Add a small integration test for the `verify-code` endpoint, or
- Add a `docs/README-DEPLOY.md` with step-by-step Raspberry Pi setup.
