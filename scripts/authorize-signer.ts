import { network } from "hardhat";

/*
 Usage: prefer setting values in `backend/.env` or pass via CLI/env rather than editing this file.
 Example:
   VOTING_V2_ADDRESS=0x... SERVER_WALLET_ADDRESS=0x... npx hardhat run scripts/authorize-signer.ts --network sepolia

 The script still supports the in-file constants for quick local runs, but DO NOT commit secrets.
*/

async function main() {
  // --- CONFIGURATION (override via env if available) ---
  const VOTING_V2_ADDRESS = process.env.VOTING_CONTRACT_ADDRESS || "0xA70C926205c8738E0B8F7e61780189CB114ce267";
  const SERVER_WALLET_ADDRESS = process.env.SERVER_WALLET_ADDRESS || "0xf0CEfA35A826C17D92FbD7Bf872275d0304B6a1c";

  if (!VOTING_V2_ADDRESS || !SERVER_WALLET_ADDRESS) {
      console.error("❌ ERROR: Please set VOTING_CONTRACT_ADDRESS and SERVER_WALLET_ADDRESS (env or edit file).");
      process.exit(1);
  }

  const { ethers } = await network.connect();
  const votingV2 = await ethers.getContractAt("VotingV2", VOTING_V2_ADDRESS);

  console.log(`Authorizing server at ${SERVER_WALLET_ADDRESS} on contract ${VOTING_V2_ADDRESS}...`);
  
  // CORRECT FUNCTION NAME: setOfficialSigner
  const tx = await votingV2.setOfficialSigner(SERVER_WALLET_ADDRESS);
  
  console.log("Transaction sent. Waiting for confirmation...");
  await tx.wait();
  console.log("✅ SUCCESS! Backend server is authorized.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});