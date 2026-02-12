import express from 'express';
import rateLimit from 'express-rate-limit';
import { supabase } from '../services/db.js';

const router = express.Router();

const RL_CHECKIN_MAX = parseInt(process.env.RL_CHECKIN_MAX || '30', 10);
const checkInLimiter = rateLimit({ windowMs: 60 * 1000, max: RL_CHECKIN_MAX });

// Check-in
router.post('/check-in', checkInLimiter, async (req, res) => {
    const { aadhaar_id } = req.body || {};
    if (typeof aadhaar_id !== 'string' || aadhaar_id.trim().length !== 12 || !/^\d{12}$/.test(aadhaar_id)) {
        return res.status(400).json({ status: 'error', message: 'Invalid Aadhaar ID format.' });
    }
    try {
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

export default router;
