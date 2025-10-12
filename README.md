# Voting DApp (Hardhat 3 + Ethers v6)

Simple, secure on-chain voting system with admin-controlled setup, single-vote enforcement, and winner calculation after closing the election. Built with Hardhat 3, Ethers v6, and Mocha/Chai.

## Features

- Admin adds candidates and authorizes voters
- Each address votes once for a valid candidate
- Total candidates & total votes tracking
- Election end and winner calculation
- Events for off-chain monitoring

## Run tests

```powershell
npx hardhat test
# or
npm test
```

## Local deploy (simulated L1)

```powershell
npx hardhat run scripts/deploy.ts --network hardhatMainnet
# or
npm run deploy:local
```

## Deploy with Ignition

```powershell
# Local simulated chain
npx hardhat ignition deploy ignition/modules/Voting.ts

# Sepolia (set SEPOLIA_RPC_URL and SEPOLIA_PRIVATE_KEY)
npx hardhat ignition deploy --network sepolia ignition/modules/Voting.ts
# or
npm run deploy:sepolia
```

Set config variables via env or keystore:

```powershell
npx hardhat keystore set SEPOLIA_RPC_URL
npx hardhat keystore set SEPOLIA_PRIVATE_KEY
```

## Contract

See `contracts/Voting.sol` for the full interface: admin state, election lifecycle, getters, and events.
