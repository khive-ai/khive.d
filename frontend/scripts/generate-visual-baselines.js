#!/usr/bin/env node

/**
 * Visual Baseline Generation Script
 * 
 * This script helps generate and organize baseline screenshots for
 * Ocean's Agentic ERP Command Center visual testing suite.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  red: '\x1b[31m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${COLORS[color]}${message}${COLORS.reset}`);
}

function header(message) {
  log(`\n${'='.repeat(60)}`, 'cyan');
  log(`  ${message}`, 'bright');
  log(`${'='.repeat(60)}`, 'cyan');
}

function section(message) {
  log(`\n${'-'.repeat(40)}`, 'blue');
  log(`  ${message}`, 'blue');
  log(`${'-'.repeat(40)}`, 'blue');
}

function success(message) {
  log(`✅ ${message}`, 'green');
}

function warning(message) {
  log(`⚠️  ${message}`, 'yellow');
}

function error(message) {
  log(`❌ ${message}`, 'red');
}

function info(message) {
  log(`ℹ️  ${message}`, 'cyan');
}

// Check if we're in the right directory
function validateEnvironment() {
  section('Environment Validation');
  
  if (!fs.existsSync('package.json')) {
    error('package.json not found. Please run this script from the frontend directory.');
    process.exit(1);
  }
  
  if (!fs.existsSync('playwright.config.ts')) {
    error('playwright.config.ts not found. Please ensure Playwright is configured.');
    process.exit(1);
  }
  
  if (!fs.existsSync('e2e')) {
    error('e2e directory not found. Please ensure test files are present.');
    process.exit(1);
  }
  
  success('Environment validation complete');
}

// Install dependencies if needed
function ensureDependencies() {
  section('Dependency Check');
  
  try {
    execSync('npx playwright --version', { stdio: 'pipe' });
    success('Playwright CLI available');
  } catch (err) {
    warning('Installing Playwright...');
    execSync('npm install @playwright/test', { stdio: 'inherit' });
  }
  
  try {
    execSync('npx playwright install --with-deps', { stdio: 'inherit' });
    success('Browser dependencies installed');
  } catch (err) {
    error('Failed to install browser dependencies');
    process.exit(1);
  }
}

// Create directory structure
function createDirectories() {
  section('Directory Structure Setup');
  
  const directories = [
    'screenshots',
    'screenshots/baseline',
    'screenshots/current',
    'screenshots/diff',
    'screenshots/browsers',
    'screenshots/browsers/chrome',
    'screenshots/browsers/firefox',
    'screenshots/browsers/safari',
    'screenshots/viewports',
    'screenshots/viewports/desktop',
    'screenshots/viewports/laptop',
    'screenshots/viewports/ultrawide',
    'screenshots/viewports/tablet',
    'screenshots/viewports/mobile',
    'test-results',
    'test-results/html-report'
  ];
  
  directories.forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      success(`Created directory: ${dir}`);
    } else {
      info(`Directory exists: ${dir}`);
    }
  });
}

// Generate baseline screenshots
function generateBaselines() {
  section('Baseline Screenshot Generation');
  
  info('Starting baseline screenshot generation...');
  info('This will take several minutes depending on your system performance.');
  
  try {
    // Start development server in background
    log('Starting development server...', 'dim');
    const devServerProcess = execSync('npm run dev > /dev/null 2>&1 &', { stdio: 'pipe' });
    
    // Wait for server to be ready
    log('Waiting for development server to be ready...', 'dim');
    let attempts = 0;
    const maxAttempts = 30;
    
    while (attempts < maxAttempts) {
      try {
        const response = execSync('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000', { 
          stdio: 'pipe',
          timeout: 2000 
        }).toString();
        
        if (response === '200') {
          success('Development server is ready');
          break;
        }
      } catch (err) {
        // Server not ready yet
      }
      
      attempts++;
      if (attempts >= maxAttempts) {
        error('Development server failed to start within timeout');
        process.exit(1);
      }
      
      // Wait 2 seconds before next attempt
      execSync('sleep 2');
    }
    
    // Generate screenshots using Playwright
    log('Generating visual regression baselines...', 'dim');
    execSync('npx playwright test --update-snapshots', { 
      stdio: 'inherit',
      env: { ...process.env, CI: 'false' }
    });
    
    success('Baseline screenshots generated successfully');
    
  } catch (err) {
    error(`Failed to generate baselines: ${err.message}`);
    process.exit(1);
  } finally {
    // Clean up development server
    try {
      execSync('pkill -f "npm run dev" || true', { stdio: 'pipe' });
      log('Development server stopped', 'dim');
    } catch (err) {
      // Ignore cleanup errors
    }
  }
}

// Generate test report
function generateReport() {
  section('Test Report Generation');
  
  try {
    execSync('npx playwright test --reporter=html', { stdio: 'inherit' });
    success('HTML test report generated');
    info('Open test-results/html-report/index.html to view results');
  } catch (err) {
    warning('Test report generation completed with some issues');
  }
}

// Organize screenshots
function organizeScreenshots() {
  section('Screenshot Organization');
  
  const testResultsDir = 'test-results';
  const screenshotsDir = 'screenshots';
  
  if (fs.existsSync(testResultsDir)) {
    try {
      // Find all screenshot files in test-results
      const findCommand = `find ${testResultsDir} -name "*.png" -type f`;
      const screenshots = execSync(findCommand, { encoding: 'utf8' })
        .split('\n')
        .filter(file => file.trim() && file.endsWith('.png'));
      
      screenshots.forEach(screenshot => {
        const filename = path.basename(screenshot);
        const targetPath = path.join(screenshotsDir, 'current', filename);
        
        try {
          fs.copyFileSync(screenshot, targetPath);
          info(`Organized: ${filename}`);
        } catch (err) {
          warning(`Failed to copy ${filename}: ${err.message}`);
        }
      });
      
      success(`Organized ${screenshots.length} screenshots`);
    } catch (err) {
      warning('Screenshot organization completed with some issues');
    }
  }
}

// Create README for screenshots directory
function createScreenshotReadme() {
  const readmeContent = `# Visual Testing Screenshots

This directory contains all screenshots generated by the visual testing suite for Ocean's Agentic ERP Command Center.

## Directory Structure

- \`baseline/\` - Reference screenshots for comparison
- \`current/\` - Screenshots from the latest test run
- \`diff/\` - Visual diff images showing changes
- \`browsers/\` - Browser-specific screenshots
- \`viewports/\` - Viewport-specific screenshots

## Screenshot Naming Convention

Screenshots follow the pattern: \`{component}-{state}-{browser?}-{viewport?}.png\`

Examples:
- \`command-center-default.png\` - Default command center layout
- \`command-palette-search-plan.png\` - Command palette searching for "plan"
- \`font-status-bar-chrome.png\` - Status bar font rendering in Chrome
- \`layout-ultrawide-firefox.png\` - Ultrawide layout in Firefox

## Usage

### Generate New Baselines
\`\`\`bash
npm run test:e2e:screenshots
\`\`\`

### Run Visual Tests
\`\`\`bash
npm run test:e2e
\`\`\`

### View Test Results
\`\`\`bash
npm run test:e2e:report
\`\`\`

## Last Updated

Generated: ${new Date().toISOString()}
Test Suite: Visual Regression v1.0
Environment: ${process.env.NODE_ENV || 'development'}
`;

  fs.writeFileSync('screenshots/README.md', readmeContent);
  success('Created screenshots/README.md');
}

// Validate screenshot quality
function validateScreenshots() {
  section('Screenshot Quality Validation');
  
  const baselineDir = 'screenshots/baseline';
  
  if (!fs.existsSync(baselineDir)) {
    warning('No baseline directory found - skipping validation');
    return;
  }
  
  const screenshots = fs.readdirSync(baselineDir).filter(f => f.endsWith('.png'));
  
  if (screenshots.length === 0) {
    warning('No baseline screenshots found');
    return;
  }
  
  success(`Found ${screenshots.length} baseline screenshots`);
  
  // Check for common issues
  screenshots.forEach(screenshot => {
    const filePath = path.join(baselineDir, screenshot);
    const stats = fs.statSync(filePath);
    
    if (stats.size < 1000) {
      warning(`${screenshot} is unusually small (${stats.size} bytes)`);
    } else if (stats.size > 500000) {
      info(`${screenshot} is large (${Math.round(stats.size / 1024)}KB) - consider optimization`);
    } else {
      success(`${screenshot} looks good (${Math.round(stats.size / 1024)}KB)`);
    }
  });
}

// Print summary and next steps
function printSummary() {
  header('Visual Testing Setup Complete');
  
  success('✨ Visual testing infrastructure is ready!');
  
  log('\n📋 What was set up:', 'bright');
  log('  • Playwright configuration for visual testing');
  log('  • Comprehensive visual regression test suites');
  log('  • Cross-browser validation tests');
  log('  • Screenshot directory structure');
  log('  • Baseline screenshot generation');
  log('  • Test reporting infrastructure');
  
  log('\n🚀 Next Steps:', 'bright');
  log('  1. Review generated baseline screenshots for accuracy');
  log('  2. Run visual tests during development: npm run test:e2e');
  log('  3. View test reports: npm run test:e2e:report');
  log('  4. Update baselines when making intentional visual changes');
  
  log('\n📚 Documentation:', 'bright');
  log('  • Visual Testing Guide: VISUAL_TESTING_GUIDE.md');
  log('  • Report Template: VISUAL_TESTING_REPORT_TEMPLATE.md');
  log('  • Screenshot Directory: screenshots/README.md');
  
  log('\n🎯 Key Features:', 'bright');
  log('  • Pixel-perfect terminal font consistency testing');
  log('  • Dark mode visual validation');
  log('  • Cross-browser compatibility verification');
  log('  • Responsive design validation');
  log('  • Command palette and interaction testing');
  
  log('');
  success('Happy testing! 🧪✨');
}

// Main execution
function main() {
  header('Visual Testing Baseline Generator for Ocean\'s Command Center');
  
  try {
    validateEnvironment();
    ensureDependencies();
    createDirectories();
    generateBaselines();
    organizeScreenshots();
    createScreenshotReadme();
    validateScreenshots();
    generateReport();
    printSummary();
    
  } catch (err) {
    error(`Setup failed: ${err.message}`);
    process.exit(1);
  }
}

// Execute if run directly
if (require.main === module) {
  main();
}

module.exports = {
  validateEnvironment,
  ensureDependencies,
  createDirectories,
  generateBaselines,
  organizeScreenshots,
  validateScreenshots
};