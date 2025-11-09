import "dotenv/config";
import { network } from "hardhat";

// Usage (Sepolia):
//   VOTING_V2_ADDRESS=0xDeployedAddress SERVER_WALLET_ADDRESS=0xServerSigner npx hardhat run scripts/authorize-signer.ts --network sepolia

async function main() {
  const contractAddress = process.env.VOTING_V2_ADDRESS;
  const serverSignerAddress = process.env.SERVER_WALLET_ADDRESS;

  if (!contractAddress) throw new Error("Missing VOTING_V2_ADDRESS env var.");
  if (!serverSignerAddress) throw new Error("Missing SERVER_WALLET_ADDRESS env var.");

  const { ethers } = await network.connect();
  const [admin] = await ethers.getSigners();
  console.log(`Admin signer: ${admin.address}`);
  console.log(`Target VotingV2: ${contractAddress}`);
  console.log(`Authorizing server signer: ${serverSignerAddress}`);

  const votingV2 = await ethers.getContractAt("VotingV2", contractAddress, admin);
  const tx = await votingV2.authorizeSigner(serverSignerAddress);
  console.log("authorizeSigner tx sent:", tx.hash);
  await tx.wait();
  console.log("Signer authorized successfully.");
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
