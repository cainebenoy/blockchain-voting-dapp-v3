import { network } from "hardhat";

/*
 Usage: set `VOTING_CONTRACT_ADDRESS` in env or pass when executing.
 Example:
   VOTING_CONTRACT_ADDRESS=0x... npx hardhat run scripts/get-results.ts --network sepolia
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