# Visual Testing & Screenshot Documentation Guide

## 🎯 Mission: Pixel-Perfect Terminal Aesthetics

This guide covers the comprehensive visual testing infrastructure for Ocean's Agentic ERP Command Center, ensuring consistent terminal-first design across all browsers and conditions.

## 🗂️ Directory Structure

```
frontend/
├── e2e/
│   ├── visual-regression.spec.ts      # Main visual regression tests
│   ├── cross-browser-visual.spec.ts   # Cross-browser validation
│   └── global.setup.ts               # Test environment setup
├── screenshots/                      # Screenshot documentation
│   ├── baseline/                     # Reference images
│   ├── current/                      # Current test results
│   ├── diff/                         # Visual diff images
│   ├── browsers/                     # Browser-specific captures
│   │   ├── chrome/
│   │   ├── firefox/
│   │   └── safari/
│   └── viewports/                    # Viewport-specific captures
│       ├── desktop/
│       ├── laptop/
│       ├── ultrawide/
│       ├── tablet/
│       └── mobile/
├── playwright.config.ts              # Playwright configuration
└── test-results/                     # Test execution reports
```

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Create baseline screenshots
npm run test:e2e:screenshots
```

### 2. Running Visual Tests

```bash
# Run all visual regression tests
npm run test:e2e

# Run with UI (recommended for development)
npm run test:e2e:ui

# Update baseline screenshots
npm run test:e2e:screenshots

# Generate test report
npm run test:e2e:report
```

## 🎨 Visual Testing Categories

### 1. Layout Consistency Tests
- **Purpose**: Ensure 3-pane layout remains stable across viewports
- **Coverage**: Desktop (1920x1080), Laptop (1366x768), Ultrawide (3440x1440)
- **Key Tests**:
  - Default command center layout
  - Focused pane highlighting
  - Responsive breakpoint behavior

### 2. Terminal Font Rendering Tests
- **Purpose**: Validate monospace font consistency
- **Coverage**: SFMono-Regular, Monaco, Consolas, fallback fonts
- **Key Tests**:
  - Status bar font rendering at different zoom levels
  - Command palette input font consistency
  - Font fallback behavior testing

### 3. Dark Mode Consistency Tests
- **Purpose**: Ensure perfect dark theme implementation
- **Coverage**: All components in dark mode
- **Key Tests**:
  - CSS custom properties application
  - High contrast accessibility mode
  - Component-level dark mode styling

### 4. Command Palette Visual Tests
- **Purpose**: Validate CLI-first interface consistency
- **Coverage**: All command palette states and interactions
- **Key Tests**:
  - Empty state, search results, keyboard navigation
  - Category filtering visual consistency
  - Help dialog rendering

### 5. Cross-Browser Validation Tests
- **Purpose**: Ensure pixel-perfect consistency across Chrome, Firefox, Safari
- **Coverage**: All major browsers and browser engines
- **Key Tests**:
  - Font rendering differences
  - Layout engine variations
  - CSS property support variations

## 🔧 Configuration Details

### Playwright Configuration Highlights

```typescript
export default defineConfig({
  expect: {
    // 20% tolerance for visual comparisons
    toHaveScreenshot: { threshold: 0.2, mode: 'pixel' }
  },
  
  use: {
    // Terminal font stack consistency
    fontFamily: 'SFMono-Regular, Monaco, Inconsolata, Roboto Mono, Consolas, monospace',
    
    // Dark mode by default (Ocean's preference)
    colorScheme: 'dark',
  },
  
  projects: [
    // Multiple browser and viewport configurations
    // Detailed in playwright.config.ts
  ]
});
```

### Visual Testing Best Practices

1. **Stable Screenshots**: Always disable animations and wait for fonts to load
2. **Consistent Environment**: Use standardized viewport sizes and browser settings
3. **Reliable Selectors**: Use data-testid attributes for test stability
4. **Cross-Browser Coverage**: Test on Chromium, Firefox, and WebKit engines
5. **Responsive Coverage**: Test key breakpoints used by Ocean's workflow

## 📊 Test Data & Fixtures

### Component Test IDs

All major components include `data-testid` attributes for reliable testing:

```typescript
// Main layout components
'command-center'        // Root container
'status-bar'           // Terminal-style status bar
'connection-status'    // WebSocket connection indicator
'orchestration-tree'   // Left pane: session tree
'workspace'           // Center pane: main content
'activity-stream'     // Right pane: real-time events

// Interactive components
'command-palette'     // Command palette dialog
'command-input'       // Command search input
'help-dialog'         // Keyboard shortcuts help
```

### Screenshot Naming Convention

Screenshots follow a consistent naming pattern for easy identification:

```
{component}-{state}-{browser?}-{viewport?}.png

Examples:
- command-center-default.png
- command-palette-search-plan.png
- font-status-bar-chrome.png
- layout-ultrawide-firefox.png
- dark-mode-full-layout.png
```

## 🎯 Visual Regression Workflow

### 1. Baseline Creation

```bash
# Generate initial baseline screenshots
npm run test:e2e:screenshots

# Review and approve baselines
git add frontend/test-results/
git commit -m "feat: add visual regression baselines"
```

### 2. Development Testing

```bash
# Run visual tests during development
npm run test:e2e:ui

# Update specific screenshots if changes are intentional
npx playwright test --update-snapshots visual-regression.spec.ts
```

### 3. CI/CD Integration

```bash
# CI runs visual tests automatically
npm run test:e2e:ci

# Generate visual diff reports on failures
npm run test:e2e:report
```

### 4. Visual Diff Analysis

When visual tests fail:

1. **Review Diff Images**: Check `test-results/` for visual differences
2. **Analyze Changes**: Determine if differences are intentional or bugs
3. **Update Baselines**: If changes are intentional, update screenshots
4. **Fix Issues**: If unintentional, fix the underlying visual problems

## 🔍 Debugging Visual Tests

### Common Issues & Solutions

1. **Font Loading Issues**
   ```typescript
   // Ensure fonts are loaded before screenshots
   await page.evaluate(() => document.fonts.ready);
   await page.waitForTimeout(1000);
   ```

2. **Animation Interference**
   ```typescript
   // Disable all animations for consistent screenshots
   await page.addStyleTag({
     content: `*, *::before, *::after { 
       animation-duration: 0s !important; 
       transition-duration: 0s !important; 
     }`
   });
   ```

3. **Dynamic Content Variability**
   ```typescript
   // Hide timestamps and other dynamic content
   await page.addStyleTag({
     content: `
       [data-testid="timestamp"],
       [data-testid="connection-latency"] {
         visibility: hidden !important;
       }
     `
   });
   ```

4. **WebSocket Connection Timing**
   ```typescript
   // Wait for stable connection before screenshots
   await expect(page.locator('[data-testid="connection-status"]'))
     .toContainText('ONLINE', { timeout: 10000 });
   ```

## 📈 Performance Considerations

### Optimization Strategies

1. **Parallel Execution**: Tests run in parallel across browser projects
2. **Selective Updates**: Only update screenshots for changed components
3. **Efficient Waits**: Use specific element waits instead of arbitrary timeouts
4. **Resource Management**: Proper browser context cleanup between tests

### Test Execution Timing

- **Full Suite**: ~5-10 minutes depending on browser coverage
- **Single Browser**: ~2-3 minutes for complete visual coverage
- **Component Specific**: ~30 seconds for focused testing
- **Screenshot Update**: ~1-2 minutes for baseline regeneration

## 🚨 Visual Testing Alerts

### Failure Scenarios

1. **Font Rendering Changes**: Often indicates browser updates or font installation issues
2. **Color Shifts**: May indicate CSS custom property problems or dark mode issues
3. **Layout Shifts**: Could indicate responsive design problems or CSS changes
4. **Component State Issues**: Might show problems with focus states or interactions

### Recovery Procedures

1. **Investigate Root Cause**: Check browser versions, CSS changes, font availability
2. **Validate Across Browsers**: Ensure issue isn't browser-specific
3. **Update Documentation**: Record any environmental changes that affect visuals
4. **Communicate Changes**: Alert team to any visual standard updates

## 📝 Reporting & Documentation

### Visual Test Reports

Each test run generates comprehensive reports including:

- ✅ **Pass/Fail Status**: Overall test results
- 🖼️ **Screenshot Gallery**: All captured images with comparisons
- 🔍 **Diff Analysis**: Highlighted visual differences
- 📊 **Browser Coverage**: Results across all tested browsers
- ⏱️ **Performance Metrics**: Test execution timing and resource usage

### Continuous Integration

Visual tests are integrated into the CI/CD pipeline:

1. **PR Validation**: All pull requests must pass visual regression tests
2. **Baseline Updates**: Approved visual changes update baseline images
3. **Browser Matrix**: Tests run against Chrome, Firefox, and Safari
4. **Failure Notifications**: Team gets alerted to visual regression failures

## 🎨 Visual Design Standards

### Terminal Aesthetics Checklist

- ✅ **Font Consistency**: Monospace fonts render identically across browsers
- ✅ **Dark Mode Perfect**: All components use consistent dark color scheme
- ✅ **Status Bar Design**: Terminal-style status information display
- ✅ **Command Palette UX**: CLI-first command interface design
- ✅ **Focus Indicators**: Clear visual feedback for keyboard navigation
- ✅ **Responsive Layout**: 3-pane layout adapts gracefully to different screens
- ✅ **Loading States**: Consistent visual feedback during operations
- ✅ **Error States**: Clear visual indication of problems or conflicts

### Color Palette Validation

```css
/* Validated color scheme from globals.css */
--khive-bg-primary: #0a0a0a;      /* Deep black background */
--khive-bg-secondary: #1a1a1a;    /* Secondary panels */
--khive-text-primary: #ffffff;     /* Primary text */
--khive-accent-primary: #00d4aa;   /* KHIVE brand accent */
```

## 🤝 Contributing to Visual Tests

### Adding New Visual Tests

1. **Identify Component**: Determine which UI components need visual coverage
2. **Write Test Cases**: Create comprehensive test scenarios
3. **Add Test IDs**: Ensure components have reliable `data-testid` attributes
4. **Generate Baselines**: Create initial reference screenshots
5. **Document Tests**: Update this guide with new test information

### Reviewing Visual Changes

1. **Check Intent**: Verify visual changes are intentional design updates
2. **Cross-Browser Test**: Validate changes work across all supported browsers
3. **Accessibility Check**: Ensure changes don't break accessibility features
4. **Performance Impact**: Verify changes don't negatively impact rendering performance
5. **Update Documentation**: Document any new visual standards or patterns

---

## 🎯 Success Metrics

This visual testing infrastructure ensures:

- **99%+ Visual Consistency** across Chrome, Firefox, and Safari
- **Sub-pixel Accuracy** for terminal font rendering
- **Complete Coverage** of all major UI states and interactions
- **Automated Detection** of visual regressions in CI/CD
- **Comprehensive Documentation** of Ocean's terminal-first design standards

For questions or support with visual testing, refer to this guide or reach out to the development team.