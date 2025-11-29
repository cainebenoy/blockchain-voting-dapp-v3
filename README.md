
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

- 2025-11-29 — Kiosk display & robustness updates (commit `c464e3d`)
  - Boot-time hardware health checks for the kiosk (LEDs / Buttons / OLED).
  - Fixed OLED rendering issues and added font fallbacks; removed border outlines from screen clears.
  - Added `show_idle()` idle screen (title font adjusted to 17pt) and `wait_for_reset()` reset helper.
  - Improved fingerprint scan and check-in flows; persistent OLED error messages on hardware faults.
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
- **Add Candidates**: Enter names and add to ballot
- **Start Election**: Enable voting (locks candidate list)
- **Register Voters**: Initiate remote fingerprint enrollment
- **End Election**: Finalize results (irreversible)
- **Deploy New Election**: Fresh contract for new election cycle

### Voter Registration Flow

1. Admin enters voter details in dashboard
2. Kiosk automatically prompts for fingerprint scan
3. Voter scans fingerprint (assigned unique ID)
4. Database records: Aadhaar ↔ Fingerprint ID mapping

### Voting Flow

1. Voter presses START button on kiosk
2. Types 12-digit Aadhaar number (displayed on OLED)
3. Presses Enter
4. Backend verifies eligibility (not already voted)
5. Kiosk prompts for fingerprint scan
6. Fingerprint verified against enrolled ID
7. Candidate selection buttons appear
8. Press candidate button twice to confirm
9. Backend signs and submits vote to blockchain
10. Success/failure displayed on OLED

### Results Dashboard (`index.html`)

Access at `http://localhost:3000`

- **Live Stats**: Total votes, candidates, election status
- **Real-time Updates**: Auto-refreshes every 5 seconds
- **Visual Progress Bars**: Vote distribution
- **Winner Display**: Shows winner after election ends
- **Blockchain Verification**: Direct link to Etherscan

## 🔐 Security Features

1. **Biometric Authentication**: R307 fingerprint scanner with 1:N matching
2. **Blockchain Immutability**: Votes stored on Ethereum, cannot be altered
3. **Double-Vote Prevention**: Smart contract enforces one vote per Aadhaar ID
4. **Authorized Signer Model**: Only backend server can submit votes (prevents voter key management)
5. **Rate Limiting**: API endpoints protected against spam
6. **Database Sync**: Supabase tracks voting status for fast lookups
7. **Audit Logging**: SHA-256 hashed Aadhaar IDs in audit trail

## 🛠️ Smart Contract Functions

```solidity
// VotingV2.sol - Key Functions

setOfficialSigner(address _signer)  // Admin only: authorize backend
addCandidate(string _name)          // Admin only: add candidate
startElection()                     // Admin only: begin voting
endElection()                       // Admin only: finalize results
vote(uint _candidateId, string _voterId)  // Signer only: record vote
getAllCandidates()                  // Public: get results
```

## 📡 API Endpoints

### Public Endpoints

- `GET /api/health` - Health check
- `GET /api/results` - Live election results
- `GET /api/active-contract` - Current contract address

### Voting Endpoints

- `POST /api/voter/check-in` - Verify voter eligibility
- `POST /api/vote` - Submit vote (signs and sends to blockchain)

### Admin Endpoints

- `POST /api/admin/deploy-contract` - Deploy new election
- `POST /api/admin/initiate-enrollment` - Queue fingerprint enrollment
- `GET /api/admin/enrollment-status` - Check enrollment status

### Kiosk Endpoints

- `GET /api/kiosk/poll-commands` - Check for pending enrollments
- `POST /api/kiosk/enrollment-complete` - Report enrollment result

## 🔧 Configuration

### Hardware Pin Mapping (BCM Mode)

```python
# GPIO Buttons
PIN_START = 4           # Start voting
PIN_CANDIDATE_A = 22    # Select Candidate A
PIN_CANDIDATE_B = 23    # Select Candidate B

# LEDs & Buzzer
PIN_LED_GREEN = 17      # Success indicator
PIN_LED_RED = 27        # Error indicator
PIN_BUZZER = 18         # Feedback beeper

# OLED Display (SPI)
DC_PIN = 24             # Data/Command
RST_PIN = 25            # Reset

# Fingerprint Sensor (UART)
SERIAL_PORT = "/dev/ttyAMA0"
BAUD_RATE = 57600
```

### Backend Configuration

```javascript
// RPC Timeout Settings
VOTE_TIMEOUT = 60000ms  // 60 seconds for slow RPCs

// Rate Limits
CHECK_IN_LIMIT = 30 requests/minute
VOTE_LIMIT = 20 requests/minute

// Polling
KIOSK_POLL_INTERVAL = 500ms  // Enrollment command polling
```

## 🐛 Troubleshooting

### Backend shows "Not authorized kiosk signer"

**Solution**: Auto-authorization runs on startup, but if needed:

```bash
npx hardhat run scripts/authorize-signer.ts --network sepolia
```

### Kiosk shows "Connection Fail, Retry" but vote succeeds

**Cause**: RPC timeout during `tx.wait()`  
**Impact**: Vote IS recorded on blockchain, just confirmation timed out  
**Solution**: Already implemented 60s timeout with graceful handling

### Fingerprint sensor not responding

**Check**:

```bash
ls -la /dev/ttyAMA0  # Should exist
sudo usermod -aG dialout $USER  # Add user to serial group
```

### GPIO "not allocated" error

**Solution**: Use `initial=GPIO.LOW` in setup calls (already implemented)

### Admin dashboard continuous reload

**Cause**: Browser cache conflict with 304 responses  
**Solution**: Hard refresh (Ctrl+Shift+R) or use incognito mode

## 📊 Testing

### Unit Tests (Smart Contract)

```bash
npx hardhat test
```

### Manual Testing Checklist

- [ ] Deploy contract and verify on Etherscan
- [ ] Add 2+ candidates via admin dashboard
- [ ] Start election
- [ ] Register test voter with fingerprint
- [ ] Cast vote via kiosk
- [ ] Verify vote on results dashboard
- [ ] Check blockchain transaction on Etherscan
- [ ] End election
- [ ] Verify winner display

## 📁 Project Structure

```text
blockchain-voting-dapp-v3/
├── contracts/
│   └── VotingV2.sol           # Smart contract
├── scripts/
│   ├── deployV2.ts            # Contract deployment
│   ├── authorize-signer.ts    # Authorize backend
│   ├── add-candidates.ts      # Bulk add candidates
│   └── get-results.ts         # Fetch results
├── backend/
│   ├── server.js              # Express API server
│   ├── VotingV2.json          # Contract ABI
│   └── package.json
├── test/
│   └── VotingV2.test.js       # Contract tests
├── docs/                      # Technical documentation
├── kiosk_main.py              # Raspberry Pi kiosk app
├── admin.html                 # Admin control panel
├── index.html                 # Public results dashboard
├── hardhat.config.ts          # Hardhat configuration
└── package.json               # Root dependencies
```

## 🔄 Workflow: New Election Cycle

1. **Deploy New Contract** (via admin dashboard or CLI)

  ```bash
  # Option A: Admin Dashboard
  # Click "Deploy New Election" button

  # Option B: CLI
  npx hardhat run scripts/deployV2.ts --network sepolia
  ```

1. **Backend Auto-authorizes** (automatic on startup/deploy) — Server detects new contract and calls `setOfficialSigner(backendWallet)`.

1. **Add Candidates** (via admin dashboard) — Must be done before starting election.

1. **Register Voters** (via admin dashboard) — Triggers remote fingerprint enrollment on kiosk; voters scan fingerprint at physical location.

1. **Start Election** (admin dashboard) — Locks candidate list and enables voting.

1. **Voting Period** (kiosk) — Voters authenticate and cast votes.

1. **End Election** (admin dashboard) — Finalizes results; winner displayed on results page.

## 🌐 Deployment

### Production Considerations

1. **Use Mainnet**: Update RPC URLs and private keys for Ethereum mainnet
2. **Systemd Services**: Auto-start backend and kiosk on boot
3. **SSL/TLS**: Enable HTTPS for backend server
4. **Firewall**: Restrict backend access to kiosk IP only
5. **Hardware Security**: Solder fingerprint sensor connections
6. **Backup**: Regular database exports and private key backups

### Systemd Service Example

```ini
[Unit]
Description=VoteChain Backend Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/blockchain-voting-dapp-v3/backend
ExecStart=/usr/bin/node server.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 📝 License

MIT License - See LICENSE file for details

## 👥 Contributors

Built as a Final Year Project demonstrating blockchain integration with embedded systems.

## 🔗 Resources

- [Hardhat Documentation](https://hardhat.org/)
- [Ethers.js v6](https://docs.ethers.org/v6/)
- [Raspberry Pi GPIO](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Supabase Docs](https://supabase.com/docs)
- [Sepolia Testnet Faucet](https://sepoliafaucet.com/)

## 📞 Support

For issues or questions, check:

1. Troubleshooting section above
1. `docs/` folder for detailed guides
1. Blockchain explorer: [Sepolia Etherscan](https://sepolia.etherscan.io/)

---

**Status**: Production-ready for testnet deployment  
**Last Updated**: November 29, 2025  
**Version**: 3.0.1
