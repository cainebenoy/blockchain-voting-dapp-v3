require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { createClient } = require('@supabase/supabase-js');

const app = express();
const port = 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Connect to Supabase
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

// --- TEST ROUTE ---
// This will try to fetch the dummy voter "Rahul Kumar" we just created.
app.get('/test-connection', async (req, res) => {
    try {
        const { data, error } = await supabase
            .from('voters')
            .select('*')
            .eq('aadhaar_id', '1234-5678-9012'); // Looking for Rahul

        if (error) throw error;
        res.json({ status: 'success', message: 'Database connected!', data: data });
    } catch (err) {
        res.status(500).json({ status: 'error', error: err.message });
    }
});

// Start the server
app.listen(port, () => {
    console.log(`🚀 Backend Server is running on http://localhost:${port}`);
});