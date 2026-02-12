import { ethers } from 'ethers';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
// Go up two levels to backend root
const backendRoot = path.join(__dirname, '..');

// State
let provider;
let wallet;
let contract;
let ABI;

// Initialize
export const initEthereum = () => {
    if (!process.env.SEPOLIA_RPC_URL || !process.env.SERVER_PRIVATE_KEY || !process.env.VOTING_CONTRACT_ADDRESS) {
        console.error("Missing Ethereum env vars");
        return;
    }

    provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL, null, {
        staticNetwork: true,
        batchMaxCount: 1
    });
    provider.pollingInterval = 4000;

    wallet = new ethers.Wallet(process.env.SERVER_PRIVATE_KEY, provider);

    const abiPath = path.join(backendRoot, 'VotingV2.json');
    const contractJson = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
    ABI = contractJson.abi;

    contract = new ethers.Contract(process.env.VOTING_CONTRACT_ADDRESS, ABI, wallet);
};

export const getProvider = () => provider;
export const getWallet = () => wallet;
export const getContract = () => contract;
export const getABI = () => ABI;

export const updateContractAddress = (newAddress) => {
    if (!contract) return;
    contract = new ethers.Contract(newAddress, ABI, wallet);
    console.log('[ETH SERVICE] Updated contract instance to', newAddress);
};

export const isContractDeployed = async (address) => {
    if (!address || typeof address !== 'string') return false;
    try {
        const code = await provider.getCode(address);
        return !!code && code !== '0x' && code !== '0x0' && code !== '0x00';
    } catch (e) {
        console.warn('[CHECK] getCode failed for', address, e.message);
        return false;
    }
};

export const ensureAuthorizedSignerFor = async (address) => {
    try {
        const target = new ethers.Contract(address, ABI, wallet);
        const [adminAddr, currentSigner] = await Promise.all([
            target.admin(),
            target.officialSigner(),
        ]);

        if (adminAddr.toLowerCase() !== wallet.address.toLowerCase()) {
            return { changed: false, reason: 'not-admin', admin: adminAddr, currentSigner };
        }

        if (currentSigner.toLowerCase() === wallet.address.toLowerCase()) {
            return { changed: false, reason: 'already-set', admin: adminAddr, currentSigner };
        }

        console.log('[AUTHZ] Setting official signer to server wallet for', address);
        const tx = await target.setOfficialSigner(wallet.address);
        await tx.wait(1);
        return { changed: true, admin: adminAddr, currentSigner: wallet.address };
    } catch (e) {
        return { changed: false, error: e.message || String(e) };
    }
};
