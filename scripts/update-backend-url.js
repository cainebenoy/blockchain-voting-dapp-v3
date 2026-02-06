// Usage: node scripts/update-backend-url.js <NEW_TUNNEL_URL>
// Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in env or .env

import fetch from 'node-fetch';
import dotenv from 'dotenv';
dotenv.config();

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

const newUrl = process.argv[2];
if (!newUrl) {
  console.error('Usage: node scripts/update-backend-url.js <NEW_TUNNEL_URL>');
  process.exit(1);
}
if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in env');
  process.exit(1);
}

async function updateBackendUrl() {
  const endpoint = `${SUPABASE_URL}/rest/v1/system_config?key=eq.backend_url`;
  const res = await fetch(endpoint, {
    method: 'PATCH',
    headers: {
      'apikey': SUPABASE_SERVICE_ROLE_KEY,
      'Authorization': `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation'
    },
    body: JSON.stringify({ value: newUrl })
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to update: ${res.status} ${text}`);
  }
  const data = await res.json();
  console.log('Updated backend_url:', data);
}

updateBackendUrl().catch(e => {
  console.error(e);
  process.exit(1);
});
