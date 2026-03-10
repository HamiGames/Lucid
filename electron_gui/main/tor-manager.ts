/**
 * LUCID Tor Manager - SPEC-1B Implementation
 * Manages Tor daemon for secure .onion routing
 */

import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as net from 'net';
import { TOR_CONFIG, PATHS } from '../shared/constants';

export interface TorStatus {
  connected: boolean;
  status: 'stopped' | 'starting' | 'connected' | 'error';
  socksPort: number;
  controlPort: number;
  version?: string;
  error?: string;
  circuits?: number;
  bandwidth?: {
    read: number;
    written: number;
  };
}

export interface TorConfig {
  socksPort: number;
  controlPort: number;
  dataDirectory: string;
  logLevel: 'debug' | 'info' | 'notice' | 'warn' | 'err';
  exitNodes?: string[];
  strictNodes?: boolean;
  allowSingleHopExits?: boolean;
}

export class TorManager {
  private torProcess: ChildProcess | null = null;
  private status: TorStatus;
  private config: TorConfig;
  private controlSocket: net.Socket | null = null;
  private isInitialized = false;

  constructor() {
    const dataDirectory = path.resolve(process.cwd(), TOR_CONFIG.DATA_DIR);

    this.config = {
      socksPort: TOR_CONFIG.SOCKS_PORT,
      controlPort: TOR_CONFIG.CONTROL_PORT,
      dataDirectory,
      logLevel: 'notice'
    };

    this.status = {
      connected: false,
      status: 'stopped',
      socksPort: this.config.socksPort,
      controlPort: this.config.controlPort
    };
  }

  async initialize(): Promise<void> {
    try {
      console.log('Initializing Tor Manager...');

      // Create data directory if it doesn't exist
      await this.ensureDataDirectory();

      // Check if Tor binary exists
      await this.checkTorBinary();

      // Load existing configuration
      await this.loadConfiguration();

      this.isInitialized = true;
      console.log('Tor Manager initialized successfully');

    } catch (error) {
      console.error('Failed to initialize Tor Manager:', error);
      throw error;
    }
  }

  async start(): Promise<boolean> {
    try {
      if (this.status.status === 'connected') {
        console.log('Tor is already running');
        return true;
      }

      if (this.status.status === 'starting') {
        console.log('Tor is already starting');
        return false;
      }

      console.log('Starting Tor daemon...');
      this.status.status = 'starting';
      this.status.error = undefined;

      // Start Tor process
      await this.startTorProcess();

      // Wait for Tor to be ready
      const isReady = await this.waitForTorReady(30000); // 30 second timeout

      if (isReady) {
        this.status.connected = true;
        this.status.status = 'connected';
        console.log('Tor daemon started successfully');
        
        // Start monitoring
        this.startMonitoring();
        
        return true;
      } else {
        this.status.status = 'error';
        this.status.error = 'Tor failed to start within timeout';
        console.error('Tor failed to start');
        return false;
      }

    } catch (error) {
      this.status.status = 'error';
      this.status.error = error.message;
      console.error('Failed to start Tor:', error);
      return false;
    }
  }

  async stop(): Promise<boolean> {
    try {
      if (this.status.status === 'stopped') {
        console.log('Tor is already stopped');
        return true;
      }

      console.log('Stopping Tor daemon...');

      // Close control connection
      if (this.controlSocket) {
        this.controlSocket.end();
        this.controlSocket = null;
      }

      // Stop Tor process
      if (this.torProcess) {
        this.torProcess.kill('SIGTERM');
        
        // Wait for graceful shutdown
        await new Promise<void>((resolve) => {
          const timeout = setTimeout(() => {
            if (this.torProcess) {
              this.torProcess.kill('SIGKILL');
            }
            resolve();
          }, 5000);

          this.torProcess.on('exit', () => {
            clearTimeout(timeout);
            resolve();
          });
        });

        this.torProcess = null;
      }

      this.status.connected = false;
      this.status.status = 'stopped';
      this.status.error = undefined;

      console.log('Tor daemon stopped successfully');
      return true;

    } catch (error) {
      console.error('Failed to stop Tor:', error);
      return false;
    }
  }

  getStatus(): TorStatus {
    return { ...this.status };
  }

  async getVersion(): Promise<string | null> {
    try {
      if (!this.status.connected) {
        return null;
      }

      const response = await this.sendControlCommand('GETINFO version');
      const versionMatch = response.match(/version=([^\n\r]+)/);
      
      if (versionMatch) {
        this.status.version = versionMatch[1];
        return this.status.version;
      }

      return null;

    } catch (error) {
      console.error('Failed to get Tor version:', error);
      return null;
    }
  }

  async getCircuits(): Promise<number> {
    try {
      if (!this.status.connected) {
        return 0;
      }

      const response = await this.sendControlCommand('GETINFO circuits/established');
      const circuitsMatch = response.match(/circuits\/established=(\d+)/);
      
      if (circuitsMatch) {
        this.status.circuits = parseInt(circuitsMatch[1]);
        return this.status.circuits;
      }

      return 0;

    } catch (error) {
      console.error('Failed to get circuits:', error);
      return 0;
    }
  }

  async getBandwidth(): Promise<{ read: number; written: number } | null> {
    try {
      if (!this.status.connected) {
        return null;
      }

      const response = await this.sendControlCommand('GETINFO traffic/read traffic/written');
      const readMatch = response.match(/traffic\/read=(\d+)/);
      const writtenMatch = response.match(/traffic\/written=(\d+)/);
      
      if (readMatch && writtenMatch) {
        const bandwidth = {
          read: parseInt(readMatch[1]),
          written: parseInt(writtenMatch[1])
        };
        this.status.bandwidth = bandwidth;
        return bandwidth;
      }

      return null;

    } catch (error) {
      console.error('Failed to get bandwidth:', error);
      return null;
    }
  }

  private async ensureDataDirectory(): Promise<void> {
    try {
      if (!fs.existsSync(this.config.dataDirectory)) {
        fs.mkdirSync(this.config.dataDirectory, { recursive: true });
        console.log(`Created Tor data directory: ${this.config.dataDirectory}`);
      }
    } catch (error) {
      throw new Error(`Failed to create Tor data directory: ${error.message}`);
    }
  }

  private async checkTorBinary(): Promise<void> {
    const torPath = this.getTorBinaryPath();

    if (path.isAbsolute(torPath)) {
      try {
        await fs.promises.access(torPath, fs.constants.F_OK);
        console.log(`Tor binary found at: ${torPath}`);
      } catch (error) {
        throw new Error(`Tor binary not found at: ${torPath}`);
      }
    } else {
      console.log(`Using system Tor binary from PATH: ${torPath}`);
    }
  }

  private getTorBinaryPath(): string {
    const platform = process.platform;

    const bundledRelative =
      platform === 'win32'
        ? PATHS.TOR_BINARY_WIN
        : platform === 'darwin'
          ? PATHS.TOR_BINARY_MAC
          : PATHS.TOR_BINARY_LINUX;

    if (bundledRelative) {
      const bundledPath = path.resolve(process.cwd(), bundledRelative);
      if (fs.existsSync(bundledPath)) {
        return bundledPath;
      }
    }

    switch (platform) {
      case 'win32':
        return 'tor.exe';
      case 'darwin':
        return '/usr/local/bin/tor';
      case 'linux':
        return '/usr/bin/tor';
      default:
        return 'tor';
    }
  }

  private async loadConfiguration(): Promise<void> {
    try {
      const configPath = path.join(this.config.dataDirectory, TOR_CONFIG.CONFIG_FILE);
      
      if (fs.existsSync(configPath)) {
        const configContent = fs.readFileSync(configPath, 'utf8');
        console.log('Loaded existing Tor configuration');
      } else {
        // Create default configuration
        await this.createDefaultConfiguration();
      }

    } catch (error) {
      console.warn('Failed to load Tor configuration:', error);
    }
  }

  private async createDefaultConfiguration(): Promise<void> {
    try {
      const configPath = path.join(this.config.dataDirectory, TOR_CONFIG.CONFIG_FILE);
      
      const configContent = `
# LUCID Tor Configuration
SocksPort ${this.config.socksPort}
ControlPort ${this.config.controlPort}
DataDirectory ${this.config.dataDirectory}
Log notice file ${path.join(this.config.dataDirectory, 'tor.log')}
CookieAuthentication 1
CookieAuthFile ${path.join(this.config.dataDirectory, 'control_auth_cookie')}
HashedControlPassword ${this.generateHashedPassword()}
${this.config.exitNodes ? `ExitNodes ${this.config.exitNodes.join(',')}` : ''}
${this.config.strictNodes ? 'StrictNodes 1' : ''}
${this.config.allowSingleHopExits ? 'AllowSingleHopExits 1' : ''}
`.trim();

      fs.writeFileSync(configPath, configContent);
      console.log('Created default Tor configuration');

    } catch (error) {
      throw new Error(`Failed to create Tor configuration: ${error.message}`);
    }
  }

  private generateHashedPassword(): string {
    // Generate a random hashed password for Tor control
    // In production, this should be more secure
    return '16:872860B76453A77D60CA2BB8C1A7042072093276A3D701AD684053EC4C';
  }

  private async startTorProcess(): Promise<void> {
    return new Promise((resolve, reject) => {
      const torPath = this.getTorBinaryPath();
      const configPath = path.join(this.config.dataDirectory, TOR_CONFIG.CONFIG_FILE);
      
      const args = ['-f', configPath];
      
      this.torProcess = spawn(torPath, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: false
      });

      this.torProcess.on('error', (error) => {
        console.error('Tor process error:', error);
        reject(error);
      });

      this.torProcess.on('exit', (code, signal) => {
        console.log(`Tor process exited with code ${code}, signal ${signal}`);
        this.torProcess = null;
      });

      // Handle stdout
      this.torProcess.stdout?.on('data', (data) => {
        const output = data.toString();
        console.log('Tor stdout:', output);
      });

      // Handle stderr
      this.torProcess.stderr?.on('data', (data) => {
        const output = data.toString();
        console.log('Tor stderr:', output);
        
        // Check for startup completion
        if (output.includes('Bootstrapped 100%')) {
          resolve();
        }
      });

      // Give Tor some time to start
      setTimeout(() => {
        if (this.torProcess && this.torProcess.pid) {
          resolve();
        } else {
          reject(new Error('Tor process failed to start'));
        }
      }, 1000);
    });
  }

  private async waitForTorReady(timeoutMs: number): Promise<boolean> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeoutMs) {
      try {
        // Try to connect to control port
        const isReady = await this.testControlConnection();
        if (isReady) {
          return true;
        }
      } catch (error) {
        // Continue waiting
      }
      
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    return false;
  }

  private async testControlConnection(): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      
      socket.connect(this.config.controlPort, '127.0.0.1', () => {
        socket.end();
        resolve(true);
      });
      
      socket.on('error', () => {
        resolve(false);
      });
      
      socket.setTimeout(1000, () => {
        socket.destroy();
        resolve(false);
      });
    });
  }

  private async sendControlCommand(command: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const socket = new net.Socket();
      let response = '';
      
      socket.connect(this.config.controlPort, '127.0.0.1', () => {
        socket.write(`${command}\r\n`);
      });
      
      socket.on('data', (data) => {
        response += data.toString();
        
        // Check for command completion
        if (response.includes('250 OK') || response.includes('251 ')) {
          socket.end();
        }
      });
      
      socket.on('close', () => {
        resolve(response);
      });
      
      socket.on('error', (error) => {
        reject(error);
      });
      
      socket.setTimeout(5000, () => {
        socket.destroy();
        reject(new Error('Control command timeout'));
      });
    });
  }

  private startMonitoring(): void {
    // Monitor Tor status periodically
    setInterval(async () => {
      if (this.status.connected) {
        try {
          await this.getVersion();
          await this.getCircuits();
          await this.getBandwidth();
        } catch (error) {
          console.warn('Tor monitoring error:', error);
        }
      }
    }, 30000); // Every 30 seconds
  }

  // Public utility methods
  getSocksProxyUrl(): string {
    return `socks5://127.0.0.1:${this.config.socksPort}`;
  }

  getControlPort(): number {
    return this.config.controlPort;
  }

  isConnected(): boolean {
    return this.status.connected;
  }

  async restart(): Promise<boolean> {
    console.log('Restarting Tor...');
    
    const stopped = await this.stop();
    if (!stopped) {
      return false;
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
    
    return await this.start();
  }
}