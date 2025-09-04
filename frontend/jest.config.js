const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.(test|spec).{js,jsx,ts,tsx}',
  ],
  
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
  ],
  
  modulePathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/build/'],
  testTimeout: 15000,
};

module.exports = createJestConfig(config);