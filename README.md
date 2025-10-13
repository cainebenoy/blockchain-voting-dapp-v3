# Blockchain Voting dApp (Hardhat 3 + Ethers)

A full-stack Ethereum voting dApp with a secure smart contract, a simple browser UI, and a complete Hardhat 3 workflow (tests, deploy, and scripts). It demonstrates an admin-managed election, voter authorization, one-vote-per-address, and winner calculation.

## Table of contents

- Overview
- Architecture
- Smart contract (API and events)
- Frontend (index.html)
- Development workflow
- Environment and configuration
- Testing
- Deployment (local and Sepolia)
- Troubleshooting
- Security notes and roadmap

## Overview

The system enables an admin to register candidates and authorize specific voter addresses. Authorized users can cast exactly one vote for a valid candidate while the election is active. The admin can end the election, after which the contract exposes a winner (id, name, votes). The UI connects via MetaMask and supports auto-switching to the Sepolia test network.

## Architecture

- contracts/Voting.sol — Solidity contract (admin-controlled lifecycle, events, getters)
- test/AdvancedVoting.test.js — 19 tests covering deployment, permissions, voting logic, lifecycle, and winner
- scripts/deploy.ts — Hardhat 3 deployment script, with balance preflight and helpful logs
- scripts/check-balance.ts — Utility to print the balance of a target address on a given network
- ignition/modules/Voting.ts — Ignition module to deploy the Voting contract
- hardhat.config.ts — Hardhat 3 config (ESM, dotenv, keystore fallback, networks)
- index.html — Minimal frontend (no bundler) using ethers UMD to interact with the contract
- package.json — ESM, useful npm scripts for test/deploy/balance

## Smart contract (contracts/Voting.sol)

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

## Frontend (index.html)

Features
- MetaMask connect, with auto-switch/add to Sepolia (11155111)
- Shows admin address and toggles admin-only controls
- Admin: Add candidate, authorize voter, end election (with confirmation)
- Voter: Choose candidate and cast vote
- Results: List candidates; when ended, show winner details
- Live updates via event listeners (CandidateAdded, VoteCast, ElectionEnded)

Important constants
- Update `const contractAddress = "…"` to your latest deployed address on Sepolia
- ABI is embedded and aligned with the current contract

## Development workflow

Install dependencies
```powershell
npm install
```

Run tests (19 passing)
```powershell
npx hardhat test
# or
npm test
```

Check account balance on Sepolia (via env var)
```powershell
$env:ADDRESS="0xYourAddress"; npm run balance:sepolia
```

Local deploy (simulated L1)
```powershell
npm run deploy:local
```

## Environment and configuration

Create a `.env` file or use the Hardhat keystore. The config prefers `.env` and falls back to keystore.

`.env` example (see `.env.example`):
```
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
npx hardhat run scripts/deploy.ts --network sepolia
```
- The script prints deployer address, network, and balance.
- If balance is too low, it aborts with a helpful message.
- On success, it prints an Etherscan link and the deployed contract address.

Ignition deploy (alternative):
```powershell
npx hardhat ignition deploy --network sepolia ignition/modules/Voting.ts
# or
npm run deploy:sepolia
```

After deployment, set the new address in `index.html`:
```html
const contractAddress = "0xDeployedAddress";
```

Open the frontend
- You can open `index.html` directly in a browser, or serve it from a local server (e.g., VS Code Live Server)

## Troubleshooting

- Task not found: The project uses script-based helpers (e.g., `scripts/check-balance.ts`) instead of custom Hardhat tasks for reliability with Hardhat 3.
- Insufficient funds: Fund the deployer account printed by `scripts/deploy.ts` with Sepolia ETH.
- Wallet connect issues: The UI now shows the underlying error and can auto-switch/add Sepolia. Reload and try again if MetaMask was locked.
- ABI mismatch: The ABI embedded in `index.html` matches the current contract. If you upgrade the contract, update the ABI and address.

## Security notes

- One vote per address enforced on-chain
- Admin-only actions gated with revert messages
- Election phase gating to protect functions like `getWinner`
- Emits events for transparency and indexing

Potential enhancements
- Role-based admin (OpenZeppelin AccessControl)
- Pause/resume (circuit breaker)
- Time-bounded elections (start/end timestamps)
- Commit–reveal or ZK voting for privacy

## License

SPDX-License-Identifier: MIT (see headers in Solidity files).
