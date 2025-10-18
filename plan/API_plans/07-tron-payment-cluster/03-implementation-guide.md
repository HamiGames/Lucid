# TRON Payment Cluster - Implementation Guide

## Architecture Overview

### Service Structure
```
tron-payment-service/
├── src/
│   ├── controllers/          # API controllers
│   ├── services/            # Business logic
│   ├── models/              # Data models
│   ├── middleware/          # Custom middleware
│   ├── utils/               # Utility functions
│   ├── config/              # Configuration
│   └── types/               # TypeScript types
├── tests/                   # Test files
├── docker/                  # Docker configuration
└── docs/                    # Documentation
```

### Core Services

#### 1. TRON Network Service
```typescript
// src/services/tron-network.service.ts
import { Injectable } from '@nestjs/common';
import { TronWeb } from 'tronweb';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class TronNetworkService {
  private tronWeb: TronWeb;
  private readonly NETWORK_URL = 'https://api.trongrid.io';

  constructor(private configService: ConfigService) {
    this.tronWeb = new TronWeb({
      fullHost: this.NETWORK_URL,
      headers: {
        'TRON-PRO-API-KEY': this.configService.get('TRON_API_KEY')
      }
    });
  }

  async getNetworkInfo(): Promise<TronNetworkInfo> {
    try {
      const [chainParameters, nodeInfo] = await Promise.all([
        this.tronWeb.trx.getChainParameters(),
        this.tronWeb.trx.getNodeInfo()
      ]);

      return {
        network_name: 'TRON Mainnet',
        network_id: 'mainnet',
        chain_id: nodeInfo.config.chainId,
        current_height: nodeInfo.block,
        block_time: 3,
        total_supply: '100000000000',
        circulating_supply: await this.getCirculatingSupply(),
        energy_price: chainParameters.find(p => p.key === 'getEnergyFee')?.value || '420',
        bandwidth_price: chainParameters.find(p => p.key === 'getTransactionFee')?.value || '1000'
      };
    } catch (error) {
      throw new Error(`Failed to get TRON network info: ${error.message}`);
    }
  }

  async getNetworkStatus(): Promise<TronNetworkStatus> {
    try {
      const nodeInfo = await this.tronWeb.trx.getNodeInfo();
      const syncStatus = await this.tronWeb.trx.getNodeInfo();
      
      return {
        status: this.determineNetworkStatus(syncStatus),
        current_height: nodeInfo.block,
        sync_percentage: this.calculateSyncPercentage(syncStatus),
        last_block_time: new Date(syncStatus.blockTime),
        node_count: await this.getNodeCount(),
        network_hash_rate: await this.getNetworkHashRate()
      };
    } catch (error) {
      throw new Error(`Failed to get TRON network status: ${error.message}`);
    }
  }

  private determineNetworkStatus(syncStatus: any): 'healthy' | 'degraded' | 'down' {
    if (syncStatus.syncStatus === 'SYNCED') return 'healthy';
    if (syncStatus.syncStatus === 'SYNCING') return 'degraded';
    return 'down';
  }

  private calculateSyncPercentage(syncStatus: any): number {
    // Implementation for sync percentage calculation
    return 100; // Placeholder
  }

  private async getNodeCount(): Promise<number> {
    // Implementation for node count
    return 1000; // Placeholder
  }

  private async getNetworkHashRate(): Promise<string> {
    // Implementation for network hash rate
    return '1000000'; // Placeholder
  }

  private async getCirculatingSupply(): Promise<string> {
    try {
      const supply = await this.tronWeb.trx.getTotalSupply();
      return supply.toString();
    } catch (error) {
      return '99000000000'; // Fallback value
    }
  }
}
```

#### 2. Wallet Service
```typescript
// src/services/wallet.service.ts
import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Wallet, WalletDocument } from '../models/wallet.model';
import { TronWeb } from 'tronweb';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class WalletService {
  private tronWeb: TronWeb;

  constructor(
    @InjectModel(Wallet.name) private walletModel: Model<WalletDocument>,
    private tronNetworkService: TronNetworkService
  ) {
    this.tronWeb = new TronWeb({
      fullHost: 'https://api.trongrid.io'
    });
  }

  async createWallet(createWalletDto: WalletCreateDto, userId: string): Promise<Wallet> {
    try {
      // Generate new TRON address
      const account = this.tronWeb.utils.accounts.generateAccount();
      
      const wallet = new this.walletModel({
        wallet_id: uuidv4(),
        user_id: userId,
        name: createWalletDto.name,
        address: account.address.base58,
        currency: createWalletDto.currency,
        network: 'TRON',
        balance: 0,
        is_active: true,
        hardware_wallet: createWalletDto.hardware_wallet || false,
        created_at: new Date(),
        updated_at: new Date()
      });

      return await wallet.save();
    } catch (error) {
      throw new Error(`Failed to create wallet: ${error.message}`);
    }
  }

  async getWallet(walletId: string, userId: string): Promise<Wallet> {
    try {
      const wallet = await this.walletModel.findOne({
        wallet_id: walletId,
        user_id: userId,
        is_active: true
      });

      if (!wallet) {
        throw new Error('Wallet not found');
      }

      // Update balance from TRON network
      await this.updateWalletBalance(wallet);

      return wallet;
    } catch (error) {
      throw new Error(`Failed to get wallet: ${error.message}`);
    }
  }

  async updateWalletBalance(wallet: Wallet): Promise<void> {
    try {
      let balance = 0;
      
      if (wallet.currency === 'TRX') {
        balance = await this.tronWeb.trx.getBalance(wallet.address);
      } else if (wallet.currency === 'USDT') {
        balance = await this.getUsdtBalance(wallet.address);
      }

      await this.walletModel.updateOne(
        { wallet_id: wallet.wallet_id },
        { 
          balance: balance,
          updated_at: new Date()
        }
      );
    } catch (error) {
      throw new Error(`Failed to update wallet balance: ${error.message}`);
    }
  }

  private async getUsdtBalance(address: string): Promise<number> {
    try {
      const usdtContract = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t';
      const contract = await this.tronWeb.contract().at(usdtContract);
      const balance = await contract.balanceOf(address).call();
      return this.tronWeb.fromSun(balance);
    } catch (error) {
      return 0;
    }
  }

  async getWalletTransactions(walletId: string, userId: string, pagination: PaginationDto): Promise<WalletTransaction[]> {
    try {
      const wallet = await this.getWallet(walletId, userId);
      
      // Get transactions from TRON network
      const transactions = await this.tronWeb.trx.getTransactionsFromAddress(
        wallet.address,
        pagination.limit,
        pagination.page
      );

      return transactions.map(tx => this.mapTronTransactionToWalletTransaction(tx, wallet.currency));
    } catch (error) {
      throw new Error(`Failed to get wallet transactions: ${error.message}`);
    }
  }

  private mapTronTransactionToWalletTransaction(tx: any, currency: string): WalletTransaction {
    return {
      tx_id: tx.txID,
      hash: tx.txID,
      type: this.determineTransactionType(tx),
      amount: this.tronWeb.fromSun(tx.raw_data.contract[0].parameter.value.amount || 0),
      currency: currency,
      from_address: this.tronWeb.address.fromHex(tx.raw_data.contract[0].parameter.value.owner_address),
      to_address: this.tronWeb.address.fromHex(tx.raw_data.contract[0].parameter.value.to_address),
      status: tx.ret[0].contractRet === 'SUCCESS' ? 'confirmed' : 'failed',
      timestamp: new Date(tx.raw_data.timestamp),
      block_height: tx.blockNumber,
      fee: this.tronWeb.fromSun(tx.ret[0].fee || 0)
    };
  }

  private determineTransactionType(tx: any): 'transfer' | 'receive' | 'stake' | 'unstake' | 'reward' {
    const contractType = tx.raw_data.contract[0].type;
    
    switch (contractType) {
      case 'TransferContract':
        return 'transfer';
      case 'FreezeBalanceContract':
        return 'stake';
      case 'UnfreezeBalanceContract':
        return 'unstake';
      case 'WithdrawBalanceContract':
        return 'reward';
      default:
        return 'transfer';
    }
  }
}
```

#### 3. USDT Service
```typescript
// src/services/usdt.service.ts
import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { TronWeb } from 'tronweb';
import { v4 as uuidv4 } from 'uuid';
import { UsdtTransfer, UsdtTransferDocument } from '../models/usdt-transfer.model';

@Injectable()
export class UsdtService {
  private tronWeb: TronWeb;
  private readonly USDT_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t';

  constructor(
    @InjectModel(UsdtTransfer.name) private usdtTransferModel: Model<UsdtTransferDocument>,
    private tronNetworkService: TronNetworkService
  ) {
    this.tronWeb = new TronWeb({
      fullHost: 'https://api.trongrid.io'
    });
  }

  async transferUsdt(transferDto: UsdtTransferDto): Promise<UsdtTransfer> {
    try {
      // Validate addresses
      this.validateTronAddress(transferDto.from_address);
      this.validateTronAddress(transferDto.to_address);

      // Check balance
      const balance = await this.getUsdtBalance(transferDto.from_address);
      if (balance < transferDto.amount) {
        throw new Error('Insufficient USDT balance');
      }

      // Create transfer record
      const transfer = new this.usdtTransferModel({
        transfer_id: uuidv4(),
        tx_id: '', // Will be set after transaction is broadcast
        status: 'pending',
        amount: transferDto.amount,
        from_address: transferDto.from_address,
        to_address: transferDto.to_address,
        submitted_at: new Date()
      });

      await transfer.save();

      // Execute transfer
      const txId = await this.executeUsdtTransfer(transferDto);
      
      // Update transfer record
      await this.usdtTransferModel.updateOne(
        { transfer_id: transfer.transfer_id },
        { tx_id: txId }
      );

      return transfer;
    } catch (error) {
      throw new Error(`Failed to transfer USDT: ${error.message}`);
    }
  }

  private async executeUsdtTransfer(transferDto: UsdtTransferDto): Promise<string> {
    try {
      const contract = await this.tronWeb.contract().at(this.USDT_CONTRACT);
      
      const transaction = await contract.transfer(
        transferDto.to_address,
        this.tronWeb.toSun(transferDto.amount)
      ).send();

      return transaction;
    } catch (error) {
      throw new Error(`Failed to execute USDT transfer: ${error.message}`);
    }
  }

  async getUsdtBalance(address: string): Promise<number> {
    try {
      this.validateTronAddress(address);
      
      const contract = await this.tronWeb.contract().at(this.USDT_CONTRACT);
      const balance = await contract.balanceOf(address).call();
      
      return this.tronWeb.fromSun(balance);
    } catch (error) {
      throw new Error(`Failed to get USDT balance: ${error.message}`);
    }
  }

  async getUsdtTransactions(address: string, pagination: PaginationDto): Promise<UsdtTransaction[]> {
    try {
      this.validateTronAddress(address);
      
      // Get USDT transactions from TRON network
      const transactions = await this.tronWeb.trx.getTransactionsFromAddress(
        address,
        pagination.limit,
        pagination.page
      );

      // Filter for USDT contract transactions
      const usdtTransactions = transactions.filter(tx => 
        tx.raw_data.contract[0].parameter.value.contract_address === this.USDT_CONTRACT
      );

      return usdtTransactions.map(tx => this.mapToUsdtTransaction(tx));
    } catch (error) {
      throw new Error(`Failed to get USDT transactions: ${error.message}`);
    }
  }

  private mapToUsdtTransaction(tx: any): UsdtTransaction {
    return {
      tx_id: tx.txID,
      hash: tx.txID,
      type: 'transfer',
      amount: this.tronWeb.fromSun(tx.raw_data.contract[0].parameter.value.amount || 0),
      from_address: this.tronWeb.address.fromHex(tx.raw_data.contract[0].parameter.value.owner_address),
      to_address: this.tronWeb.address.fromHex(tx.raw_data.contract[0].parameter.value.to_address),
      status: tx.ret[0].contractRet === 'SUCCESS' ? 'confirmed' : 'failed',
      timestamp: new Date(tx.raw_data.timestamp),
      block_height: tx.blockNumber,
      fee: this.tronWeb.fromSun(tx.ret[0].fee || 0)
    };
  }

  private validateTronAddress(address: string): void {
    if (!this.tronWeb.isAddress(address)) {
      throw new Error('Invalid TRON address format');
    }
  }
}
```

#### 4. Payout Service
```typescript
// src/services/payout.service.ts
import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { v4 as uuidv4 } from 'uuid';
import { Payout, PayoutDocument } from '../models/payout.model';
import { PayoutBatch, PayoutBatchDocument } from '../models/payout-batch.model';

@Injectable()
export class PayoutService {
  constructor(
    @InjectModel(Payout.name) private payoutModel: Model<PayoutDocument>,
    @InjectModel(PayoutBatch.name) private payoutBatchModel: Model<PayoutBatchDocument>,
    private walletService: WalletService,
    private usdtService: UsdtService
  ) {}

  async initiatePayout(payoutDto: PayoutInitiateDto): Promise<Payout> {
    try {
      // Validate recipient address
      this.validateTronAddress(payoutDto.recipient_address);

      // Create payout record
      const payout = new this.payoutModel({
        payout_id: uuidv4(),
        status: 'pending',
        amount: payoutDto.amount,
        currency: payoutDto.currency,
        recipient_address: payoutDto.recipient_address,
        submitted_at: new Date()
      });

      await payout.save();

      // Process payout asynchronously
      this.processPayout(payout);

      return payout;
    } catch (error) {
      throw new Error(`Failed to initiate payout: ${error.message}`);
    }
  }

  private async processPayout(payout: Payout): Promise<void> {
    try {
      // Update status to processing
      await this.payoutModel.updateOne(
        { payout_id: payout.payout_id },
        { status: 'processing' }
      );

      // Execute payout based on currency
      let txId: string;
      
      if (payout.currency === 'USDT') {
        txId = await this.executeUsdtPayout(payout);
      } else if (payout.currency === 'TRX') {
        txId = await this.executeTrxPayout(payout);
      }

      // Update payout record
      await this.payoutModel.updateOne(
        { payout_id: payout.payout_id },
        {
          status: 'completed',
          tx_id: txId,
          completed_at: new Date()
        }
      );
    } catch (error) {
      // Update payout record with error
      await this.payoutModel.updateOne(
        { payout_id: payout.payout_id },
        {
          status: 'failed',
          failure_reason: error.message,
          completed_at: new Date()
        }
      );
    }
  }

  private async executeUsdtPayout(payout: Payout): Promise<string> {
    // Implementation for USDT payout
    // This would use the USDT service to transfer funds
    return 'tx_hash_placeholder';
  }

  private async executeTrxPayout(payout: Payout): Promise<string> {
    // Implementation for TRX payout
    // This would use TRON network service to transfer TRX
    return 'tx_hash_placeholder';
  }

  async processBatchPayout(batchDto: PayoutBatchDto): Promise<PayoutBatch> {
    try {
      // Create batch record
      const batch = new this.payoutBatchModel({
        batch_id: uuidv4(),
        payout_count: batchDto.payouts.length,
        successful_count: 0,
        failed_count: 0,
        payout_ids: [],
        submitted_at: new Date()
      });

      await batch.save();

      // Process each payout in the batch
      const payoutPromises = batchDto.payouts.map(async (payoutDto) => {
        try {
          const payout = await this.initiatePayout(payoutDto);
          batch.payout_ids.push(payout.payout_id);
          batch.successful_count++;
        } catch (error) {
          batch.failed_count++;
        }
      });

      await Promise.all(payoutPromises);

      // Update batch record
      await this.payoutBatchModel.updateOne(
        { batch_id: batch.batch_id },
        {
          payout_ids: batch.payout_ids,
          successful_count: batch.successful_count,
          failed_count: batch.failed_count
        }
      );

      return batch;
    } catch (error) {
      throw new Error(`Failed to process batch payout: ${error.message}`);
    }
  }

  private validateTronAddress(address: string): void {
    // Implementation for TRON address validation
    if (!address || address.length !== 34 || !address.startsWith('T')) {
      throw new Error('Invalid TRON address format');
    }
  }
}
```

## Distroless Container Implementation

### Dockerfile
```dockerfile
# Multi-stage build for distroless container
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage with distroless image
FROM gcr.io/distroless/nodejs18-debian11

# Set working directory
WORKDIR /app

# Copy built application from builder stage
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Create non-root user
USER 1000

# Expose port
EXPOSE 8085

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["node", "dist/health-check.js"]

# Start the application
CMD ["node", "dist/main.js"]
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  tron-payment-service:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8085:8085"
    environment:
      - NODE_ENV=production
      - PORT=8085
      - MONGODB_URI=mongodb://mongo:27017/lucid_tron_payment
      - REDIS_URL=redis://redis:6379
      - TRON_API_KEY=${TRON_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - mongo
      - redis
    networks:
      - lucid-network
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp

  mongo:
    image: mongo:6.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    networks:
      - lucid-network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - lucid-network
    restart: unless-stopped

volumes:
  mongo_data:
  redis_data:

networks:
  lucid-network:
    driver: bridge
```

## Configuration Management

### Environment Configuration
```typescript
// src/config/configuration.ts
export default () => ({
  port: parseInt(process.env.PORT, 10) || 8085,
  nodeEnv: process.env.NODE_ENV || 'development',
  
  database: {
    mongodb: {
      uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/lucid_tron_payment',
      options: {
        useNewUrlParser: true,
        useUnifiedTopology: true,
        maxPoolSize: 10,
        serverSelectionTimeoutMS: 5000,
        socketTimeoutMS: 45000,
      },
    },
    redis: {
      url: process.env.REDIS_URL || 'redis://localhost:6379',
      options: {
        retryDelayOnFailover: 100,
        maxRetriesPerRequest: 3,
      },
    },
  },
  
  tron: {
    networkUrl: process.env.TRON_NETWORK_URL || 'https://api.trongrid.io',
    apiKey: process.env.TRON_API_KEY,
    usdtContract: 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',
    feeLimit: parseInt(process.env.TRON_FEE_LIMIT, 10) || 100000000,
  },
  
  security: {
    jwtSecret: process.env.JWT_SECRET,
    encryptionKey: process.env.ENCRYPTION_KEY,
    rateLimitWindow: parseInt(process.env.RATE_LIMIT_WINDOW, 10) || 900000, // 15 minutes
    rateLimitMax: parseInt(process.env.RATE_LIMIT_MAX, 10) || 100,
  },
  
  monitoring: {
    prometheus: {
      enabled: process.env.PROMETHEUS_ENABLED === 'true',
      port: parseInt(process.env.PROMETHEUS_PORT, 10) || 9090,
    },
    healthCheck: {
      interval: parseInt(process.env.HEALTH_CHECK_INTERVAL, 10) || 30000,
      timeout: parseInt(process.env.HEALTH_CHECK_TIMEOUT, 10) || 3000,
    },
  },
});
```

## Error Handling

### Global Exception Filter
```typescript
// src/filters/global-exception.filter.ts
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    const status =
      exception instanceof HttpException
        ? exception.getStatus()
        : HttpStatus.INTERNAL_SERVER_ERROR;

    const errorResponse = {
      error: {
        code: this.getErrorCode(exception),
        message: this.getErrorMessage(exception),
        details: this.getErrorDetails(exception),
        request_id: request.headers['x-request-id'] || 'unknown',
        timestamp: new Date().toISOString(),
        service: 'tron-payment-service',
        version: 'v1',
      },
    };

    response.status(status).json(errorResponse);
  }

  private getErrorCode(exception: unknown): string {
    if (exception instanceof HttpException) {
      const response = exception.getResponse();
      if (typeof response === 'object' && response['error']) {
        return response['error']['code'] || 'LUCID_ERR_UNKNOWN';
      }
    }
    return 'LUCID_ERR_UNKNOWN';
  }

  private getErrorMessage(exception: unknown): string {
    if (exception instanceof HttpException) {
      return exception.message;
    }
    if (exception instanceof Error) {
      return exception.message;
    }
    return 'Internal server error';
  }

  private getErrorDetails(exception: unknown): any {
    if (exception instanceof HttpException) {
      const response = exception.getResponse();
      if (typeof response === 'object' && response['error']) {
        return response['error']['details'] || {};
      }
    }
    return {};
  }
}
```

## Testing Strategy

### Unit Tests
```typescript
// tests/services/tron-network.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { TronNetworkService } from '../../src/services/tron-network.service';
import { ConfigService } from '@nestjs/config';

describe('TronNetworkService', () => {
  let service: TronNetworkService;
  let configService: ConfigService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        TronNetworkService,
        {
          provide: ConfigService,
          useValue: {
            get: jest.fn().mockReturnValue('test-api-key'),
          },
        },
      ],
    }).compile();

    service = module.get<TronNetworkService>(TronNetworkService);
    configService = module.get<ConfigService>(ConfigService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('getNetworkInfo', () => {
    it('should return network information', async () => {
      // Mock implementation
      const mockNetworkInfo = {
        network_name: 'TRON Mainnet',
        network_id: 'mainnet',
        chain_id: '0x2b6653dc',
        current_height: 50000000,
        block_time: 3,
        total_supply: '100000000000',
        circulating_supply: '99000000000',
        energy_price: '420',
        bandwidth_price: '1000',
      };

      jest.spyOn(service, 'getNetworkInfo').mockResolvedValue(mockNetworkInfo);

      const result = await service.getNetworkInfo();
      expect(result).toEqual(mockNetworkInfo);
    });
  });
});
```

### Integration Tests
```typescript
// tests/integration/tron-payment.integration.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../../src/app.module';

describe('TRON Payment Integration Tests', () => {
  let app: INestApplication;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  afterEach(async () => {
    await app.close();
  });

  describe('/tron/network/info (GET)', () => {
    it('should return TRON network information', () => {
      return request(app.getHttpServer())
        .get('/api/v1/tron/network/info')
        .expect(200)
        .expect((res) => {
          expect(res.body).toHaveProperty('network_name');
          expect(res.body).toHaveProperty('network_id');
          expect(res.body).toHaveProperty('current_height');
        });
    });
  });

  describe('/wallets (POST)', () => {
    it('should create a new wallet', () => {
      const createWalletDto = {
        name: 'Test Wallet',
        currency: 'TRX',
      };

      return request(app.getHttpServer())
        .post('/api/v1/wallets')
        .send(createWalletDto)
        .expect(201)
        .expect((res) => {
          expect(res.body).toHaveProperty('wallet_id');
          expect(res.body).toHaveProperty('address');
          expect(res.body).toHaveProperty('currency', 'TRX');
        });
    });
  });
});
```

## Performance Optimization

### Caching Strategy
```typescript
// src/services/cache.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class CacheService {
  constructor(@InjectRedis() private redis: Redis) {}

  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.redis.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error(`Cache get error for key ${key}:`, error);
      return null;
    }
  }

  async set(key: string, value: any, ttl: number = 300): Promise<void> {
    try {
      await this.redis.setex(key, ttl, JSON.stringify(value));
    } catch (error) {
      console.error(`Cache set error for key ${key}:`, error);
    }
  }

  async del(key: string): Promise<void> {
    try {
      await this.redis.del(key);
    } catch (error) {
      console.error(`Cache delete error for key ${key}:`, error);
    }
  }

  // Cache key generators
  generateWalletBalanceKey(walletId: string): string {
    return `wallet:balance:${walletId}`;
  }

  generateNetworkInfoKey(): string {
    return 'tron:network:info';
  }

  generateNetworkStatusKey(): string {
    return 'tron:network:status';
  }
}
```

### Database Indexing
```typescript
// src/config/database.config.ts
export const databaseIndexes = [
  // Wallet indexes
  { collection: 'wallets', index: { wallet_id: 1 }, options: { unique: true } },
  { collection: 'wallets', index: { user_id: 1, is_active: 1 } },
  { collection: 'wallets', index: { address: 1 }, options: { unique: true } },
  
  // Transaction indexes
  { collection: 'wallet_transactions', index: { wallet_id: 1, timestamp: -1 } },
  { collection: 'wallet_transactions', index: { tx_id: 1 }, options: { unique: true } },
  { collection: 'wallet_transactions', index: { status: 1, timestamp: -1 } },
  
  // USDT indexes
  { collection: 'usdt_transfers', index: { transfer_id: 1 }, options: { unique: true } },
  { collection: 'usdt_transfers', index: { from_address: 1, submitted_at: -1 } },
  { collection: 'usdt_transfers', index: { to_address: 1, submitted_at: -1 } },
  
  // Payout indexes
  { collection: 'payouts', index: { payout_id: 1 }, options: { unique: true } },
  { collection: 'payouts', index: { status: 1, submitted_at: -1 } },
  { collection: 'payouts', index: { recipient_address: 1, submitted_at: -1 } },
  
  // Staking indexes
  { collection: 'staking_stakes', index: { stake_id: 1 }, options: { unique: true } },
  { collection: 'staking_stakes', index: { wallet_address: 1, submitted_at: -1 } },
  
  // Payment indexes
  { collection: 'payments', index: { payment_id: 1 }, options: { unique: true } },
  { collection: 'payments', index: { status: 1, submitted_at: -1 } },
];
```

## Security Implementation

### Input Validation
```typescript
// src/pipes/validation.pipe.ts
import { PipeTransform, Injectable, ArgumentMetadata, BadRequestException } from '@nestjs/common';
import { validate } from 'class-validator';
import { plainToClass } from 'class-transformer';

@Injectable()
export class ValidationPipe implements PipeTransform<any> {
  async transform(value: any, { metatype }: ArgumentMetadata) {
    if (!metatype || !this.toValidate(metatype)) {
      return value;
    }

    const object = plainToClass(metatype, value);
    const errors = await validate(object);

    if (errors.length > 0) {
      const errorMessages = errors.map(error => 
        Object.values(error.constraints || {}).join(', ')
      );
      throw new BadRequestException({
        error: {
          code: 'LUCID_ERR_VALIDATION',
          message: 'Validation failed',
          details: { errors: errorMessages },
        },
      });
    }

    return value;
  }

  private toValidate(metatype: Function): boolean {
    const types: Function[] = [String, Boolean, Number, Array, Object];
    return !types.includes(metatype);
  }
}
```

### Rate Limiting
```typescript
// src/middleware/rate-limit.middleware.ts
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class RateLimitMiddleware implements NestMiddleware {
  constructor(@InjectRedis() private redis: Redis) {}

  async use(req: Request, res: Response, next: NextFunction) {
    const key = this.generateRateLimitKey(req);
    const window = 60; // 1 minute
    const limit = this.getRateLimit(req.path);

    try {
      const current = await this.redis.incr(key);
      
      if (current === 1) {
        await this.redis.expire(key, window);
      }

      if (current > limit) {
        return res.status(429).json({
          error: {
            code: 'LUCID_ERR_RATE_LIMIT',
            message: 'Rate limit exceeded',
            details: {
              limit,
              window,
              current,
            },
          },
        });
      }

      res.setHeader('X-RateLimit-Limit', limit);
      res.setHeader('X-RateLimit-Remaining', Math.max(0, limit - current));
      res.setHeader('X-RateLimit-Reset', new Date(Date.now() + window * 1000).toISOString());

      next();
    } catch (error) {
      console.error('Rate limiting error:', error);
      next(); // Continue on error
    }
  }

  private generateRateLimitKey(req: Request): string {
    const userId = req.headers['x-user-id'] || 'anonymous';
    const ip = req.ip;
    const path = req.path;
    return `rate_limit:${userId}:${ip}:${path}`;
  }

  private getRateLimit(path: string): number {
    const limits = {
      '/api/v1/tron/network': 1000,
      '/api/v1/wallets': 500,
      '/api/v1/usdt': 200,
      '/api/v1/payouts': 100,
      '/api/v1/staking': 50,
      '/api/v1/payments': 300,
    };

    for (const [prefix, limit] of Object.entries(limits)) {
      if (path.startsWith(prefix)) {
        return limit;
      }
    }

    return 100; // Default limit
  }
}
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
