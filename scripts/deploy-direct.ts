import { network } from "hardhat";

const { ethers } = await network.connect();

async function main() {
  console.log("🚀 Deploying VotingV2 contract to Sepolia...");
  
  const [deployer] = await ethers.getSigners();
  console.log("📝 Deploying with account:", deployer.address);
  
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log("💰 Account balance:", ethers.formatEther(balance), "ETH");
  
  const VotingV2 = await ethers.getContractFactory("VotingV2");
  console.log("📋 Deploying contract...");
  
  const contract = await VotingV2.deploy();
  await contract.waitForDeployment();
  
  const address = await contract.getAddress();
  console.log("✅ VotingV2 deployed to:", address);
  console.log("");
  console.log("📝 Next steps:");
  console.log(`1. Update backend/.env with: VOTING_CONTRACT_ADDRESS="${address}"`);
  console.log(`2. Run: npm run authorize:signer:sepolia`);
  console.log(`3. Start the backend: npm run serve`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
