import { ethers } from "ethers";
import "dotenv/config";

async function main() {
    const rpcUrl = process.env.SEPOLIA_RPC_URL || "https://eth-sepolia.g.alchemy.com/v2/U--2deFkV2sB2Ui12j-yG";
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const pk = process.env.SEPOLIA_PRIVATE_KEY || process.env.SERVER_PRIVATE_KEY;
    const wallet = new ethers.Wallet(pk, provider);

    const contractAddress = process.env.VOTING_CONTRACT_ADDRESS;

    // Minimal ABI for endElection
    const abi = [
        "function endElection() external",
        "function electionActive() external view returns (bool)"
    ];

    const contract = new ethers.Contract(contractAddress, abi, wallet);

    console.log(`📍 Contract: ${contractAddress}`);
    console.log(`👤 Admin: ${wallet.address}`);

    // Check current status
    const isActive = await contract.electionActive();
    console.log(`📊 Election currently: ${isActive ? 'ACTIVE' : 'INACTIVE'}`);

    if (!isActive) {
        console.log('⚠️  Election is already ended!');
        return;
    }

    console.log('🛑 Ending election...');
    const tx = await contract.endElection();
    console.log(`📤 Transaction sent: ${tx.hash}`);

    await tx.wait();
    console.log('✅ Election ended successfully!');
    console.log(`🔗 View on Etherscan: https://sepolia.etherscan.io/tx/${tx.hash}`);
}

main().catch(console.error);
