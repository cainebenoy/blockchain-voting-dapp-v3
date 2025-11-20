import { network } from "hardhat";

async function main() {
  // --- CONFIGURATION ---
  // Paste your current VotingV2 contract address here
  const VOTING_V2_ADDRESS = "0x62f589eED2fEfEe77690FF83542EbAcc4d8670CA";

  if (VOTING_V2_ADDRESS.includes("PASTE")) {
      console.error("❌ ERROR: Please paste your contract address at the top of the script.");
      process.exit(1);
  }

  // --- CONNECT ---
  const { ethers } = await network.connect();
  const votingV2 = await ethers.getContractAt("VotingV2", VOTING_V2_ADDRESS);

  console.log(`\n📊 Fetching live election results from ${VOTING_V2_ADDRESS}...\n`);

  // --- GET ALL CANDIDATES ---
  const candidates = await votingV2.getAllCandidates();

  if (candidates.length === 0) {
      console.log("No candidates found in this election.");
      return;
  }

  // --- DISPLAY RESULTS ---
  console.log("--- ELECTION RESULTS ---");
  for (const candidate of candidates) {
      // The voteCount is a BigInt, so we convert it to a string or number to read it
      console.log(`[ID: ${candidate.id}] ${candidate.name}: ${candidate.voteCount.toString()} votes`);
  }
  console.log("------------------------\n");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});