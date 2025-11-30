
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

# Install backend dependencies
cd backend
npm install
```

### Configuration

- Copy `backend/.env.example` to `.env` and fill in your Supabase and blockchain credentials.
- Deploy the smart contract using Hardhat:

```bash
npm run deploy:sepolia
```

### Running the System

```bash
# Start backend server
cd backend
node server.js

# View dashboard
Open browser to http://localhost:3000
```

## API Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Public results dashboard |
| `/api/health` | GET | System health check |
| `/api/results` | GET | Live election data |
| `/api/config` | GET | Contract configuration |
| `/api/metrics` | GET | Blockchain metrics |
| `/api/voter/check-in` | POST | Voter eligibility check |
| `/api/vote` | POST | Submit vote (kiosk model) |

## Project Structure

```text
blockchain-voting-dapp-v3/
├── contracts/
│   └── VotingV2.sol
├── backend/
│   ├── server.js
│   ├── VotingV2.json
│   └── .env.example
├── test/
│   └── AdvancedVoting.test.js
├── scripts/
│   ├── deploy.ts
│   └── authorize-signer.ts
├── index.html
├── hardhat.config.ts
├── package.json
└── README.md
```

## Security

- Biometric authentication
- Blockchain immutability
- Server-signed transactions
- Double-vote prevention
- Voter identity separation
- Rate limiting
- CORS protection
- Audit logging (SHA-256)

## Support & Resources

- [Etherscan](https://sepolia.etherscan.io/address/0xe75558A0d3b90a409EED77dDcc5ae35537D5eb5c)
- [Hardhat Docs](https://hardhat.org/)
- [Ethers.js Docs](https://docs.ethers.org/v6/)
- [Supabase Docs](https://supabase.com/docs)

## License

MIT

## Contact

For questions or support, open an issue on GitHub or contact the project maintainer.

- LEDs and Buzzer for feedback

### Software

- **Smart Contract**: Solidity (VotingV2.sol)
- **Backend**: Node.js 20+ with Express.js, Ethers.js v6
- **Frontend**: Vanilla HTML/CSS/JavaScript with Tailwind CSS
- **Kiosk**: Python 3.13 with RPi.GPIO, luma.oled, adafruit-fingerprint

## 📰 Recent Changes

- 2025-11-30 — Short Code Receipt System & Verification
  - After voting, the kiosk displays a unique short code (e.g., ABC-123) as a vote receipt.
  - Voters can use this code on the verify page (`verify.html`) to confirm their vote on the blockchain.
  - Backend maps short codes to transaction hashes and provides a `/api/verify-code` endpoint for verification.
  - `verify.html` now accepts both short codes and transaction hashes for verification.
  - See `CHANGELOG.md` for full details.

- **Database**: Supabase (PostgreSQL)
- **Blockchain**: Ethereum Sepolia Testnet
- **Development**: Hardhat 3, TypeScript 5

## 🚀 Quick Start

### Prerequisites

```bash
# System dependencies (Raspberry Pi OS)
sudo apt update
sudo apt install -y python3 python3-pip nodejs npm

# Python packages
pip3 install RPi.GPIO luma.oled adafruit-circuitpython-fingerprint requests pyserial

# Enable SPI and Serial
sudo raspi-config
# Interface Options → SPI → Enable
# Interface Options → Serial Port → Hardware YES, Login Shell NO
```

### Installation

1. **Clone and Install Dependencies**

```bash
cd "~/Desktop/FInal Year Project/blockchain-voting-dapp-v3"

# Root project dependencies (Hardhat, TypeScript)
npm install

# Backend server dependencies
cd backend
npm install
cd ..
```

1. **Configure Environment Variables**

```bash
# Root .env (for contract deployment)
cat > .env << EOF
SEPOLIA_RPC_URL="https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY"
SEPOLIA_PRIVATE_KEY="YOUR_ADMIN_WALLET_PRIVATE_KEY"
SUPABASE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"
SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
SERVER_PRIVATE_KEY="YOUR_BACKEND_WALLET_PRIVATE_KEY"
VOTING_CONTRACT_ADDRESS="0xYourContractAddress"
EOF

# Backend .env (same config)
cp .env backend/.env
```

1. **Deploy Smart Contract** (First time only)

```bash
npx hardhat run scripts/deployV2.ts --network sepolia
# Copy the deployed contract address to .env files
```

1. **Start the System**

```bash
# Terminal 1: Start backend server
cd backend
node server.js

# Terminal 2: Start kiosk (requires sudo for GPIO)
cd ..
sudo -E python3 kiosk_main.py

# Terminal 3: Open results dashboard
# Navigate to http://localhost:3000 in browser
```

## Environment Variables Reference

Below is a concise reference for the environment variables used by the project. Keep secrets out of version control and prefer a secure secrets manager for production.

| Variable | Example / Format | Purpose | Secret? |
| --- | --- | --- | --- |
| `SEPOLIA_RPC_URL` | `https://eth-sepolia.g.alchemy.com/v2/<ALCHEMY_KEY>` | RPC endpoint for Sepolia network | No (endpoint) |
| `SEPOLIA_PRIVATE_KEY` | `0x...` or `...` | Admin wallet for contract deployment | Yes |
| `SERVER_PRIVATE_KEY` | `0x...` | Backend signing wallet (official signer) | Yes |
| `SUPABASE_URL` | `https://<project>.supabase.co` | Supabase project URL | No |
| `SUPABASE_KEY` | `service_role` key | Supabase service role key used by backend | Yes (do not commit) |
| `VOTING_CONTRACT_ADDRESS` | `0x...` | Deployed VotingV2 contract address | No |

Notes:

- Use `backend/.env.example` as the authoritative template and copy it to `backend/.env` during setup.
- Mark any secret values as environment-only and never commit them. For production, use a secrets manager (Vault, AWS Secrets Manager, Dotenvx, etc.).

## Signer Authorization (Walkthrough)

After deploying the contract, the backend wallet must be authorized as the `officialSigner` on the `VotingV2` contract so it can submit votes on behalf of kiosks.

1. Ensure `VOTING_CONTRACT_ADDRESS` and `SERVER_PRIVATE_KEY` are set in your `backend/.env`.
1. From the repo root run:

  ```bash
  npx hardhat run scripts/authorize-signer.ts --network sepolia
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
