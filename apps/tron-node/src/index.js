#!/usr/bin/env node

/**
 * Lucid RDP TRON Node Service
 * TronWeb integration for TRON blockchain interactions
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import dotenv from 'dotenv';
import TronWeb from 'tronweb';
import { createLogger, format, transports } from 'winston';
import Redis from 'ioredis';
import Queue from 'bull';
import cron from 'node-cron';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// Import services
import { TronClient } from './services/TronClient.js';
import { TronContractManager } from './services/TronContractManager.js';
import { TronTransactionManager } from './services/TronTransactionManager.js';
import { TronEventListener } from './services/TronEventListener.js';
import { TronHealthChecker } from './services/TronHealthChecker.js';
import { TronMetricsCollector } from './services/TronMetricsCollector.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const config = {
  port: process.env.PORT || 8086,
  nodeEnv: process.env.NODE_ENV || 'development',
  tronNetwork: process.env.TRON_NETWORK || 'mainnet',
  tronApiKey: process.env.TRON_API_KEY,
  privateKey: process.env.TRON_PRIVATE_KEY,
  contractAddress: process.env.TRON_CONTRACT_ADDRESS,
  redisUrl: process.env.REDIS_URL || 'redis://localhost:6379',
  logLevel: process.env.LOG_LEVEL || 'info'
};

// Logger setup
const logger = createLogger({
  level: config.logLevel,
  format: format.combine(
    format.timestamp(),
    format.errors({ stack: true }),
    format.json()
  ),
  defaultMeta: { service: 'lucid-tron-node' },
  transports: [
    new transports.Console({
      format: format.combine(
        format.colorize(),
        format.simple()
      )
    }),
    new transports.File({ 
      filename: 'logs/error.log', 
      level: 'error' 
    }),
    new transports.File({ 
      filename: 'logs/combined.log' 
    })
  ]
});

// TronWeb setup
const tronWebConfig = {
  mainnet: {
    fullHost: 'https://api.trongrid.io',
    privateKey: config.privateKey
  },
  shasta: {
    fullHost: 'https://api.shasta.trongrid.io',
    privateKey: config.privateKey
  },
  nile: {
    fullHost: 'https://nile.trongrid.io',
    privateKey: config.privateKey
  }
};

const tronWeb = new TronWeb(tronWebConfig[config.tronNetwork]);

// Redis setup
const redis = new Redis(config.redisUrl, {
  retryDelayOnFailover: 100,
  enableReadyCheck: false,
  maxRetriesPerRequest: null
});

// Queue setup
const tronQueue = new Queue('tron processing', {
  redis: {
    host: 'localhost',
    port: 6379
  }
});

// Express app setup
const app = express();

// Middleware
app.use(helmet());
app.use(cors());
app.use(compression());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Initialize services
let tronClient;
let tronContractManager;
let tronTransactionManager;
let tronEventListener;
let tronHealthChecker;
let tronMetricsCollector;

async function initializeServices() {
  try {
    logger.info('Initializing TRON services...');

    // Initialize services
    tronClient = new TronClient(tronWeb, logger);
    tronContractManager = new TronContractManager(tronWeb, config.contractAddress, logger);
    tronTransactionManager = new TronTransactionManager(tronWeb, config.privateKey, logger);
    tronEventListener = new TronEventListener(tronWeb, tronContractManager, logger);
    tronHealthChecker = new TronHealthChecker(tronClient, logger);
    tronMetricsCollector = new TronMetricsCollector(tronClient, logger);

    // Initialize services
    await tronClient.initialize();
    await tronContractManager.initialize();
    await tronTransactionManager.initialize();
    await tronEventListener.initialize();
    await tronHealthChecker.initialize();
    await tronMetricsCollector.initialize();

    logger.info('All TRON services initialized successfully');
  } catch (error) {
    logger.error('Failed to initialize TRON services:', error);
    process.exit(1);
  }
}

// API Routes
app.get('/health', async (req, res) => {
  try {
    const health = await tronHealthChecker.checkHealth();
    res.json(health);
  } catch (error) {
    logger.error('Health check failed:', error);
    res.status(500).json({ error: 'Health check failed' });
  }
});

app.get('/metrics', async (req, res) => {
  try {
    const metrics = await tronMetricsCollector.getMetrics();
    res.json(metrics);
  } catch (error) {
    logger.error('Metrics collection failed:', error);
    res.status(500).json({ error: 'Metrics collection failed' });
  }
});

app.get('/tron/status', async (req, res) => {
  try {
    const status = await tronClient.getTronStatus();
    res.json(status);
  } catch (error) {
    logger.error('TRON status check failed:', error);
    res.status(500).json({ error: 'TRON status check failed' });
  }
});

app.get('/tron/latest-block', async (req, res) => {
  try {
    const block = await tronClient.getLatestBlock();
    res.json(block);
  } catch (error) {
    logger.error('Latest block fetch failed:', error);
    res.status(500).json({ error: 'Latest block fetch failed' });
  }
});

app.get('/tron/account/:address', async (req, res) => {
  try {
    const { address } = req.params;
    const account = await tronClient.getAccount(address);
    
    if (!account) {
      return res.status(404).json({ error: 'Account not found' });
    }
    
    res.json(account);
  } catch (error) {
    logger.error('Account fetch failed:', error);
    res.status(500).json({ error: 'Account fetch failed' });
  }
});

app.get('/tron/balance/:address', async (req, res) => {
  try {
    const { address } = req.params;
    const balance = await tronClient.getBalance(address);
    
    res.json({ address, balance });
  } catch (error) {
    logger.error('Balance fetch failed:', error);
    res.status(500).json({ error: 'Balance fetch failed' });
  }
});

app.get('/contract/info', async (req, res) => {
  try {
    const info = await tronContractManager.getContractInfo();
    res.json(info);
  } catch (error) {
    logger.error('Contract info fetch failed:', error);
    res.status(500).json({ error: 'Contract info fetch failed' });
  }
});

app.post('/transaction/send', async (req, res) => {
  try {
    const { to, amount, asset, memo } = req.body;
    
    const transaction = await tronTransactionManager.sendTransaction({
      to,
      amount,
      asset,
      memo
    });
    
    res.json(transaction);
  } catch (error) {
    logger.error('Transaction send failed:', error);
    res.status(500).json({ error: 'Transaction send failed' });
  }
});

app.get('/transaction/:hash', async (req, res) => {
  try {
    const { hash } = req.params;
    const transaction = await tronClient.getTransaction(hash);
    
    if (!transaction) {
      return res.status(404).json({ error: 'Transaction not found' });
    }
    
    res.json(transaction);
  } catch (error) {
    logger.error('Transaction fetch failed:', error);
    res.status(500).json({ error: 'Transaction fetch failed' });
  }
});

app.post('/contract/call', async (req, res) => {
  try {
    const { method, params } = req.body;
    const result = await tronContractManager.callContract(method, params);
    
    res.json({ result });
  } catch (error) {
    logger.error('Contract call failed:', error);
    res.status(500).json({ error: 'Contract call failed' });
  }
});

app.post('/contract/send', async (req, res) => {
  try {
    const { method, params, feeLimit, callValue } = req.body;
    const transaction = await tronContractManager.sendContractTransaction(
      method, 
      params, 
      { feeLimit, callValue }
    );
    
    res.json(transaction);
  } catch (error) {
    logger.error('Contract transaction failed:', error);
    res.status(500).json({ error: 'Contract transaction failed' });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Queue processing
tronQueue.process(async (job) => {
  try {
    const { transaction } = job.data;
    logger.info('Processing TRON transaction:', transaction.txID);
    
    // Process transaction logic here
    await tronTransactionManager.processTransaction(transaction);
    
    logger.info('TRON transaction processed successfully:', transaction.txID);
  } catch (error) {
    logger.error('TRON transaction processing failed:', error);
    throw error;
  }
});

// Scheduled tasks
cron.schedule('*/30 * * * * *', async () => {
  try {
    await tronHealthChecker.checkHealth();
    await tronMetricsCollector.collectMetrics();
  } catch (error) {
    logger.error('Scheduled task failed:', error);
  }
});

// Graceful shutdown
process.on('SIGINT', async () => {
  logger.info('Received SIGINT, shutting down gracefully...');
  
  try {
    await tronEventListener.stop();
    await tronHealthChecker.stop();
    await tronMetricsCollector.stop();
    
    await redis.quit();
    await tronQueue.close();
    
    logger.info('Shutdown completed');
    process.exit(0);
  } catch (error) {
    logger.error('Error during shutdown:', error);
    process.exit(1);
  }
});

process.on('SIGTERM', async () => {
  logger.info('Received SIGTERM, shutting down gracefully...');
  
  try {
    await tronEventListener.stop();
    await tronHealthChecker.stop();
    await tronMetricsCollector.stop();
    
    await redis.quit();
    await tronQueue.close();
    
    logger.info('Shutdown completed');
    process.exit(0);
  } catch (error) {
    logger.error('Error during shutdown:', error);
    process.exit(1);
  }
});

// Start server
async function startServer() {
  try {
    await initializeServices();
    
    app.listen(config.port, () => {
      logger.info(`Lucid TRON Node started on port ${config.port}`);
      logger.info(`Environment: ${config.nodeEnv}`);
      logger.info(`TRON Network: ${config.tronNetwork}`);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();
