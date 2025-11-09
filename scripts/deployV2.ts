import { network } from "hardhat";

async function main() {
  console.log("Setting up connection for VotingV2 deployment...");
  // Explicitly connect to the network to get the ethers object
  const { ethers } = await network.connect();

  console.log("Deploying VotingV2...");
  const votingV2 = await ethers.deployContract("VotingV2");
  await votingV2.waitForDeployment();
  const address = await votingV2.getAddress();

  console.log("----------------------------------------------------");
  console.log(`✅ VotingV2 deployed to: ${address}`);
  console.log("👉 COPY THIS ADDRESS NOW for the next step.");
  console.log("----------------------------------------------------");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});