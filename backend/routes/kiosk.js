import express from 'express';
import { supabase } from '../services/db.js';
import { getEnrollmentStatus, setEnrollmentStatus, getPendingEnrollment } from '../services/enrollmentService.js';

const router = express.Router();

// Poll Commands
router.get('/poll-commands', async (req, res) => {
    try {
        const pending = await getEnrollmentStatus();
        if (pending && pending.status === 'WAITING_FOR_KIOSK') {
            console.log(`[REMOTE ENROLL] Kiosk polled, sending command for ${pending.name}...`);
            res.json({ command: 'ENROLL', ...pending });
        } else {
            res.json({ command: 'NONE' });
        }
    } catch (e) {
        console.error("Poll Error:", e);
        res.status(500).json({ command: 'NONE', error: e.message });
    }
});

// Complete Enrollment
router.post('/enrollment-complete', async (req, res) => {
    const pending = await getPendingEnrollment();
    if (!pending) {
        return res.status(400).json({ status: 'error', message: 'No active enrollment request.' });
    }

    const { success, fingerprint_id } = req.body;

    if (success) {
        // Save to DB
        const { error } = await supabase.from('voters').insert([{
            aadhaar_id: pending.aadhaar_id,
            name: pending.name,
            constituency: pending.constituency,
            fingerprint_id: fingerprint_id,
            has_voted: false
        }]);

        if (error) {
            console.error('[REMOTE ENROLL] DB Save Error:', error);
            await setEnrollmentStatus(pending.id, 'FAILED', 'Database save failed');
            return res.status(500).json({ status: 'error', message: 'Database save failed' });
        }

        console.log(`[REMOTE ENROLL] ✅ Success! Saved ${pending.name} as ID #${fingerprint_id}`);
        await setEnrollmentStatus(pending.id, 'COMPLETED');

        res.json({ status: 'success', message: 'Voter enrolled successfully.' });
    } else {
        console.log('[REMOTE ENROLL] ❌ Kiosk reported failure.');
        await setEnrollmentStatus(pending.id, 'FAILED', 'Fingerprint scan failed');
        res.json({ status: 'received', message: 'Enrollment failed, state updated.' });
    }
});

export default router;
