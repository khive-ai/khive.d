import { Page, Locator } from '@playwright/test';
import path from 'path';
import fs from 'fs/promises';

/**
 * Screenshot Manager for KHIVE E2E Tests
 * Handles visual documentation and regression testing with consistent naming
 */
export class ScreenshotManager {
  private page: Page;
  private baseDir: string;
  private testName: string = '';
  
  constructor(page: Page, baseDir: string = 'e2e/screenshots') {
    this.page = page;
    this.baseDir = baseDir;
    this.ensureDirectoryExists();
  }

  /**
   * Set current test context for screenshot naming
   */
  setTestContext(testName: string): void {
    this.testName = testName.replace(/[^a-zA-Z0-9-_]/g, '-').toLowerCase();
  }

  /**
   * Take a full page screenshot
   */
  async captureFullPage(name: string, options?: {
    clip?: { x: number; y: number; width: number; height: number };
    fullPage?: boolean;
    threshold?: number;
  }): Promise<string> {
    const filename = this.generateFilename(name, 'full-page');
    const filepath = path.join(this.baseDir, filename);
    
    await this.page.screenshot({
      path: filepath,
      fullPage: options?.fullPage ?? true,
      clip: options?.clip,
      animations: 'disabled', // Consistent screenshots
      caret: 'hide', // Hide text cursor
    });
    
    console.log(`📸 Screenshot captured: ${filename}`);
    return filepath;
  }

  /**
   * Take a screenshot of a specific element
   */
  async captureElement(
    selector: string | Locator, 
    name: string,
    options?: {
      padding?: number;
      threshold?: number;
    }
  ): Promise<string> {
    const filename = this.generateFilename(name, 'element');
    const filepath = path.join(this.baseDir, filename);
    
    const element = typeof selector === 'string' 
      ? this.page.locator(selector) 
      : selector;
    
    // Wait for element to be visible and stable
    await element.waitFor({ state: 'visible' });
    await this.page.waitForTimeout(500); // Allow animations to complete
    
    await element.screenshot({
      path: filepath,
      animations: 'disabled',
    });
    
    console.log(`📸 Element screenshot captured: ${filename}`);
    return filepath;
  }

  /**
   * Capture command palette state
   */
  async captureCommandPalette(name: string): Promise<string> {
    const filename = this.generateFilename(name, 'command-palette');
    const filepath = path.join(this.baseDir, filename);
    
    // Wait for command palette to be fully rendered
    await this.page.waitForSelector('[data-testid="command-palette"]', {
      state: 'visible',
      timeout: 10000
    });
    
    // Capture the command palette area
    const commandPalette = this.page.locator('[data-testid="command-palette"]');
    await commandPalette.screenshot({
      path: filepath,
      animations: 'disabled',
    });
    
    console.log(`📸 Command Palette screenshot: ${filename}`);
    return filepath;
  }

  /**
   * Capture terminal/CLI output
   */
  async captureTerminal(name: string): Promise<string> {
    const filename = this.generateFilename(name, 'terminal');
    const filepath = path.join(this.baseDir, filename);
    
    // Wait for terminal content to stabilize
    await this.page.waitForSelector('[data-testid="terminal-content"]', {
      state: 'visible',
      timeout: 10000
    });
    
    const terminal = this.page.locator('[data-testid="terminal-content"]');
    await terminal.screenshot({
      path: filepath,
      animations: 'disabled',
    });
    
    console.log(`📸 Terminal screenshot: ${filename}`);
    return filepath;
  }

  /**
   * Capture orchestration tree visualization
   */
  async captureOrchestrationTree(name: string): Promise<string> {
    const filename = this.generateFilename(name, 'orchestration');
    const filepath = path.join(this.baseDir, filename);
    
    // Wait for orchestration tree to load
    await this.page.waitForSelector('[data-testid="orchestration-tree"]', {
      state: 'visible',
      timeout: 10000
    });
    
    // Allow time for animations and data loading
    await this.page.waitForTimeout(2000);
    
    const orchestrationTree = this.page.locator('[data-testid="orchestration-tree"]');
    await orchestrationTree.screenshot({
      path: filepath,
      animations: 'disabled',
    });
    
    console.log(`📸 Orchestration Tree screenshot: ${filename}`);
    return filepath;
  }

  /**
   * Capture workflow progression with before/after comparison
   */
  async captureWorkflowProgression(
    beforeName: string,
    afterName: string,
    action: () => Promise<void>
  ): Promise<{ before: string; after: string }> {
    // Capture before state
    const beforePath = await this.captureFullPage(beforeName);
    
    // Perform action
    await action();
    
    // Wait for changes to settle
    await this.page.waitForTimeout(1000);
    
    // Capture after state
    const afterPath = await this.captureFullPage(afterName);
    
    console.log(`📸 Workflow progression captured: ${beforeName} → ${afterName}`);
    
    return {
      before: beforePath,
      after: afterPath
    };
  }

  /**
   * Create a visual test comparison
   */
  async compareWithBaseline(
    name: string,
    threshold: number = 0.2
  ): Promise<void> {
    const baselinePath = path.join(this.baseDir, 'baselines', this.generateFilename(name, 'baseline'));
    const currentPath = await this.captureFullPage(name + '-current');
    
    // For now, just capture - actual comparison would be handled by Playwright's built-in
    console.log(`📸 Baseline comparison setup for: ${name}`);
    console.log(`   Baseline: ${baselinePath}`);
    console.log(`   Current: ${currentPath}`);
  }

  /**
   * Generate documentation screenshots with annotations
   */
  async captureForDocumentation(
    name: string,
    annotations?: Array<{
      x: number;
      y: number;
      width: number;
      height: number;
      label: string;
    }>
  ): Promise<string> {
    const filename = this.generateFilename(name, 'docs');
    const filepath = path.join(this.baseDir, 'documentation', filename);
    
    // Ensure documentation directory exists
    await this.ensureDirectoryExists('documentation');
    
    // If annotations are provided, add visual indicators
    if (annotations) {
      for (const annotation of annotations) {
        await this.page.evaluate((ann) => {
          const overlay = document.createElement('div');
          overlay.style.position = 'fixed';
          overlay.style.left = ann.x + 'px';
          overlay.style.top = ann.y + 'px';
          overlay.style.width = ann.width + 'px';
          overlay.style.height = ann.height + 'px';
          overlay.style.border = '2px solid red';
          overlay.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
          overlay.style.zIndex = '9999';
          overlay.style.pointerEvents = 'none';
          overlay.setAttribute('data-test-annotation', ann.label);
          
          // Add label
          const label = document.createElement('div');
          label.textContent = ann.label;
          label.style.position = 'absolute';
          label.style.top = '-20px';
          label.style.left = '0';
          label.style.fontSize = '12px';
          label.style.backgroundColor = 'red';
          label.style.color = 'white';
          label.style.padding = '2px 4px';
          overlay.appendChild(label);
          
          document.body.appendChild(overlay);
        }, annotation);
      }
      
      // Wait for annotations to render
      await this.page.waitForTimeout(500);
    }
    
    await this.page.screenshot({
      path: filepath,
      fullPage: true,
      animations: 'disabled',
    });
    
    // Clean up annotations
    if (annotations) {
      await this.page.evaluate(() => {
        const overlays = document.querySelectorAll('[data-test-annotation]');
        overlays.forEach(overlay => overlay.remove());
      });
    }
    
    console.log(`📚 Documentation screenshot: ${filename}`);
    return filepath;
  }

  /**
   * Generate filename with consistent naming convention
   */
  private generateFilename(name: string, type: string): string {
    const sanitizedName = name.replace(/[^a-zA-Z0-9-_]/g, '-').toLowerCase();
    const timestamp = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
    const testPrefix = this.testName ? `${this.testName}-` : '';
    
    return `${testPrefix}${type}-${sanitizedName}-${timestamp}.png`;
  }

  /**
   * Ensure screenshot directory exists
   */
  private async ensureDirectoryExists(subDir?: string): Promise<void> {
    const targetDir = subDir ? path.join(this.baseDir, subDir) : this.baseDir;
    
    try {
      await fs.access(targetDir);
    } catch {
      await fs.mkdir(targetDir, { recursive: true });
      console.log(`📁 Created screenshot directory: ${targetDir}`);
    }
  }

  /**
   * Clean up old screenshots (older than specified days)
   */
  async cleanupOldScreenshots(daysOld: number = 30): Promise<void> {
    console.log(`🧹 Cleaning up screenshots older than ${daysOld} days`);
    
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysOld);
    
    try {
      const files = await fs.readdir(this.baseDir);
      
      for (const file of files) {
        const filepath = path.join(this.baseDir, file);
        const stat = await fs.stat(filepath);
        
        if (stat.mtime < cutoffDate) {
          await fs.unlink(filepath);
          console.log(`🗑️  Deleted old screenshot: ${file}`);
        }
      }
    } catch (error) {
      console.warn('⚠️  Error cleaning up screenshots:', error);
    }
  }

  /**
   * Get all screenshots for a test
   */
  async getTestScreenshots(): Promise<string[]> {
    if (!this.testName) return [];
    
    try {
      const files = await fs.readdir(this.baseDir);
      return files.filter(file => file.startsWith(this.testName));
    } catch {
      return [];
    }
  }
}