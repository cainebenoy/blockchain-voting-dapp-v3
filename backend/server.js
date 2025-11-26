import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import { createClient } from '@supabase/supabase-js';
import { ethers } from 'ethers';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

// Load environment variables
dotenv.config();

// Validate required environment variables at startup
const requiredEnv = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'SEPOLIA_RPC_URL',
    'SERVER_PRIVATE_KEY',
    'VOTING_CONTRACT_ADDRESS',
];

const missing = requiredEnv.filter((key) => !process.env[key] || String(process.env[key]).trim() === '');
if (missing.length) {
    console.error('\u26a0\ufe0f Missing required environment variables:', missing.join(', '));
    console.error('Please set them in your .env file before starting the server.');
    process.exit(1);
}

// Fix for __dirname in ESM (it doesn't exist by default)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = 3000;

// Restrict CORS (use env ALLOWED_ORIGINS=comma,separated list)
const envOrigins = (process.env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
const allowedOrigins = envOrigins.length ? envOrigins : [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
];
app.use(cors({
    origin: function (origin, callback) {
        // allow non-browser tools (no origin)
        if (!origin) return callback(null, true);
        if (allowedOrigins.includes(origin)) return callback(null, true);
        callback(new Error('Not allowed by CORS'));
    },
}));
app.use(express.json());

// Request ID + basic structured logging
app.use((req, res, next) => {
    const id = crypto.randomUUID();
    // @ts-ignore add id to request
    req.id = id;
    res.setHeader('X-Request-Id', id);
    const start = Date.now();
    res.on('finish', () => {
        const entry = {
            reqId: id,
            method: req.method,
            path: req.path,
            status: res.statusCode,
            durationMs: Date.now() - start,
        };
        console.log(JSON.stringify(entry));
    });
    next();
});

// --- 0. FRONTEND SERVING (Public Results Dashboard) ---
// Serve the public results dashboard from the project root
const frontendPath = path.join(__dirname, '..');
app.use(express.static(frontendPath));

// --- 1. SETUP DATABASE CONNECTION ---
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

// --- 2. SETUP BLOCKCHAIN CONNECTION ---
const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
const wallet = new ethers.Wallet(process.env.SERVER_PRIVATE_KEY, provider);

// Load the Contract ABI (Kiosk model: VotingV2)
const abiPath = path.join(__dirname, 'VotingV2.json');
const contractJson = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
const ABI = contractJson.abi;
const contract = new ethers.Contract(process.env.VOTING_CONTRACT_ADDRESS, ABI, wallet);

// --- API ENDPOINTS ---

// Health check
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', service: 'VoteChain Backend', time: new Date().toISOString() });
});

// Contract configuration endpoint (for frontend)
app.get('/api/config', (req, res) => {
    res.json({
        status: 'ok',
        contractAddress: process.env.VOTING_CONTRACT_ADDRESS,
        rpcUrl: process.env.SEPOLIA_RPC_URL,
        network: 'sepolia'
    });
});

// Live results endpoint (proxy blockchain data)
app.get('/api/results', async (req, res) => {
    try {
        const active = await contract.electionActive();
        const vCount = await contract.totalVotes();
        const cCount = await contract.totalCandidates();
        const candidates = await contract.getAllCandidates();
        
        res.json({
            status: 'ok',
            data: {
                electionActive: active,
                totalVotes: Number(vCount),
                totalCandidates: Number(cCount),
                candidates: candidates.map(c => ({
                    id: Number(c.id),
                    name: c.name,
                    voteCount: Number(c.voteCount)
                }))
            }
        });
    } catch (e) {
        console.error('Results fetch error:', e);
        res.status(500).json({ status: 'error', message: 'Failed to fetch results from blockchain' });
    }
});

// Fallback: serve index.html for non-API routes (SPA support)
app.use((req, res, next) => {
    if (req.path.startsWith('/api')) return next();
    if (req.method === 'GET') {
        return res.sendFile(path.join(frontendPath, 'index.html'));
    }
    next();
});

// STAGE 1: CHECK-IN (Front Desk)
const RL_CHECKIN_MAX = parseInt(process.env.RL_CHECKIN_MAX || '30', 10);
const RL_VOTE_MAX = parseInt(process.env.RL_VOTE_MAX || '20', 10);
const checkInLimiter = rateLimit({ windowMs: 60 * 1000, max: RL_CHECKIN_MAX });
app.post('/api/voter/check-in', checkInLimiter, async (req, res) => {
    const { aadhaar_id } = req.body || {};
    if (typeof aadhaar_id !== 'string' || aadhaar_id.trim().length !== 12 || !/^\d{12}$/.test(aadhaar_id)) {
        return res.status(400).json({ status: 'error', message: 'Invalid Aadhaar ID format.' });
    }
    try {
        // 1. Check Database
        const { data: voter, error } = await supabase
            .from('voters')
            .select('*')
            .eq('aadhaar_id', aadhaar_id)
            .single();

        if (error || !voter) {
            return res.status(404).json({ status: 'error', message: 'Voter not found.', data: null });
        }

        if (voter.has_voted) {
            return res.status(403).json({ status: 'error', message: 'Voter has already voted.', data: null });
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
        res.status(500).json({ status: 'error', message: 'Internal server error.', data: null });
    }
});

// STAGE 2: CAST VOTE (Kiosk)
const voteLimiter = rateLimit({ windowMs: 60 * 1000, max: RL_VOTE_MAX });
app.post('/api/vote', voteLimiter, async (req, res) => {
    const { aadhaar_id, candidate_id } = req.body || {};
    if (typeof aadhaar_id !== 'string' || !/^\d{12}$/.test(aadhaar_id)) {
        return res.status(400).json({ status: 'error', message: 'Invalid Aadhaar ID.' });
    }
    const cidNum = Number(candidate_id);
    if (!Number.isInteger(cidNum) || cidNum <= 0) {
        return res.status(400).json({ status: 'error', message: 'Invalid candidate ID.' });
    }
    try {
        console.log(`Processing vote for ${aadhaar_id}...`);

        // 1. Double-check eligibility (Safety first!)
        const { data: voter } = await supabase
            .from('voters')
            .select('has_voted')
            .eq('aadhaar_id', aadhaar_id)
            .single();

        if (voter?.has_voted) {
            return res.status(403).json({ status: 'error', message: 'Double voting detected!', data: null });
        }

        // 2. Submit to Blockchain (This might take a few seconds)
        console.log("Submitting to blockchain...");
        // VotingV2 expects candidate ID and voterId (aadhaar)
        const tx = await contract.vote(cidNum, aadhaar_id);
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

        // Write audit log (hash Aadhaar ID for privacy)
        try {
            const aadhaarHash = crypto.createHash('sha256').update(aadhaar_id).digest('hex');
            const auditEntry = {
                ts: new Date().toISOString(),
                reqId: req.id,
                aadhaarHash,
                candidateId: cidNum,
                txHash: tx.hash,
            };
            fs.appendFile(path.join(__dirname, 'logs', 'vote-audit.log'), JSON.stringify(auditEntry) + '\n', () => {});
        } catch {}

        res.json({
            status: 'success',
            message: 'Vote officially recorded on-chain.',
            data: { transaction_hash: tx.hash }
        });

    } catch (err) {
        console.error("Voting Error:", err);
        const errorMessage = err.reason || err.message || "Blockchain transaction failed.";
        res.status(500).json({ status: 'error', message: errorMessage, data: null });
    }
});

// Metrics endpoint: on-chain totals + Supabase voted count
app.get('/api/metrics', async (_req, res) => {
    try {
        const votesOnChain = await contract.totalVotes();
        const candidatesOnChain = await contract.totalCandidates();
        const { count, error } = await supabase
            .from('voters')
            .select('*', { count: 'exact', head: true })
            .eq('has_voted', true);
        if (error) throw error;
        res.json({
            status: 'success',
            message: 'Metrics ready',
            data: {
                totalVotesOnChain: Number(votesOnChain),
                totalCandidatesOnChain: Number(candidatesOnChain),
                votersMarkedVoted: count ?? 0,
            },
        });
    } catch (e) {
        res.status(500).json({ status: 'error', message: e.message || 'Metrics failed', data: null });
    }
});

// Start the server
app.listen(port, () => {
    console.log(`🤖 Election Official (Backend) is listening on port ${port}`);
});