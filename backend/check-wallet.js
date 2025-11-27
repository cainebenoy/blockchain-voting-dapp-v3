import dotenv from 'dotenv';
import { ethers } from 'ethers';

dotenv.config();

async function checkWallet() {
    console.log("🔍 Inspecting Backend Server Wallet...");
    
    try {
        // Connect to the network
        const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
        // Load the wallet
        const wallet = new ethers.Wallet(process.env.SERVER_PRIVATE_KEY, provider);
        
        console.log("------------------------------------------------");
        console.log("📍 Wallet Address:  ", wallet.address);
        
        // Check Balance
        const balance = await provider.getBalance(wallet.address);
        const ethBalance = ethers.formatEther(balance);
        
        console.log("💰 Current Balance: ", ethBalance, "SEP");
        console.log("------------------------------------------------");
        
        if (parseFloat(ethBalance) < 0.01) {
            console.log("⚠️  WARNING: Balance is low! Please top up soon.");
        } else {
            console.log("✅ Status: Healthy. Ready for voting.");
        }

    } catch (error) {
        console.error("❌ Error:", error.message);
    }
}

checkWallet();
