
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';


// Load env
const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '../backend/.env') });

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const BACKEND_URL = 'http://localhost:3000';

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTest() {
    console.log("🚀 Starting Enrollment Flow Test...");

    // 1. Clean up previous test data
    console.log("🧹 Cleaning up...");
    await supabase.from('enrollment_requests').delete().eq('name', 'TEST_USER_FLOW');
    await supabase.from('voters').delete().eq('name', 'TEST_USER_FLOW');

    // 2. Admin: Queue Enrollment
    console.log("Admin: Requesting enrollment...");
    try {
        const res = await axios.post(`${BACKEND_URL}/api/admin/add-voter`, {
            aadhaar_id: "999988887777",
            name: "TEST_USER_FLOW",
            constituency: "Testville"
        }, { headers: { 'x-admin-secret': process.env.ADMIN_SECRET } });
        console.log("✅ Admin Request Success:", res.data);
    } catch (e) {
        console.error("❌ Admin Request Failed:", e.response?.data || e.message);
        return;
    }

    // 3. Kiosk: Poll for commands
    console.log("Kiosk: Polling for commands...");
    let command = null;
    let attempts = 0;
    while (!command && attempts < 5) {
        try {
            const res = await axios.post(`${BACKEND_URL}/api/kiosk/poll-commands`, {
                kiosk_id: "TEST_KIOSK",
                status: "IDLE",
                uptime: 100
            });
            if (res.data.command === 'ENROLL') {
                command = res.data;
                console.log("✅ Kiosk Received Command:", command);
            } else {
                console.log("... waiting for command ...");
                await sleep(1000);
            }
        } catch (e) {
            console.error("❌ Poll Failed:", e.message);
        }
        attempts++;
    }

    if (!command) {
        console.error("❌ Failed to receive ENROLL command.");
        return;
    }

    if (!command.target_id && !command.target_finger_id) {
        console.error("❌ Command missing target_id:", command);
        return;
    }

    const targetId = command.target_id || command.target_finger_id;

    // 4. Simulate Processing Time
    console.log("Kiosk: Processing enrollment (simulated)...");
    await sleep(2000);

    // 5. Kiosk: Report Success
    console.log("Kiosk: Reporting success...");
    try {
        const res = await axios.post(`${BACKEND_URL}/api/kiosk/enrollment-complete`, {
            success: true,
            fingerprint_id: targetId
        });
        console.log("✅ Report Success:", res.data);
    } catch (e) {
        console.error("❌ Report Failed:", e.response?.data || e.message);
        return;
    }

    // 6. Verify DB State
    console.log("Verifying DB State...");
    await sleep(1000);
    const { data: request } = await supabase.from('enrollment_requests').select('*').eq('name', 'TEST_USER_FLOW').single();
    const { data: voter } = await supabase.from('voters').select('*').eq('name', 'TEST_USER_FLOW').single();

    console.log("Enrollment Request Status:", request.status);
    console.log("Voter Record:", voter ? "CHECKED_IN" : "MISSING");

    if (request.status === 'COMPLETED' && voter) {
        console.log("🎉 TEST PASSED: Flow is correct.");
    } else {
        console.error("❌ TEST FAILED: State mismatch.");
    }
}

runTest();
