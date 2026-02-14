import express from 'express';
import { supabase } from '../services/db.js';
import { getContract, isContractDeployed } from '../services/ethereumService.js';

const router = express.Router();

// HEALTH CHECK
router.get('/health', (req, res) => {
    res.json({ status: 'ok', service: 'VoteChain Backend', time: new Date().toISOString() });
});

// CONFIG
router.get('/config', (req, res) => {
    res.json({
        status: 'ok',
        contractAddress: process.env.VOTING_CONTRACT_ADDRESS,
        rpcUrl: process.env.SEPOLIA_RPC_URL, // Should we expose this? Using Sepolia is public anyway.
        network: 'sepolia'
    });
});

// ACTIVE CONTRACT
router.get('/active-contract', (req, res) => {
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');

    // Always return the environment variable as the source of truth
    // The contract instance may be stale if the address was updated after initialization

    // Manual CORS Fallback
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, ngrok-skip-browser-warning');

    res.json({
        status: 'ok',
        contractAddress: process.env.VOTING_CONTRACT_ADDRESS,
        network: 'sepolia'
    });
});

// RESULTS
router.get('/results', async (req, res) => {
    try {
        const contract = getContract();
        if (!contract) return res.status(503).json({ status: 'error', message: 'Contract not initialized' });

        const addr = contract.target || contract.address;
        const deployed = await isContractDeployed(addr);
        if (!deployed) {
            return res.status(503).json({ status: 'error', message: 'Election contract not deployed.' });
        }

        const active = await contract.electionActive();
        const vCount = await contract.totalVotes();
        const cCount = await contract.totalCandidates();
        const candidates = await contract.getAllCandidates();

        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, ngrok-skip-browser-warning');
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

// METRICS
router.get('/metrics', async (_req, res) => {
    try {
        const contract = getContract();
        let votesOnChain = 0;
        let candidatesOnChain = 0;

        // Try to get blockchain data, but don't fail if contract is unavailable
        try {
            if (contract) {
                votesOnChain = await contract.totalVotes();
                candidatesOnChain = await contract.totalCandidates();
            }
        } catch (contractError) {
            console.warn('[METRICS] Contract query failed:', contractError.message);
        }

        // Try to get Supabase data with graceful fallback
        let votedCount = 0;
        let totalCount = 0;

        try {
            const { count: voted, error: votedError } = await supabase
                .from('voters')
                .select('*', { count: 'exact', head: true })
                .eq('has_voted', true);

            if (votedError) {
                console.warn('[METRICS] Supabase voted count error:', votedError.message);
            } else {
                votedCount = voted ?? 0;
            }
        } catch (e) {
            console.warn('[METRICS] Supabase voted query failed:', e.message);
        }

        try {
            const { count: total, error: totalError } = await supabase
                .from('voters')
                .select('*', { count: 'exact', head: true });

            if (totalError) {
                console.warn('[METRICS] Supabase total count error:', totalError.message);
            } else {
                totalCount = total ?? 0;
            }
        } catch (e) {
            console.warn('[METRICS] Supabase total query failed:', e.message);
        }

        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, ngrok-skip-browser-warning');
        res.json({
            status: 'success',
            message: 'Metrics ready',
            data: {
                totalVotesOnChain: Number(votesOnChain),
                totalCandidatesOnChain: Number(candidatesOnChain),
                votersMarkedVoted: votedCount,
                totalRegisteredVoters: totalCount,
            },
        });
    } catch (e) {
        console.error('[METRICS] Fatal error:', e);
        res.status(500).json({ status: 'error', message: e.message || 'Metrics failed', data: null });
    }
});

export default router;
