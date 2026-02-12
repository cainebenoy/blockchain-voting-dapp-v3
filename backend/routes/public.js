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
    const contract = getContract();
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');

    res.json({
        status: 'ok',
        contractAddress: contract?.target || contract?.address || process.env.VOTING_CONTRACT_ADDRESS,
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
        const votesOnChain = contract ? await contract.totalVotes() : 0;
        const candidatesOnChain = contract ? await contract.totalCandidates() : 0;

        const { count: votedCount, error: votedError } = await supabase
            .from('voters')
            .select('*', { count: 'exact', head: true })
            .eq('has_voted', true);
        if (votedError) throw votedError;

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

export default router;
