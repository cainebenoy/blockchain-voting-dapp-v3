# VoteChain V3: Secure Cyber-Physical Voting System

## Phase 1 Completion Summary

This project is a decentralized voting system combining blockchain transparency with off-chain voter privacy. The admin dashboard now supports:

- Automated contract deployment to Sepolia (VotingV2.sol)
- Election lifecycle management (Start/End Election, registry lock/unlock)
- Candidate management on-chain
- Voter registration in Supabase (with Row-Level Security and service_role key)
- Real-time results dashboard (public and admin views)
- MetaMask integration for admin actions
- Automatic .env updates and database resets

### Architecture Overview

- **Smart Contract**: VotingV2.sol (constructor starts inactive, startElection() added)
- **Backend**: Node.js/Express, Ethers.js, Supabase client, CORS enabled for dev
- **Database**: Supabase PostgreSQL, voters table with Aadhaar, name, constituency, fingerprint_id, has_voted
- **Frontend**: admin.html (admin dashboard), index.html (public results)

### Workflow

1. **Deploy New Election**: Admin dashboard button triggers backend deployment, resets voter database, updates .env
2. **Add Candidates**: Registry unlocked, candidates added on-chain
3. **Register Voters**: Voters added to Supabase via backend API
4. **Start Election**: Registry locks, voting opens
5. **Vote Submission**: Backend validates voter, submits vote to blockchain, updates has_voted
6. **End Election**: Registry unlocks, results finalized

### Security

- Supabase RLS enabled, backend uses service_role key
- Voter identities stored only in Supabase, not on-chain
- Admin-only contract functions
- Aadhaar validation and duplicate prevention

### Pending Features

- Fingerprint integration for voter registration and authentication
- Comprehensive frontend voting interface
- Production deployment and security hardening

---

## For full details, see `docs/PHASE1_COMPLETION_SUMMARY.md`.

## Project Overview

VoteChain is a decentralized electronic voting system designed to address the "trust gap" in traditional EVMs. It combines the physical security of a polling booth kiosk with the transparency and immutability of the Ethereum blockchain.

**Key Innovation:** The system separates voter identity (verified off-chain via biometrics) from the vote record (stored on-chain), ensuring privacy while maintaining a publicly auditable ledger.

## System Architecture (4-Tier Model)

The project is architected into four distinct layers to ensure security and scalability.

### Tier 1: Smart Kiosk (Edge Layer)

**Hardware:**

- Raspberry Pi 5 (8GB)
- Official Camera Module 3
- R307 Fingerprint Scanner
- 1.3" OLED Display
- Physical Buttons

**Software:** Python client (`kiosk_main.py`) handling hardware I/O.

**Function:**

- Captures voter Aadhaar ID via keyboard
- Scans fingerprint to verify identity against the retrieved profile
- Captures vote choice via physical buttons
- Sends encrypted vote data to the backend

**Status:** ✅ Fully Functional. Hardware integrated and Python client operational.

### Tier 2: Backend Server (Trust Layer)

**Technology:** Node.js with Express.js

**Security:** Manages a funded Ethereum wallet (Server Signer)

**Function:**

- API Endpoint `/api/voter/check-in`: Verifies Aadhaar against the database
- API Endpoint `/api/vote`: Signs the vote transaction and submits it to the blockchain
- API Endpoint `/api/results`: Provides live election data for public dashboard
- Database Sync: Updates the voter's status to `has_voted = true`

**Status:** ✅ Live. Server is running on port 3000 and successfully processing votes.

### Tier 3: Voter Database (Data Layer)

**Technology:** Supabase (PostgreSQL)

**Function:** Stores the official electoral roll (Aadhaar, Name, Fingerprint ID)

**Security:** Row Level Security (RLS) enabled. Does NOT store vote choices.

**Status:** ✅ Live. Schema finalized and populated with test data.

### Tier 4: Blockchain Ledger (Verification Layer)

**Network:** Ethereum Sepolia Testnet

**Smart Contract:** VotingV2.sol

**Address:** `0xe75558A0d3b90a409EED77dDcc5ae35537D5eb5c`

**Function:** Immutable public ledger. Only accepts votes from the authorized Backend Server.

**Status:** ✅ Deployed & Verified. Accessible on Etherscan.

## Operational Workflow

1. **Voter Check-In:** Official enters Aadhaar number. Backend verifies eligibility.
2. **Biometric Auth:** Voter scans fingerprint. Kiosk verifies match with database record.
3. **Vote Casting:** Voter presses physical candidate button.
4. **Blockchain Commit:** Backend signs transaction. Vote is mined on Sepolia.
5. **Confirmation:** Kiosk displays success message. Public dashboard updates instantly.

## Current Metrics (Live Demo)

- **Status:** Active & Voting
- **Total Votes:** 3 (Confirmed on Sepolia)
- **Candidates:** 2 (Candidate A, Candidate B)
- **Leading:** Candidate A (3 votes)
- **Contract Address:** [0xe75558A0d3b90a409EED77dDcc5ae35537D5eb5c](https://sepolia.etherscan.io/address/0xe75558A0d3b90a409EED77dDcc5ae35537D5eb5c)

## Project Structure

```text
my-voting-dapp/
├── contracts/
│   └── VotingV2.sol              # Kiosk-based voting contract (server signer model)
├── scripts/
│   ├── deployV2.ts               # Deploy VotingV2 to Sepolia
│   ├── authorize-signer.ts       # Authorize backend wallet as signer
│   ├── check-balance.ts          # Check account balance on network
│   ├── add-candidates.ts         # Add candidates to deployed contract
│   └── get-results.ts            # Fetch election results from contract
├── test/
│   └── AdvancedVoting.test.js    # 19 comprehensive tests
├── backend/
│   └── server.js                 # Express API server (kiosk endpoints)
├── frontend/
│   ├── verify.html               # Biometric verification UI
│   └── vote.html                 # Voting interface UI
├── docs/
│   ├── FRONTEND_DESIGN_SPEC.md   # UI/UX specification
│   └── supabase-schema.md        # Database schema and setup
├── hardhat.config.ts             # Hardhat 3 config (ESM, networks)
├── package.json                  # npm scripts and dependencies
└── index.html                    # Public results dashboard
```

## Smart contract (contracts/VotingV2.sol)

**Kiosk Model:** VotingV2 uses an authorized server signer to cast votes on behalf of authenticated voters.

State

- admin (address): deployer address with admin privileges
- electionEnded (bool): false when active; true after admin ends the election
- totalCandidates (uint), totalVotes (uint)
- candidates (mapping(uint => Candidate))
- voters (mapping(address => Voter))

Structs

- Candidate { id, name, voteCount }
- Voter { isAuthorized, hasVoted, votedCandidateId }

Admin-only functions

- addCandidate(string name) — only when election is active
- authorizeVoter(address voter) — only when election is active
- endElection() — finalizes, emits ElectionEnded, and prevents further votes

User function

- vote(uint candidateId) — requires authorized, not yet voted, valid candidate id, and active election

Views

- isElectionActive() -> bool
- getCandidate(uint id) -> (id, name, voteCount)
- getAllCandidates() -> Candidate[]
- getVoterInfo(address) -> (isAuthorized, hasVoted, votedCandidateId)
- getWinner() -> uint (id), only after election ends
- getWinnerDetails() -> (id, name, voteCount), only after election ends

Events

- CandidateAdded(uint candidateId, string name)
- VoterAuthorized(address voter)
- VoteCast(address voter, uint candidateId)
- ElectionEnded(uint winnerCandidateId, string winnerName, uint winningVoteCount)

## Running the system

### 1. Start the backend server

```powershell
cd backend
node server.js
```

The server will:

- Listen on port 3000
- Serve the public results dashboard at `http://localhost:3000`
- Expose API endpoints at `/api/*`

### View the public dashboard

Open your browser to `http://localhost:3000` to see the live election results dashboard. The dashboard:

- Shows real-time election status, vote counts, and candidate standings
- Auto-refreshes every 5 seconds
- Works in dark/light mode (dark mode by default)
- Fetches data from the backend API (no direct blockchain calls)
- Public access - no wallet or authentication required

### 3. Backend API endpoints

- `GET /` - Public results dashboard (web interface)
- `GET /api/health` - Health check
- `GET /api/results` - Live election results (status, votes, candidates)
- `GET /api/config` - Contract configuration
- `GET /api/metrics` - On-chain metrics
- `POST /api/voter/check-in` - Voter eligibility check (Aadhaar verification)
- `POST /api/vote` - Submit vote (kiosk model with VotingV2)

## Development workflow

Install dependencies

```powershell
npm install
```

Run tests (19 passing)

```powershell
npm test
```

Check account balance on Sepolia

```powershell
npm run balance:sepolia
```

Authorize backend signer

```powershell
npm run authorize:signer:sepolia
```

Start backend server

```powershell
npm run serve
```

## Environment and configuration

Create a `.env` file or use the Hardhat keystore. The config prefers `.env` and falls back to keystore.

`.env` example (see `.env.example`):

```bash
SEPOLIA_RPC_URL=https://eth-sepolia.example/v2/yourKey
SEPOLIA_PRIVATE_KEY=0xabc123...
```

Alternatively, set values in the keystore:

```powershell
npx hardhat keystore set SEPOLIA_RPC_URL
npx hardhat keystore set SEPOLIA_PRIVATE_KEY
```

## Deployment

Script deploy to Sepolia (requires funded account):

```powershell
npx hardhat run scripts/deployV2.ts --network sepolia
```

- The script deploys VotingV2 contract
- Copy the deployed address for backend configuration
- Use `authorize-signer.ts` to authorize your backend wallet

Alternatively, use the npm script:

```powershell
npm run deploy:sepolia
```

After deployment, update the backend environment variables:

```bash
# In backend/.env
VOTING_CONTRACT_ADDRESS=0xYourDeployedVotingV2Address
```

### Backend API server (API-only)

The backend provides kiosk-style endpoints for Aadhaar check-in and on-chain voting via a server wallet.

Environment variables (create `backend/.env`):

```bash
SUPABASE_URL=...           # Supabase project URL
SUPABASE_KEY=...           # Supabase service role key (secure!)
SEPOLIA_RPC_URL=...        # Sepolia RPC endpoint (e.g., https://rpc.sepolia.org)
SERVER_PRIVATE_KEY=...     # Backend signer private key (DO NOT COMMIT)
VOTING_CONTRACT_ADDRESS=...# Deployed VotingV2.sol address
```

Install backend deps and run:

```powershell
cd backend
npm install
node ../backend/server.js
```

API Endpoints:

- `POST /api/voter/check-in` — body `{ aadhaar_id: "123456789012" }`
- `POST /api/vote` — body `{ aadhaar_id: "123456789012", candidate_id: 1 }`
- `GET /api/health` — backend health status
- `GET /api/metrics` — on-chain totals + Supabase voted count

You can exercise these endpoints using curl/Postman until the new frontend is built.

### Supabase schema

See `docs/supabase-schema.md` for the `voters` table SQL and sample seed. Backend uses an SHA-256 hash in its vote audit log to avoid storing raw Aadhaar IDs.

### CORS & rate limits

Configure allowed origins and per-endpoint rate limits via environment variables in `backend/.env`:

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
RL_CHECKIN_MAX=30
RL_VOTE_MAX=20
```

### Authorize backend signer (VotingV2)

After deploying VotingV2, authorize your backend wallet to cast votes:

```powershell
npm run authorize:signer:sepolia
```

This script reads the contract address from `backend/.env` and authorizes the backend wallet.

## Troubleshooting

- **Insufficient funds:** Fund the deployer account with Sepolia ETH from a faucet.
- **Backend connection errors:** Ensure `.env` file in `backend/` has correct `SUPABASE_URL`, `SUPABASE_KEY`, `SEPOLIA_RPC_URL`, `SERVER_PRIVATE_KEY`, and `VOTING_CONTRACT_ADDRESS`.
- **Unauthorized signer:** Run `npm run authorize:signer:sepolia` to authorize your backend wallet address on the deployed contract.
- **Contract deployment fails:** Verify your private key is funded and `SEPOLIA_RPC_URL` is valid in `.env`.

## Security notes

- One vote per voter ID (Aadhaar) enforced on-chain
- Admin-only actions gated with require statements
- Election phase gating to protect sensitive functions
- Server signer authorization prevents unauthorized vote submission
- Emits events for transparency and blockchain indexing
- Voter identity separated from vote record (privacy preserved)
- Row Level Security (RLS) on Supabase database

Potential enhancements:

- Role-based admin (OpenZeppelin AccessControl)
- Pause/resume (circuit breaker)
- Time-bounded elections (start/end timestamps)
- Commit–reveal or ZK voting for enhanced privacy
- Hardware security module (HSM) for key management

## Future Roadmap

### Planned Enhancements

1. **Admin Dashboard**
   - Web interface for election officials
   - Add/remove candidates dynamically
   - Monitor kiosk status and connectivity
   - Real-time voter turnout analytics

2. **Face Recognition**
   - Re-integrate face verification for multi-factor biometric auth
   - Currently disabled for stability

3. **Physical Kiosk Enclosure**
   - Design and 3D print professional casing
   - Integrated display and button panel
   - Tamper-evident seals and security features

4. **Security Hardening**
   - Hardware security module (HSM) for private key storage
   - End-to-end encryption for kiosk-to-backend communication
   - Multi-signature admin controls for critical operations

5. **Scalability**
   - Support for multiple concurrent kiosks
   - Load balancing and automatic failover
   - Mainnet deployment preparation
   - Optimistic rollups for reduced gas costs

## Conclusion

VoteChain V3 successfully demonstrates a practical, scalable solution for secure elections. By abstracting blockchain complexity away from the voter, it provides a familiar user experience while delivering the unparalleled transparency of a public ledger.

The system maintains voter privacy through biometric verification while ensuring vote integrity through blockchain immutability. This cyber-physical approach bridges the gap between traditional polling booth security and modern cryptographic verification, addressing the "trust gap" in electronic voting systems.

## License

SPDX-License-Identifier: MIT (see headers in Solidity files).
