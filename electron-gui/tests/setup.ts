// tests/setup.ts - Jest setup file for unit tests
// Based on the electron-multi-gui-development.plan.md specifications

import '@testing-library/jest-dom';

// Mock Electron modules
jest.mock('electron', () => ({
  ipcMain: {
    handle: jest.fn(),
    on: jest.fn(),
    removeHandler: jest.fn(),
    removeAllListeners: jest.fn()
  },
  ipcRenderer: {
    invoke: jest.fn(),
    on: jest.fn(),
    removeListener: jest.fn(),
    removeAllListeners: jest.fn()
  },
  BrowserWindow: jest.fn().mockImplementation(() => ({
    loadFile: jest.fn(),
    loadURL: jest.fn(),
    webContents: {
      send: jest.fn(),
      on: jest.fn(),
      session: {
        cookies: {
          set: jest.fn(),
          remove: jest.fn(),
          get: jest.fn()
        }
      }
    },
    on: jest.fn(),
    show: jest.fn(),
    hide: jest.fn(),
    close: jest.fn(),
    destroy: jest.fn(),
    isVisible: jest.fn(() => true),
    isFocused: jest.fn(() => false),
    focus: jest.fn(),
    minimize: jest.fn(),
    maximize: jest.fn(),
    restore: jest.fn(),
    setPosition: jest.fn(),
    setSize: jest.fn(),
    center: jest.fn(),
    setAlwaysOnTop: jest.fn()
  })),
  app: {
    whenReady: jest.fn(() => Promise.resolve()),
    on: jest.fn(),
    quit: jest.fn(),
    getName: jest.fn(() => 'Lucid Electron GUI'),
    getVersion: jest.fn(() => '1.0.0'),
    getPath: jest.fn((path) => `/mock/path/${path}`),
    setPath: jest.fn(),
    isReady: jest.fn(() => true),
    requestSingleInstanceLock: jest.fn(() => true),
    releaseSingleInstanceLock: jest.fn()
  },
  dialog: {
    showOpenDialog: jest.fn(),
    showSaveDialog: jest.fn(),
    showMessageBox: jest.fn(),
    showErrorBox: jest.fn()
  },
  shell: {
    openExternal: jest.fn(),
    openPath: jest.fn(),
    showItemInFolder: jest.fn()
  },
  Notification: jest.fn(),
  Menu: {
    setApplicationMenu: jest.fn(),
    buildFromTemplate: jest.fn()
  },
  MenuItem: jest.fn()
}));

// Mock Node.js modules
jest.mock('child_process', () => ({
  spawn: jest.fn(() => ({
    pid: 12345,
    kill: jest.fn(),
    on: mockedOn,
    stdout: {
      on: jest.fn()
    },
    stderr: {
      on: jest.fn()
    }
  })),
  exec: jest.fn(),
  execSync: jest.fn()
}));

jest.mock('fs', () => ({
  existsSync: jest.fn(),
  readFileSync: jest.fn(),
  writeFileSync: jest.fn(),
  mkdirSync: jest.fn(),
  readdirSync: jest.fn(),
  statSync: jest.fn(),
  watch: jest.fn(),
  createReadStream: jest.fn(),
  createWriteStream: jest.fn()
}));

jest.mock('path', () => ({
  join: jest.fn((...args) => args.join('/')),
  resolve: jest.fn((...args) => args.join('/')),
  dirname: jest.fn((path) => path.split('/').slice(0, -1).join('/')),
  basename: jest.fn((path) => path.split('/').pop()),
  extname: jest.fn((path) => {
    const parts = path.split('.');
    return parts.length > 1 ? `.${parts.pop()}` : '';
  })
}));

// Mock fetch for API tests
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    headers: new Map()
  })
) as jest.Mock;

// Mock WebSocket
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN
})) as any;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn()
};
global.localStorage = localStorageMock;

// Mock sessionStorage
global.sessionStorage = { ...localStorageMock };

// Mock console methods to reduce noise in tests
const originalConsole = { ...console };
global.console = {
  ...originalConsole,
  log: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  info: jest.fn(),
  debug: jest.fn()
};

// Mock performance API
global.performance = {
  now: jest.fn(() => Date.now()),
  mark: jest.fn(),
  measure: jest.fn(),
  getEntriesByType: jest.fn(() => []),
  getEntriesByName: jest.fn(() => [])
} as any;

// Mock crypto API
global.crypto = {
  randomUUID: jest.fn(() => 'mock-uuid-123'),
  getRandomValues: jest.fn((arr) => {
    for (let i = 0; i < arr.length; i++) {
      arr[i] = Math.floor(Math.random() * 256);
    }
    return arr;
  })
} as any;

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn()
})) as any;

// Mock ResizeObserver
global.ResizeObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn()
})) as any;

// Mock MutationObserver
global.MutationObserver = jest.fn(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  takeRecords: jest.fn(() => [])
})) as any;

// Helper function for mocked on events
function mockedOn(event: string, callback: Function) {
  if (event === 'exit') {
    // Simulate process exit after a short delay
    setTimeout(() => callback(0), 100);
  }
  return {
    on: mockedOn,
    kill: jest.fn()
  };
}

// Setup test environment
beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks();
  
  // Reset localStorage mock
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();
  localStorageMock.clear.mockClear();
  
  // Reset fetch mock
  (global.fetch as jest.Mock).mockClear();
  
  // Reset console mocks
  jest.clearAllMocks();
});

afterEach(() => {
  // Clean up after each test
  jest.restoreAllMocks();
});

// Global test utilities
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R;
      toHaveClass(className: string): R;
      toHaveAttribute(attr: string, value?: string): R;
      toHaveTextContent(text: string): R;
      toBeVisible(): R;
      toBeDisabled(): R;
      toBeEnabled(): R;
      toHaveValue(value: string): R;
      toBeChecked(): R;
      toBePartiallyChecked(): R;
      toHaveFocus(): R;
      toBeRequired(): R;
      toBeInvalid(): R;
      toBeValid(): R;
      toHaveDisplayValue(value: string | RegExp): R;
      toHaveFormValues(values: Record<string, any>): R;
      toHaveAccessibleDescription(description?: string): R;
      toHaveAccessibleName(name?: string): R;
    }
  }
}
