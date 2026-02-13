import express from 'express';
import { ethers } from 'ethers';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';
import crypto from 'crypto';
import { supabase } from '../services/db.js';
import { getWallet, getABI, ensureAuthorizedSignerFor, updateContractAddress, getContract } from '../services/ethereumService.js';
import { queueEnrollment, getEnrollmentStatus } from '../services/enrollmentService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendRoot = path.join(__dirname, '..');
console.log('[DEBUG] admin.js backendRoot calculated as:', backendRoot);

const router = express.Router();

// DEPLOY NEW ELECTION
router.post('/deploy-contract', async (req, res) => {
    console.log('[ADMIN] Deploying new VotingV2 contract...');
    const wallet = getWallet();
    const ABI = getABI();
    const abiPath = path.join(backendRoot, 'VotingV2.json');
    // Wait, backendRoot is 'backend/'. server.js was in backend/. VotingV2.json is in backend/.
    // Note: getABI() loaded it from there too. But for ContractFactory we need bytecode.
    // getABI() in ethereumService only loaded ABI. We need bytecode too.
    // I should probably export bytecode from ethereumService or re-read it.
    // Let's re-read it to be safe, or update service to export it.
    // Re-reading is fine.

    try {
        const contractJson = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
        const ContractFactory = new ethers.ContractFactory(ABI, contractJson.bytecode, wallet);
        const newContract = await ContractFactory.deploy();
        await newContract.waitForDeployment();

        const contractAddress = await newContract.getAddress();
        console.log(`[ADMIN] ✅ New contract deployed at: ${contractAddress}`);

        // Reset DB
        console.log('[ADMIN] Resetting voter voting status...');
        const { error: resetError } = await supabase
            .from('voters')
            .update({ has_voted: false })
            .neq('id', 0);

        if (resetError) {
            console.error('[ADMIN] ⚠️ Database reset failed:', resetError);
        }

        // Update .env
        console.log('[ADMIN] Updating .env file...');
        const envPath = path.join(backendRoot, '.env');
        let envContent = fs.readFileSync(envPath, 'utf8');

        envContent = envContent.replace(
            /VOTING_CONTRACT_ADDRESS="0x[a-fA-F0-9]{40}"/,
            `VOTING_CONTRACT_ADDRESS="${contractAddress}"`
        );

        fs.writeFileSync(envPath, envContent, 'utf8');

        // Update Runtime
        process.env.VOTING_CONTRACT_ADDRESS = contractAddress;
        updateContractAddress(contractAddress);

        // Authorize Signer
        console.log('[ADMIN] Authorizing server wallet as official signer...');
        const authz = await ensureAuthorizedSignerFor(contractAddress);

        // Schedule Restart
        if (process.env.AUTO_RESTART === 'true') {
            setTimeout(() => {
                console.log('[ADMIN] 🔄 Restarting backend service...');
                const candidates = ['votechain', 'votechain.service', 'votechain-backend.service'];
                (function tryNext(i) {
                    if (i >= candidates.length) return;
                    const svc = candidates[i];
                    exec(`sudo systemctl is-active --quiet ${svc} && sudo systemctl restart ${svc}`, (err) => {
                        if (err) tryNext(i + 1);
                        else console.log(`[ADMIN] ✅ Restarted ${svc}`);
                    });
                })(0);
            }, 2000);
        }

        res.json({
            status: 'success',
            message: 'New election deployed! Backend will restart in 2 seconds...',
            data: {
                contractAddress: contractAddress,
                network: 'Sepolia',
                deployer: wallet.address,
                votersReset: !resetError,
                envUpdated: true,
                signerAuthorized: !authz.error,
                autoRestart: true
            }
        });

    } catch (err) {
        console.error('[ADMIN] Contract deployment failed:', err);
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// ADD VOTER (Queue Enrollment)
router.post('/add-voter', async (req, res) => {
    const { aadhaar_id, name, constituency } = req.body;

    if (!aadhaar_id || !name) return res.status(400).json({ status: 'error', message: 'Missing fields.' });
    if (!/^\d{12}$/.test(aadhaar_id)) return res.status(400).json({ status: 'error', message: 'Invalid Aadhaar ID.' });

    try {
        const { data: lastVoter } = await supabase
            .from('voters')
            .select('fingerprint_id')
            .order('fingerprint_id', { ascending: false })
            .limit(1)
            .single();

        const nextId = (lastVoter?.fingerprint_id || 0) + 1;

        // Hash Aadhaar for privacy in enrollment requests table
        const salt = process.env.AADHAAR_SALT || 'default-salt';
        const aadhaar_hash = crypto.createHash('sha256').update(aadhaar_id + salt).digest('hex');

        const enrollment = await queueEnrollment({
            aadhaar_hash,
            name,
            constituency,
            target_id: nextId
        });

        console.log(`[REMOTE ENROLL] Queued ${name} -> ID #${nextId} (Request ID: ${enrollment.id})`);
        res.json({
            status: 'success',
            message: 'Waiting for Kiosk scan...',
            target_id: nextId,
            request_id: enrollment.id
        });

    } catch (err) {
        console.error('[REMOTE ENROLL] Init Error:', err);
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// ENROLLMENT STATUS
router.get('/enrollment-status', async (req, res) => {
    const { id } = req.query;
    const status = await getEnrollmentStatus(id);
    res.json(status);
});

// VOTER STATS (Turnout Base)
router.get('/voter-stats', async (req, res) => {
    try {
        const { count, error } = await supabase
            .from('voters')
            .select('*', { count: 'exact', head: true });

        if (error) throw error;

        res.json({ status: 'success', count });
    } catch (err) {
        console.error('[ADMIN] Failed to get voter stats:', err);
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// MANUAL ENROLLMENT BYPASS (Hardware Offline)
router.post('/enroll-manual-confirm', async (req, res) => {
    const { request_id, fingerprint_id } = req.body;
    if (!request_id) return res.status(400).json({ status: 'error', message: 'Missing request ID.' });

    try {
        const { data: pending, error: fetchErr } = await supabase
            .from('enrollment_requests')
            .select('*')
            .eq('id', request_id)
            .single();

        if (fetchErr || !pending) return res.status(404).json({ status: 'error', message: 'Request not found.' });
        if (pending.status === 'COMPLETED') return res.status(400).json({ status: 'error', message: 'Already completed.' });

        const targetFingerId = fingerprint_id || pending.target_id;

        // Save to voters table
        const { error: insertErr } = await supabase.from('voters').insert([{
            aadhaar_id: pending.aadhaar_hash,
            name: pending.name,
            constituency: pending.constituency,
            fingerprint_id: String(targetFingerId),
            has_voted: false
        }]);

        if (insertErr) throw insertErr;

        // Update enrollment status
        await supabase.from('enrollment_requests').update({ status: 'COMPLETED' }).eq('id', request_id);

        console.log(`[ADMIN BYPASS] ✅ Manually enrolled ${pending.name} as ID #${targetFingerId}`);
        res.json({ status: 'success', message: 'Manual enrollment completed.' });

    } catch (err) {
        console.error('[ADMIN BYPASS] Error:', err);
        res.status(500).json({ status: 'error', message: err.message });
    }
});

// --- ELECTION MANAGEMENT (Backend Proxy) ---

// ADD CANDIDATE
router.post('/add-candidate', async (req, res) => {
    const { name } = req.body;
    if (!name) return res.status(400).json({ status: 'error', message: 'Candidate name required.' });

    try {
        console.log(`[ADMIN] Adding candidate: ${name}`);
        const contract = getContract();
        if (!contract) throw new Error("Contract not connected.");

        // Use server wallet (owner)
        const tx = await contract.addCandidate(name);
        console.log(`[ADMIN] Tx sent: ${tx.hash}`);
        await tx.wait();
        console.log(`[ADMIN] Candidate ${name} added.`);

        res.json({ status: 'success', message: 'Candidate added successfully.', tx: tx.hash });
    } catch (e) {
        console.error('[ADMIN] Add Candidate Failed:', e);
        res.status(500).json({ status: 'error', message: e.message || "Blockchain transaction failed" });
    }
});

// START ELECTION
router.post('/start-election', async (req, res) => {
    try {
        console.log('[ADMIN] Starting election...');
        const contract = getContract();
        if (!contract) throw new Error("Contract not connected.");

        const tx = await contract.startElection();
        await tx.wait();

        console.log('[ADMIN] Election started.');
        res.json({ status: 'success', message: 'Election started.', tx: tx.hash });
    } catch (e) {
        console.error('[ADMIN] Start Election Failed:', e);
        res.status(500).json({ status: 'error', message: e.message });
    }
});

// END ELECTION
router.post('/end-election', async (req, res) => {
    try {
        console.log('[ADMIN] Ending election...');
        const contract = getContract();
        if (!contract) throw new Error("Contract not connected.");

        const tx = await contract.endElection();
        await tx.wait();

        console.log('[ADMIN] Election ended.');
        res.json({ status: 'success', message: 'Election ended.', tx: tx.hash });
    } catch (e) {
        console.error('[ADMIN] End Election Failed:', e);
        res.status(500).json({ status: 'error', message: e.message });
    }
});

export default router;
