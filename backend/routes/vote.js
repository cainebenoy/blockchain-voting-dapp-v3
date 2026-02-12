import express from 'express';
import rateLimit from 'express-rate-limit';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { supabase } from '../services/db.js';
import { getContract, getProvider, isContractDeployed } from '../services/ethereumService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendRoot = path.join(__dirname, '../..'); // Go up two levels to root backend? No, up one level to 'backend', then logs are in 'backend/logs'?
// server.js was in backend. logs were in backend/logs.
// This file is in backend/routes. So logs are in ../logs
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

        const { data: voter } = await supabase
            .from('voters')
            .select('has_voted')
            .eq('aadhaar_id', aadhaar_id)
            .single();

        if (voter?.has_voted) {
            return res.status(403).json({ status: 'error', message: 'Double voting detected!', data: null });
        }

        const contract = getContract();
        const addr = contract.target || contract.address; // ethers v6
        const deployed = await isContractDeployed(addr);
        if (!deployed) {
            return res.status(503).json({ status: 'error', message: 'Election contract not available yet.' });
        }

        // Hash Aadhaar ID for Privacy (SHA-256 -> bytes32)
        const voterHash = crypto.createHash('sha256').update(aadhaar_id).digest('hex');
        const voterHashBytes32 = '0x' + voterHash;

        const tx = await contract.vote(cidNum, voterHashBytes32);
        console.log("Transaction sent:", tx.hash);

        const receiptPromise = tx.wait(1);
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('RPC_TIMEOUT')), 60000)
        );

        try {
            await Promise.race([receiptPromise, timeoutPromise]);
            console.log("Transaction confirmed on-chain.");
        } catch (err) {
            if (err.message === 'RPC_TIMEOUT') {
                console.warn("⚠️ RPC timeout during tx.wait(), but transaction was sent.");
            } else {
                throw err;
            }
        }

        const { error: dbError } = await supabase
            .from('voters')
            .update({ has_voted: true })
            .eq('aadhaar_id', aadhaar_id);

        if (dbError) {
            console.error("Database update failed AFTER blockchain success:", aadhaar_id);
        }

        // Audit Log
        try {
            const aadhaarHash = crypto.createHash('sha256').update(aadhaar_id).digest('hex');
            const auditEntry = {
                ts: new Date().toISOString(),
                reqId: req.id, // req.id injected by middleware
                aadhaarHash,
                candidateId: cidNum,
                txHash: tx.hash,
            };
            fs.appendFile(path.join(logsDir, 'vote-audit.log'), JSON.stringify(auditEntry) + '\n', () => { });
        } catch { }

        let shortCode = null;
        try {
            shortCode = generateShortCode();
            await supabase.from('receipts').insert([{ code: shortCode, tx_hash: tx.hash }]);
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

// Verify Code (Short Code -> Tx Hash)
router.post('/verify-code', async (req, res) => {
    const code = (req.body && req.body.code ? String(req.body.code).toUpperCase() : '');
    try {
        const { data, error } = await supabase
            .from('receipts')
            .select('tx_hash')
            .eq('code', code)
            .single();
        if (error || !data) return res.status(404).json({ status: 'error', message: 'Invalid Code' });
        res.json({ status: 'success', tx_hash: data.tx_hash });
    } catch (_e) {
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
    } catch (e) {
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
    } catch (e) {
        res.status(500).json({ status: 'error', message: 'Failed to fetch transaction.' });
    }
});

export default router;
