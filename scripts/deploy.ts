import { network } from "hardhat";

async function main() {
  console.log("Deploying contract...");
  const { ethers } = await network.connect();
  const [deployer] = await ethers.getSigners();
  const balanceWei = await ethers.provider.getBalance(deployer.address);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Network: ${await ethers.provider.getNetwork().then(n => n.name)}\nBalance: ${ethers.formatEther(balanceWei)} ETH`);

  // Simple preflight: require at least ~0.002 ETH for gas on Sepolia (adjust as needed)
  const minEth = 0.002;
  if (Number(ethers.formatEther(balanceWei)) < minEth) {
    throw new Error(`Insufficient funds: need at least ~${minEth} ETH for gas to deploy. Fund ${deployer.address} on the target network and try again.`);
  }

  const voting = await ethers.deployContract("Voting");

  await voting.waitForDeployment();

  const contractAddress = await voting.getAddress();
  console.log(`Voting contract deployed to: ${contractAddress}`);
  // Convenience: print a likely explorer link for Sepolia
  if ((await ethers.provider.getNetwork()).name?.toLowerCase().includes("sepolia")) {
    console.log(`Explorer: https://sepolia.etherscan.io/address/${contractAddress}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});