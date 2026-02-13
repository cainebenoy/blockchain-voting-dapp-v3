import express from 'express';
import { ethers } from 'ethers';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';
import { supabase } from '../services/db.js';
import { getWallet, getABI, ensureAuthorizedSignerFor, updateContractAddress } from '../services/ethereumService.js';
import { queueEnrollment, getEnrollmentStatus } from '../services/enrollmentService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendRoot = path.join(__dirname, '../..');

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

        const enrollment = await queueEnrollment({ aadhaar_id, name, constituency, target_finger_id: nextId });

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

export default router;
