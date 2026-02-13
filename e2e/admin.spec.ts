import { test, expect } from '@playwright/test';

test.describe('Admin Flow', () => {
    const ADMIN_SECRET = 'test-secret'; // Should match what's in the test env

    test.beforeEach(async ({ page }) => {
        await page.goto('/admin.html');
        // Handle admin auth if overlay is visible
        const overlay = page.locator('#adminAuthOverlay');
        if (await overlay.isVisible()) {
            await page.fill('#adminSecretInput', ADMIN_SECRET);
            await page.click('button:has-text("Grant Access")');
            await expect(overlay).toBeHidden();
        }
    });

    test('should load admin page and show system status', async ({ page }) => {
        await expect(page).toHaveTitle(/Admin Console/);

        // Check health indicators
        const backendDot = page.locator('#backendDot');
        await expect(backendDot).toHaveClass(/bg-online/);
    });

    test('should add a new voter', async ({ page }) => {
        const aadhaar = '123456789012';
        const name = 'E2E Test Voter';

        await page.fill('#voterAadhaar', aadhaar);
        await page.fill('#voterName', name);
        await page.click('#btnEnroll');

        // Resilience: wait for status transition using toPass
        await expect(async () => {
            const statusText = page.locator('#enrollmentStatusText');
            await expect(statusText).toContainText(/Scanning Finger/i);
        }).toPass({ timeout: 5000 });
    });

    test('should attempt deploy new election', async ({ page, request }) => {
        // We might want to mock the backend response for deployment to avoid gas usage in E2E
        // but the prompt suggests a realistic environment. 
        // For now, let's verify the UI trigger.

        // Intercept deployment to avoid actual gas cost if necessary, 
        // or just verify the confirmation dialog.
        page.on('dialog', async dialog => {
            expect(dialog.message()).toContain('Deploy fresh contract');
            await dialog.accept();
        });

        await page.click('#btnDeploy');

        // Since deployment takes time, we look for the toast
        const toast = page.locator('#toast-container');
        await expect(toast).toContainText(/Deploying/i);
    });
});
