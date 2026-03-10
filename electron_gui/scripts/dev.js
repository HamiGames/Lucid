#!/usr/bin/env node

const { spawn, exec } = require('child_process');
const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logStep(step, message) {
  log(`[${step}] ${message}`, 'cyan');
}

function logSuccess(message) {
  log(`✓ ${message}`, 'green');
}

function logError(message) {
  log(`✗ ${message}`, 'red');
}

function logWarning(message) {
  log(`⚠ ${message}`, 'yellow');
}

// Development configuration
const config = {
  nodeEnv: 'development',
  electronEnv: 'development',
  webpackDevServerPort: 3000,
  mainProcessPort: 3001,
  hotReload: true,
  watchMode: true,
};

// Process management
let processes = {
  main: null,
  renderer: null,
  webpackDevServer: null,
};

// Cleanup function
function cleanup() {
  logStep('CLEANUP', 'Stopping development processes...');
  
  Object.values(processes).forEach(process => {
    if (process && !process.killed) {
      process.kill('SIGTERM');
    }
  });
  
  logSuccess('Development processes stopped');
  process.exit(0);
}

// Handle process signals
process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
process.on('exit', cleanup);

// Start main process
function startMainProcess() {
  logStep('MAIN', 'Starting main process...');
  
  const mainProcess = spawn('npm', ['run', 'dev:main'], {
    stdio: 'inherit',
    shell: true,
    env: {
      ...process.env,
      NODE_ENV: config.nodeEnv,
      ELECTRON_ENV: config.electronEnv,
    },
  });
  
  mainProcess.on('error', (error) => {
    logError(`Main process error: ${error.message}`);
  });
  
  mainProcess.on('exit', (code) => {
    if (code !== 0) {
      logError(`Main process exited with code ${code}`);
    }
  });
  
  processes.main = mainProcess;
  return mainProcess;
}

// Start webpack dev server
function startWebpackDevServer() {
  logStep('RENDERER', 'Starting webpack dev server...');
  
  const devServer = spawn('npm', ['run', 'dev:renderer'], {
    stdio: 'inherit',
    shell: true,
    env: {
      ...process.env,
      NODE_ENV: config.nodeEnv,
      ELECTRON_ENV: config.electronEnv,
      WEBPACK_DEV_SERVER_PORT: config.webpackDevServerPort,
    },
  });
  
  devServer.on('error', (error) => {
    logError(`Webpack dev server error: ${error.message}`);
  });
  
  devServer.on('exit', (code) => {
    if (code !== 0) {
      logError(`Webpack dev server exited with code ${code}`);
    }
  });
  
  processes.webpackDevServer = devServer;
  return devServer;
}

// Wait for webpack dev server to be ready
function waitForWebpackDevServer() {
  return new Promise((resolve, reject) => {
    const timeout = 30000; // 30 seconds
    const startTime = Date.now();
    
    const checkServer = () => {
      exec(`curl -s http://localhost:${config.webpackDevServerPort}`, (error) => {
        if (!error) {
          logSuccess('Webpack dev server is ready');
          resolve();
        } else if (Date.now() - startTime > timeout) {
          reject(new Error('Webpack dev server startup timeout'));
        } else {
          setTimeout(checkServer, 1000);
        }
      });
    };
    
    checkServer();
  });
}

// Setup file watchers
function setupFileWatchers() {
  logStep('WATCH', 'Setting up file watchers...');
  
  const watchPaths = [
    'main/**/*.ts',
    'shared/**/*.ts',
    'configs/**/*.json',
  ];
  
  watchPaths.forEach(watchPath => {
    if (fs.existsSync(path.dirname(watchPath))) {
      fs.watch(watchPath, { recursive: true }, (eventType, filename) => {
        if (filename && !filename.includes('node_modules')) {
          logStep('WATCH', `File changed: ${filename}`);
          // Trigger main process restart if needed
          if (processes.main && !processes.main.killed) {
            processes.main.kill('SIGTERM');
            setTimeout(() => {
              processes.main = startMainProcess();
            }, 1000);
          }
        }
      });
    }
  });
  
  logSuccess('File watchers setup complete');
}

// Check dependencies
function checkDependencies() {
  logStep('DEPS', 'Checking dependencies...');
  
  const packageJsonPath = path.join(process.cwd(), 'package.json');
  const nodeModulesPath = path.join(process.cwd(), 'node_modules');
  
  if (!fs.existsSync(packageJsonPath)) {
    logError('package.json not found');
    process.exit(1);
  }
  
  if (!fs.existsSync(nodeModulesPath)) {
    logWarning('node_modules not found, installing dependencies...');
    exec('npm install', (error) => {
      if (error) {
        logError(`Failed to install dependencies: ${error.message}`);
        process.exit(1);
      }
      logSuccess('Dependencies installed');
      startDevelopment();
    });
    return false;
  }
  
  logSuccess('Dependencies check passed');
  return true;
}

// Start development environment
async function startDevelopment() {
  try {
    log(`Starting Lucid Desktop Development Environment`, 'bright');
    log(`Mode: ${config.nodeEnv} | Hot Reload: ${config.hotReload}`, 'blue');
    log('');
    
    // Start webpack dev server first
    startWebpackDevServer();
    
    // Wait for webpack dev server to be ready
    await waitForWebpackDevServer();
    
    // Start main process
    startMainProcess();
    
    // Setup file watchers
    setupFileWatchers();
    
    log('');
    logSuccess('Development environment started successfully');
    log(`Webpack Dev Server: http://localhost:${config.webpackDevServerPort}`, 'blue');
    log('Press Ctrl+C to stop', 'yellow');
    
  } catch (error) {
    logError(`Failed to start development environment: ${error.message}`);
    cleanup();
  }
}

// Handle command line arguments
const args = process.argv.slice(2);
const command = args[0];

switch (command) {
  case 'main':
    startMainProcess();
    break;
  case 'renderer':
    startWebpackDevServer();
    break;
  case 'watch':
    setupFileWatchers();
    break;
  default:
    if (checkDependencies()) {
      startDevelopment();
    }
    break;
}
