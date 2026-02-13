import { test, expect } from '@playwright/test';

test.describe('Verification Flow', () => {
    test('should load verify page', async ({ page }) => {
        await page.goto('/verify.html');
        await expect(page).toHaveTitle(/Verify Ballot/);
    });

    test('should handle invalid receipt code', async ({ page }) => {
        await page.goto('/verify.html');
        await page.fill('#txInput', 'INVALID-CODE');
        await page.click('#btnVerify');

        await expect(async () => {
            const errorMsg = page.locator('#errorMsg');
            await expect(errorMsg).toBeVisible();
            await expect(page.locator('#errorText')).toContainText(/Invalid Code/i);
        }).toPass({ timeout: 5000 });
    });
});
