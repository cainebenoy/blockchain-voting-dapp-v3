import { test, expect } from '@playwright/test';
import crypto from 'crypto';

test.describe('End-to-End Voting Flow', () => {
    const ADMIN_SECRET = 'test-secret'; // Default for test env if not set
    const SERVER_PRIVATE_KEY = process.env.SERVER_PRIVATE_KEY || '0x5c393fa306c6b29ac29476b6033f270f9cee7e0e7403a5f983570e82c6da2f98';
    const TEST_AADHAAR = '999988887777';
    const TEST_NAME = 'E2E Voter Alpha';

    test('should progress from admin enrollment to vote verification', async ({ page, request }) => {
        // 1. Admin Adds Voter
        await page.goto('/admin.html');

        // Handle Auth
        const overlay = page.locator('#adminAuthOverlay');
        if (await overlay.isVisible()) {
            await page.fill('#adminSecretInput', ADMIN_SECRET);
            await page.click('button:has-text("Grant Access")');
        }

        await page.fill('#voterAadhaar', TEST_AADHAAR);
        await page.fill('#voterName', TEST_NAME);
        await page.click('#btnEnroll');

        // Verify waiting state
        await expect(page.locator('#enrollmentStatusText')).toContainText(/Scanning Finger/i);

        // 2. Mock Kiosk Completion (Enrollment)
        const enrollComplete = await request.post('/api/kiosk/enrollment-complete', {
            data: {
                success: true,
                fingerprint_id: 101 // Dummy ID
            }
        });
        expect(enrollComplete.ok()).toBeTruthy();

        // Admin UI should reflect success
        await expect(page.locator('#enrollmentStatusText')).toContainText(/Success/i);

        // 3. Cast Vote (Mocking Kiosk logic)
        // Kiosk calculates session_token using its knowledge of the shared secret (SERVER_PRIVATE_KEY)
        const sessionToken = crypto.createHmac('sha256', SERVER_PRIVATE_KEY)
            .update(TEST_AADHAAR)
            .digest('hex');

        const kioskNonce = '0x' + crypto.randomBytes(32).toString('hex');

        const voteRes = await request.post('/api/vote', {
            data: {
                aadhaar_id: TEST_AADHAAR,
                candidate_id: 1,
                session_token: sessionToken,
                kiosk_nonce: kioskNonce
            }
        });
        expect(voteRes.ok()).toBeTruthy();
        const voteData = await voteRes.json();
        const receiptCode = voteData.data.receipt_code;
        expect(receiptCode).toBeDefined();

        // 4. Verify Receipt on verify.html
        await page.goto('/verify.html');
        await page.fill('#txInput', receiptCode);
        await page.click('#btnVerify');

        // Check for success display
        await expect(page.locator('#resultCard')).toBeVisible();
        await expect(page.locator('#blockNum')).not.toContainText('--');

        // Optionally check direct hash lookup
        const txHash = page.locator('#etherscanLink');
        const href = await txHash.getAttribute('href');
        expect(href).toContain('0x');
    });
});
