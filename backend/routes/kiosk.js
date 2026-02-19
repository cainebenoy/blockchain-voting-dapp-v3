import express from 'express';
import { supabase } from '../services/db.js';
import { getEnrollmentStatus, setEnrollmentStatus, getPendingEnrollment } from '../services/enrollmentService.js';

const router = express.Router();

// Poll Commands & Heartbeat
router.all('/poll-commands', async (req, res) => {
    try {
        const telemetry = req.method === 'POST' ? req.body : null;
        if (telemetry) {
            // Log telemetry (In production, this could go to a 'kiosk_telemetry' table)
            console.log(`[KIOSK HEARTBEAT] Status: ${telemetry.status}, ID: ${telemetry.kiosk_id}, Uptime: ${telemetry.uptime}s`);

            // Optionally update system_config with last seen
            await supabase.from('system_config').upsert({
                key: 'kiosk_last_pulse',
                value: new Date().toISOString()
            }, { onConflict: 'key' });
        }

        // 1. Check for system-level commands (like WIPE)
        const { data: config } = await supabase
            .from('system_config')
            .select('value')
            .eq('key', 'kiosk_pending_command')
            .maybeSingle();

        if (config && config.value === 'WIPE') {
            console.log('[KIOSK LOOP] Found WIPE command. Sending to device...');

            // Consume the command (delete or set to NONE) so it doesn't loop
            await supabase.from('system_config').delete().eq('key', 'kiosk_pending_command');

            return res.json({ command: 'WIPE' });
        }

        const pending = await getEnrollmentStatus();
        if (pending && pending.status === 'WAITING_FOR_KIOSK') {
            console.log(`[REMOTE ENROLL] Kiosk polled, sending command for ${pending.name}...`);
            res.json({ command: 'ENROLL', ...pending });
        } else {
            res.json({ command: 'NONE' });
        }
    } catch (e) {
        console.error("Poll/Heartbeat Error:", e);
        res.status(500).json({ command: 'NONE', error: e.message });
    }
});

// Complete Enrollment
router.post('/enrollment-complete', async (req, res) => {
    console.log('[REMOTE ENROLL] Received completion report:', req.body);
    const pending = await getPendingEnrollment();
    if (!pending) {
        console.warn('[REMOTE ENROLL] No pending enrollment found for report.');
        return res.status(400).json({ status: 'error', message: 'No active enrollment request.' });
    }

    const { success, fingerprint_id } = req.body;

    if (success) {
        // Save to DB
        const { error } = await supabase.from('voters').insert([{
            aadhaar_id: pending.aadhaar_hash,
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
