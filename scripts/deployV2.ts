import { network } from "hardhat";

async function main() {
  console.log("Deploying VotingV2 contract...");
  const { ethers } = await network.connect();
  const [deployer] = await ethers.getSigners();
  const balanceWei = await ethers.provider.getBalance(deployer.address);
  const balanceEth = ethers.formatEther(balanceWei);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Network: ${(await ethers.provider.getNetwork()).name}`);
  console.log(`Balance: ${balanceEth} ETH`);

  const minEth = 0.002;
  if (Number(balanceEth) < minEth) {
    throw new Error(`Insufficient funds (<${minEth} ETH). Fund ${deployer.address} and retry.`);
  }

  const VotingV2Factory = await ethers.getContractFactory("VotingV2", deployer);
  const votingV2 = await VotingV2Factory.deploy();
  await votingV2.waitForDeployment();
  const address = await votingV2.getAddress();
  console.log(`VotingV2 deployed at: ${address}`);

  const netName = (await ethers.provider.getNetwork()).name?.toLowerCase() || "";
  if (netName.includes("sepolia")) {
    console.log(`Explorer: https://sepolia.etherscan.io/address/${address}`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
