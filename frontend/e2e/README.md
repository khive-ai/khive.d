# KHIVE WebSocket Integration E2E Test Suite

Comprehensive end-to-end testing suite for KHIVE backend WebSocket connectivity, designed to validate real-time communication, performance targets, and system resilience.

## 🎯 Performance Targets

- **WebSocket Connection Latency**: <200ms
- **Command Response Time**: <100ms  
- **Event Propagation**: <50ms
- **Reconnection Time**: <5s
- **System Reliability**: >99% uptime
- **Command Success Rate**: >95%

## 📋 Test Coverage

### 1. Connection Management (`websocket-connection.spec.ts`)
- ✅ WebSocket connection establishment and handshake
- ✅ Automatic reconnection on connection loss
- ✅ Connection health monitoring and latency tracking
- ✅ Graceful degradation when backend unavailable
- ✅ Multiple rapid disconnection handling
- ✅ Connection state transitions

### 2. Real-time Event Streaming (`real-time-events.spec.ts`)
- ✅ Activity stream updates for agent events
- ✅ Session status changes propagation
- ✅ Coordination event broadcasting
- ✅ Event ordering and consistency
- ✅ Event deduplication and filtering
- ✅ High-frequency event handling
- ✅ Performance under event load

### 3. Command Execution Pipeline (`command-execution.spec.ts`)
- ✅ Command execution through WebSocket
- ✅ Command response handling and error cases
- ✅ Concurrent command execution
- ✅ Command queuing and prioritization
- ✅ Command history and state management
- ✅ Complex workflow execution
- ✅ Error recovery and resilience

### 4. Performance Validation (`performance-validation.spec.ts`)
- ✅ WebSocket latency measurement and validation
- ✅ Command response time benchmarks
- ✅ Concurrent operation performance
- ✅ Sustained load performance
- ✅ Recovery performance after disruption
- ✅ Comprehensive performance reporting

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- KHIVE frontend running on localhost:3000
- Mock backend server (automatically started)

### Installation
```bash
# Install dependencies (already included in main package.json)
npm install

# Install Playwright browsers
npx playwright install
```

### Running Tests

#### All E2E Tests
```bash
npm run test:e2e
```

#### Interactive Mode (Debug)
```bash
npm run test:e2e:ui
```

#### Specific Test Files
```bash
# Connection tests only
npx playwright test e2e/websocket-connection.spec.ts

# Performance validation only
npx playwright test e2e/performance-validation.spec.ts

# Real-time events only
npx playwright test e2e/real-time-events.spec.ts

# Command execution only
npx playwright test e2e/command-execution.spec.ts
```

#### Generate Test Report
```bash
npm run test:e2e:report
```

## 🏗️ Architecture

### Mock Backend Server
Located in `e2e/mock-backend/`, provides:
- WebSocket server simulation
- HTTP API endpoints
- Realistic latency and error scenarios  
- Performance metrics collection
- Connection disruption simulation

### Test Structure
```
e2e/
├── websocket-connection.spec.ts    # Connection lifecycle tests
├── real-time-events.spec.ts        # Event streaming tests  
├── command-execution.spec.ts       # Command pipeline tests
├── performance-validation.spec.ts  # Performance benchmarks
├── setup/                          # Global setup/teardown
├── mock-backend/                   # Mock KHIVE server
└── README.md                       # This file
```

### Global Setup/Teardown
- `setup/global-setup.ts`: Verifies frontend and mock server readiness
- `setup/global-teardown.ts`: Cleanup and report generation

## 📊 Performance Monitoring

### Built-in Metrics Collection
Tests automatically collect:
- WebSocket connection latency
- Command response times
- Event propagation delays
- Memory usage patterns
- Reconnection performance
- Concurrent operation throughput

### Performance Reports
Detailed performance reports available in:
- Console output during test runs
- HTML test reports (`npm run test:e2e:report`)
- JSON metrics files in `test-results/`

### Example Performance Output
```
=== COMPREHENSIVE PERFORMANCE REPORT ===
Connection Health: { status: 'healthy', latency: '45ms' }
Server Metrics: { connectionLatency: 32, commandResponseTime: 67 }
WebSocket Latency: 45.23ms avg (target: <200ms) ✅
Command Response: 67.89ms avg (target: <100ms) ✅
Event Propagation: 23.45ms avg (target: <50ms) ✅
=== END PERFORMANCE REPORT ===
```

## 🔧 Configuration

### Playwright Configuration (`playwright.config.ts`)
- Cross-browser testing (Chrome, Firefox, Safari)
- Mobile viewport testing
- Performance timeout settings
- Video/screenshot capture
- Test parallelization

### Mock Server Configuration
- Port: 8767 (WebSocket and HTTP)
- Realistic network latency simulation
- Configurable error scenarios
- Performance metrics endpoint

### Environment Variables
```bash
# Optional: Override WebSocket URL
NEXT_PUBLIC_KHIVE_WS_URL=ws://localhost:8767

# Optional: Override API URL  
NEXT_PUBLIC_KHIVE_API_URL=http://localhost:8767

# Test mode flag
NODE_ENV=test
```

## 🐛 Debugging

### Debug Mode
```bash
# Run with debug info
DEBUG=pw:api npm run test:e2e

# Run with headed browser
npx playwright test --headed

# Run with slow motion
npx playwright test --headed --slow-mo=1000
```

### Test Artifacts
- Screenshots on failure: `test-results/`
- Video recordings: `test-results/`
- Trace files: `test-results/`
- Performance metrics: `test-results/results.json`

### Common Issues

#### Mock Server Not Starting
```bash
# Manual server start
cd e2e/mock-backend
npm install
npm start
```

#### WebSocket Connection Issues
- Verify frontend is running on localhost:3000
- Check firewall/antivirus blocking WebSocket connections
- Ensure no other services using port 8767

#### Performance Test Failures
- Run on dedicated testing machine for accurate metrics
- Disable other applications consuming CPU/memory
- Check network latency to mock server

## 📈 CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E WebSocket Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm install
      
      - name: Install Playwright
        run: npx playwright install --with-deps
      
      - name: Run E2E tests
        run: npm run test:e2e
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## 🎯 Test Data & Scenarios

### Mock Data
- 1 orchestration session (`session_001`)
- 1 test agent (`agent_001`)
- Periodic automated events
- Realistic daemon status updates

### Error Scenarios
- WebSocket disconnections
- High latency simulation
- Command execution failures
- Network timeout scenarios
- Concurrent connection limits

### Performance Scenarios
- Sustained load testing (30s)
- Burst command execution
- High-frequency event streaming
- Connection recovery testing
- Memory leak detection

## 📝 Contributing

### Adding New Tests
1. Create test file in `e2e/` directory
2. Follow existing naming convention: `feature-name.spec.ts`
3. Include performance assertions where relevant
4. Add test documentation to this README
5. Update global setup if new infrastructure needed

### Test Patterns
```typescript
// Standard test structure
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup per test
  });

  test('should meet performance target', async ({ page }) => {
    // Test implementation with performance assertions
    expect(responseTime).toBeLessThan(targetMs);
  });
});
```

### Performance Assertion Standards
```typescript
// WebSocket latency
expect(latency).toBeLessThan(200);

// Command response  
expect(responseTime).toBeLessThan(100);

// Event propagation
expect(propagationTime).toBeLessThan(50);

// Success rates
expect(successRate).toBeGreaterThan(0.95);
```

---

**Built by Ocean's KHIVE AI Team** - Ensuring real-time WebSocket reliability and performance for agentic orchestration systems.