import { expect, test } from "@playwright/test";

test.describe("Khive Dashboard", () => {
  test("homepage loads successfully", async ({ page }) => {
    await page.goto("/");

    // Wait for the page to load
    await expect(page).toHaveTitle(/Create Next App/);

    // Check for Next.js logo
    await expect(page.locator('img[alt="Next.js logo"]')).toBeVisible();
  });

  test("navigation works correctly", async ({ page }) => {
    await page.goto("/");

    // Test responsive design
    await page.setViewportSize({ width: 375, height: 667 }); // Mobile
    await expect(page.locator("main")).toBeVisible();

    await page.setViewportSize({ width: 1200, height: 800 }); // Desktop
    await expect(page.locator("main")).toBeVisible();
  });

  test("performance metrics", async ({ page }) => {
    await page.goto("/");

    // Wait for page to fully load
    await page.waitForLoadState("networkidle");

    // Check for performance - inspired by rust-performance principles
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType(
        "navigation",
      )[0] as PerformanceNavigationTiming;
      return {
        loadTime: navigation.loadEventEnd - navigation.loadEventStart,
        domContentLoaded: navigation.domContentLoadedEventEnd -
          navigation.domContentLoadedEventStart,
        firstPaint: performance.getEntriesByName("first-paint")[0]?.startTime ||
          0,
      };
    });

    // Assert reasonable performance thresholds
    expect(performanceMetrics.loadTime).toBeLessThan(3000); // 3 seconds max
    expect(performanceMetrics.domContentLoaded).toBeLessThan(2000); // 2 seconds max
  });
});
