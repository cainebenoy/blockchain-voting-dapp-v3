import { network } from "hardhat";

async function main() {
  // --- CONFIGURATION ---
  const VOTING_V2_ADDRESS = "0xA70C926205c8738E0B8F7e61780189CB114ce267";
  // Your backend server address (from the previous step 0.1 ETH funding)
  const SERVER_WALLET_ADDRESS = "0xf0CEfA35A826C17D92FbD7Bf872275d0304B6a1c";

  if (VOTING_V2_ADDRESS.includes("PASTE") || SERVER_WALLET_ADDRESS.includes("PASTE")) {
      console.error("❌ ERROR: Please paste your real addresses at the top of the script.");
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