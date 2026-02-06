# VoteChain V3 - AI Agent Instructions

## Architecture Overview

Four-layer cyber-physical voting system combining biometrics with blockchain:

1. **Edge Layer**: Raspberry Pi kiosk (`kiosk/kiosk/kiosk_main.py`) with R307 fingerprint scanner, OLED display, GPIO buttons
2. **Trust Layer**: Node.js backend (`backend/server.js`) - signs transactions, validates voters, generates receipts
3. **Data Layer**: Supabase PostgreSQL - stores voter mappings, biometric templates, service discovery config
4. **Verification Layer**: Ethereum Sepolia smart contract (`contracts/VotingV2.sol`) - immutable vote ledger

**Critical Pattern**: Voters don't have wallets. Backend server signs all transactions using `SERVER_PRIVATE_KEY`. Only the backend's `officialSigner` address can submit votes to the contract.

## Service Discovery Architecture

Frontend (GitHub Pages) → Queries Supabase `system_config` table → Discovers backend URL → Calls backend API

- `start_tunnel.py` runs Cloudflare Tunnel and updates Supabase with public backend URL
- Frontend auto-discovers backend via `/api/health` and Supabase lookup
- No manual URL configuration required for hybrid hosting

## Critical Workflows

### Development Setup
```bash
npm install && cd backend && npm install
# Configure backend/.env with required keys (see backend/.env.example)
npm run serve  # Start backend on port 3000
```

### Testing
```bash
npm test  # Run hardhat tests (must pass 11/11)
# Tests use Hardhat 3 ESM pattern: const { ethers } = await network.connect()
```

### Smart Contract Deployment
**Option A (Production)**: Use admin UI at `/admin.html` → Deploy New Election button
- Calls `/api/admin/deploy-contract` which:
  - Deploys new VotingV2 contract
  - Updates `backend/.env` with new address
  - Resets voter `has_voted` status in Supabase
  - Auto-authorizes backend wallet as `officialSigner`
  - Optionally restarts systemd service if `AUTO_RESTART=true`

**Option B (Manual)**: `npm run deploy:sepolia` then `npm run authorize:signer:sepolia`

## Blockchain Integration Patterns

### Transaction Signing (backend/server.js)
```javascript
// Backend signs transactions for voters (no wallet required)
const tx = await contract.vote(candidateId, aadhaarId);
await tx.wait(1);  // Always wait 1 confirmation
```

### Contract Initialization
- Contract instance created at startup: `new ethers.Contract(address, ABI, wallet)`
- Auto-authorization check runs on startup via `ensureAuthorizedSignerFor()`
- Use `isContractDeployed()` helper before calling contract methods

### Ethers.js v6 Specifics
- Use `JsonRpcProvider` with `staticNetwork: true` for performance
- Access contract address: `contract.target` (v6) not `contract.address` (v5)
- BigInt conversions: `Number(vCount)` for safe serialization

## Kiosk Hardware Patterns

### State Machine (kiosk_main.py)
Idle → Admin Check-in → Biometric Auth → Vote Selection → Confirmation

### Display Management
- Always clear screen before drawing: `draw.rectangle(device.bounding_box, fill="black")`
- Use DejaVu fonts with fallback to default: `ImageFont.truetype(...) except: font=None`
- Hardware error displays persist until restart (no auto-recovery)

### GPIO Conventions
```python
PIN_BTN_START = 4   # Admin/Start button
PIN_BTN_A = 22      # Candidate A
PIN_BTN_B = 23      # Candidate B
PIN_LED_GREEN = 17  # Success indicator
PIN_LED_RED = 27    # Error indicator
```

## Backend API Patterns

### Rate Limiting
- Check-in: 30 req/min (configurable via `RL_CHECKIN_MAX`)
- Vote: 20 req/min (configurable via `RL_VOTE_MAX`)

### Request Logging
- Structured JSON logs with `reqId`, `method`, `path`, `status`, `durationMs`
- Request ID added to all requests via middleware, returned in `X-Request-Id` header

### Double-Vote Prevention
Two-layer check:
1. Supabase `voters.has_voted` column (database)
2. Smart contract `hasVoted` mapping (blockchain)

### Receipt Generation
- Short codes: 6 chars (e.g. "A7B-29X") using confusion-resistant charset
- Stored in `receipts` table with `tx_hash` for verification
- Verified via `/api/verify-code` endpoint

## Database Schema (Supabase)

### voters table
- `aadhaar_id` (TEXT, hashed): Voter identifier
- `fingerprint_id` (INT): Maps to kiosk fingerprint template slot
- `has_voted` (BOOLEAN): Prevents double-voting
- Reset to `false` on new election deployment

### system_config table
- `key='backend_url'`: Dynamic backend URL for service discovery
- Updated by `start_tunnel.py` when Cloudflare tunnel starts
- Public read access (RLS policy), service role write access

## Project-Specific Conventions

### Module System
- **Backend**: ESM modules (`"type": "module"` in package.json)
- Use `import` not `require()`
- Fix `__dirname` for ESM: `const __dirname = path.dirname(fileURLToPath(import.meta.url))`

### Environment Variables
Required in `backend/.env`:
- `SUPABASE_URL`, `SUPABASE_KEY` (service_role, not anon)
- `SEPOLIA_RPC_URL` (Alchemy/Infura endpoint)
- `SERVER_PRIVATE_KEY` (backend signing wallet, must be contract admin)
- `VOTING_CONTRACT_ADDRESS` (auto-updated by admin deploy)

### Frontend-Backend Communication
- All frontends query Supabase first for backend URL
- Fallback to `localhost:3000` in development
- CORS enabled for all origins (development mode)

## Testing Patterns

### Smart Contract Tests (test/VotingV2.test.js)
- Contract starts inactive - must call `startElection()` before voting
- Use `setOfficialSigner()` not deprecated `authorizeSigner()`
- Access `electionActive` property directly (not `isElectionActive()` function)
- BigInt properties: `candidate[2]` for voteCount (array index, not named)

### API Testing
Run backend, then test endpoints:
- `/api/health` - System status
- `/api/config` - Contract configuration
- `/api/voter/check-in` - Aadhaar validation (12 digits)
- `/api/vote` - Submit vote (requires valid aadhaar_id, candidate_id)

## File References

- **Architecture deep-dive**: `docs/ARCHITECTURE.md`
- **Deployment guide**: `docs/DEPLOYMENT.md` (Raspberry Pi setup)
- **Service discovery**: `docs/SERVICE_DISCOVERY.md` (Cloudflare tunnel setup)
- **Hardware wiring**: `docs/HARDWARE.md` (GPIO pinout, sensor connections)
- **Backend entry**: `backend/server.js` (793 lines, all API endpoints)
- **Kiosk entry**: `kiosk/kiosk_main.py` (1118 lines, state machine)
- **Contract**: `contracts/VotingV2.sol` (server-signed voting model)
