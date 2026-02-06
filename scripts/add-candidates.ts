import { network } from "hardhat";

/*
 Usage: prefer env/CLI args. Example:
   VOTING_CONTRACT_ADDRESS=0x... npx hardhat run scripts/add-candidates.ts --network sepolia
*/

async function main() {
  // --- CONFIGURATION (override via env if available) ---
  const VOTING_V2_ADDRESS = process.env.VOTING_CONTRACT_ADDRESS || "0x62f589eED2fEfEe77690FF83542EbAcc4d8670CA";

  if (!VOTING_V2_ADDRESS) {
      console.error("❌ ERROR: Please set VOTING_CONTRACT_ADDRESS in env or edit the script.");
      process.exit(1);
  }

  // --- CONNECT ---
  const { ethers } = await network.connect();
  const votingV2 = await ethers.getContractAt("VotingV2", VOTING_V2_ADDRESS);
  console.log(`Connected to election at ${VOTING_V2_ADDRESS}`);

  // --- ADD CANDIDATES ---
  console.log("Adding Candidate A...");
  let tx = await votingV2.addCandidate("Candidate A");
  console.log("Transaction sent, waiting...");
  await tx.wait();
  console.log("✅ Candidate A added (ID: 1)");

  console.log("Adding Candidate B...");
  tx = await votingV2.addCandidate("Candidate B");
  console.log("Transaction sent, waiting...");
  await tx.wait();
  console.log("✅ Candidate B added (ID: 2)");

  console.log("\n🎉 Election is ready for voting!");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});