/**
 * LUCID Connection Validator - SPEC-1B Implementation
 * Validates connectivity to Docker services by phase.
 *
 * Config resolution (aligned with electron_gui/utils/load_host_config.py):
 * - LUCID_ELECTRON_ENDPOINTS_FILE — absolute path to endpoints YAML (or JSON)
 * - LUCID_ELECTRON_SERVICE_CONFIG_DIR — directory containing electron-endpoints.yml
 * - Else /app/service-configs (Docker), else electron_gui/configs relative to this file
 * - LUCID_VALIDATOR_HTTP_VIA_TOR=1 — force SOCKS proxy for http(s) checks (default off for LAN)
 * - LUCID_VALIDATOR_REQUIRE_TOR=1 — overallHealth needs Tor + httpbin check (default off)
 *
 * @file electron_gui/main/connection-validator.ts
 */

import * as fs from 'fs';
import * as net from 'net';
import * as path from 'path';
import axios, { AxiosError } from 'axios';
import { SocksProxyAgent } from 'socks-proxy-agent';
import { API_ENDPOINTS, TOR_CONFIG } from '../shared/constants';

/** Directory containing this module (electron_gui/main at dev; electron_gui/dist/main when compiled). */
export const CONNECTION_VALIDATOR_MODULE_DIR = typeof __dirname !== 'undefined' ? __dirname : path.resolve('.');

export interface ValidationResult {
  phase: string;
  success: boolean;
  services: Array<{
    name: string;
    endpoint: string;
    status: 'connected' | 'failed' | 'timeout';
    responseTime?: number;
    error?: string;
  }>;
  timestamp: string;
  totalServices: number;
  connectedServices: number;
}

export type EndpointMap = Record<string, string>;

const DEFAULT_ENDPOINTS_BASENAME = 'electron-endpoints.yml';
const DEFAULT_SERVICE_CONFIG_DIR_DOCKER = '/app/service-configs';

function envFlag(name: string): boolean {
  const v = process.env[name]?.trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}

/**
 * Resolve electron_gui/configs from this file's location.
 * dist/main → ../../configs; main/ → ../configs
 */
export function resolveElectronGuiConfigsDir(): string {
  const candidates = [
    path.join(CONNECTION_VALIDATOR_MODULE_DIR, '..', 'configs'),
    path.join(CONNECTION_VALIDATOR_MODULE_DIR, '..', '..', 'configs'),
  ];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p) && fs.statSync(p).isDirectory()) {
        return path.resolve(p);
      }
    } catch {
      /* skip */
    }
  }
  return path.resolve(CONNECTION_VALIDATOR_MODULE_DIR, '..', 'configs');
}

/**
 * Resolve path to electron-endpoints.yml (same contract as load_host_config.resolve_electron_endpoints_path).
 */
export function resolveElectronEndpointsPath(): string {
  const envFile = process.env.LUCID_ELECTRON_ENDPOINTS_FILE?.trim();
  if (envFile) {
    return path.resolve(envFile);
  }

  const envDir = process.env.LUCID_ELECTRON_SERVICE_CONFIG_DIR?.trim();
  if (envDir) {
    return path.resolve(envDir, DEFAULT_ENDPOINTS_BASENAME);
  }

  try {
    if (fs.existsSync(DEFAULT_SERVICE_CONFIG_DIR_DOCKER)) {
      const dockerPath = path.join(DEFAULT_SERVICE_CONFIG_DIR_DOCKER, DEFAULT_ENDPOINTS_BASENAME);
      if (fs.existsSync(dockerPath)) {
        return dockerPath;
      }
    }
  } catch {
    /* skip */
  }

  return path.join(resolveElectronGuiConfigsDir(), DEFAULT_ENDPOINTS_BASENAME);
}

/**
 * Flat key: value YAML (one level). Rest-of-line capture so URLs with colons parse correctly.
 */
export function parseFlatEndpointYaml(text: string): EndpointMap {
  const out: EndpointMap = {};
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const m = trimmed.match(/^([A-Za-z0-9_]+)\s*:\s*(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    if (v && !v.startsWith('#')) {
      out[m[1]] = v;
    }
  }
  return out;
}

function loadEndpointOverridesFromDisk(): EndpointMap {
  const filePath = resolveElectronEndpointsPath();
  try {
    if (!fs.existsSync(filePath)) {
      return {};
    }
    const text = fs.readFileSync(filePath, 'utf8');
    if (!text.trim()) {
      return {};
    }
    const ext = path.extname(filePath).toLowerCase();
    if (ext === '.json') {
      const parsed = JSON.parse(text) as Record<string, unknown>;
      const flat: EndpointMap = {};
      for (const [k, val] of Object.entries(parsed)) {
        if (typeof val === 'string') {
          flat[k] = val;
        }
      }
      return flat;
    }
    return parseFlatEndpointYaml(text);
  } catch (e) {
    console.warn(`[ConnectionValidator] Could not load endpoints from ${filePath}:`, e);
    return {};
  }
}

function mergeEndpoints(base: EndpointMap, overrides: EndpointMap): EndpointMap {
  return { ...base, ...overrides };
}

function endpointMapFromConstants(): EndpointMap {
  const m: EndpointMap = {};
  (Object.keys(API_ENDPOINTS) as Array<keyof typeof API_ENDPOINTS>).forEach((k) => {
    m[k] = API_ENDPOINTS[k];
  });
  return m;
}

function parseTcpTarget(urlString: string): { host: string; port: number } | null {
  try {
    const u = new URL(urlString);
    const host = u.hostname;
    const defaultPort = u.protocol === 'redis:' ? 6379 : 27017;
    const port = u.port ? parseInt(u.port, 10) : defaultPort;
    if (!host || Number.isNaN(port)) return null;
    return { host, port };
  } catch {
    return null;
  }
}

function checkTcp(host: string, port: number, timeoutMs: number): Promise<boolean> {
  return new Promise((resolve) => {
    const done = (ok: boolean) => {
      try {
        socket.destroy();
      } catch {
        /* ignore */
      }
      resolve(ok);
    };
    const socket = net.createConnection({ host, port }, () => {
      done(true);
    });
    socket.setTimeout(timeoutMs);
    socket.on('timeout', () => done(false));
    socket.on('error', () => done(false));
  });
}

/** Hosts that should not be forced through Tor (LAN / loopback). */
function shouldUseSocksForHttpUrl(urlString: string): boolean {
  if (envFlag('LUCID_VALIDATOR_HTTP_VIA_TOR')) {
    return true;
  }
  try {
    const u = new URL(urlString);
    const host = u.hostname.toLowerCase();
    if (host === 'localhost' || host === '127.0.0.1' || host === '::1') {
      return false;
    }
    if (
      /^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(host) ||
      /^192\.168\.\d{1,3}\.\d{1,3}$/.test(host) ||
      /^172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}$/.test(host)
    ) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

function axiosCode(error: unknown): string | undefined {
  if (!axios.isAxiosError(error)) return undefined;
  const code = (error as AxiosError).code;
  return typeof code === 'string' ? code : undefined;
}

export class ConnectionValidator {
  private torProxy: string;
  private requestTimeoutMs: number;
  private endpoints: EndpointMap;

  constructor() {
    this.torProxy = `socks5://127.0.0.1:${TOR_CONFIG.SOCKS_PORT}`;
    this.requestTimeoutMs = 5000;
    const overrides = loadEndpointOverridesFromDisk();
    this.endpoints = mergeEndpoints(endpointMapFromConstants(), overrides);
  }

  refreshEndpoints(): void {
    const overrides = loadEndpointOverridesFromDisk();
    this.endpoints = mergeEndpoints(endpointMapFromConstants(), overrides);
  }

  getEndpoint(key: keyof typeof API_ENDPOINTS | string): string | undefined {
    return this.endpoints[key];
  }

  async validatePhase1(): Promise<ValidationResult> {
    const phase = 'foundation';
    const services = [
      { name: 'MongoDB', endpoint: this.requireEndpoint('MONGODB') },
      { name: 'Redis', endpoint: this.requireEndpoint('REDIS') },
      { name: 'Elasticsearch', endpoint: this.requireEndpoint('ELASTICSEARCH') },
      { name: 'Auth Service', endpoint: this.requireEndpoint('AUTH') },
    ];
    return this.validateServices(phase, services);
  }

  async validatePhase2(): Promise<ValidationResult> {
    const phase = 'core';
    const services = [
      { name: 'API Gateway', endpoint: this.requireEndpoint('API_GATEWAY') },
      { name: 'Blockchain Engine', endpoint: this.requireEndpoint('BLOCKCHAIN_ENGINE') },
      { name: 'Service Mesh', endpoint: this.requireEndpoint('SERVICE_MESH') },
      { name: 'Session Anchoring', endpoint: this.requireEndpoint('SESSION_ANCHORING') },
      { name: 'Block Manager', endpoint: this.requireEndpoint('BLOCK_MANAGER') },
      { name: 'Data Chain', endpoint: this.requireEndpoint('DATA_CHAIN') },
    ];
    return this.validateServices(phase, services);
  }

  async validatePhase3(): Promise<ValidationResult> {
    const phase = 'application';
    const services = [
      { name: 'Session API', endpoint: this.requireEndpoint('SESSION_API') },
      { name: 'RDP Server', endpoint: this.requireEndpoint('RDP_SERVER') },
      { name: 'Session Controller', endpoint: this.requireEndpoint('SESSION_CONTROLLER') },
      { name: 'Resource Monitor', endpoint: this.requireEndpoint('RESOURCE_MONITOR') },
      { name: 'Node Management', endpoint: this.requireEndpoint('NODE_MANAGEMENT') },
    ];
    return this.validateServices(phase, services);
  }

  async validatePhase4(): Promise<ValidationResult> {
    const phase = 'support';
    const services = [
      { name: 'Admin Interface', endpoint: this.requireEndpoint('ADMIN') },
      { name: 'TRON Client', endpoint: this.requireEndpoint('TRON_CLIENT') },
      { name: 'Payout Router', endpoint: this.requireEndpoint('PAYOUT_ROUTER') },
      { name: 'Wallet Manager', endpoint: this.requireEndpoint('WALLET_MANAGER') },
      { name: 'USDT Manager', endpoint: this.requireEndpoint('USDT_MANAGER') },
      { name: 'TRX Staking', endpoint: this.requireEndpoint('TRX_STAKING') },
      { name: 'Payment Gateway', endpoint: this.requireEndpoint('PAYMENT_GATEWAY') },
    ];
    return this.validateServices(phase, services);
  }

  async validateAllPhases(): Promise<ValidationResult[]> {
    return Promise.all([
      this.validatePhase1(),
      this.validatePhase2(),
      this.validatePhase3(),
      this.validatePhase4(),
    ]);
  }

  async validateService(
    name: string,
    endpoint: string
  ): Promise<{
    name: string;
    endpoint: string;
    status: 'connected' | 'failed' | 'timeout';
    responseTime?: number;
    error?: string;
  }> {
    const startTime = Date.now();

    const lower = endpoint.toLowerCase();
    if (lower.startsWith('mongodb:') || lower.startsWith('redis:')) {
      const target = parseTcpTarget(endpoint);
      if (!target) {
        return {
          name,
          endpoint,
          status: 'failed',
          error: 'Invalid TCP URL',
        };
      }
      const ok = await checkTcp(target.host, target.port, this.requestTimeoutMs);
      const responseTime = Date.now() - startTime;
      return ok
        ? { name, endpoint, status: 'connected', responseTime }
        : { name, endpoint, status: 'failed', responseTime, error: 'TCP connection failed' };
    }

    if (!lower.startsWith('http://') && !lower.startsWith('https://')) {
      return {
        name,
        endpoint,
        status: 'failed',
        error: 'Unsupported URL scheme (use http(s), mongodb, or redis)',
      };
    }

    const base = endpoint.replace(/\/$/, '');
    const healthCandidates =
      name === 'Elasticsearch' || keyLooksLikeElasticsearch(endpoint)
        ? [`${base}/_cluster/health`, `${base}/health`]
        : [`${base}/health`];

    const useSocks = shouldUseSocksForHttpUrl(endpoint);
    const agent = useSocks ? new SocksProxyAgent(this.torProxy) : undefined;

    let lastError = 'All health paths failed';

    for (const healthUrl of healthCandidates) {
      try {
        const response = await axios.get(healthUrl, {
          ...(agent ? { httpAgent: agent, httpsAgent: agent } : {}),
          timeout: this.requestTimeoutMs,
          headers: { 'User-Agent': 'Lucid-Electron-GUI/1.0.0' },
          validateStatus: () => true,
        });

        const responseTime = Date.now() - startTime;

        if (response.status >= 200 && response.status < 300) {
          return { name, endpoint, status: 'connected', responseTime };
        }
        lastError = `HTTP ${response.status}: ${response.statusText}`;
      } catch (error: unknown) {
        const responseTime = Date.now() - startTime;
        const msg = error instanceof Error ? error.message : String(error);
        const code = axiosCode(error);

        if (code === 'ECONNABORTED' || msg.toLowerCase().includes('timeout')) {
          lastError = 'Connection timeout';
          continue;
        }
        if (code === 'ECONNREFUSED') {
          return {
            name,
            endpoint,
            status: 'failed',
            responseTime,
            error: 'Connection refused',
          };
        }
        lastError = msg || 'Unknown error';
      }
    }

    const responseTime = Date.now() - startTime;
    const timedOut = lastError === 'Connection timeout';

    return {
      name,
      endpoint,
      status: timedOut ? 'timeout' : 'failed',
      responseTime,
      error: lastError,
    };
  }

  private async validateServices(
    phase: string,
    services: Array<{ name: string; endpoint: string }>
  ): Promise<ValidationResult> {
    const serviceResults = await Promise.all(
      services.map((s: { name: string; endpoint: string }) => this.validateService(s.name, s.endpoint))
    );

    const connectedServices = serviceResults.filter((r) => r.status === 'connected').length;
    const success = connectedServices === services.length;

    return {
      phase,
      success,
      services: serviceResults,
      timestamp: new Date().toISOString(),
      totalServices: services.length,
      connectedServices,
    };
  }

  private requireEndpoint(key: keyof typeof API_ENDPOINTS): string {
    const v = this.endpoints[key] ?? API_ENDPOINTS[key];
    if (!v) {
      throw new Error(`Missing endpoint key ${String(key)} in merged config`);
    }
    return v;
  }

  async validateTorConnection(): Promise<boolean> {
    try {
      const agent = new SocksProxyAgent(this.torProxy);
      const response = await axios.get('https://httpbin.org/ip', {
        httpAgent: agent,
        httpsAgent: agent,
        timeout: 10000,
        validateStatus: (status: number) => status === 200,
      });
      return response.status === 200;
    } catch (error: unknown) {
      console.error('Tor connection validation failed:', error);
      return false;
    }
  }

  async getConnectionSummary(): Promise<{
    torConnected: boolean;
    phases: ValidationResult[];
    overallHealth: 'healthy' | 'degraded' | 'critical';
    totalServices: number;
    connectedServices: number;
  }> {
    const torConnected = await this.validateTorConnection();
    const phases = await this.validateAllPhases();

    const totalServices = phases.reduce((sum, ph) => sum + ph.totalServices, 0);
    const connectedServices = phases.reduce((sum, ph) => sum + ph.connectedServices, 0);

    const torGate = envFlag('LUCID_VALIDATOR_REQUIRE_TOR');
    const torOk = !torGate || torConnected;

    let overallHealth: 'healthy' | 'degraded' | 'critical';
    if (connectedServices === totalServices && torOk) {
      overallHealth = 'healthy';
    } else if (connectedServices >= totalServices * 0.7 && torOk) {
      overallHealth = 'degraded';
    } else {
      overallHealth = 'critical';
    }

    return {
      torConnected,
      phases,
      overallHealth,
      totalServices,
      connectedServices,
    };
  }

  setRequestTimeout(ms: number): void {
    this.requestTimeoutMs = ms;
  }

  /** @deprecated Use setRequestTimeout — avoids shadowing global setTimeout */
  setTimeout(ms: number): void {
    this.setRequestTimeout(ms);
  }

  setTorProxy(proxyUrl: string): void {
    this.torProxy = proxyUrl;
  }
}

function keyLooksLikeElasticsearch(endpoint: string): boolean {
  return /:9200(\/|$)/.test(endpoint) || /elasticsearch/i.test(endpoint);
}
