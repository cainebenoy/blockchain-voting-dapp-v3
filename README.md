# VoteChain V3 — Blockchain Voting DApp

> A secure, cyber-physical voting system combining biometric authentication, blockchain transparency, and cryptographic auditability — built for real-world elections.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Smart Contracts](#smart-contracts)
- [Auditor Toolkit (Merkle Tree Verification)](#auditor-toolkit-merkle-tree-verification)
- [Kiosk Features](#kiosk-features)
- [Receipt Verification System](#receipt-verification-system)
- [Database Schema](#database-schema)
- [Deployment & Production](#deployment--production)
- [Testing & CI](#testing--ci)
- [Documentation](#documentation)
- [Changelog](#changelog)

---

## Overview

VoteChain V3 is a full-stack decentralized voting application designed for real-world pilot elections. It features:

- A **Raspberry Pi kiosk** with fingerprint scanner and OLED display for voter authentication
- A **Node.js backend** that signs and submits votes to an Ethereum smart contract
- An **Auditor Toolkit** that anchors the voter registry to the blockchain using Merkle Trees, enabling Zero-Trust verification
- A suite of **premium web pages** (Admin Portal, Results Dashboard, Auditor Page, Vote Simulator, Receipt Verifier)

The system enforces **one-person-one-vote** through biometric deduplication, and all votes are recorded immutably on the Ethereum Sepolia testnet.

---

## Key Features

### Core Voting
- Biometric voter authentication (fingerprint) with 2-second hold and retry logic
- Immutable blockchain vote ledger (Ethereum Sepolia)
- Server-signed transactions — no voter wallet required
- One-person-one-vote enforcement via kiosk nonce
- Short-code receipt system for easy vote verification

### Security & Privacy
- **Salted Aadhaar hashing** — raw IDs are never stored in the database or on-chain
- **Merkle Tree integrity** — the entire voter registry is anchored to the blockchain as a single hash
- Double-vote prevention, rate limiting, CORS protection, audit logging
- Admin routes protected by `x-admin-secret` header

### Administration
- Deploy new election contracts via the Admin Portal
- Add/remove candidates on-chain
- Start and end elections with one click
- **Remote fingerprint reset** — admin can signal kiosk to wipe its fingerprint library
- **Election tie detection** — results page correctly identifies and displays tied candidates

### Infrastructure
- Automatic service discovery via Supabase (frontend and kiosk auto-discover backend URL)
- Ngrok tunnel for HTTPS exposure of the Raspberry Pi backend
- Systemd auto-start on boot (`votechain-startup.service`)
- Dual `.env` synchronization on contract deployment

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (GitHub Pages)                      │
│  index.html │ admin.html │ results.html │ auditor.html │ verify.html│
│  about.html │ simulator.html                                        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTPS (Ngrok Tunnel)
┌───────────────────────────▼─────────────────────────────────────────┐
│                     BACKEND (Node.js / Express)                      │
│                                                                      │
│  Routes: /api/admin  /api/vote  /api/audit  /api/kiosk  /api/public │
│  Services: ethereumService.js  db.js (Supabase)                      │
│  Utils: merkle.js (Merkle Tree generation)                           │
└────────┬────────────────────────────┬───────────────────────────────┘
         │                            │
┌────────▼────────┐          ┌────────▼────────┐
│   SUPABASE      │          │   ETHEREUM      │
│   (Postgres)    │          │   (Sepolia)     │
│                 │          │                 │
│  voters         │          │  VotingV3.sol   │
│  receipts       │          │  - candidates   │
│  system_config  │          │  - votes        │
│  audit_log      │          │  - voterListRoot│
└─────────────────┘          └─────────────────┘
         ▲
┌────────┴────────┐
│   KIOSK         │
│   (Raspberry Pi)│
│                 │
│  Fingerprint    │
│  OLED Display   │
│  USB Keyboard   │
└─────────────────┘
```

### Layer Breakdown

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Edge** | Raspberry Pi Kiosk | Biometric authentication, voter UI |
| **Trust** | Node.js Backend | API gateway, transaction signing, Merkle generation |
| **Data** | Supabase (Postgres) | Voter records, receipts, service discovery |
| **Verification** | Ethereum Sepolia | Immutable vote ledger, Merkle Root anchor |
| **Connectivity** | Ngrok Tunnel | HTTPS exposure for Pi backend |

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **Frontend** | HTML5, Tailwind CSS, ethers.js (v5 UMD), Material Symbols |
| **Backend** | Node.js, Express, ethers.js (v6), dotenv |
| **Smart Contracts** | Solidity ^0.8.28, Hardhat 3, OpenZeppelin |
| **Database** | Supabase (PostgreSQL) |
| **Blockchain** | Ethereum Sepolia Testnet |
| **Cryptography** | merkletreejs, keccak256, SHA-256 (salted) |
| **Kiosk** | Python 3, Adafruit Fingerprint, SSD1306 OLED, evdev |
| **DevOps** | systemd, Ngrok, GitHub Actions (ESLint) |

---

## Quick Start

### Prerequisites

- Node.js v18+
- Python 3.9+ (for kiosk)
- Supabase project with `service_role` key
- Sepolia RPC URL (Alchemy) and wallet with testnet ETH

### Installation

```bash
git clone https://github.com/cainebenoy/blockchain-voting-dapp-v3.git
cd blockchain-voting-dapp-v3
npm install
```

### Configuration

Copy `.env.example` to `.env` in the project root and configure:

```env
# Supabase
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-service-role-key"

# Blockchain
SEPOLIA_RPC_URL="https://eth-sepolia.g.alchemy.com/v2/your-key"
SERVER_PRIVATE_KEY="0x..."
VOTING_CONTRACT_ADDRESS="0x..."

# Security
ADMIN_SECRET="your-admin-secret"
AADHAAR_SALT="your-salt-for-hashing"

# Networking
PORT=3000
```

> **Note**: Also ensure `backend/.env` is a copy of the root `.env`. The startup script sources environment variables from `backend/.env`.

### Running Locally

```bash
# Start backend
npm run serve

# Or via systemd (Raspberry Pi)
sudo systemctl start votechain-startup.service
```

Then open:
- **Admin Portal**: `http://localhost:3000/admin.html`
- **Results Dashboard**: `http://localhost:3000/results.html`
- **Auditor Toolkit**: `http://localhost:3000/auditor.html`
- **Vote Verifier**: `http://localhost:3000/verify.html`

---

## API Reference

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/config` | Contract and RPC info |
| `GET` | `/api/results` | On-chain election results |
| `GET` | `/api/metrics` | Combined on-chain + DB metrics |
| `GET` | `/api/active-contract` | Current contract address |
| `GET` | `/api/recent-transactions` | Last 5 vote transactions |

### Voting

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/voter/check-in` | `{ aadhaar_id }` | Validate voter, return fingerprint ID |
| `POST` | `/api/vote` | `{ aadhaar_id, candidate_id }` | Cast vote on-chain |

### Receipt Verification

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/verify-code` | `{ code }` | Resolve short code to tx hash |
| `POST` | `/api/lookup-receipt` | `{ tx_hash }` | Resolve tx hash to short code |

### Auditor

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `GET` | `/api/audit/root` | — | Fetch on-chain Merkle Root (backend proxy) |
| `POST` | `/api/audit/proof` | `{ aadhaar_id }` | Generate Merkle Proof for voter |

### Admin (Protected by `x-admin-secret` header)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/admin/deploy-contract` | Deploy new VotingV3 contract |
| `POST` | `/api/admin/add-candidate` | Add candidate to election |
| `POST` | `/api/admin/start-election` | Start election + anchor Merkle Root |
| `POST` | `/api/admin/end-election` | End election |
| `POST` | `/api/admin/add-voter` | Queue voter enrollment |
| `POST` | `/api/admin/reset-fingerprints` | Signal kiosk to wipe fingerprint DB |
| `GET` | `/api/admin/enrollment-status` | Poll enrollment progress |

### Kiosk

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/kiosk/poll-commands` | Check for ENROLL/WIPE commands |
| `POST` | `/api/kiosk/enrollment-complete` | Report enrollment result |
| `POST` | `/api/kiosk/heartbeat` | Kiosk heartbeat signal |

---

## Smart Contracts

### VotingV3.sol

The latest smart contract (`contracts/VotingV3.sol`) inherits from VotingV2 and adds Merkle Root anchoring:

```solidity
contract VotingV3 is VotingV2 {
    bytes32 public voterListRoot;

    event VoterListRootSet(bytes32 root);

    function setVoterListRoot(bytes32 _root) external {
        require(msg.sender == admin, "Only admin can set root");
        require(voterListRoot == bytes32(0), "Root already set");
        voterListRoot = _root;
        emit VoterListRootSet(_root);
    }
}
```

**Current Deployment**: `0xCfF751AB2d5594822Cf85e7bF68209748Ab6B9cF` (Sepolia)

### Deployment

#### Via Admin Portal (Recommended)
Click **"Deploy New Election"** in the Admin Portal. The backend automatically:
1. Deploys a new VotingV3 contract
2. Updates both `.env` files
3. Authorizes the backend wallet as the official signer
4. Optionally restarts the systemd service

#### Via Hardhat
```bash
npx hardhat run scripts/deployV3.ts --network sepolia
```

---

## Auditor Toolkit (Merkle Tree Verification)

The Auditor Toolkit enables **Zero-Trust** verification of the voter registry. It allows anyone to cryptographically prove that a voter's identity is part of the official registry without revealing private data.

### How It Works

```
Raw Aadhaar ID
       │
       ▼ (+ Secret Salt)
   SHA-256 Hash ──────────► Stored in Supabase (private)
       │
       ▼
   Keccak-256 Hash ───────► Merkle Tree Leaf (never stored)
       │
       ▼
   Merkle Tree ──────────► Merkle Root ──► On-Chain (VotingV3)
```

### Privacy Guarantees

1. **Salted Hashing**: Aadhaar IDs are combined with a secret salt and hashed (SHA-256) before database storage
2. **Merkle Hashing**: Database hashes are hashed again (Keccak-256) to form tree leaves
3. **On-Chain Anchor**: Only the final 32-byte Merkle Root is stored on Ethereum — it is mathematically impossible to reverse this to reveal any voter's identity

### Verification Flow

1. User enters their Aadhaar ID on the Auditor Page
2. Backend reconstructs the Merkle Tree and returns the **Proof** (sibling hashes) and the **Leaf**
3. Browser fetches the **Merkle Root** from the smart contract (via backend proxy to avoid CORS)
4. Browser locally re-computes the root from the leaf and proof
5. If the computed root matches the on-chain root → **Mathematical Proof Valid** ✅

---

## Kiosk Features

### Hardware Components
- Raspberry Pi 5
- Adafruit Fingerprint Sensor (UART)
- SSD1306 OLED Display (SPI)
- USB Numeric Keyboard (evdev)

### Authentication Flow
1. Voter enters 12-digit Aadhaar ID via keyboard
2. Kiosk validates format and checks against backend
3. Voter places finger on scanner (2-second hold required)
4. On match → vote is submitted to backend → receipt displayed on OLED
5. On failure → one retry allowed, then session resets

### Admin Commands
The kiosk polls `/api/kiosk/poll-commands` for:
- **ENROLL**: Captures new fingerprint and registers voter
- **WIPE**: Clears the entire fingerprint library (triggered by admin)

---

## Receipt Verification System

1. After a vote transaction is confirmed, the backend generates a short code (e.g., `ABC-123`)
2. The `{ code, tx_hash }` pair is stored in Supabase
3. The kiosk displays the code on the OLED screen
4. Voters can verify their vote at `verify.html` by entering the short code
5. The system resolves the code to a transaction hash and verifies it on Ethereum

---

## Database Schema

### Supabase Tables

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `voters` | `aadhaar_id`, `name`, `fingerprint_id`, `has_voted` | Voter registry |
| `receipts` | `code`, `tx_hash`, `inserted_at` | Vote receipt mapping |
| `system_config` | `key`, `value` | Service discovery, kiosk commands |
| `audit_log` | `action`, `details`, `timestamp` | Security audit trail |

### Receipts Table SQL

```sql
CREATE TABLE IF NOT EXISTS receipts (
  id BIGSERIAL PRIMARY KEY,
  code VARCHAR(32) NOT NULL UNIQUE,
  tx_hash VARCHAR(66) NOT NULL UNIQUE,
  inserted_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Deployment & Production

### Systemd Service

The system auto-starts on boot via `votechain-startup.service`:

```ini
[Unit]
Description=VoteChain V3 - Automated Startup Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/cainepi/Desktop/VoteChain - V3/blockchain-voting-dapp-v3
ExecStart=/bin/bash "start-votechain.sh"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Startup Script (`start-votechain.sh`)

The script orchestrates:
1. **Backend Server** — `node server.js`
2. **Ngrok Tunnel** — exposes port 3000 with a static domain
3. **Service Discovery** — updates Supabase with the public URL
4. **Kiosk Terminal** — launches `kiosk_main.py` in the foreground

### Production Checklist

- [ ] Use strong, unique values for `ADMIN_SECRET` and `AADHAAR_SALT`
- [ ] Enable Supabase RLS policies for all tables
- [ ] Ensure backend wallet has sufficient Sepolia ETH
- [ ] Verify `backend/.env` is in sync with root `.env`
- [ ] Test the full enrollment → vote → verify flow after each deploy

---

## Testing & CI

- **Smart Contract Tests**: `npx hardhat test`
- **E2E Tests**: `npx playwright test` (see `e2e/`)
- **Linting**: `npm run lint` (ESLint, enforced via GitHub Actions)

---

## Documentation

| Document | Description |
|----------|-------------|
| [SERVICE_DISCOVERY.md](docs/SERVICE_DISCOVERY.md) | Service discovery architecture and setup |
| [HOSTING.md](docs/HOSTING.md) | Hybrid hosting (GitHub Pages + Pi backend) |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Raspberry Pi deployment guide |
| [HARDWARE.md](docs/HARDWARE.md) | Hardware wiring and components |
| [SECURITY.md](docs/SECURITY.md) | Security policies and API key management |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [PRIVACY.md](docs/PRIVACY.md) | Privacy design and Aadhaar handling |
| [RECEIPTS.md](docs/RECEIPTS.md) | Receipt code system |
| [NGROK_SETUP.md](NGROK_SETUP.md) | Ngrok tunnel configuration |

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-19 | **V3.2** | Deployed VotingV3 with Merkle Root anchoring. Added Auditor Toolkit (`/api/audit/root`, `/api/audit/proof`). Fixed CORS proxy for ngrok, leaf hashing bug, and dual `.env` sync. Added election tie detection and admin fingerprint reset. |
| 2026-02-13 | V3.1 | Final security hardening: on-chain idempotency (kiosk nonces), session-token check-in, hardened RLS policies, Raspberry Pi audit. |
| 2025-12-04 | V3.0 | Service discovery system, Cloudflare Tunnel, Supabase config, hybrid hosting. |
| 2025-11-30 | V2.5 | Short-code receipt system, verify-code endpoint, kiosk polling, verify UI. |

---

## Contributing

- Keep backend as ESM (`"type": "module"` in package.json)
- Follow existing route/service architecture
- Add tests for new behavior
- Run `npm run lint` before committing
- Open PRs against `main` with a changelog entry

---

## License

ISC

## Contact

Open an issue on [GitHub](https://github.com/cainebenoy/blockchain-voting-dapp-v3) or contact the project owner for questions or deployment guidance.
