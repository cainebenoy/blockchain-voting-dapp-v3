import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import { createClient } from '@supabase/supabase-js';
import { ethers } from 'ethers';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Load environment variables
dotenv.config();

// Fix for __dirname in ESM (it doesn't exist by default)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = 3000;

app.use(cors());
app.use(express.json());

// --- 1. SETUP DATABASE CONNECTION ---
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

// --- 2. SETUP BLOCKCHAIN CONNECTION ---
const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
const wallet = new ethers.Wallet(process.env.SERVER_PRIVATE_KEY, provider);

// Load the Contract ABI
const abiPath = path.join(__dirname, 'VotingV2.json');
const contractJson = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
const ABI = contractJson.abi;
const contract = new ethers.Contract(process.env.VOTING_CONTRACT_ADDRESS, ABI, wallet);

// --- API ENDPOINTS ---

// Test Route
app.get('/', (req, res) => {
    res.send('VoteChain Election Server is ONLINE.');
});

// STAGE 1: CHECK-IN (Front Desk)
app.post('/api/voter/check-in', async (req, res) => {
    const { aadhaar_id } = req.body;
    try {
        // 1. Check Database
        const { data: voter, error } = await supabase
            .from('voters')
            .select('*')
            .eq('aadhaar_id', aadhaar_id)
            .single();

        if (error || !voter) {
            return res.status(404).json({ status: 'error', message: 'Voter not found.' });
        }

        if (voter.has_voted) {
            return res.status(403).json({ status: 'error', message: 'Voter has already voted.' });
        }

        // 2. Return success and data for biometric verification
        res.json({
            status: 'success',
            message: 'Voter eligible.',
            data: {
                name: voter.name,
                fingerprint_id: voter.fingerprint_id,
                photo_url: voter.photo_url
            }
        });

    } catch (err) {
        console.error("Check-in Error:", err);
        res.status(500).json({ status: 'error', message: 'Internal server error.' });
    }
});

// STAGE 2: CAST VOTE (Kiosk)
app.post('/api/vote', async (req, res) => {
    const { aadhaar_id, candidate_id } = req.body;
    try {
        console.log(`Processing vote for ${aadhaar_id}...`);

        // 1. Double-check eligibility (Safety first!)
        const { data: voter } = await supabase
            .from('voters')
            .select('has_voted')
            .eq('aadhaar_id', aadhaar_id)
            .single();

        if (voter.has_voted) {
            return res.status(403).json({ status: 'error', message: 'Double voting detected!' });
        }

        // 2. Submit to Blockchain (This might take a few seconds)
        console.log("Submitting to blockchain...");
        const tx = await contract.vote(candidate_id, aadhaar_id);
        console.log("Transaction sent:", tx.hash);
        
        // Wait for 1 confirmation to be sure
        await tx.wait(1);
        console.log("Transaction confirmed on-chain.");

        // 3. Mark as Voted in Database
        const { error: dbError } = await supabase
            .from('voters')
            .update({ has_voted: true })
            .eq('aadhaar_id', aadhaar_id);

        if (dbError) {
            console.error("Database update failed AFTER blockchain success. Manual sync needed for:", aadhaar_id);
        }

        res.json({
            status: 'success',
            message: 'Vote officially recorded on-chain.',
            transaction_hash: tx.hash
        });

    } catch (err) {
        console.error("Voting Error:", err);
        const errorMessage = err.reason || err.message || "Blockchain transaction failed.";
        res.status(500).json({ status: 'error', message: errorMessage });
    }
});

// Start the server
app.listen(port, () => {
    console.log(`🤖 Election Official (Backend) is listening on port ${port}`);
});