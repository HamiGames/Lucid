// jest.config.js - Jest configuration for Electron GUI testing
// Based on the electron-multi-gui-development.plan.md specifications

module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // Test file patterns
  testMatch: [
    '<rootDir>/tests/**/*.spec.ts',
    '<rootDir>/tests/**/*.spec.tsx',
    '<rootDir>/tests/**/*.test.ts',
    '<rootDir>/tests/**/*.test.tsx'
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
  
  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/tests/setup.ts'
  ],
  
  // Coverage configuration
  collectCoverage: true,
  collectCoverageFrom: [
    'main/**/*.{ts,tsx}',
    'renderer/**/*.{ts,tsx}',
    'shared/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/tests/**',
    '!**/coverage/**',
    '!**/dist/**',
    '!**/build/**'
  ],
  
  // Coverage thresholds
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70
    }
  },
  
  // Coverage reporters
  coverageReporters: [
    'text',
    'text-summary',
    'html',
    'lcov',
    'json'
  ],
  
  // Test timeout
  testTimeout: 30000,
  
  // Clear mocks between tests
  clearMocks: true,
  
  // Restore mocks after each test
  restoreMocks: true,
  
  // Verbose output
  verbose: true,
  
  // Globals for Electron testing
  globals: {
    'ts-jest': {
      tsconfig: 'tsconfig.json',
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
    '/coverage/'
  ],
  
  // Transform ignore patterns
  transformIgnorePatterns: [
    'node_modules/(?!(electron|@electron|electron-builder)/)'
  ],
  
  // Mock modules for Electron
  moduleNameMapping: {
    ...require('jest.config.js').moduleNameMapping,
    '^electron$': '<rootDir>/tests/mocks/electron.ts',
    '^electron/main$': '<rootDir>/tests/mocks/electron-main.ts',
    '^electron/renderer$': '<rootDir>/tests/mocks/electron-renderer.ts'
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
  
  // Parallel execution
  maxWorkers: process.env.CI ? 2 : '50%',
  
  // Cache configuration
  cache: true,
  cacheDirectory: '<rootDir>/.jest-cache',
  
  // Reporters
  reporters: [
    'default',
    process.env.CI ? 'jest-junit' : 'jest-html-reporters'
  ]
};
