import express from 'express';
import rateLimit from 'express-rate-limit';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { supabase } from '../services/db.js';
import { getContract, getProvider, isContractDeployed } from '../services/ethereumService.js';
import SimpleVoteQueue from '../utils/vote-queue.js';
import { ethers } from 'ethers';

let voteQueue;
const initQueue = () => {
    if (!voteQueue) {
        const contract = getContract();
        if (contract) {
            voteQueue = new SimpleVoteQueue(contract, 5000); // 5s interval for responsive testnet
            console.log("✅ Vote Queue initialized");
        }
    }
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const logsDir = path.join(__dirname, '../logs');

// Ensure logs directory exists
if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
}

const router = express.Router();

const RL_VOTE_MAX = parseInt(process.env.RL_VOTE_MAX || '20', 10);
const voteLimiter = rateLimit({ windowMs: 60 * 1000, max: RL_VOTE_MAX });

// Helper: Generate Short Code
function generateShortCode() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 6; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return code.substring(0, 3) + '-' + code.substring(3, 6);
}

// CAST VOTE
router.post('/vote', voteLimiter, async (req, res) => {
    initQueue();
    const { aadhaar_id, candidate_id, session_token, kiosk_nonce } = req.body || {};

    // 0. Nonce Check
    if (!kiosk_nonce) return res.status(400).json({ status: 'error', message: 'Missing transaction nonce.' });

    // 1. Basic Validation
    if (typeof aadhaar_id !== 'string' || !/^\d{12}$/.test(aadhaar_id)) {
        return res.status(400).json({ status: 'error', message: 'Invalid Aadhaar ID.' });
    }
    const cidNum = Number(candidate_id);
    if (!Number.isInteger(cidNum) || cidNum <= 0) {
        return res.status(400).json({ status: 'error', message: 'Invalid candidate ID.' });
    }

    // 2. Session Validation (P0 Security)
    const expectedToken = crypto.createHmac('sha256', process.env.SERVER_PRIVATE_KEY)
        .update(aadhaar_id)
        .digest('hex');

    if (!session_token || session_token !== expectedToken) {
        return res.status(401).json({ status: 'error', message: 'Invalid or expired biometric session.' });
    }

    try {
        console.log(`Processing vote for ${aadhaar_id}...`);

        const salt = process.env.AADHAAR_SALT || 'default-salt';
        const voterHash = crypto.createHash('sha256').update(aadhaar_id + salt).digest('hex');

        // Robust Lookup (Hashed then Plain) - Same as auth.js
        let { data: voter, error: voterErr } = await supabase
            .from('voters')
            .select('has_voted, aadhaar_id')
            .eq('aadhaar_id', voterHash)
            .single();

        let usedIdentifier = voterHash;

        if (voterErr || !voter) {
            const { data: plainVoter, error: plainError } = await supabase
                .from('voters')
                .select('has_voted, aadhaar_id')
                .eq('aadhaar_id', aadhaar_id)
                .single();

            if (!plainError && plainVoter) {
                voter = plainVoter;
                usedIdentifier = aadhaar_id;
            } else {
                return res.status(404).json({ status: 'error', message: 'Voter not found.', data: null });
            }
        }

        if (voter?.has_voted) {
            return res.status(403).json({ status: 'error', message: 'Double voting detected!', data: null });
        }

        const contract = getContract();
        const addr = contract.target || contract.address;
        const deployed = await isContractDeployed(addr);
        if (!deployed) {
            return res.status(503).json({ status: 'error', message: 'Election contract not available yet.' });
        }

        // 2.5 Safety Check: Is Election Active?
        const isActive = await contract.electionActive();
        if (!isActive) {
            return res.status(403).json({ status: 'error', message: 'Election is closed. Voting disabled.' });
        }

        const voterHashBytes32 = '0x' + voterHash;
        const nonceBytes32 = ethers.isBytesLike(kiosk_nonce) ? kiosk_nonce : ethers.keccak256(ethers.toUtf8Bytes(kiosk_nonce));

        // 4. Queue Vote (Hardened Nonce Mgmt)
        console.log(`[API] Queuing vote with nonce ${kiosk_nonce}...`);

        // We set has_voted in DB to "true" (or we could use PENDING if we had the column)
        // to prevent immediate double-vote attempts while queue processes.
        await supabase
            .from('voters')
            .update({ has_voted: true })
            .eq('aadhaar_id', usedIdentifier);

        // Queue it
        // Pass kiosk_nonce (original string) as 4th arg for DB reconciliation
        const qResult = await voteQueue.queueVote(cidNum, voterHashBytes32, nonceBytes32, kiosk_nonce);

        // Generate receipt placeholder (tx_hash will be null until worked)
        const shortCode = generateShortCode();
        const { error: receiptErr } = await supabase.from('receipts').insert([{
            code: shortCode,
            tx_hash: `PENDING_${kiosk_nonce}`
            // is_confirmed removed due to schema mismatch
        }]);

        if (receiptErr) {
            console.error(`[API] Receipt insertion failed for ${shortCode}:`, receiptErr);
            // We don't fail the whole vote for a receipt error, but we should know
        } else {
            console.log(`[API] Receipt ${shortCode} created (pending)`);
        }

        res.json({
            status: 'success',
            message: 'Vote queued for blockchain processing.',
            data: {
                receipt_code: shortCode,
                queue_position: qResult.queuePosition
            }
        });

    } catch (err) {
        console.error("Voting Error:", err);
        res.status(500).json({ status: 'error', message: err.message || "Internal Server Error" });
    }
});

// Verify Code (Short Code -> Tx Hash)
router.post('/verify-code', async (req, res) => {
    const code = (req.body && req.body.code ? String(req.body.code).toUpperCase() : '');
    console.log(`[DEBUG] Verifying code: "${code}"`);
    try {
        const { data, error } = await supabase
            .from('receipts')
            .select('tx_hash')
            .eq('code', code)
            .single();

        if (error) {
            console.error(`[DEBUG] DB Error finding code ${code}:`, error.message);
            return res.status(404).json({ status: 'error', message: 'Invalid Code' });
        }

        if (!data) {
            console.warn(`[DEBUG] No data found for code ${code}`);
            return res.status(404).json({ status: 'error', message: 'Invalid Code' });
        }

        console.log(`[DEBUG] Code ${code} resolved to ${data.tx_hash}`);
        res.json({ status: 'success', tx_hash: data.tx_hash });
    } catch (e) {
        console.error(`[DEBUG] Internal error during verification:`, e);
        res.status(500).json({ status: 'error' });
    }
});

// Lookup Receipt (Tx Hash -> Short Code)
router.post('/lookup-receipt', async (req, res) => {
    const tx_hash = req.body && req.body.tx_hash ? String(req.body.tx_hash) : '';
    try {
        const { data, error } = await supabase
            .from('receipts')
            .select('code')
            .eq('tx_hash', tx_hash)
            .single();
        if (error || !data) return res.status(404).json({ status: 'error', message: 'Receipt not found.' });
        res.json({ status: 'success', code: data.code });
    } catch (err) {
        res.status(500).json({ status: 'error', message: 'Lookup failed.' });
    }
});

// Verify Transaction (Frontend details)
router.post('/verify-transaction', async (req, res) => {
    const { tx_hash } = req.body;
    if (!tx_hash || !tx_hash.startsWith('0x') || tx_hash.length !== 66) {
        return res.status(400).json({ status: 'error', message: 'Invalid transaction hash.' });
    }
    try {
        const provider = getProvider();
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
    } catch (err) {
        res.status(500).json({ status: 'error', message: 'Failed to fetch transaction.' });
    }
});

export default router;
