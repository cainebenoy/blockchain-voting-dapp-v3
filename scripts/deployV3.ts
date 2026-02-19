
import { ethers } from "hardhat";

async function main() {
    console.log("Deploying VotingV3...");

    // Get the ContractFactory
    const Voting = await ethers.getContractFactory("VotingV3");

    // Deploy
    const voting = await Voting.deploy();
    await voting.waitForDeployment();

    const address = await voting.getAddress();
    console.log(`VotingV3 deployed to: ${address}`);

    // Optional: Verify on Etherscan if needed, but for now just log
    console.log("Don't forget to update .env and restart backend!");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
