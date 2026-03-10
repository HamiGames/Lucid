// tests/e2e/global-setup.ts - Global setup for E2E tests
// Based on the electron-multi-gui-development.plan.md specifications

import { chromium, Browser, Page } from 'playwright';
import { spawn, ChildProcess } from 'child_process';
import { join } from 'path';

// Global variables for E2E tests
let browser: Browser;
let appProcess: ChildProcess;

export default async function globalSetup() {
  console.log('Starting global E2E test setup...');

  try {
    // Start the Electron app for testing
    await startElectronApp();
    
    // Setup browser for E2E testing
    await setupBrowser();
    
    // Setup test data
    await setupTestData();
    
    console.log('Global E2E test setup completed successfully');
  } catch (error) {
    console.error('Global E2E test setup failed:', error);
    throw error;
  }
}

async function startElectronApp(): Promise<void> {
  console.log('Starting Electron app for E2E testing...');
  
  return new Promise((resolve, reject) => {
    // Start the Electron app in test mode
    appProcess = spawn('npm', ['run', 'test:e2e:app'], {
      cwd: process.cwd(),
      stdio: 'pipe',
      env: {
        ...process.env,
        NODE_ENV: 'test',
        ELECTRON_IS_DEV: 'false',
        TEST_MODE: 'true'
      }
    });

    appProcess.stdout?.on('data', (data) => {
      const output = data.toString();
      console.log('App output:', output);
      
      // Look for app ready signal
      if (output.includes('Electron app ready') || output.includes('App started')) {
        resolve();
      }
    });

    appProcess.stderr?.on('data', (data) => {
      console.error('App error:', data.toString());
    });

    appProcess.on('error', (error) => {
      console.error('Failed to start Electron app:', error);
      reject(error);
    });

    appProcess.on('exit', (code) => {
      if (code !== 0) {
        console.error(`Electron app exited with code ${code}`);
        reject(new Error(`App exited with code ${code}`));
      }
    });

    // Timeout after 30 seconds
    setTimeout(() => {
      if (appProcess.killed) {
        reject(new Error('App startup timeout'));
      }
    }, 30000);
  });
}

async function setupBrowser(): Promise<void> {
  console.log('Setting up browser for E2E testing...');
  
  try {
    // Launch browser with appropriate settings for E2E testing
    browser = await chromium.launch({
      headless: process.env.CI === 'true', // Run headless in CI
      slowMo: 100, // Slow down operations for better visibility
      args: [
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--no-sandbox',
        '--disable-setuid-sandbox'
      ]
    });

    // Create a test page
    const page = await browser.newPage();
    
    // Set viewport size
    await page.setViewportSize({ width: 1280, height: 720 });
    
    // Setup page event listeners
    page.on('console', (msg) => {
      console.log('Browser console:', msg.text());
    });

    page.on('pageerror', (error) => {
      console.error('Browser page error:', error.message);
    });

    // Close the test page
    await page.close();
    
    console.log('Browser setup completed');
  } catch (error) {
    console.error('Browser setup failed:', error);
    throw error;
  }
}

async function setupTestData(): Promise<void> {
  console.log('Setting up test data...');
  
  try {
    // Create test database
    // await createTestDatabase();
    
    // Seed test data
    // await seedTestData();
    
    // Setup test services
    // await setupTestServices();
    
    console.log('Test data setup completed');
  } catch (error) {
    console.error('Test data setup failed:', error);
    throw error;
  }
}

// Export cleanup function
export async function globalTeardown() {
  console.log('Starting global E2E test teardown...');

  try {
    // Close browser
    if (browser) {
      await browser.close();
    }
    
    // Stop Electron app
    if (appProcess && !appProcess.killed) {
      appProcess.kill('SIGTERM');
      
      // Wait for graceful shutdown
      await new Promise((resolve) => {
        appProcess.on('exit', resolve);
        setTimeout(resolve, 5000); // Force exit after 5 seconds
      });
    }
    
    // Cleanup test data
    // await cleanupTestData();
    
    console.log('Global E2E test teardown completed');
  } catch (error) {
    console.error('Global E2E test teardown failed:', error);
  }
}
