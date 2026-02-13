import dotenv from 'dotenv';
import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

// Services
import { initEthereum, ensureAuthorizedSignerFor } from './services/ethereumService.js';

// Routes
import authRoutes from './routes/auth.js';
import voteRoutes from './routes/vote.js';
import adminRoutes from './routes/admin.js';
import kioskRoutes from './routes/kiosk.js';
import publicRoutes from './routes/public.js';

// Initialize Env
dotenv.config();

// Fix for __dirname in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Validate Env
const requiredEnv = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'SEPOLIA_RPC_URL',
    'SERVER_PRIVATE_KEY',
    'VOTING_CONTRACT_ADDRESS',
];

const missing = requiredEnv.filter((key) => !process.env[key] || String(process.env[key]).trim() === '');
if (missing.length) {
    console.error('\u26a0\ufe0f Missing required environment variables:', missing.join(', '));
    process.exit(1);
}

// Initialize App
const app = express();
const port = 3000;

app.use(cors());
app.use(express.json());

// Auth Middleware
const adminAuth = (req, res, next) => {
    const secret = req.headers['x-admin-secret'];
    if (!process.env.ADMIN_SECRET || secret !== process.env.ADMIN_SECRET) {
        return res.status(401).json({ status: 'error', message: 'Unauthorized Admin Access' });
    }
    next();
};

// Logger Middleware
app.use((req, res, next) => {
    const id = crypto.randomUUID();
    // @ts-ignore
    req.id = id;
    res.setHeader('X-Request-Id', id);
    const start = Date.now();
    res.on('finish', () => {
        const entry = {
            reqId: id,
            method: req.method,
            path: req.path,
            status: res.statusCode,
            durationMs: Date.now() - start,
        };
        console.log(JSON.stringify(entry));
    });
    next();
});

// Initialize Ethereum Service
initEthereum();

// Mount Routes
app.use('/api/voter', authRoutes);
app.use('/api', voteRoutes);
app.use('/api/admin', adminAuth, adminRoutes); // Protected admin routes
app.use('/api/kiosk', kioskRoutes);
app.use('/api', publicRoutes);

// Frontend Serving
const frontendPath = path.join(__dirname, '..');
app.use(express.static(frontendPath));

app.get(['/results', '/results.html'], (req, res) => {
    res.sendFile(path.join(frontendPath, 'results.html'));
});

// SPA Fallback
app.use((req, res, next) => {
    if (req.path.startsWith('/api')) return next();
    if (req.method === 'GET') {
        if (req.path === '/results' || req.path === '/results.html') {
            return res.sendFile(path.join(frontendPath, 'results.html'));
        }
        return res.sendFile(path.join(frontendPath, 'index.html'));
    }
    next();
});

// Startup Checks
(async () => {
    const addr = process.env.VOTING_CONTRACT_ADDRESS;
    console.log('[AUTHZ] Startup check for contract', addr);
    await ensureAuthorizedSignerFor(addr);
})();

// Start Server
app.listen(port, () => {
    console.log(`🤖 Election Official (Backend) is listening on port ${port}`);
});