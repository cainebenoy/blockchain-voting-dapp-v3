
import express from 'express';
import crypto from 'crypto';
import keccak256 from 'keccak256';
import { supabase } from '../services/db.js';
import { generateMerkleTree, getProof, getRoot } from '../utils/merkle.js';
import { getContract } from '../services/ethereumService.js';

const router = express.Router();

// GET MERKLE ROOT from on-chain contract (proxy to avoid browser CORS issues)
router.get('/root', async (req, res) => {
    try {
        const contract = getContract();
        if (!contract) return res.status(503).json({ status: 'error', message: 'Contract not initialized.' });

        // voterListRoot only exists on VotingV3
        if (!contract.voterListRoot) {
            return res.json({ status: 'ok', root: null, message: 'Contract is V2, root not supported.' });
        }

        const root = await contract.voterListRoot();
        res.json({ status: 'ok', root: root });
    } catch (e) {
        console.error('[AUDIT] Root fetch failed:', e.message);
        res.status(500).json({ status: 'error', message: e.message });
    }
});


// GET PROOF
router.post('/proof', async (req, res) => {
    const { aadhaar_id } = req.body;

    if (!aadhaar_id) return res.status(400).json({ status: 'error', message: 'Aadhaar ID required.' });

    try {
        // 1. Re-hash input (assuming frontend sends raw ID, or hashed? let's support raw)
        // Similar to vote.js, let's try to match what's in DB
        const salt = process.env.AADHAAR_SALT || 'default-salt';
        const aadhaar_hash = crypto.createHash('sha256').update(aadhaar_id + salt).digest('hex');

        // Check if voter exists
        // We need ALL voters to rebuild tree to get proof
        // Optimization: Cache tree? For now, rebuild is safer as list is small.

        const { data: voters } = await supabase
            .from('voters')
            .select('aadhaar_id');

        if (!voters || voters.length === 0) {
            return res.status(404).json({ status: 'error', message: 'Registry empty.' });
        }

        const ids = voters.map(v => v.aadhaar_id);
        const tree = generateMerkleTree(ids);
        const root = getRoot(tree);

        // Find leaf
        // We try both hash and raw just in case
        let leaf = aadhaar_hash;
        if (!ids.includes(leaf)) {
            // Maybe it was manual enroll and stored differently? 
            // Logic in admin.js suggests we use whatever is in DB
            if (ids.includes(aadhaar_id)) leaf = aadhaar_id;
            else return res.status(404).json({ status: 'error', message: 'Voter not found in registry.' });
        }

        const proof = getProof(tree, leaf);
        const proofHex = proof.map(p => '0x' + p.data.toString('hex'));

        // The actual leaf in the Merkle tree is keccak256(leaf_id_string) - a Buffer.
        // We must return this value to the frontend so it can reconstruct the path correctly.
        // merkle.js: hashVoterId(id) = keccak256(id) where keccak256 npm hashes UTF-8 bytes.
        const leafBuffer = keccak256(leaf);
        const leafHex = '0x' + leafBuffer.toString('hex');

        res.json({
            status: 'success',
            root: root,
            leaf: leafHex, // The actual keccak256'd leaf stored in the tree
            proof: proofHex
        });

    } catch (e) {
        console.error('[AUDIT] Proof generation failed:', e);
        res.status(500).json({ status: 'error', message: e.message });
    }
});

export default router;
