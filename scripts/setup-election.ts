import { ethers } from "ethers";
import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");

  try {
    const network = await provider.getNetwork();
    console.log(`📡 Connected to network: ${network.name} (ChainID: ${network.chainId})`);
  } catch (e) {
    console.error("❌ Failed to connect to provider at http://127.0.0.1:8545");
    process.exit(1);
  }

  const contractAddress = process.env.VOTING_CONTRACT_ADDRESS;
  console.log(`🔍 Checking contract at address: ${contractAddress}`);

  if (!contractAddress) {
    console.error("❌ VOTING_CONTRACT_ADDRESS is not defined in .env");
    process.exit(1);
  }

  const code = await provider.getCode(contractAddress);
  console.log(`📄 Contract code length: ${code.length}`);
  if (code === "0x") {
    console.log("⚠️  NO CODE FOUND at this address.");

    // List some accounts to see if we are on the right node
    const accounts = await provider.listAccounts();
    console.log(`🏦 Node has ${accounts.length} accounts. First account: ${accounts[0].address}`);

    process.exit(1);
  }

  console.log("✅ Code found! Proceeding with setup...");

  const pk = process.env.SERVER_PRIVATE_KEY || "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
  const wallet = new ethers.Wallet(pk, provider);
  const artifactPath = path.join(__dirname, "../backend/VotingV2.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
  const contract = new ethers.Contract(contractAddress, artifact.abi, wallet);

  let nonce = await wallet.getNonce();
  const waitTx = async (txResponse: any) => {
    console.log(`> Sending TX... ${txResponse.hash} (Nonce: ${nonce})`);
    const receipt = await txResponse.wait();
    console.log(`> Confirmed in block ${receipt.blockNumber}`);
    nonce++;
    return receipt;
  };

  const total = await contract.totalCandidates();
  console.log(`Current candidates: ${total}`);

  if (Number(total) === 0) {
    await waitTx(await contract.addCandidate("Alice Johnson", { nonce }));
    await waitTx(await contract.addCandidate("Bob Smith", { nonce }));
    await waitTx(await contract.addCandidate("Carol Williams", { nonce }));
  }

  await waitTx(await contract.setOfficialSigner(wallet.address, { nonce }));

  if (!(await contract.electionActive())) {
    await waitTx(await contract.startElection({ nonce }));
  }

  console.log("✅ Election Ready!");
}

main().catch(err => {
  console.error("❌ Fatal error:", err);
  process.exit(1);
});
