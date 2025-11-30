// This script forwards deploy requests to the backend admin endpoint so the backend
// (which has the server private key) performs the contract deployment centrally.
import http from 'http';

function postJson(url: string, body: any, timeout = 60000): Promise<any> {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body || {});
    const parsed = new URL(url);
    const opts: any = {
      hostname: parsed.hostname,
      port: parsed.port || 80,
      path: parsed.pathname + (parsed.search || ''),
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    };
    const req = http.request(opts, (res) => {
      let resp = '';
      res.on('data', (chunk) => resp += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(resp)); } catch (e) { resolve(resp); }
      });
    });
    req.on('error', reject);
    req.setTimeout(timeout, () => {
      req.destroy(new Error('Request timeout'));
    });
    req.write(data);
    req.end();
  });
}

async function main() {
  console.log('➡️  Requesting backend to deploy new VotingV2 contract...');
  try {
    const json = await postJson('http://localhost:3000/api/admin/deploy-contract', {});
    console.log('✅ Backend deploy response:');
    console.log(JSON.stringify(json, null, 2));
  } catch (e) {
    console.error('❌ Failed to call backend deploy endpoint:', e && e.message ? e.message : e);
    process.exit(1);
  }
}

main();