import { test, expect } from '@playwright/test';

test.describe('Service Discovery', () => {
    test('should discover backend URL', async ({ page }) => {
        // We can check the console logs for the discovery message
        const logs: string[] = [];
        page.on('console', msg => logs.push(msg.text()));

        await page.goto('/index.html');
        // Discovery happens on load for most pages
        // results.html has explicit discovery logic
        await page.goto('/results.html');

        // Wait for discovery
        await page.waitForTimeout(3000);

        // Check if any log contains "Discovered Backend" or similar if running remotely
        // In local mode it should say "Running locally"
        const discoveryLog = logs.find(log => log.includes('Discovered Backend') || log.includes('locally'));
        expect(discoveryLog).toBeDefined();
    });
});
