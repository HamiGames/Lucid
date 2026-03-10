#!/usr/bin/env node

/**
 * Lucid RDP Chain Client
 * Node.js service for blockchain interactions
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import dotenv from 'dotenv';
import { Web3 } from 'web3';
import { ethers } from 'ethers';
import { createLogger, format, transports } from 'winston';
import Redis from 'ioredis';
import Queue from 'bull';
import cron from 'node-cron';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Import modules
import { ChainClient } from './services/ChainClient.js';
import { ContractManager } from './services/ContractManager.js';
import { TransactionManager } from './services/TransactionManager.js';
import { EventListener } from './services/EventListener.js';
import { HealthChecker } from './services/HealthChecker.js';
import { MetricsCollector } from './services/MetricsCollector.js';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration
const config = {
  port: process.env.PORT || 8085,
  nodeEnv: process.env.NODE_ENV || 'development',
  rpcUrl: process.env.RPC_URL || 'http://localhost:8545',
  privateKey: process.env.PRIVATE_KEY,
  contractAddress: process.env.CONTRACT_ADDRESS,
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
  defaultMeta: { service: 'lucid-chain-client' },
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

// Redis setup
const redis = new Redis(config.redisUrl, {
  retryDelayOnFailover: 100,
  enableReadyCheck: false,
  maxRetriesPerRequest: null
});

// Queue setup
const transactionQueue = new Queue('transaction processing', {
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
let chainClient;
let contractManager;
let transactionManager;
let eventListener;
let healthChecker;
let metricsCollector;

async function initializeServices() {
  try {
    logger.info('Initializing services...');

    // Initialize Web3
    const web3 = new Web3(config.rpcUrl);
    const provider = new ethers.JsonRpcProvider(config.rpcUrl);
    
    // Initialize services
    chainClient = new ChainClient(web3, provider, logger);
    contractManager = new ContractManager(web3, provider, config.contractAddress, logger);
    transactionManager = new TransactionManager(web3, provider, config.privateKey, logger);
    eventListener = new EventListener(web3, contractManager, logger);
    healthChecker = new HealthChecker(chainClient, logger);
    metricsCollector = new MetricsCollector(chainClient, logger);

    // Initialize services
    await chainClient.initialize();
    await contractManager.initialize();
    await transactionManager.initialize();
    await eventListener.initialize();
    await healthChecker.initialize();
    await metricsCollector.initialize();

    logger.info('All services initialized successfully');
  } catch (error) {
    logger.error('Failed to initialize services:', error);
    process.exit(1);
  }
}

// API Routes
app.get('/health', async (req, res) => {
  try {
    const health = await healthChecker.checkHealth();
    res.json(health);
  } catch (error) {
    logger.error('Health check failed:', error);
    res.status(500).json({ error: 'Health check failed' });
  }
});

app.get('/metrics', async (req, res) => {
  try {
    const metrics = await metricsCollector.getMetrics();
    res.json(metrics);
  } catch (error) {
    logger.error('Metrics collection failed:', error);
    res.status(500).json({ error: 'Metrics collection failed' });
  }
});

app.get('/chain/status', async (req, res) => {
  try {
    const status = await chainClient.getChainStatus();
    res.json(status);
  } catch (error) {
    logger.error('Chain status check failed:', error);
    res.status(500).json({ error: 'Chain status check failed' });
  }
});

app.get('/chain/latest-block', async (req, res) => {
  try {
    const block = await chainClient.getLatestBlock();
    res.json(block);
  } catch (error) {
    logger.error('Latest block fetch failed:', error);
    res.status(500).json({ error: 'Latest block fetch failed' });
  }
});

app.get('/contract/info', async (req, res) => {
  try {
    const info = await contractManager.getContractInfo();
    res.json(info);
  } catch (error) {
    logger.error('Contract info fetch failed:', error);
    res.status(500).json({ error: 'Contract info fetch failed' });
  }
});

app.post('/transaction/send', async (req, res) => {
  try {
    const { to, data, value, gasLimit, gasPrice } = req.body;
    
    const transaction = await transactionManager.sendTransaction({
      to,
      data,
      value,
      gasLimit,
      gasPrice
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
    const transaction = await transactionManager.getTransaction(hash);
    
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
    const result = await contractManager.callContract(method, params);
    
    res.json({ result });
  } catch (error) {
    logger.error('Contract call failed:', error);
    res.status(500).json({ error: 'Contract call failed' });
  }
});

app.post('/contract/send', async (req, res) => {
  try {
    const { method, params, value, gasLimit, gasPrice } = req.body;
    const transaction = await contractManager.sendContractTransaction(
      method, 
      params, 
      { value, gasLimit, gasPrice }
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
transactionQueue.process(async (job) => {
  try {
    const { transaction } = job.data;
    logger.info('Processing transaction:', transaction.hash);
    
    // Process transaction logic here
    await transactionManager.processTransaction(transaction);
    
    logger.info('Transaction processed successfully:', transaction.hash);
  } catch (error) {
    logger.error('Transaction processing failed:', error);
    throw error;
  }
});

// Scheduled tasks
cron.schedule('*/30 * * * * *', async () => {
  try {
    await healthChecker.checkHealth();
    await metricsCollector.collectMetrics();
  } catch (error) {
    logger.error('Scheduled task failed:', error);
  }
});

// Graceful shutdown
process.on('SIGINT', async () => {
  logger.info('Received SIGINT, shutting down gracefully...');
  
  try {
    await eventListener.stop();
    await healthChecker.stop();
    await metricsCollector.stop();
    
    await redis.quit();
    await transactionQueue.close();
    
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
    await eventListener.stop();
    await healthChecker.stop();
    await metricsCollector.stop();
    
    await redis.quit();
    await transactionQueue.close();
    
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
      logger.info(`Lucid Chain Client started on port ${config.port}`);
      logger.info(`Environment: ${config.nodeEnv}`);
      logger.info(`RPC URL: ${config.rpcUrl}`);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();
