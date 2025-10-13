# Demo checklist

Use this as a quick run-of-show for presenting the dApp.

## 1) Prep
- Ensure MetaMask is installed and unlocked.
- Set MetaMask to Sepolia network.
- Fund the deployer account (from your .env private key) with Sepolia ETH.
- In the repo root:
  - `npm install`
  - Ensure `.env` is configured (or keystore values are set).

## 2) Deploy
- Run deployment:
  - `npx hardhat run scripts/deploy.ts --network sepolia`
- Copy the deployed address from the logs.
- Edit `index.html` and set `const contractAddress = "0x..."`.

## 3) Open the UI
- Open `index.html` in a browser (or via Live Server).
- Click "Connect Wallet" and allow MetaMask to connect.
- If prompted, approve network switch/add for Sepolia.

## 4) Admin flow
- Confirm the connected address matches "Admin: ..." in the UI.
- Add two candidates (e.g., Alice, Bob).
- Authorize 1-2 voter addresses (can be your other accounts in MetaMask).

## 5) Voting flow
- Switch MetaMask account to an authorized voter.
- Select a candidate and click Vote.
- Observe the "VoteCast" event and the candidate's vote count increasing in the list.

## 6) End election
- Switch back to the admin account.
- Click "End Election" and confirm.
- The UI now displays the winner details.

## 7) Show resilience
- Attempt to vote again (should fail: already voted).
- Attempt to vote from unauthorized address (should fail: not authorized).
- Attempt admin actions after end (should fail: election ended).

## 8) Wrap up
- Mention that the ABI is inlined, events are subscribed, and network switching is handled.
- Point to test suite (19 passing) and `scripts/check-balance.ts`.
