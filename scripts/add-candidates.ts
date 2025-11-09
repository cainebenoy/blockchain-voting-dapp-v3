import { network } from "hardhat";

async function main() {
  // --- CONFIGURATION ---
  // Paste your VotingV2 address here if it's missing
  const VOTING_V2_ADDRESS = "0x62f589eED2fEfEe77690FF83542EbAcc4d8670CA"; 

  if (!VOTING_V2_ADDRESS || VOTING_V2_ADDRESS.includes("PASTE")) {
      console.error("❌ ERROR: Please check the VotingV2 address at the top of the script.");
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