import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.join(__dirname, '../.env') });

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

async function checkVoters() {
    console.log("🔍 Fetching voters from Supabase...");
    const { data, error } = await supabase
        .from('voters')
        .select('*')
        .limit(5);

    if (error) {
        console.error("❌ Error fetching voters:", error.message);
        console.error("Detailed error:", error);
        return;
    }

    if (data && data.length > 0) {
        console.log("✅ Found voters:");
        data.forEach(v => {
            console.log(`- ${v.full_name} (Aadhaar: ${v.aadhaar_id}), Voted: ${v.has_voted}`);
        });
    } else {
        console.log("⚠️ No voters found in the 'voters' table.");
    }
}

checkVoters();
