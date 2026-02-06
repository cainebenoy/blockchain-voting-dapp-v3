import { network } from "hardhat";

const { ethers } = await network.connect();

async function main() {
  const contractAddress = process.env.VOTING_CONTRACT_ADDRESS;
  console.log("📋 Setting up election with candidates...");
  console.log("Contract:", contractAddress);
  
  const [deployer] = await ethers.getSigners();
  console.log("Admin address:", deployer.address);
  
  const VotingV2 = await ethers.getContractFactory("VotingV2");
  const contract = VotingV2.attach(contractAddress);
  
  // Add candidates
  console.log("\n1️⃣ Adding Candidate: Alice Johnson");
  let tx = await contract.addCandidate("Alice Johnson");
  await tx.wait();
  console.log("✅ Alice added");
  
  console.log("\n2️⃣ Adding Candidate: Bob Smith");
  tx = await contract.addCandidate("Bob Smith");
  await tx.wait();
  console.log("✅ Bob added");
  
  console.log("\n3️⃣ Adding Candidate: Carol Williams");
  tx = await contract.addCandidate("Carol Williams");
  await tx.wait();
  console.log("✅ Carol added");
  
  // Set official signer
  console.log("\n4️⃣ Setting official signer...");
  const signerAddress = deployer.address;
  tx = await contract.setOfficialSigner(signerAddress);
  await tx.wait();
  console.log("✅ Official signer set:", signerAddress);
  
  // Start election
  console.log("\n5️⃣ Starting election...");
  tx = await contract.startElection();
  await tx.wait();
  console.log("✅ Election started!");
  
  // Verify setup
  const totalCandidates = await contract.totalCandidates();
  const isActive = await contract.electionActive();
  const candidates = await contract.getAllCandidates();
  
  console.log("\n📊 Election Setup Complete:");
  console.log("  Status: Active =", isActive);
  console.log("  Total Candidates:", Number(totalCandidates));
  console.log("\n  Candidates:");
  candidates.forEach((c, i) => {
    console.log(`    ${i + 1}. ${c.name} (ID: ${c.id})`);
  });
  
  console.log("\n✅ Election is ready for voting!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Setup failed:", error);
    process.exit(1);
  });
