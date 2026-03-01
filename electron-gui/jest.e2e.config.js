// jest.e2e.config.js - End-to-End testing configuration for Electron GUI
// Based on the electron-multi-gui-development.plan.md specifications

module.exports = {
  // Test environment for E2E tests
  testEnvironment: 'node',
  
  // Test file patterns for E2E tests
  testMatch: [
    '<rootDir>/tests/e2e/**/*.e2e.spec.ts',
    '<rootDir>/tests/e2e/**/*.e2e.test.ts',
    '<rootDir>/tests/integration/**/*.integration.spec.ts',
    '<rootDir>/tests/integration/**/*.integration.test.ts'
  ],
  
  // File extensions to consider
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  
  // Transform files
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest'
  },
  
  // TypeScript configuration
  preset: 'ts-jest/presets/js-with-ts',
  
  // Module name mapping for absolute imports
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@shared/(.*)$': '<rootDir>/shared/$1',
    '^@main/(.*)$': '<rootDir>/main/$1',
    '^@renderer/(.*)$': '<rootDir>/renderer/$1',
    '^@tests/(.*)$': '<rootDir>/tests/$1'
  },
  
  // Setup files for E2E tests
  setupFilesAfterEnv: [
    '<rootDir>/tests/e2e/setup.ts'
  ],
  
  // Global setup and teardown
  globalSetup: '<rootDir>/tests/e2e/global-setup.ts',
  globalTeardown: '<rootDir>/tests/e2e/global-teardown.ts',
  
  // Coverage configuration for E2E tests
  collectCoverage: false, // Disable coverage for E2E tests by default
  
  // Test timeout for E2E tests (longer than unit tests)
  testTimeout: 120000, // 2 minutes
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Restore mocks after each test
  restoreMocks: true,
  
  // Verbose output
  verbose: true,
  
  // Globals for E2E testing
  globals: {
    'ts-jest': {
      tsconfig: 'tsconfig.e2e.json',
      isolatedModules: true
    }
  },
  
  // Test environment options
  testEnvironmentOptions: {
    url: 'http://localhost'
  },
  
  // Module paths
  modulePaths: [
    '<rootDir>/node_modules',
    '<rootDir>/shared',
    '<rootDir>/main',
    '<rootDir>/renderer'
  ],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/',
    '/coverage/',
    '/tests/unit/',
    '/tests/components/'
  ],
  
  // Transform ignore patterns
  transformIgnorePatterns: [
    'node_modules/(?!(electron|@electron|electron-builder|playwright)/)'
  ],
  
  // Mock modules for E2E testing
  moduleNameMapping: {
    ...require('jest.e2e.config.js').moduleNameMapping,
    '^electron$': '<rootDir>/tests/e2e/mocks/electron.ts',
    '^playwright$': '<rootDir>/tests/e2e/mocks/playwright.ts'
  },
  
  // Custom test runner
  testRunner: 'jest-circus/runner',
  
  // Watch plugins
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname'
  ],
  
  // Error handling
  errorOnDeprecated: true,
  
  // Bail on first failure in CI
  bail: process.env.CI ? 1 : 0,
  
  // Parallel execution (limited for E2E tests)
  maxWorkers: 1, // E2E tests should run sequentially
  
  // Cache configuration
  cache: true,
  cacheDirectory: '<rootDir>/.jest-e2e-cache',
  
  // Reporters
  reporters: [
    'default',
    process.env.CI ? 'jest-junit' : 'jest-html-reporters'
  ],
  
  // E2E specific configuration
  testSequencer: '<rootDir>/tests/e2e/test-sequencer.ts',
  
  // Custom matchers
  setupFilesAfterEnv: [
    '<rootDir>/tests/e2e/setup.ts',
    '<rootDir>/tests/e2e/custom-matchers.ts'
  ]
};
