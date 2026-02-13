import { ethers } from "ethers";

const privateKey = "0x65bbc10d73c7c2afe50c370b8f485848aa3ec2aa4ec787abb25561333a235e1e";
const wallet = new ethers.Wallet(privateKey);

console.log("Address from private key:", wallet.address);
console.log("Expected address with funds: 0xd86459Ba3400927f908371CF72787Cc16EC3f4d5");
console.log("Match:", wallet.address.toLowerCase() === "0xd86459Ba3400927f908371CF72787Cc16EC3f4d5".toLowerCase());

// Check balance on Sepolia
const provider = new ethers.JsonRpcProvider("https://eth-sepolia.g.alchemy.com/v2/U--2deFkV2sB2Ui12j-yG");
const connectedWallet = wallet.connect(provider);

async function checkBalance() {
    const balance = await provider.getBalance(wallet.address);
    console.log("Sepolia Balance (Wei):", balance.toString());
    console.log("Sepolia Balance (ETH):", ethers.formatEther(balance));
}

checkBalance().catch(console.error);
