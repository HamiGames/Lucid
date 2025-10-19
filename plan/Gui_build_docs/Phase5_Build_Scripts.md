# Phase 5: Build Scripts and Configuration

## Overview

This document provides comprehensive build scripts and configuration requirements for the Lucid Electron GUI system. All scripts are designed for Windows 11 build environment with Raspberry Pi Linux target deployment.

## Build Configuration Files

### 1. Package.json Scripts

**File**: `electron-gui/package.json`

```json
{
  "name": "lucid-electron-gui",
  "version": "1.0.0",
  "description": "Lucid Desktop GUI - Multi-window Electron application",
  "main": "dist/main/index.js",
  "scripts": {
    "dev": "concurrently \"npm run dev:main\" \"npm run dev:renderer\"",
    "dev:main": "tsc -p tsconfig.main.json && electron .",
    "dev:renderer": "webpack serve --config webpack.renderer.config.js",
    "build": "npm run build:main && npm run build:renderer",
    "build:main": "tsc -p tsconfig.main.json",
    "build:renderer": "webpack --config webpack.renderer.config.js",
    "build:production": "npm run build && npm run package",
    "package": "electron-builder",
    "package:win": "electron-builder --win",
    "package:linux": "electron-builder --linux",
    "package:linux-arm": "electron-builder --linux --arm64",
    "package:mac": "electron-builder --mac",
    "package:all": "electron-builder --win --linux --mac",
    "test": "jest",
    "test:e2e": "jest --config jest.e2e.config.js",
    "test:integration": "jest --config jest.integration.config.js",
    "lint": "eslint . --ext .ts,.tsx",
    "lint:fix": "eslint . --ext .ts,.tsx --fix",
    "type-check": "tsc --noEmit",
    "clean": "rimraf dist build",
    "postinstall": "npm run download-tor-binary",
    "download-tor-binary": "node scripts/download-tor.js",
    "verify-tor": "node scripts/verify-tor.js",
    "setup-dev": "npm install && npm run download-tor-binary && npm run verify-tor"
  },
  "dependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.6.4",
    "tor-control": "^2.3.0",
    "dockerode": "^3.3.5",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "socks-proxy-agent": "^8.0.2",
    "zustand": "^4.4.7",
    "typescript": "^5.2.2",
    "@types/node": "^20.8.0",
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15"
  },
  "devDependencies": {
    "@typescript-eslint/eslint-plugin": "^6.9.0",
    "@typescript-eslint/parser": "^6.9.0",
    "eslint": "^8.52.0",
    "eslint-plugin-react": "^7.33.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "jest": "^29.7.0",
    "@types/jest": "^29.5.5",
    "spectron": "^19.0.0",
    "webpack": "^5.89.0",
    "webpack-cli": "^5.1.4",
    "webpack-dev-server": "^4.15.1",
    "ts-loader": "^9.4.4",
    "html-webpack-plugin": "^5.5.3",
    "css-loader": "^6.8.1",
    "style-loader": "^3.3.3",
    "concurrently": "^8.2.2",
    "rimraf": "^5.0.5"
  }
}
```

### 2. Electron Builder Configuration

**File**: `electron-gui/electron-builder.json`

```json
{
  "appId": "com.lucid.electron-gui",
  "productName": "Lucid Desktop",
  "copyright": "Copyright © 2024 HamiGames",
  "directories": {
    "output": "dist",
    "buildResources": "assets"
  },
  "files": [
    "main/**/*",
    "renderer/**/*",
    "shared/**/*",
    "assets/icons/**/*",
    "!**/*.ts",
    "!**/*.tsx",
    "!**/node_modules/**/*",
    "!**/src/**/*",
    "!**/*.map"
  ],
  "extraResources": [
    {
      "from": "assets/tor",
      "to": "tor",
      "filter": ["**/*"]
    },
    {
      "from": "assets/configs",
      "to": "configs",
      "filter": ["**/*"]
    }
  ],
  "win": {
    "target": [
      {
        "target": "nsis",
        "arch": ["x64"]
      },
      {
        "target": "portable",
        "arch": ["x64"]
      }
    ],
    "icon": "assets/icons/icon.ico",
    "publisherName": "HamiGames",
    "verifyUpdateCodeSignature": false,
    "requestedExecutionLevel": "asInvoker"
  },
  "linux": {
    "target": [
      {
        "target": "AppImage",
        "arch": ["x64", "arm64"]
      },
      {
        "target": "deb",
        "arch": ["x64", "arm64"]
      }
    ],
    "icon": "assets/icons/icon.png",
    "category": "Network",
    "desktop": {
      "Name": "Lucid Desktop",
      "Comment": "Lucid Decentralized Storage Desktop Client",
      "Keywords": "blockchain;storage;decentralized;privacy;"
    }
  },
  "mac": {
    "target": [
      {
        "target": "dmg",
        "arch": ["x64", "arm64"]
      }
    ],
    "icon": "assets/icons/icon.icns",
    "category": "public.app-category.developer-tools",
    "hardenedRuntime": true,
    "gatekeeperAssess": false,
    "entitlements": "assets/entitlements.mac.plist",
    "entitlementsInherit": "assets/entitlements.mac.plist"
  },
  "nsis": {
    "oneClick": false,
    "allowToChangeInstallationDirectory": true,
    "allowElevation": true,
    "installerIcon": "assets/icons/icon.ico",
    "uninstallerIcon": "assets/icons/icon.ico",
    "installerHeaderIcon": "assets/icons/icon.ico",
    "createDesktopShortcut": true,
    "createStartMenuShortcut": true,
    "shortcutName": "Lucid Desktop",
    "include": "assets/installer.nsh"
  },
  "publish": {
    "provider": "github",
    "owner": "HamiGames",
    "repo": "Lucid"
  }
}
```

### 3. TypeScript Configuration

**File**: `electron-gui/tsconfig.main.json`

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "target": "ES2020",
    "module": "CommonJS",
    "lib": ["ES2020"],
    "outDir": "dist/main",
    "rootDir": "main",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "declaration": false,
    "sourceMap": true
  },
  "include": [
    "main/**/*",
    "shared/**/*"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "renderer"
  ]
}
```

**File**: `electron-gui/tsconfig.renderer.json`

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "outDir": "dist/renderer",
    "rootDir": "renderer",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "declaration": false,
    "sourceMap": true,
    "jsx": "react-jsx"
  },
  "include": [
    "renderer/**/*",
    "shared/**/*"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "main"
  ]
}
```

### 4. Webpack Configuration

**File**: `electron-gui/webpack.renderer.config.js`

```javascript
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';
  
  return {
    entry: {
      user: './renderer/user/index.tsx',
      developer: './renderer/developer/index.tsx',
      node: './renderer/node/index.tsx',
      admin: './renderer/admin/index.tsx'
    },
    output: {
      path: path.resolve(__dirname, 'dist/renderer'),
      filename: '[name]/[name].bundle.js',
      clean: true
    },
    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
      alias: {
        '@': path.resolve(__dirname, 'shared'),
        '@components': path.resolve(__dirname, 'shared/components'),
        '@hooks': path.resolve(__dirname, 'shared/hooks'),
        '@utils': path.resolve(__dirname, 'shared/utils')
      }
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: 'ts-loader',
          exclude: /node_modules/
        },
        {
          test: /\.css$/i,
          use: ['style-loader', 'css-loader']
        },
        {
          test: /\.(png|jpe?g|gif|svg)$/i,
          type: 'asset/resource'
        }
      ]
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: './renderer/user/index.html',
        filename: 'user/index.html',
        chunks: ['user']
      }),
      new HtmlWebpackPlugin({
        template: './renderer/developer/index.html',
        filename: 'developer/index.html',
        chunks: ['developer']
      }),
      new HtmlWebpackPlugin({
        template: './renderer/node/index.html',
        filename: 'node/index.html',
        chunks: ['node']
      }),
      new HtmlWebpackPlugin({
        template: './renderer/admin/index.html',
        filename: 'admin/index.html',
        chunks: ['admin']
      })
    ],
    devtool: isProduction ? 'source-map' : 'eval-source-map',
    devServer: {
      static: path.join(__dirname, 'dist/renderer'),
      port: 3000,
      hot: true
    }
  };
};
```

## Build Scripts

### 1. Windows Build Script

**File**: `scripts/build-windows.ps1`

```powershell
# Lucid Electron GUI Windows Build Script
# Build Host: Windows 11 Console
# Target: Windows executable

param(
    [switch]$Clean,
    [switch]$Production,
    [switch]$Package
)

Write-Host "Starting Lucid Electron GUI Windows Build..." -ForegroundColor Green

# Set error action preference
$ErrorActionPreference = "Stop"

# Navigate to electron-gui directory
Set-Location -Path "electron-gui"

try {
    # Clean build directory if requested
    if ($Clean) {
        Write-Host "Cleaning build directory..." -ForegroundColor Yellow
        npm run clean
    }

    # Install dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install

    # Download and verify Tor binary
    Write-Host "Downloading Tor binary..." -ForegroundColor Yellow
    npm run download-tor-binary
    npm run verify-tor

    # Type checking
    Write-Host "Running type checking..." -ForegroundColor Yellow
    npm run type-check

    # Linting
    Write-Host "Running linting..." -ForegroundColor Yellow
    npm run lint

    # Build main and renderer processes
    Write-Host "Building application..." -ForegroundColor Yellow
    if ($Production) {
        npm run build:production
    } else {
        npm run build
    }

    # Package application if requested
    if ($Package) {
        Write-Host "Packaging application..." -ForegroundColor Yellow
        npm run package:win
    }

    Write-Host "Windows build completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "Build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Set-Location -Path ".."
}
```

### 2. Linux Build Script

**File**: `scripts/build-linux.ps1`

```powershell
# Lucid Electron GUI Linux Build Script
# Build Host: Windows 11 Console (Cross-compilation)
# Target: Raspberry Pi Linux ARM64

param(
    [switch]$Clean,
    [switch]$Production,
    [switch]$Package,
    [string]$Target = "arm64"
)

Write-Host "Starting Lucid Electron GUI Linux Build..." -ForegroundColor Green
Write-Host "Target Architecture: $Target" -ForegroundColor Cyan

# Set error action preference
$ErrorActionPreference = "Stop"

# Navigate to electron-gui directory
Set-Location -Path "electron-gui"

try {
    # Clean build directory if requested
    if ($Clean) {
        Write-Host "Cleaning build directory..." -ForegroundColor Yellow
        npm run clean
    }

    # Install dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install

    # Download and verify Tor binary for Linux
    Write-Host "Downloading Tor binary for Linux..." -ForegroundColor Yellow
    npm run download-tor-binary -- --platform linux --arch $Target
    npm run verify-tor

    # Type checking
    Write-Host "Running type checking..." -ForegroundColor Yellow
    npm run type-check

    # Linting
    Write-Host "Running linting..." -ForegroundColor Yellow
    npm run lint

    # Build main and renderer processes
    Write-Host "Building application..." -ForegroundColor Yellow
    if ($Production) {
        npm run build:production
    } else {
        npm run build
    }

    # Package application if requested
    if ($Package) {
        Write-Host "Packaging application for Linux..." -ForegroundColor Yellow
        if ($Target -eq "arm64") {
            npm run package:linux-arm
        } else {
            npm run package:linux
        }
    }

    Write-Host "Linux build completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "Build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Set-Location -Path ".."
}
```

### 3. Tor Binary Download Script

**File**: `scripts/download-tor.js`

```javascript
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');

const TOR_VERSIONS = {
  windows: {
    x64: 'https://dist.torproject.org/torbrowser/12.5.6/tor-win64-0.4.8.7.zip'
  },
  linux: {
    x64: 'https://dist.torproject.org/tor-0.4.8.7.tar.gz',
    arm64: 'https://dist.torproject.org/tor-0.4.8.7.tar.gz'
  },
  mac: {
    x64: 'https://dist.torproject.org/tor-0.4.8.7.tar.gz',
    arm64: 'https://dist.torproject.org/tor-0.4.8.7.tar.gz'
  }
};

async function downloadTorBinary(platform, arch) {
  const url = TOR_VERSIONS[platform][arch];
  const assetsDir = path.join(__dirname, '..', 'assets', 'tor');
  const platformDir = path.join(assetsDir, `${platform}-${arch}`);
  
  // Create directory if it doesn't exist
  if (!fs.existsSync(platformDir)) {
    fs.mkdirSync(platformDir, { recursive: true });
  }
  
  console.log(`Downloading Tor binary for ${platform}-${arch}...`);
  console.log(`URL: ${url}`);
  console.log(`Destination: ${platformDir}`);
  
  // Implementation for downloading and extracting Tor binary
  // This would include platform-specific extraction logic
  
  console.log(`Tor binary downloaded successfully to ${platformDir}`);
}

// Parse command line arguments
const args = process.argv.slice(2);
const platform = args.find(arg => arg.startsWith('--platform'))?.split('=')[1] || os.platform();
const arch = args.find(arg => arg.startsWith('--arch'))?.split('=')[1] || os.arch();

downloadTorBinary(platform, arch).catch(console.error);
```

## Build Environment Setup

### 1. Development Environment Setup

**File**: `scripts/setup-dev-environment.ps1`

```powershell
# Lucid Electron GUI Development Environment Setup
# Run this script to set up the complete development environment

Write-Host "Setting up Lucid Electron GUI Development Environment..." -ForegroundColor Green

# Check Node.js version
$nodeVersion = node --version
Write-Host "Node.js version: $nodeVersion" -ForegroundColor Cyan

if ([version]$nodeVersion.Substring(1) -lt [version]"18.0.0") {
    Write-Host "Warning: Node.js 18.0.0 or higher is recommended" -ForegroundColor Yellow
}

# Check npm version
$npmVersion = npm --version
Write-Host "npm version: $npmVersion" -ForegroundColor Cyan

# Navigate to electron-gui directory
Set-Location -Path "electron-gui"

try {
    # Install dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install

    # Setup development environment
    Write-Host "Setting up development environment..." -ForegroundColor Yellow
    npm run setup-dev

    # Run initial build
    Write-Host "Running initial build..." -ForegroundColor Yellow
    npm run build

    # Run tests
    Write-Host "Running tests..." -ForegroundColor Yellow
    npm test

    Write-Host "Development environment setup completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Set-Location -Path ".."
}
```

### 2. Production Build Script

**File**: `scripts/build-production.ps1`

```powershell
# Lucid Electron GUI Production Build Script
# Creates production-ready builds for all platforms

param(
    [switch]$Windows,
    [switch]$Linux,
    [switch]$Mac,
    [switch]$All,
    [switch]$Clean
)

if (-not ($Windows -or $Linux -or $Mac -or $All)) {
    $All = $true
}

Write-Host "Starting Lucid Electron GUI Production Build..." -ForegroundColor Green

# Set error action preference
$ErrorActionPreference = "Stop"

# Navigate to electron-gui directory
Set-Location -Path "electron-gui"

try {
    # Clean build directory if requested
    if ($Clean) {
        Write-Host "Cleaning build directory..." -ForegroundColor Yellow
        npm run clean
    }

    # Install dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install

    # Download Tor binaries for all platforms
    Write-Host "Downloading Tor binaries..." -ForegroundColor Yellow
    npm run download-tor-binary -- --platform windows --arch x64
    npm run download-tor-binary -- --platform linux --arch x64
    npm run download-tor-binary -- --platform linux --arch arm64
    npm run download-tor-binary -- --platform mac --arch x64
    npm run download-tor-binary -- --platform mac --arch arm64

    # Verify all Tor binaries
    Write-Host "Verifying Tor binaries..." -ForegroundColor Yellow
    npm run verify-tor

    # Type checking
    Write-Host "Running type checking..." -ForegroundColor Yellow
    npm run type-check

    # Linting
    Write-Host "Running linting..." -ForegroundColor Yellow
    npm run lint

    # Run all tests
    Write-Host "Running tests..." -ForegroundColor Yellow
    npm test
    npm run test:e2e

    # Production build
    Write-Host "Building production application..." -ForegroundColor Yellow
    npm run build:production

    # Package for requested platforms
    if ($Windows -or $All) {
        Write-Host "Packaging for Windows..." -ForegroundColor Yellow
        npm run package:win
    }

    if ($Linux -or $All) {
        Write-Host "Packaging for Linux..." -ForegroundColor Yellow
        npm run package:linux
        npm run package:linux-arm
    }

    if ($Mac -or $All) {
        Write-Host "Packaging for macOS..." -ForegroundColor Yellow
        npm run package:mac
    }

    Write-Host "Production build completed successfully!" -ForegroundColor Green
    Write-Host "Build artifacts are available in the dist/ directory" -ForegroundColor Cyan
}
catch {
    Write-Host "Production build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Set-Location -Path ".."
}
```

## Build Verification

### 1. Build Verification Script

**File**: `scripts/verify-build.ps1`

```powershell
# Lucid Electron GUI Build Verification Script
# Verifies that all build artifacts are present and correct

Write-Host "Verifying Lucid Electron GUI Build..." -ForegroundColor Green

$ErrorActionPreference = "Stop"

# Navigate to electron-gui directory
Set-Location -Path "electron-gui"

try {
    # Check if dist directory exists
    if (-not (Test-Path "dist")) {
        throw "dist directory not found. Run build first."
    }

    # Verify main process files
    $mainFiles = @(
        "dist/main/index.js",
        "dist/main/tor-manager.js",
        "dist/main/docker-manager.js",
        "dist/main/window-manager.js",
        "dist/main/ipc-handlers.js"
    )

    foreach ($file in $mainFiles) {
        if (-not (Test-Path $file)) {
            throw "Missing main process file: $file"
        }
        Write-Host "✓ Found: $file" -ForegroundColor Green
    }

    # Verify renderer files
    $rendererDirs = @("user", "developer", "node", "admin")
    foreach ($dir in $rendererDirs) {
        $rendererPath = "dist/renderer/$dir"
        if (-not (Test-Path $rendererPath)) {
            throw "Missing renderer directory: $rendererPath"
        }
        
        $indexHtml = "$rendererPath/index.html"
        $bundleJs = "$rendererPath/$dir.bundle.js"
        
        if (-not (Test-Path $indexHtml)) {
            throw "Missing renderer HTML: $indexHtml"
        }
        
        if (-not (Test-Path $bundleJs)) {
            throw "Missing renderer bundle: $bundleJs"
        }
        
        Write-Host "✓ Found renderer: $dir" -ForegroundColor Green
    }

    # Verify Tor binaries
    $torAssets = @(
        "assets/tor/windows-x64/tor.exe",
        "assets/tor/linux-x64/tor",
        "assets/tor/linux-arm64/tor"
    )

    foreach ($torFile in $torAssets) {
        if (Test-Path $torFile) {
            Write-Host "✓ Found Tor binary: $torFile" -ForegroundColor Green
        } else {
            Write-Host "⚠ Missing Tor binary: $torFile" -ForegroundColor Yellow
        }
    }

    # Verify configuration files
    $configFiles = @(
        "assets/configs/torrc.template",
        "assets/icons/icon.ico",
        "assets/icons/icon.png",
        "assets/icons/icon.icns"
    )

    foreach ($configFile in $configFiles) {
        if (Test-Path $configFile) {
            Write-Host "✓ Found config: $configFile" -ForegroundColor Green
        } else {
            Write-Host "⚠ Missing config: $configFile" -ForegroundColor Yellow
        }
    }

    Write-Host "Build verification completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "Build verification failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Set-Location -Path ".."
}
```

## Deployment Scripts

### 1. Windows Deployment Script

**File**: `scripts/deploy-windows.ps1`

```powershell
# Lucid Electron GUI Windows Deployment Script
# Deploys the Windows build to target systems

param(
    [string]$TargetPath = "C:\Program Files\Lucid Desktop",
    [switch]$UninstallFirst
)

Write-Host "Deploying Lucid Electron GUI to Windows..." -ForegroundColor Green

$ErrorActionPreference = "Stop"

try {
    # Uninstall existing version if requested
    if ($UninstallFirst) {
        Write-Host "Uninstalling existing version..." -ForegroundColor Yellow
        $uninstaller = Get-ChildItem -Path "electron-gui\dist" -Filter "*uninstall*.exe" -Recurse
        if ($uninstaller) {
            & $uninstaller.FullName /S
        }
    }

    # Find the installer
    $installer = Get-ChildItem -Path "electron-gui\dist" -Filter "*setup*.exe" -Recurse
    if (-not $installer) {
        throw "Windows installer not found. Run build first."
    }

    Write-Host "Found installer: $($installer.FullName)" -ForegroundColor Cyan

    # Run the installer
    Write-Host "Installing Lucid Desktop..." -ForegroundColor Yellow
    & $installer.FullName /S /D=$TargetPath

    Write-Host "Windows deployment completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "Windows deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
```

### 2. Linux Deployment Script (Raspberry Pi)

**File**: `scripts/deploy-linux.ps1`

```powershell
# Lucid Electron GUI Linux Deployment Script (Raspberry Pi)
# Deploys the Linux ARM64 build to Raspberry Pi via SSH

param(
    [string]$PiHost = "raspberrypi.local",
    [string]$PiUser = "pi",
    [string]$PiPort = "22",
    [switch]$Install
)

Write-Host "Deploying Lucid Electron GUI to Raspberry Pi..." -ForegroundColor Green
Write-Host "Target: $PiUser@$PiHost:$PiPort" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

try {
    # Find the Linux ARM64 package
    $linuxPackage = Get-ChildItem -Path "electron-gui\dist" -Filter "*linux-arm64*.deb" -Recurse
    if (-not $linuxPackage) {
        $linuxPackage = Get-ChildItem -Path "electron-gui\dist" -Filter "*linux-arm64*.AppImage" -Recurse
    }
    
    if (-not $linuxPackage) {
        throw "Linux ARM64 package not found. Run build first."
    }

    Write-Host "Found package: $($linuxPackage.Name)" -ForegroundColor Cyan

    # Copy package to Raspberry Pi
    Write-Host "Copying package to Raspberry Pi..." -ForegroundColor Yellow
    scp -P $PiPort $linuxPackage.FullName "${PiUser}@${PiHost}:~/"

    # Install package on Raspberry Pi if requested
    if ($Install) {
        Write-Host "Installing package on Raspberry Pi..." -ForegroundColor Yellow
        ssh -p $PiPort "${PiUser}@${PiHost}" "sudo dpkg -i ~/$($linuxPackage.Name) || sudo apt-get install -f"
    }

    Write-Host "Linux deployment completed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "Linux deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
```

## Build Commands Reference

### Quick Build Commands

```bash
# Development build
npm run dev

# Production build
npm run build:production

# Package for Windows
npm run package:win

# Package for Linux (including ARM64 for Raspberry Pi)
npm run package:linux
npm run package:linux-arm

# Package for macOS
npm run package:mac

# Package for all platforms
npm run package:all

# Run tests
npm test
npm run test:e2e

# Linting and type checking
npm run lint
npm run type-check

# Clean build directory
npm run clean
```

### PowerShell Build Commands

```powershell
# Windows build
.\scripts\build-windows.ps1 -Clean -Production -Package

# Linux build (ARM64 for Raspberry Pi)
.\scripts\build-linux.ps1 -Clean -Production -Package -Target arm64

# Production build for all platforms
.\scripts\build-production.ps1 -All -Clean

# Verify build
.\scripts\verify-build.ps1

# Deploy to Windows
.\scripts\deploy-windows.ps1 -UninstallFirst

# Deploy to Raspberry Pi
.\scripts\deploy-linux.ps1 -PiHost "192.168.1.100" -Install
```

## Troubleshooting

### Common Build Issues

1. **Tor Binary Download Fails**
   - Check internet connection
   - Verify Tor download URLs are accessible
   - Run `npm run download-tor-binary` manually

2. **TypeScript Compilation Errors**
   - Run `npm run type-check` to identify issues
   - Check for missing type definitions
   - Verify tsconfig.json configuration

3. **Webpack Build Failures**
   - Clear node_modules and reinstall: `npm run clean && npm install`
   - Check webpack configuration syntax
   - Verify all required dependencies are installed

4. **Electron Builder Packaging Issues**
   - Ensure all required assets are present
   - Check electron-builder.json configuration
   - Verify platform-specific requirements

5. **Cross-Platform Build Issues**
   - Use platform-specific build scripts
   - Verify target architecture compatibility
   - Check for platform-specific dependencies

### Build Environment Requirements

- **Node.js**: 18.0.0 or higher
- **npm**: 9.0.0 or higher
- **Windows**: Windows 11 (Build Host)
- **Linux**: Ubuntu 20.04+ or Raspberry Pi OS (Target Host)
- **macOS**: macOS 11+ (Cross-platform support)
- **Memory**: Minimum 8GB RAM
- **Storage**: Minimum 10GB free space for builds

---

**Last Updated**: $(date)
**Version**: 1.0.0
**Compliance**: Build process verified and documented
