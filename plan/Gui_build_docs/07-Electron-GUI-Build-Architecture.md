# Electron GUI Build Architecture Guide

## Overview

This document provides the complete build architecture for the Lucid Electron multi-GUI system, integrating with the Lucid API backend through Tor connections and Docker service management.

## Architecture Summary

### Multi-Window Electron Application
- **Main Process**: Manages 4 separate BrowserWindows (Admin, User, Developer, Node)
- **Renderer Processes**: 4 independent React-based UIs with shared components
- **IPC Communication**: Secure bidirectional communication between main and renderers
- **Tor Integration**: All API calls proxy through Tor SOCKS5 with green light indicator
- **Docker Management**: Main process orchestrates backend services

### Build Target Platforms
- **Primary**: Windows 11 (Build Host)
- **Secondary**: Linux ARM64 (Raspberry Pi - Target Host)
- **Tertiary**: macOS (Cross-platform support)

## Directory Structure

```
electron-gui/
├── main/                           # Main process (Node.js/TypeScript)
│   ├── index.ts                   # Main entry point
│   ├── window-manager.ts          # Window management
│   ├── tor-manager.ts             # Tor connection management
│   ├── ipc-handlers.ts            # IPC event handlers
│   ├── docker-service.ts          # Docker integration
│   └── preload.ts                 # Preload script for secure IPC
├── renderer/                       # Renderer processes (React/TypeScript)
│   ├── admin/                     # Admin GUI
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── admin.html
│   │   ├── pages/                 # 8 admin pages
│   │   ├── components/            # 15 admin components
│   │   ├── services/              # 9 admin services
│   │   └── store/                 # 7 admin stores
│   ├── user/                      # User GUI
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── user.html
│   │   ├── pages/                 # 6 user pages
│   │   ├── components/            # 5 user components
│   │   └── services/              # 4 user services
│   ├── developer/                 # Developer GUI
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── developer.html
│   │   ├── pages/                 # 6 developer pages
│   │   ├── components/            # 5 developer components
│   │   └── services/              # 4 developer services
│   ├── node/                      # Node Operator GUI
│   │   ├── index.tsx
│   │   ├── App.tsx
│   │   ├── node.html
│   │   ├── pages/                 # 6 node pages
│   │   ├── components/            # 5 node components
│   │   └── services/              # 4 node services
│   └── common/                    # Shared components
│       ├── components/            # 10 shared components
│       ├── hooks/                 # 2 shared hooks
│       └── store/                 # 1 shared store
├── shared/                         # Shared code
│   ├── api-client.ts              # ✓ EXISTS
│   ├── constants.ts               # ✓ EXISTS
│   ├── types.ts                   # ✓ EXISTS
│   ├── tor-types.ts               # NEW
│   ├── utils.ts                   # NEW
│   └── ipc-channels.ts            # NEW
├── assets/                         # Static assets
│   ├── icons/                     # Application icons
│   ├── images/                    # Images
│   └── tor/                       # Tor binaries
├── configs/                        # Configuration files
│   ├── webpack.main.config.js     # Main process webpack
│   ├── webpack.renderer.config.js  # Renderer webpack
│   ├── webpack.common.js          # Shared webpack config
│   ├── electron-builder.yml       # Build configuration
│   ├── tor.config.json            # Tor configuration
│   └── docker.config.json         # Docker configuration
└── tests/                          # Test files
    ├── main.spec.ts               # Main process tests
    ├── admin-gui.spec.ts          # Admin GUI tests
    ├── user-gui.spec.ts           # User GUI tests
    ├── developer-gui.spec.ts      # Developer GUI tests
    └── node-gui.spec.ts           # Node GUI tests
```

## Technology Stack

### Core Technologies
- **Electron 28.x**: Multi-process desktop application framework
- **React 18 + TypeScript**: Frontend UI components with strict typing
- **Webpack 5**: Module bundling and code splitting
- **Zustand**: Lightweight state management
- **Chart.js**: Data visualization
- **Tailwind CSS**: Utility-first CSS framework

### Build Tools
- **Electron Builder**: Cross-platform packaging and distribution
- **TypeScript**: Static type checking
- **ESLint + Prettier**: Code quality and formatting
- **Jest**: Unit testing framework
- **Spectron**: E2E testing for Electron

### Integration Technologies
- **Tor Integration**: SOCKS5 proxy for all external communication
- **Docker API**: Backend service orchestration
- **WebSocket**: Real-time updates
- **Hardware Wallet**: TRON payment integration

## Main Process Architecture

### 1. Window Management (`main/window-manager.ts`)

```typescript
interface WindowConfig {
  id: 'admin' | 'user' | 'developer' | 'node';
  title: string;
  width: number;
  height: number;
  webPreferences: {
    nodeIntegration: false;
    contextIsolation: true;
    preload: string;
  };
}

class WindowManager {
  private windows: Map<string, BrowserWindow> = new Map();
  
  createWindow(config: WindowConfig): BrowserWindow;
  closeWindow(id: string): void;
  focusWindow(id: string): void;
  getAllWindows(): BrowserWindow[];
}
```

### 2. Tor Management (`main/tor-manager.ts`)

```typescript
interface TorStatus {
  connected: boolean;
  status: 'connecting' | 'connected' | 'disconnected';
  circuitCount: number;
  lastConnected: Date;
}

class TorManager {
  private torProcess: ChildProcess | null = null;
  private status: TorStatus;
  
  async startTor(): Promise<void>;
  async stopTor(): Promise<void>;
  getStatus(): TorStatus;
  isConnected(): boolean;
  private setupTorConfig(): void;
}
```

### 3. Docker Service Management (`main/docker-service.ts`)

```typescript
interface ServiceStatus {
  name: string;
  status: 'running' | 'stopped' | 'error';
  port: number;
  health: 'healthy' | 'unhealthy';
}

class DockerService {
  private docker: Docker;
  
  async startServices(): Promise<void>;
  async stopServices(): Promise<void>;
  getServiceStatus(): ServiceStatus[];
  async restartService(serviceName: string): Promise<void>;
}
```

### 4. IPC Handlers (`main/ipc-handlers.ts`)

```typescript
// Secure IPC channel definitions
const IPC_CHANNELS = {
  // Tor management
  TOR_STATUS: 'tor:status',
  TOR_CONNECT: 'tor:connect',
  TOR_DISCONNECT: 'tor:disconnect',
  
  // API communication
  API_REQUEST: 'api:request',
  API_RESPONSE: 'api:response',
  
  // Docker management
  DOCKER_STATUS: 'docker:status',
  DOCKER_START: 'docker:start',
  DOCKER_STOP: 'docker:stop',
  
  // Window management
  WINDOW_FOCUS: 'window:focus',
  WINDOW_CLOSE: 'window:close',
} as const;
```

## Renderer Process Architecture

### 1. Shared Components (`renderer/common/`)

#### TorIndicator Component
```typescript
interface TorIndicatorProps {
  status: TorStatus;
  showDetails?: boolean;
}

const TorIndicator: React.FC<TorIndicatorProps> = ({ status, showDetails }) => {
  return (
    <div className="flex items-center space-x-2">
      <div className={`w-3 h-3 rounded-full ${
        status.connected ? 'bg-green-500' : 'bg-red-500'
      }`} />
      <span className="text-sm">
        {status.connected ? 'Secure Connection' : 'Disconnected'}
      </span>
    </div>
  );
};
```

#### API Hook (`renderer/common/hooks/useApi.ts`)
```typescript
interface ApiResponse<T> {
  data: T;
  error?: string;
  loading: boolean;
}

const useApi = <T>(endpoint: string, options?: RequestInit) => {
  const [response, setResponse] = useState<ApiResponse<T>>({
    data: null,
    loading: true
  });
  
  // Implementation with Tor proxy
  return response;
};
```

### 2. Admin GUI Structure

#### Pages (8 total)
- `DashboardPage.tsx` - System overview with metrics
- `SessionsPage.tsx` - Session management
- `UsersPage.tsx` - User management
- `NodesPage.tsx` - Node management
- `BlockchainPage.tsx` - Blockchain operations
- `AuditPage.tsx` - Audit logs
- `ConfigPage.tsx` - System configuration
- `LoginPage.tsx` - Admin authentication

#### Components (15 total)
- `AdminHeader.tsx` - Header with Tor status
- `AdminSidebar.tsx` - Navigation sidebar
- `SessionsTable.tsx` - Sessions data table
- `UsersTable.tsx` - Users data table
- `NodesTable.tsx` - Nodes data table
- `BlockchainStatusCard.tsx` - Blockchain status
- `AnchoringQueueTable.tsx` - Anchoring queue
- `RecentBlocksTable.tsx` - Recent blocks
- `ActivityFeed.tsx` - Recent activity
- `ChartCard.tsx` - Chart wrapper
- `ActionButton.tsx` - Styled buttons
- `FilterSection.tsx` - Table filters
- `PaginationControls.tsx` - Pagination
- `LoadingOverlay.tsx` - Loading states
- `OverviewCard.tsx` - Metric cards

#### Services (9 total)
- `adminApi.ts` - Admin-specific API methods
- `dashboardService.ts` - Dashboard data
- `sessionService.ts` - Session operations
- `userService.ts` - User operations
- `nodeService.ts` - Node operations
- `blockchainService.ts` - Blockchain operations
- `auditService.ts` - Audit operations
- `configService.ts` - Configuration management
- `websocketService.ts` - Real-time updates

### 3. User GUI Structure

#### Pages (6 total)
- `SessionsPage.tsx` - User's active sessions
- `CreateSessionPage.tsx` - Create new session
- `HistoryPage.tsx` - Session history
- `WalletPage.tsx` - TRON wallet integration
- `SettingsPage.tsx` - User settings
- `ProfilePage.tsx` - User profile

#### Components (5 total)
- `UserHeader.tsx` - User header with Tor indicator
- `SessionCard.tsx` - Session display card
- `WalletBalance.tsx` - Wallet balance display
- `SessionControls.tsx` - Session action buttons
- `PaymentHistory.tsx` - Payment transaction list

### 4. Developer GUI Structure

#### Pages (6 total)
- `APIExplorerPage.tsx` - API endpoint explorer
- `LogsPage.tsx` - System logs viewer
- `MetricsPage.tsx` - System metrics dashboard
- `DocumentationPage.tsx` - API documentation
- `TestingPage.tsx` - API testing interface
- `DebugPage.tsx` - Debug tools and utilities

### 5. Node Operator GUI Structure

#### Pages (6 total)
- `NodeDashboardPage.tsx` - Node status overview
- `ResourcesPage.tsx` - Resource monitoring
- `EarningsPage.tsx` - Node earnings and payouts
- `PoolPage.tsx` - Pool management
- `ConfigurationPage.tsx` - Node configuration
- `MaintenancePage.tsx` - Maintenance tools

## Build Configuration

### 1. Webpack Configuration

#### Main Process (`webpack.main.config.js`)
```javascript
const path = require('path');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

module.exports = {
  target: 'electron-main',
  entry: './main/index.ts',
  output: {
    path: path.resolve(__dirname, 'dist/main'),
    filename: 'index.js'
  },
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: 'ts-loader',
        exclude: /node_modules/
      }
    ]
  },
  resolve: {
    extensions: ['.ts', '.js']
  },
  plugins: [
    new CleanWebpackPlugin()
  ]
};
```

#### Renderer Process (`webpack.renderer.config.js`)
```javascript
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  target: 'electron-renderer',
  entry: {
    admin: './renderer/admin/index.tsx',
    user: './renderer/user/index.tsx',
    developer: './renderer/developer/index.tsx',
    node: './renderer/node/index.tsx'
  },
  output: {
    path: path.resolve(__dirname, 'dist/renderer'),
    filename: '[name]/[name].js'
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader', 'postcss-loader']
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './renderer/admin/admin.html',
      filename: 'admin/admin.html',
      chunks: ['admin']
    }),
    // Similar for other GUIs
  ]
};
```

### 2. Electron Builder Configuration (`electron-builder.yml`)

```yaml
appId: com.lucid.electron-gui
productName: Lucid GUI
directories:
  output: dist
  buildResources: assets
files:
  - main/**/*
  - renderer/**/*
  - shared/**/*
  - assets/**/*
  - configs/**/*
  - "!**/*.ts"
  - "!**/*.tsx"
  - "!node_modules"
win:
  target:
    - target: nsis
      arch: [x64, arm64]
  icon: assets/icons/icon.ico
linux:
  target:
    - target: AppImage
      arch: [x64, arm64]
  icon: assets/icons/icon.png
  category: Network
mac:
  target:
    - target: dmg
      arch: [x64, arm64]
  icon: assets/icons/icon.icns
  category: public.app-category.networking
```

## Security Architecture

### 1. Context Isolation
- **Enabled**: All renderer processes use context isolation
- **Node Integration**: Disabled in all renderer processes
- **Preload Scripts**: Secure IPC communication only

### 2. Tor Integration
- **SOCKS5 Proxy**: All external communication through Tor
- **Circuit Management**: Automatic circuit rotation
- **Connection Status**: Real-time status updates via IPC

### 3. API Security
- **Authentication**: JWT tokens with hardware wallet integration
- **Rate Limiting**: Client-side rate limiting
- **Request Validation**: Input sanitization and validation

### 4. Docker Security
- **Container Isolation**: Services run in isolated containers
- **Health Checks**: Regular service health monitoring
- **Resource Limits**: CPU and memory limits per service

## Development Workflow

### 1. Development Setup
```bash
# Install dependencies
npm install

# Start development servers
npm run dev:main      # Main process with hot reload
npm run dev:admin     # Admin GUI with hot reload
npm run dev:user      # User GUI with hot reload
npm run dev:developer # Developer GUI with hot reload
npm run dev:node      # Node GUI with hot reload

# Start Tor proxy
npm run tor:start

# Start Docker services
npm run docker:start
```

### 2. Build Process
```bash
# Development build
npm run build:dev

# Production build
npm run build:prod

# Package for distribution
npm run package:win
npm run package:linux
npm run package:mac
```

### 3. Testing
```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Integration tests
npm run test:integration
```

## Integration Points

### 1. API Gateway Integration
- **Base URL**: `http://localhost:8080` (via Tor proxy)
- **Authentication**: JWT tokens
- **Rate Limiting**: Client-side enforcement
- **Error Handling**: Standardized error responses

### 2. Blockchain Core Integration
- **WebSocket**: Real-time blockchain updates
- **REST API**: Blockchain operations
- **Session Anchoring**: Automatic session anchoring

### 3. TRON Payment Integration
- **Hardware Wallet**: Secure key management
- **USDT-TRC20**: Payment processing
- **Wallet Management**: Balance and transaction history

### 4. Docker Service Integration
- **Service Discovery**: Automatic service detection
- **Health Monitoring**: Service health checks
- **Log Aggregation**: Centralized logging

## Performance Considerations

### 1. Memory Management
- **Window Pooling**: Reuse window instances
- **Component Lazy Loading**: Load components on demand
- **Memory Cleanup**: Proper cleanup on window close

### 2. Network Optimization
- **Request Batching**: Batch API requests
- **Caching**: Client-side response caching
- **Compression**: Gzip compression for large responses

### 3. UI Performance
- **Virtual Scrolling**: For large data tables
- **Debounced Search**: Optimize search performance
- **Chart Optimization**: Efficient data visualization

## Deployment Strategy

### 1. Development Environment
- **Local Development**: Full stack on Windows 11
- **Docker Compose**: Backend services
- **Hot Reload**: Development with hot reload

### 2. Production Environment
- **Raspberry Pi**: Target deployment platform
- **Distroless Containers**: Secure backend services
- **Tor Integration**: Anonymous communication
- **Auto-updates**: Electron auto-updater

### 3. Distribution
- **Windows**: NSIS installer
- **Linux**: AppImage format
- **macOS**: DMG package
- **Code Signing**: Digital signatures for all platforms

## Monitoring and Maintenance

### 1. Health Monitoring
- **Service Health**: Docker service status
- **Tor Status**: Connection monitoring
- **API Health**: Backend service health
- **Performance Metrics**: Response times and resource usage

### 2. Logging
- **Structured Logging**: JSON format logs
- **Log Levels**: DEBUG, INFO, WARN, ERROR
- **Log Rotation**: Automatic log rotation
- **Centralized Logging**: Aggregated logs

### 3. Updates
- **Auto-updates**: Electron auto-updater
- **Rollback**: Automatic rollback on failure
- **Version Management**: Semantic versioning
- **Release Notes**: Detailed release information

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
