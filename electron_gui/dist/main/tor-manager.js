"use strict";
/**
 * LUCID Tor Manager - SPEC-1B Implementation
 * Manages Tor daemon for secure .onion routing
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.TorManager = void 0;
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const net = __importStar(require("net"));
const events_1 = require("events");
const constants_1 = require("../shared/constants");
class TorManager extends events_1.EventEmitter {
    constructor() {
        super();
        this.torProcess = null;
        this.controlSocket = null;
        this.isInitialized = false;
        const dataDirectory = path.resolve(process.cwd(), constants_1.TOR_CONFIG.DATA_DIR);
        this.config = {
            socksPort: constants_1.TOR_CONFIG.SOCKS_PORT,
            controlPort: constants_1.TOR_CONFIG.CONTROL_PORT,
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
    async initialize() {
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
        }
        catch (error) {
            console.error('Failed to initialize Tor Manager:', error);
            throw error;
        }
    }
    async start() {
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
            }
            else {
                this.status.status = 'error';
                this.status.error = 'Tor failed to start within timeout';
                console.error('Tor failed to start');
                return false;
            }
        }
        catch (error) {
            this.status.status = 'error';
            this.status.error = error instanceof Error ? error.message : String(error);
            console.error('Failed to start Tor:', error);
            return false;
        }
    }
    async stop() {
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
                await new Promise((resolve) => {
                    const timeout = setTimeout(() => {
                        if (this.torProcess) {
                            this.torProcess.kill('SIGKILL');
                        }
                        resolve();
                    }, 5000);
                    this.torProcess?.on('exit', () => {
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
        }
        catch (error) {
            console.error('Failed to stop Tor:', error);
            return false;
        }
    }
    getStatus() {
        return { ...this.status };
    }
    async getVersion() {
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
        }
        catch (error) {
            console.error('Failed to get Tor version:', error);
            return null;
        }
    }
    async getCircuits() {
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
        }
        catch (error) {
            console.error('Failed to get circuits:', error);
            return 0;
        }
    }
    async getBandwidth() {
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
        }
        catch (error) {
            console.error('Failed to get bandwidth:', error);
            return null;
        }
    }
    async ensureDataDirectory() {
        try {
            if (!fs.existsSync(this.config.dataDirectory)) {
                fs.mkdirSync(this.config.dataDirectory, { recursive: true });
                console.log(`Created Tor data directory: ${this.config.dataDirectory}`);
            }
        }
        catch (error) {
            throw new Error(`Failed to create Tor data directory: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async checkTorBinary() {
        const torPath = this.getTorBinaryPath();
        if (path.isAbsolute(torPath)) {
            try {
                await fs.promises.access(torPath, fs.constants.F_OK);
                console.log(`Tor binary found at: ${torPath}`);
            }
            catch (error) {
                throw new Error(`Tor binary not found at: ${torPath}`);
            }
        }
        else {
            console.log(`Using system Tor binary from PATH: ${torPath}`);
        }
    }
    getTorBinaryPath() {
        const platform = process.platform;
        const bundledRelative = platform === 'win32'
            ? constants_1.PATHS.TOR_BINARY_WIN
            : platform === 'darwin'
                ? constants_1.PATHS.TOR_BINARY_MAC
                : constants_1.PATHS.TOR_BINARY_LINUX;
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
    async loadConfiguration() {
        try {
            const configPath = path.join(this.config.dataDirectory, constants_1.TOR_CONFIG.CONFIG_FILE);
            if (fs.existsSync(configPath)) {
                const configContent = fs.readFileSync(configPath, 'utf8');
                console.log('Loaded existing Tor configuration');
            }
            else {
                // Create default configuration
                await this.createDefaultConfiguration();
            }
        }
        catch (error) {
            console.warn('Failed to load Tor configuration:', error);
        }
    }
    async createDefaultConfiguration() {
        try {
            const configPath = path.join(this.config.dataDirectory, constants_1.TOR_CONFIG.CONFIG_FILE);
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
        }
        catch (error) {
            throw new Error(`Failed to create Tor configuration: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    generateHashedPassword() {
        // Generate a random hashed password for Tor control
        // In production, this should be more secure
        return '16:872860B76453A77D60CA2BB8C1A7042072093276A3D701AD684053EC4C';
    }
    async startTorProcess() {
        return new Promise((resolve, reject) => {
            const torPath = this.getTorBinaryPath();
            const configPath = path.join(this.config.dataDirectory, constants_1.TOR_CONFIG.CONFIG_FILE);
            const args = ['-f', configPath];
            this.torProcess = (0, child_process_1.spawn)(torPath, args, {
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
                }
                else {
                    reject(new Error('Tor process failed to start'));
                }
            }, 1000);
        });
    }
    async waitForTorReady(timeoutMs) {
        const startTime = Date.now();
        while (Date.now() - startTime < timeoutMs) {
            try {
                // Try to connect to control port
                const isReady = await this.testControlConnection();
                if (isReady) {
                    return true;
                }
            }
            catch (error) {
                // Continue waiting
            }
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        return false;
    }
    async testControlConnection() {
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
    async sendControlCommand(command) {
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
    startMonitoring() {
        // Monitor Tor status periodically
        setInterval(async () => {
            if (this.status.connected) {
                try {
                    await this.getVersion();
                    await this.getCircuits();
                    await this.getBandwidth();
                }
                catch (error) {
                    console.warn('Tor monitoring error:', error);
                }
            }
        }, 30000); // Every 30 seconds
    }
    // Public utility methods
    getSocksProxyUrl() {
        return `socks5://127.0.0.1:${this.config.socksPort}`;
    }
    getControlPort() {
        return this.config.controlPort;
    }
    isConnected() {
        return this.status.connected;
    }
    async restart() {
        console.log('Restarting Tor...');
        const stopped = await this.stop();
        if (!stopped) {
            return false;
        }
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
        return await this.start();
    }
    addEventListener(type, listener) {
        return this.on(type, listener);
    }
    async getMetrics() {
        const bandwidth = await this.getBandwidth();
        const circuits = await this.getCircuits();
        return {
            uptimeSeconds: process.uptime(),
            bytesRead: bandwidth?.read ?? 0,
            bytesWritten: bandwidth?.written ?? 0,
            circuitsBuilt: circuits,
            circuitsFailed: 0,
            lastUpdated: new Date().toISOString(),
        };
    }
    async testConnection(options) {
        const url = typeof options === 'string' ? options : options.url;
        const timeout = typeof options === 'string' ? 10000 : options.timeout ?? 10000;
        try {
            const { SocksProxyAgent } = await Promise.resolve().then(() => __importStar(require('socks-proxy-agent')));
            const axios = (await Promise.resolve().then(() => __importStar(require('axios')))).default;
            const agent = new SocksProxyAgent(`socks5://127.0.0.1:${this.config.socksPort}`);
            const res = await axios.get(url, {
                httpAgent: agent,
                httpsAgent: agent,
                timeout,
                validateStatus: () => true,
            });
            return res.status >= 200 && res.status < 500;
        }
        catch {
            return false;
        }
    }
    async healthCheck() {
        const start = Date.now();
        try {
            const controlOk = await this.testControlConnection();
            const healthy = this.status.connected && controlOk;
            return {
                healthy,
                responseTime: Date.now() - start,
                socksProxy: controlOk,
                controlPort: controlOk,
                bootstrap: this.status.status === 'connected',
                circuitBuild: (this.status.circuits ?? 0) > 0,
                error: healthy ? undefined : this.status.error,
            };
        }
        catch (error) {
            return {
                healthy: false,
                responseTime: Date.now() - start,
                socksProxy: false,
                controlPort: false,
                bootstrap: false,
                circuitBuild: false,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }
}
exports.TorManager = TorManager;
