// Diagnostic test endpoint to check route registration
// Diagnostic test endpoint to check route registration
// ...existing imports and app initialization...

// (Moved) Verify transaction details endpoint is defined after app initialization.
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
import { exec } from 'child_process';

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


// Register /api/verify-code as the first API endpoint
app.post('/api/verify-code', async (req, res) => {
    const code = (req.body && req.body.code ? String(req.body.code).toUpperCase() : '');
    try {
        const { data, error } = await supabase
            .from('receipts')
            .select('tx_hash')
            .eq('code', code)
            .single();
        if (error || !data) return res.status(404).json({ status: 'error', message: 'Invalid Code' });
        res.json({ status: 'success', tx_hash: data.tx_hash });
    } catch (e) {
        res.status(500).json({ status: 'error' });
    }
});


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
// --- API ENDPOINTS ---
// (All API routes are defined below)

// ...existing API endpoints...

// --- 0. FRONTEND SERVING (Public Results Dashboard) ---
const frontendPath = path.join(__dirname, '..');
app.use(express.static(frontendPath));

// Serve results.html directly for /results or /results.html
app.get(['/results', '/results.html'], (req, res) => {
    res.sendFile(path.join(frontendPath, 'results.html'));
});

// Fallback: serve index.html for non-API routes (SPA support)
app.use((req, res, next) => {
    if (req.path.startsWith('/api')) return next();
    if (req.method === 'GET') {
        // If requesting /results or /results.html, serve results.html
        if (req.path === '/results' || req.path === '/results.html') {
            return res.sendFile(path.join(frontendPath, 'results.html'));
        }
        // Otherwise, serve index.html (landing)
        return res.sendFile(path.join(frontendPath, 'index.html'));
    }
    next();
});

// --- 1. SETUP DATABASE CONNECTION ---
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

// --- 2. SETUP BLOCKCHAIN CONNECTION ---
// --- HELPER: Generate Short Code (e.g. "A7B-29X") ---
function generateShortCode() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // No I, 1, O, 0 to avoid confusion
    let code = '';
    for (let i = 0; i < 6; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return code.substring(0, 3) + '-' + code.substring(3, 6);
}
const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL, null, {
    staticNetwork: true,
    batchMaxCount: 1
});
// Increase polling interval and timeout for Pi's network
provider.pollingInterval = 4000; // 4 seconds between polls
const wallet = new ethers.Wallet(process.env.SERVER_PRIVATE_KEY, provider);

// Load the Contract ABI (Kiosk model: VotingV2)
const abiPath = path.join(__dirname, 'VotingV2.json');
const contractJson = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
const ABI = contractJson.abi;
let contract = new ethers.Contract(process.env.VOTING_CONTRACT_ADDRESS, ABI, wallet);

// Helper: check whether a contract has code at the given address
async function isContractDeployed(address) {
    if (!address || typeof address !== 'string') return false;
    try {
        const code = await provider.getCode(address);
        // provider.getCode() returns '0x' if no code is present
        return !!code && code !== '0x' && code !== '0x0' && code !== '0x00';
    } catch (e) {
        console.warn('[CHECK] getCode failed for', address, e && e.message ? e.message : e);
        return false;
    }
}

// --- 3. SERVER STATE (Remote Enrollment System) ---
// This acts as temporary memory to coordinate between Admin Dashboard and Kiosk
let pendingEnrollment = null;

// --- Auto-authorize official signer (server wallet) ---
async function ensureAuthorizedSignerFor(address) {
    try {
        const target = new ethers.Contract(address, ABI, wallet);
        const [adminAddr, currentSigner] = await Promise.all([
            target.admin(),
            target.officialSigner(),
        ]);

        if (adminAddr.toLowerCase() !== wallet.address.toLowerCase()) {
            console.warn('[AUTHZ] Skipping: server wallet is not admin of', address);
            return { changed: false, reason: 'not-admin', admin: adminAddr, currentSigner };
        }

        if (currentSigner.toLowerCase() === wallet.address.toLowerCase()) {
            console.log('[AUTHZ] Official signer already set.');
            return { changed: false, reason: 'already-set', admin: adminAddr, currentSigner };
        }

        console.log('[AUTHZ] Setting official signer to server wallet for', address);
        const tx = await target.setOfficialSigner(wallet.address);
        console.log('[AUTHZ] Tx sent:', tx.hash);
        await tx.wait(1);
        console.log('[AUTHZ] ✅ Official signer authorized');
        return { changed: true, admin: adminAddr, currentSigner: wallet.address };
    } catch (e) {
        console.warn('[AUTHZ] Authorization check failed:', e.message || e);
        return { changed: false, error: e.message || String(e) };
    }
}

// Kick off authorization check on startup (non-blocking)
(async () => {
    const addr = process.env.VOTING_CONTRACT_ADDRESS;
    console.log('[AUTHZ] Startup check for contract', addr);
    await ensureAuthorizedSignerFor(addr);
})();

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

// Simple test POST endpoint to confirm POST routing works

// Verify transaction details for frontend (used by verify.html)
app.post('/api/verify-transaction', async (req, res) => {
    const { tx_hash } = req.body;
    if (!tx_hash || typeof tx_hash !== 'string' || !tx_hash.startsWith('0x') || tx_hash.length !== 66) {
        return res.status(400).json({ status: 'error', message: 'Invalid transaction hash.' });
    }
    try {
        // Use ethers.js to fetch transaction and receipt
        const tx = await provider.getTransaction(tx_hash);
        const receipt = await provider.getTransactionReceipt(tx_hash);
        if (tx && receipt && receipt.status === 1) {
            res.json({
                status: 'success',
                tx: {
                    blockNumber: receipt.blockNumber,
                    from: tx.from,
                    to: tx.to,
                }
            });
        } else {
            res.status(404).json({ status: 'error', message: 'Transaction not found or not confirmed.' });
        }
    } catch (e) {
        console.error('Verify transaction error:', e);
        res.status(500).json({ status: 'error', message: 'Failed to fetch transaction.' });
    }
});

// Lookup receipt code by transaction hash (used by kiosk to wait for short code)
app.post('/api/lookup-receipt', async (req, res) => {
    const tx_hash = req.body && req.body.tx_hash ? String(req.body.tx_hash) : '';
    if (!tx_hash || !tx_hash.startsWith('0x') || tx_hash.length !== 66) {
        return res.status(400).json({ status: 'error', message: 'Invalid transaction hash.' });
    }
    try {
        const { data, error } = await supabase
            .from('receipts')
            .select('code')
            .eq('tx_hash', tx_hash)
            .single();
        if (error || !data) return res.status(404).json({ status: 'error', message: 'Receipt not found.' });
        res.json({ status: 'success', code: data.code });
    } catch (e) {
        console.error('Lookup receipt error:', e);
        res.status(500).json({ status: 'error', message: 'Lookup failed.' });
    }
});

// Top-level /api/verify-code endpoint
app.post('/api/verify-code', async (req, res) => {
    const code = (req.body && req.body.code ? String(req.body.code).toUpperCase() : '');
    try {
        const { data, error } = await supabase
            .from('receipts')
            .select('tx_hash')
            .eq('code', code)
            .single();
        if (error || !data) return res.status(404).json({ status: 'error', message: 'Invalid Code' });
        res.json({ status: 'success', tx_hash: data.tx_hash });
    } catch (e) {
        res.status(500).json({ status: 'error' });
    }
});

// Top-level /api/verify-code endpoint

// Top-level /api/verify-code endpoint
// Get current active contract (returns runtime contract, useful after deployments)
app.get('/api/active-contract', (req, res) => {
    // Prevent caching to avoid reload loops
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    
    res.json({
        status: 'ok',
        contractAddress: contract.target || contract.address || process.env.VOTING_CONTRACT_ADDRESS,
        network: 'sepolia'
    });
});

// Live results endpoint (proxy blockchain data)
app.get('/api/results', async (req, res) => {
    try {
        const addr = contract.target || contract.address || process.env.VOTING_CONTRACT_ADDRESS;
        const deployed = await isContractDeployed(addr);
        if (!deployed) {
            console.warn('[RESULTS] Contract not deployed at', addr);
            return res.status(503).json({ status: 'error', message: 'Election contract not deployed at configured address.' });
        }

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
        // Verify contract is deployed before attempting to call
        const addr = contract.target || contract.address || process.env.VOTING_CONTRACT_ADDRESS;
        const deployed = await isContractDeployed(addr);
        if (!deployed) {
            console.warn('[VOTE] Attempt to vote but contract not deployed at', addr);
            return res.status(503).json({ status: 'error', message: 'Election contract not available yet. Please try again later.' });
        }

        // VotingV2 expects candidate ID and voterId (aadhaar)
        const tx = await contract.vote(cidNum, aadhaar_id);
        console.log("Transaction sent:", tx.hash);
        
        // Wait for 1 confirmation with timeout protection
        const receiptPromise = tx.wait(1);
        const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error('RPC_TIMEOUT')), 60000) // 60 second timeout
        );
        
            // let receipt; // Removed unused variable
        try {
            await Promise.race([receiptPromise, timeoutPromise]);
            console.log("Transaction confirmed on-chain.");
        } catch (err) {
            if (err.message === 'RPC_TIMEOUT') {
                console.warn("⚠️ RPC timeout during tx.wait(), but transaction was sent. Hash:", tx.hash);
                console.log("Proceeding with database update (vote likely succeeded).");
                // Continue execution - transaction was sent successfully
            } else {
                throw err; // Re-throw other errors
            }
        }

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

        // 4. Generate a short receipt code and save mapping to tx_hash in Supabase
        let shortCode = null;
        try {
            shortCode = generateShortCode();
            const { error: receiptError } = await supabase
                .from('receipts')
                .insert([{ code: shortCode, tx_hash: tx.hash }]);
            if (receiptError) {
                console.error('Failed to save receipt code to DB:', receiptError);
                shortCode = null; // don't return invalid code
            }
        } catch (e) {
            console.error('Receipt save error:', e);
            shortCode = null;
        }

        res.json({
            status: 'success',
            message: 'Vote officially recorded on-chain.',
            data: { transaction_hash: tx.hash, receipt_code: shortCode }
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
        
// Removed verify transaction details endpoint
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

        // 4b. Update in-memory contract instance so runtime uses the new address
        try {
            contract = new ethers.Contract(contractAddress, ABI, wallet);
            console.log('[ADMIN] ✅ Runtime contract instance updated to new address');
        } catch (e) {
            console.warn('[ADMIN] ⚠️ Failed to update runtime contract instance:', e && e.message ? e.message : e);
        }
        
        // 5. Auto-authorize server wallet as official signer on the new contract
        console.log('[ADMIN] Authorizing server wallet as official signer...');
        const authz = await ensureAuthorizedSignerFor(contractAddress);
        if (authz.error) {
            console.warn('[ADMIN] ⚠️ Authorization failed:', authz.error);
        } else if (authz.changed) {
            console.log('[ADMIN] ✅ Official signer set successfully');
        } else {
            console.log('[ADMIN] Official signer unchanged:', authz.reason);
        }
        
                // 6. Schedule automatic backend restart (async, after response sent)
                if (process.env.AUTO_RESTART === 'true') {
                    setTimeout(() => {
                        console.log('[ADMIN] 🔄 Restarting backend service to load new contract...');

                        // Try a list of candidate service names to be robust across deployments
                        const candidates = ['votechain', 'votechain.service', 'votechain-backend.service'];
                        (function tryNext(i) {
                            if (i >= candidates.length) {
                                console.error('[ADMIN] ⚠️ Auto-restart failed for all known service names. Please restart manually.');
                                return;
                            }
                            const svc = candidates[i];
                            exec(`sudo systemctl is-active --quiet ${svc} && sudo systemctl restart ${svc}`, (error, stdout, stderr) => {
                                if (error) {
                                    console.warn(`[ADMIN] Service '${svc}' not active or restart failed, trying next...`);
                                    tryNext(i + 1);
                                } else {
                                    console.log(`[ADMIN] ✅ Backend service '${svc}' restarted successfully`);
                                }
                            });
                        })(0);

                    }, 2000); // 2 second delay allows response to be sent first
                } else {
                    console.log('[ADMIN] AUTO_RESTART disabled; skipping systemd restart. Backend will use updated runtime instance.');
                }
        
        res.json({
            status: 'success',
            message: 'New election deployed! Backend will restart in 2 seconds...',
            data: {
                contractAddress: contractAddress,
                network: 'Sepolia',
                deployer: wallet.address,
                votersReset: resetError ? false : true,
                envUpdated: true,
                signerAuthorized: !authz.error,
                autoRestart: true
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
        // Only queue the enrollment command for the kiosk, do not process vote or require candidate_id
        // Find last fingerprint_id for next assignment
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
        console.error('[REMOTE ENROLL] Init Error:', err && err.stack ? err.stack : err);
        res.status(500).json({ status: 'error', message: err && err.message ? err.message : String(err), data: null });
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
        
        // Get voters who have voted
        const { count: votedCount, error: votedError } = await supabase
            .from('voters')
            .select('*', { count: 'exact', head: true })
            .eq('has_voted', true);
        if (votedError) throw votedError;
        
        // Get total registered voters
        const { count: totalCount, error: totalError } = await supabase
            .from('voters')
            .select('*', { count: 'exact', head: true });
        if (totalError) throw totalError;
        
        res.json({
            status: 'success',
            message: 'Metrics ready',
            data: {
                totalVotesOnChain: Number(votesOnChain),
                totalCandidatesOnChain: Number(candidatesOnChain),
                votersMarkedVoted: votedCount ?? 0,
                totalRegisteredVoters: totalCount ?? 0,
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