#!/usr/bin/env node

const { execSync, spawn } = require('child_process');
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

// Build configuration
const config = {
  buildDir: 'dist',
  mainDir: 'main',
  rendererDir: 'renderer',
  sharedDir: 'shared',
  assetsDir: 'assets',
  configsDir: 'configs',
  nodeEnv: process.env.NODE_ENV || 'production',
  platform: process.env.PLATFORM || process.platform,
  arch: process.env.ARCH || process.arch,
};

// Clean build directory
function cleanBuildDir() {
  logStep('CLEAN', 'Cleaning build directory...');
  
  if (fs.existsSync(config.buildDir)) {
    fs.rmSync(config.buildDir, { recursive: true, force: true });
    logSuccess('Build directory cleaned');
  } else {
    log('Build directory does not exist, skipping clean');
  }
}

// Build main process
function buildMain() {
  logStep('MAIN', 'Building main process...');
  
  try {
    execSync('tsc –p tsconfig.main.json', { 
      stdio: 'inherit',
      cwd: process.cwd()
    });
    logSuccess('Main process built successfully');
  } catch (error) {
    logError('Failed to build main process');
    throw error;
  }
}

// Build renderer processes
function buildRenderer() {
  logStep('RENDERER', 'Building renderer processes...');
  
  try {
    execSync('webpack --config webpack.renderer.config.js --mode production', { 
      stdio: 'inherit',
      cwd: process.cwd()
    });
    logSuccess('Renderer processes built successfully');
  } catch (error) {
    logError('Failed to build renderer processes');
    throw error;
  }
}

// Copy static assets
function copyAssets() {
  logStep('ASSETS', 'Copying static assets...');
  
  const assetsSource = path.join(process.cwd(), config.assetsDir);
  const assetsDest = path.join(process.cwd(), config.buildDir, 'assets');
  
  if (fs.existsSync(assetsSource)) {
    fs.cpSync(assetsSource, assetsDest, { recursive: true });
    logSuccess('Static assets copied');
  } else {
    logWarning('Assets directory not found, skipping asset copy');
  }
}

// Copy configuration files
function copyConfigs() {
  logStep('CONFIGS', 'Copying configuration files...');
  
  const configsSource = path.join(process.cwd(), config.configsDir);
  const configsDest = path.join(process.cwd(), config.buildDir, 'configs');
  
  if (fs.existsSync(configsSource)) {
    fs.cpSync(configsSource, configsDest, { recursive: true });
    logSuccess('Configuration files copied');
  } else {
    logWarning('Configs directory not found, skipping config copy');
  }
}

// Copy shared files
function copyShared() {
  logStep('SHARED', 'Copying shared files...');
  
  const sharedSource = path.join(process.cwd(), config.sharedDir);
  const sharedDest = path.join(process.cwd(), config.buildDir, 'shared');
  
  if (fs.existsSync(sharedSource)) {
    fs.cpSync(sharedSource, sharedDest, { recursive: true });
    logSuccess('Shared files copied');
  } else {
    logWarning('Shared directory not found, skipping shared copy');
  }
}

// Validate build
function validateBuild() {
  logStep('VALIDATE', 'Validating build...');
  
  const requiredFiles = [
    'main/index.js',
    'renderer/admin/admin.html',
    'renderer/user/user.html',
    'renderer/developer/developer.html',
    'renderer/node/node.html',
  ];
  
  const missingFiles = [];
  
  requiredFiles.forEach(file => {
    const filePath = path.join(config.buildDir, file);
    if (!fs.existsSync(filePath)) {
      missingFiles.push(file);
    }
  });
  
  if (missingFiles.length > 0) {
    logError(`Missing required files: ${missingFiles.join(', ')}`);
    throw new Error('Build validation failed');
  }
  
  logSuccess('Build validation passed');
}

// Generate build info
function generateBuildInfo() {
  logStep('INFO', 'Generating build information...');
  
  const buildInfo = {
    version: process.env.npm_package_version || '1.0.0',
    buildTime: new Date().toISOString(),
    platform: config.platform,
    arch: config.arch,
    nodeEnv: config.nodeEnv,
    nodeVersion: process.version,
    electronVersion: process.env.npm_package_devDependencies_electron || '28.1.0',
    gitCommit: getGitCommit(),
    gitBranch: getGitBranch(),
  };
  
  const buildInfoPath = path.join(config.buildDir, 'build-info.json');
  fs.writeFileSync(buildInfoPath, JSON.stringify(buildInfo, null, 2));
  
  logSuccess('Build information generated');
}

// Get git commit hash
function getGitCommit() {
  try {
    return execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

// Get git branch
function getGitBranch() {
  try {
    return execSync('git rev-parse --abbrev-ref HEAD', { encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

// Main build function
async function build() {
  const startTime = Date.now();
  
  try {
    log(`Building Lucid Desktop Application`, 'bright');
    log(`Platform: ${config.platform} | Arch: ${config.arch} | Mode: ${config.nodeEnv}`, 'blue');
    log('');
    
    // Build steps
    cleanBuildDir();
    buildMain();
    buildRenderer();
    copyAssets();
    copyConfigs();
    copyShared();
    validateBuild();
    generateBuildInfo();
    
    const endTime = Date.now();
    const duration = ((endTime - startTime) / 1000).toFixed(2);
    
    log('');
    logSuccess(`Build completed successfully in ${duration}s`);
    log(`Build output: ${config.buildDir}`, 'blue');
    
  } catch (error) {
    logError(`Build failed: ${error.message}`);
    process.exit(1);
  }
}

// Handle command line arguments
const args = process.argv.slice(2);
const command = args[0];

switch (command) {
  case 'clean':
    cleanBuildDir();
    break;
  case 'main':
    buildMain();
    break;
  case 'renderer':
    buildRenderer();
    break;
  case 'assets':
    copyAssets();
    break;
  case 'validate':
    validateBuild();
    break;
  default:
    build();
    break;
}
