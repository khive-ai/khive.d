import '@testing-library/jest-dom';

// Mock environment variables
process.env.NEXT_PUBLIC_KHIVE_API_URL = 'http://localhost:8000';
process.env.NEXT_PUBLIC_KHIVE_WS_URL = 'ws://localhost:8767';

// Mock performance.now
global.performance = global.performance || {};
global.performance.now = global.performance.now || jest.fn(() => Date.now());

// Suppress console warnings during tests
const originalWarn = console.warn;
const originalError = console.error;

beforeEach(() => {
  console.warn = jest.fn();
  console.error = jest.fn();
});

afterEach(() => {
  console.warn = originalWarn;
  console.error = originalError;
});