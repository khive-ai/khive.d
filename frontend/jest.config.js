/**
 * Jest Configuration
 * Unit and integration testing setup for the Next.js application
 */

const nextJest = require("next/jest");

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: "./",
});

// Add any custom config to be passed to Jest
const customJestConfig = {
  // Test environment
  testEnvironment: "jsdom",

  // Setup files
  setupFilesAfterEnv: ["<rootDir>/src/__tests__/setup.ts"],

  // Module name mapping for path aliases
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    "^@/components/(.*)$": "<rootDir>/src/components/$1",
    "^@/ui/(.*)$": "<rootDir>/src/components/ui/$1",
    "^@/feature/(.*)$": "<rootDir>/src/components/feature/$1",
    "^@/layout/(.*)$": "<rootDir>/src/components/layout/$1",
    "^@/lib/(.*)$": "<rootDir>/src/lib/$1",
    "^@/api/(.*)$": "<rootDir>/src/lib/api/$1",
    "^@/hooks/(.*)$": "<rootDir>/src/lib/hooks/$1",
    "^@/utils/(.*)$": "<rootDir>/src/lib/utils/$1",
    "^@/types/(.*)$": "<rootDir>/src/lib/types/$1",
    "^@/constants/(.*)$": "<rootDir>/src/lib/constants/$1",
    "^@/stores/(.*)$": "<rootDir>/src/lib/stores/$1",
    "^@/config/(.*)$": "<rootDir>/src/lib/config/$1",
    "^@/styles/(.*)$": "<rootDir>/src/styles/$1",
    "^@/app/(.*)$": "<rootDir>/src/app/$1",
    "^@/public/(.*)$": "<rootDir>/public/$1",
  },

  // Test patterns
  testMatch: [
    "<rootDir>/src/**/__tests__/**/*.(ts|tsx|js)",
    "<rootDir>/src/**/*.(test|spec).(ts|tsx|js)",
    "<rootDir>/__tests__/**/*.(ts|tsx|js)",
  ],

  // Coverage configuration
  collectCoverageFrom: [
    "src/**/*.{js,jsx,ts,tsx}",
    "!src/**/*.d.ts",
    "!src/**/*.stories.{js,jsx,ts,tsx}",
    "!src/**/index.{js,jsx,ts,tsx}",
    "!src/app/**/*.{js,jsx,ts,tsx}", // Exclude app router files
    "!**/node_modules/**",
  ],

  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 80,
      statements: 80,
    },
  },

  coverageReporters: ["text", "lcov", "html"],

  // Transform configuration
  transform: {
    "^.+\\.(js|jsx|ts|tsx)$": ["babel-jest", { presets: ["next/babel"] }],
  },

  // Module file extensions
  moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json", "node"],

  // Test timeout
  testTimeout: 30000,

  // Mock configuration
  clearMocks: true,
  resetMocks: true,
  restoreMocks: true,

  // Ignore patterns
  testPathIgnorePatterns: [
    "<rootDir>/.next/",
    "<rootDir>/node_modules/",
    "<rootDir>/build/",
    "<rootDir>/dist/",
  ],

  // Watch plugins - Disabled due to version conflicts
  // watchPlugins: [
  //   'jest-watch-typeahead/filename',
  //   'jest-watch-typeahead/testname',
  // ],

  // Globals
  globals: {
    "ts-jest": {
      tsconfig: "tsconfig.json",
    },
  },
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig);
