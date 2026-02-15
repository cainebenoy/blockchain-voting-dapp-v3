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
        rpcUrl: process.env.SEPOLIA_RPC_URL,
        network: 'sepolia'
    });
});

// ACTIVE CONTRACT
router.get('/active-contract', (req, res) => {
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');

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

        try {
            if (contract) {
                votesOnChain = await contract.totalVotes();
                candidatesOnChain = await contract.totalCandidates();
            }
        } catch (contractError) {
            console.warn('[METRICS] Contract query failed:', contractError.message);
        }

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

// RECENT TRANSACTIONS (Alternative to Blockchain Query)
router.get('/recent-transactions', async (req, res) => {
    try {
        // Fetch raw last 100 receipts. If created_at is missing, we fetch all and reverse in memory.
        // Most DBs return in insertion order if no order is specified.
        const { data, error } = await supabase
            .from('receipts')
            .select('tx_hash');

        if (error) {
            console.error('[LEDGER] Supabase error:', error);
            throw error;
        }

        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, ngrok-skip-browser-warning');

        // Filter valid hashes and reverse to get "newest" first
        const validTxs = (data || [])
            .filter(r => r.tx_hash && r.tx_hash.length > 20 && !r.tx_hash.startsWith('PENDING'))
            .map(r => r.tx_hash)
            .reverse() // Reverse to approximate newest first
            .slice(0, 5);

        res.json({
            status: 'success',
            data: validTxs
        });
    } catch (e) {
        console.error('[LEDGER] Failed to fetch recent txs:', e);
        res.status(500).json({ status: 'error', message: 'Failed to fetch ledger' });
    }
});

export default router;
