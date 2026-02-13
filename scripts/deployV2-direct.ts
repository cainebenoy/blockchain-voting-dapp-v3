import { ethers } from "ethers";
import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
    const rpcUrl = process.env.SEPOLIA_RPC_URL || "http://127.0.0.1:8545";
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const pk = process.env.SEPOLIA_PRIVATE_KEY || "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
    const wallet = new ethers.Wallet(pk, provider);

    console.log(`🚀 Deploying VotingV2 to Sepolia...`);
    console.log(`📍 Deployer address: ${wallet.address}`);

    // Check balance
    const balance = await provider.getBalance(wallet.address);
    console.log(`💰 Balance: ${ethers.formatEther(balance)} ETH`);

    const artifactPath = path.join(__dirname, "../backend/VotingV2.json");
    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));

    const factory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, wallet);

    // Estimate gas
    const deployTx = await factory.getDeployTransaction();
    const gasEstimate = await provider.estimateGas(deployTx);
    const feeData = await provider.getFeeData();
    const gasCost = gasEstimate * (feeData.gasPrice || 0n);

    console.log(`⛽ Estimated gas: ${gasEstimate.toString()}`);
    console.log(`💸 Estimated cost: ${ethers.formatEther(gasCost)} ETH`);

    if (balance < gasCost) {
        throw new Error(`Insufficient balance! Need ${ethers.formatEther(gasCost)} ETH, have ${ethers.formatEther(balance)} ETH`);
    }

    console.log('📤 Sending deployment transaction...');
    const contract = await factory.deploy();
    console.log('⏳ Waiting for deployment...');
    await contract.waitForDeployment();

    const address = await contract.getAddress();
    console.log(`✅ Contract deployed at: ${address}`);

    // Update .env files
    const envPaths = [
        path.join(__dirname, "../.env"),
        path.join(__dirname, "../backend/.env")
    ];

    for (const envPath of envPaths) {
        if (fs.existsSync(envPath)) {
            let content = fs.readFileSync(envPath, "utf8");
            content = content.replace(/VOTING_CONTRACT_ADDRESS="0x[a-fA-F0-9]{40}"/, `VOTING_CONTRACT_ADDRESS="${address}"`);
            fs.writeFileSync(envPath, content);
            console.log(`📝 Updated ${envPath}`);
        }
    }
}

main().catch(console.error);
