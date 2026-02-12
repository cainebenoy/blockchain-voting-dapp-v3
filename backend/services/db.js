import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

if (!process.env.SUPABASE_URL || !process.env.SUPABASE_KEY) {
    console.error("Missing Supabase credentials in environment variables.");
}

export const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);
