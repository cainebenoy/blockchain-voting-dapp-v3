import { ethers } from "ethers";
import "dotenv/config";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const COLORS = {
    green: "\x1b[32m",
    red: "\x1b[31m",
    yellow: "\x1b[33m",
    reset: "\x1b[0m",
    bold: "\x1b[1m"
};

const log = (msg: string, color: string = COLORS.reset) => console.log(`${color}${msg}${COLORS.reset}`);

async function checkUrl(url: string) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        const res = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        return res.ok;
    } catch {
        return false;
    }
}

async function main() {
    log("\n🏥 SYSTEM HEALTH CHECK\n", COLORS.bold);

    let allGood = true;

    // 1. Filesystem Check
    log("--- Filesystem ---", COLORS.bold);
    const rootEnv = path.join(__dirname, "../.env");
    const backendEnv = path.join(__dirname, "../backend/.env");

    if (fs.existsSync(rootEnv)) log("✅ Root .env found", COLORS.green);
    else { log("❌ Root .env missing", COLORS.red); allGood = false; }

    if (fs.existsSync(backendEnv)) log("✅ Backend .env found", COLORS.green);
    else { log("❌ Backend .env missing", COLORS.red); allGood = false; }

    // 2. Blockchain Check
    log("\n--- Blockchain Node ---", COLORS.bold);
    const rpcUrl = process.env.SEPOLIA_RPC_URL || "http://127.0.0.1:8545";
    const provider = new ethers.JsonRpcProvider(rpcUrl);

    try {
        const net = await provider.getNetwork();
        log(`✅ Connected to ${net.name} (ChainID: ${net.chainId})`, COLORS.green);

        const contractAddr = process.env.VOTING_CONTRACT_ADDRESS;
        if (contractAddr) {
            const code = await provider.getCode(contractAddr);
            if (code !== "0x") log(`✅ Contract found at ${contractAddr} (${code.length} bytes)`, COLORS.green);
            else { log(`❌ No code at ${contractAddr} - Needs Deploy`, COLORS.red); allGood = false; }
        } else {
            log("❌ VOTING_CONTRACT_ADDRESS missing in .env", COLORS.red);
            allGood = false;
        }

    } catch (e: any) {
        log(`❌ Failed to connect to Blockchain at ${rpcUrl}: ${e.message}`, COLORS.red);
        allGood = false;
    }

    // 3. Backend Check
    log("\n--- Backend Server ---", COLORS.bold);
    // Assuming backend is at port 3000. Could parse .env for PORT but 3000 is standard here.
    const backendUrl = "http://127.0.0.1:3000";
    const isBackendUp = await checkUrl(`${backendUrl}/`); // server.js usually serves / as index.html

    if (isBackendUp) {
        log("✅ Backend is responding (port 3000)", COLORS.green);
        // Try API
        const isApiUp = await checkUrl(`${backendUrl}/api/active-contract`);
        if (isApiUp) log("✅ API /active-contract responds", COLORS.green);
        else { log("⚠️ API endpoint failure", COLORS.yellow); }
    } else {
        log("❌ Backend is OFFLINE (port 3000)", COLORS.red);
        allGood = false;
    }

    // Summary
    log("\n--- Diagnosis ---", COLORS.bold);
    if (allGood) {
        log("🎉 All Systems Operational via Simulator!", COLORS.green);
    } else {
        log("⚠️ Issues detected. See above logs.", COLORS.yellow);
        process.exit(1);
    }
}

main().catch(console.error);
