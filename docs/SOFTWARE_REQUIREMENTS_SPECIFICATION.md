# Software Requirements Specification (SRS)
## VoteChain V3 — Blockchain Voting DApp

### 1. Introduction

#### 1.1 Purpose
VoteChain V3 is a secure, transparent, and auditable blockchain-based voting system designed for deployment on Raspberry Pi kiosks. It enables biometric voter authentication, real-time vote recording on Ethereum, and public results dashboards.

#### 1.2 Scope
The system covers voter enrollment, biometric authentication, vote casting, blockchain transaction signing, and results display. It supports hybrid hosting (Pi backend, GitHub Pages frontend) and dynamic service discovery.

#### 1.3 Definitions
- **Kiosk:** Raspberry Pi device with fingerprint scanner, OLED, and buttons.
- **Backend:** Node.js/Express server for API, transaction signing, and DB sync.
- **Frontend:** Static HTML/JS dashboard and admin UI.
- **Supabase:** PostgreSQL DB for voter data and service discovery.
- **Ethereum Sepolia:** Blockchain network for vote ledger.

---

### 2. Overall Description

#### 2.1 Product Perspective
VoteChain V3 is a cyber-physical system integrating hardware kiosks, a backend server, a blockchain smart contract, and a web dashboard.

#### 2.2 Product Functions
- Voter enrollment and biometric authentication
- Vote casting via kiosk or web dashboard
- Transaction signing and submission to Ethereum
- Real-time results dashboard
- Admin controls for contract deployment and election management

#### 2.3 User Classes
- **Voters:** Use kiosks for biometric authentication and voting
- **Admins:** Manage elections, deploy contracts, monitor results
- **Observers:** View public dashboard and verify receipts

#### 2.4 Operating Environment
- Raspberry Pi 5 (Linux, Python 3)
- Node.js 18+/20+ (backend)
- Supabase (PostgreSQL)
- Ethereum Sepolia testnet
- Cloudflare Tunnel for remote backend access

#### 2.5 Design and Implementation Constraints
- Backend must use ESM (import/export)
- All secrets in `.env`, never committed
- Service discovery required for frontend-backend communication
- API error format: `{ status, message, data }`
- Contract deployment only via backend

---

### 3. Specific Requirements

#### 3.1 Functional Requirements

- **Voter Enrollment**
  - API: `/api/voter/check-in` (POST)
  - Validates Aadhaar, returns fingerprint ID

- **Biometric Authentication**
  - Kiosk hardware integration (Python)
  - Fingerprint scan required for voting

- **Vote Casting**
  - API: `/api/vote` (POST)
  - Records vote, returns transaction hash and receipt code

- **Receipt Verification**
  - API: `/api/verify-code` (POST)
  - Verifies short code, returns transaction hash

- **Results Dashboard**
  - API: `/api/results` (GET)
  - Displays live election results

- **Admin Controls**
  - API: `/api/admin/deploy-contract` (POST)
  - Deploys new contract, resets election

- **Service Discovery**
  - Frontend queries Supabase for backend URL

#### 3.2 Non-Functional Requirements

- **Security**
  - Biometric authentication, server-signed transactions, RLS on DB
  - Rate limiting, CORS, audit logging

- **Performance**
  - API response time <100ms
  - Real-time dashboard auto-refresh

- **Reliability**
  - Systemd services for auto-restart
  - End-to-end test scripts

- **Usability**
  - Mobile-responsive dashboard
  - No wallet required for voters

- **Maintainability**
  - Modular codebase, ESM modules, conventional commits

---

### 4. External Interfaces

- **Hardware:** Raspberry Pi, fingerprint scanner, OLED, buttons
- **Blockchain:** Ethereum Sepolia, VotingV2 smart contract
- **Database:** Supabase PostgreSQL
- **Web:** Static HTML/JS frontend, admin dashboard

---

### 5. System Features

- Secure voter authentication and vote casting
- Immutable blockchain vote ledger
- Real-time public results dashboard
- Admin contract deployment and election management
- Hybrid hosting and dynamic service discovery

---

### 6. Appendices

- See `README.md`, `PROJECT_SUMMARY.md`, and `docs/` for architecture, deployment, and troubleshooting details.
