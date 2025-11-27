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

// CORS - Allow all origins for development
app.use(cors());
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

// --- 3. SERVER STATE (Remote Enrollment System) ---
// This acts as temporary memory to coordinate between Admin Dashboard and Kiosk
let pendingEnrollment = null;

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

// Get current active contract (returns runtime contract, useful after deployments)
app.get('/api/active-contract', (req, res) => {
    res.json({
        status: 'ok',
        contractAddress: contract.target || contract.address || process.env.VOTING_CONTRACT_ADDRESS,
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
            fs.appendFile(path.join(__dirname, 'logs', 'vote-audit.log'), JSON.stringify(auditEntry) + '\n', () => {
                // Audit log written
            });
        } catch {
            // Audit logging failed, but vote succeeded
        }

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

// ---------------------------------------------------------
// ADMIN ENDPOINTS
// ---------------------------------------------------------

// Deploy New Election Contract
app.post('/api/admin/deploy-contract', async (req, res) => {
    console.log('[ADMIN] Deploying new VotingV2 contract...');
    
    try {
        // 1. Deploy new contract
        const ContractFactory = new ethers.ContractFactory(ABI, contractJson.bytecode, wallet);
        const newContract = await ContractFactory.deploy();
        await newContract.waitForDeployment();
        
        const contractAddress = await newContract.getAddress();
        console.log(`[ADMIN] ✅ New contract deployed at: ${contractAddress}`);
        
        // 2. Reset voter database for new election (keep fingerprints)
        console.log('[ADMIN] Resetting voter voting status...');
        const { error: resetError } = await supabase
            .from('voters')
            .update({ has_voted: false })
            .neq('id', 0); // Update all records
        
        if (resetError) {
            console.error('[ADMIN] ⚠️ Database reset failed:', resetError);
        } else {
            console.log('[ADMIN] ✅ All voters reset to has_voted=false (fingerprints preserved)');
        }
        
        // 3. Update .env file automatically
        console.log('[ADMIN] Updating .env file...');
        const envPath = path.join(__dirname, '.env');
        let envContent = fs.readFileSync(envPath, 'utf8');
        
        // Replace the contract address line
        envContent = envContent.replace(
            /VOTING_CONTRACT_ADDRESS="0x[a-fA-F0-9]{40}"/,
            `VOTING_CONTRACT_ADDRESS="${contractAddress}"`
        );
        
        fs.writeFileSync(envPath, envContent, 'utf8');
        console.log('[ADMIN] ✅ .env file updated with new contract address');
        
        // 4. Update runtime environment variable
        process.env.VOTING_CONTRACT_ADDRESS = contractAddress;
        
        res.json({
            status: 'success',
            message: 'New election deployed! Contract address saved to .env',
            data: {
                contractAddress: contractAddress,
                network: 'Sepolia',
                deployer: wallet.address,
                votersReset: resetError ? false : true,
                envUpdated: true
            }
        });
        
    } catch (err) {
        console.error('[ADMIN] Contract deployment failed:', err);
        res.status(500).json({
            status: 'error',
            message: err.message || 'Contract deployment failed',
            data: null
        });
    }
});

// Add Eligible Voter to Registry
app.post('/api/admin/add-voter', async (req, res) => {
    const { aadhaar_id, name, constituency } = req.body;
    
    // Validate input
    if (!aadhaar_id || !name) {
        return res.status(400).json({ status: 'error', message: 'Aadhaar ID and name are required.' });
    }
    
    if (!/^\d{12}$/.test(aadhaar_id)) {
        return res.status(400).json({ status: 'error', message: 'Invalid Aadhaar ID format (must be 12 digits).' });
    }
    
    console.log(`[ADMIN] Registering voter: ${name} (${aadhaar_id})`);

    try {
        // 1. Check if already exists
        const { data: existing } = await supabase
            .from('voters')
            .select('id')
            .eq('aadhaar_id', aadhaar_id)
            .single();

        if (existing) {
            return res.status(400).json({ status: 'error', message: 'Voter already registered.' });
        }

        // 2. Insert new voter 
        // Note: fingerprint_id is null initially. Enroll at kiosk later.
        const { data, error } = await supabase
            .from('voters')
            .insert([{ 
                aadhaar_id, 
                name, 
                constituency: constituency || null,
                fingerprint_id: null, // Pending enrollment
                has_voted: false 
            }])
            .select();

        if (error) throw error;

        res.json({ 
            status: 'success', 
            message: 'Voter added to registry successfully.', 
            data: data[0] 
        });

    } catch (err) {
        console.error('[ADMIN] Add Voter Error:', err);
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// ---------------------------------------------------------
// REMOTE ENROLLMENT ENDPOINTS (Kiosk Integration)
// ---------------------------------------------------------

// 1. Initiate Remote Enrollment (Called by Admin Dashboard)
app.post('/api/admin/initiate-enrollment', async (req, res) => {
    const { aadhaar_id, name, constituency } = req.body;
    
    // Validate input
    if (!aadhaar_id || !name) {
        return res.status(400).json({ status: 'error', message: 'Aadhaar ID and name are required.' });
    }
    
    if (!/^\d{12}$/.test(aadhaar_id)) {
        return res.status(400).json({ status: 'error', message: 'Invalid Aadhaar ID format (must be 12 digits).' });
    }
    
    try {
        // Check if already exists
        const { data: existing } = await supabase
            .from('voters')
            .select('id')
            .eq('aadhaar_id', aadhaar_id)
            .single();

        if (existing) {
            return res.status(400).json({ status: 'error', message: 'Voter already registered.' });
        }

        // Get the next available Fingerprint ID
        // We check the highest ID currently in the DB and add 1
        const { data: lastVoter } = await supabase
            .from('voters')
            .select('fingerprint_id')
            .order('fingerprint_id', { ascending: false })
            .limit(1)
            .single();
            
        const nextId = (lastVoter?.fingerprint_id || 0) + 1;
        
        // Queue the enrollment command in server memory
        pendingEnrollment = {
            status: 'WAITING_FOR_KIOSK',
            aadhaar_id,
            name,
            constituency: constituency || null,
            target_finger_id: nextId,
            timestamp: Date.now()
        };
        
        console.log(`[REMOTE ENROLL] Command queued for ${name} -> Target ID #${nextId}`);
        res.json({ 
            status: 'success', 
            message: 'Waiting for Kiosk scan...', 
            target_id: nextId 
        });

    } catch (err) {
        console.error('[REMOTE ENROLL] Init Error:', err);
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// 2. Check Enrollment Status (Polled by Admin Dashboard to update UI)
app.get('/api/admin/enrollment-status', (req, res) => {
    // If a request is older than 60 seconds, clear it (timeout)
    if (pendingEnrollment && (Date.now() - pendingEnrollment.timestamp > 60000)) {
        console.log('[REMOTE ENROLL] Request timed out, clearing...');
        pendingEnrollment = null;
    }
    res.json(pendingEnrollment || { status: 'IDLE' });
});

// 3. Poll for Commands (Called by Kiosk in a loop)
app.get('/api/kiosk/poll-commands', (req, res) => {
    if (pendingEnrollment && pendingEnrollment.status === 'WAITING_FOR_KIOSK') {
        console.log('[REMOTE ENROLL] Kiosk polled, sending command...');
        res.json({ command: 'ENROLL', ...pendingEnrollment });
    } else {
        res.json({ command: 'NONE' });
    }
});

// 4. Complete Enrollment (Called by Kiosk after successful scan)
app.post('/api/kiosk/enrollment-complete', async (req, res) => {
    if (!pendingEnrollment) {
        return res.status(400).json({ 
            status: 'error', 
            message: 'No active enrollment request.' 
        });
    }

    const { success, fingerprint_id } = req.body;

    if (success) {
        // The Kiosk succeeded! Now save to Database.
        const { error } = await supabase.from('voters').insert([{
            aadhaar_id: pendingEnrollment.aadhaar_id,
            name: pendingEnrollment.name,
            constituency: pendingEnrollment.constituency,
            fingerprint_id: fingerprint_id, // The ID the kiosk actually used
            has_voted: false
        }]);
        
        if (error) {
            console.error('[REMOTE ENROLL] DB Save Error:', error);
            pendingEnrollment.status = 'FAILED';
            pendingEnrollment.error_message = 'Database save failed';
            return res.status(500).json({ 
                status: 'error', 
                message: 'Database save failed' 
            });
        }

        console.log(`[REMOTE ENROLL] ✅ Success! Saved ${pendingEnrollment.name} as ID #${fingerprint_id}`);
        pendingEnrollment.status = 'COMPLETED'; // Signal success to Admin UI
        
        // Clear the pending state after a few seconds so the system resets
        setTimeout(() => { 
            pendingEnrollment = null; 
            console.log('[REMOTE ENROLL] State cleared, ready for next enrollment.');
        }, 5000);
        
        res.json({ status: 'success', message: 'Voter enrolled successfully.' });
    } else {
        console.log('[REMOTE ENROLL] ❌ Kiosk reported failure.');
        pendingEnrollment.status = 'FAILED';
        pendingEnrollment.error_message = 'Fingerprint scan failed';
        
        // Clear failure state quickly
        setTimeout(() => { 
            pendingEnrollment = null; 
            console.log('[REMOTE ENROLL] Failed state cleared.');
        }, 5000);
        
        res.json({ status: 'received', message: 'Enrollment failed, cleared.' });
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