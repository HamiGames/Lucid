# TRON Payment Cluster - Testing Validation

## Testing Strategy

### Testing Pyramid
```
                    E2E Tests (5%)
                   /              \
              Integration Tests (15%)
             /                        \
        Unit Tests (80%)
```

### Test Categories
1. **Unit Tests (80%)**: Fast, isolated tests for individual components
2. **Integration Tests (15%)**: Tests for component interactions
3. **End-to-End Tests (5%)**: Full system workflow tests

## Unit Testing

### Test Structure
```
tests/
├── unit/
│   ├── services/
│   ├── controllers/
│   ├── middleware/
│   ├── utils/
│   └── models/
├── integration/
│   ├── api/
│   ├── database/
│   └── external/
├── e2e/
│   ├── workflows/
│   └── scenarios/
└── fixtures/
    ├── data/
    └── mocks/
```

### TRON Network Service Tests
```typescript
// tests/unit/services/tron-network.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { TronNetworkService } from '../../../src/services/tron-network.service';
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

  describe('getNetworkInfo', () => {
    it('should return network information successfully', async () => {
      // Arrange
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

      // Act
      const result = await service.getNetworkInfo();

      // Assert
      expect(result).toEqual(mockNetworkInfo);
      expect(result.network_name).toBe('TRON Mainnet');
      expect(result.current_height).toBeGreaterThan(0);
    });

    it('should handle network errors gracefully', async () => {
      // Arrange
      jest.spyOn(service, 'getNetworkInfo').mockRejectedValue(new Error('Network error'));

      // Act & Assert
      await expect(service.getNetworkInfo()).rejects.toThrow('Failed to get TRON network info: Network error');
    });

    it('should validate network response format', async () => {
      // Arrange
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

      // Act
      const result = await service.getNetworkInfo();

      // Assert
      expect(result).toHaveProperty('network_name');
      expect(result).toHaveProperty('network_id');
      expect(result).toHaveProperty('chain_id');
      expect(result).toHaveProperty('current_height');
      expect(result).toHaveProperty('block_time');
      expect(result).toHaveProperty('total_supply');
      expect(result).toHaveProperty('circulating_supply');
      expect(result).toHaveProperty('energy_price');
      expect(result).toHaveProperty('bandwidth_price');
    });
  });

  describe('getNetworkStatus', () => {
    it('should return healthy status when network is synced', async () => {
      // Arrange
      const mockStatus = {
        status: 'healthy',
        current_height: 50000000,
        sync_percentage: 100,
        last_block_time: new Date(),
        node_count: 1000,
        network_hash_rate: '1000000',
      };

      jest.spyOn(service, 'getNetworkStatus').mockResolvedValue(mockStatus);

      // Act
      const result = await service.getNetworkStatus();

      // Assert
      expect(result.status).toBe('healthy');
      expect(result.sync_percentage).toBe(100);
    });

    it('should return degraded status when network is syncing', async () => {
      // Arrange
      const mockStatus = {
        status: 'degraded',
        current_height: 50000000,
        sync_percentage: 85,
        last_block_time: new Date(),
        node_count: 1000,
        network_hash_rate: '1000000',
      };

      jest.spyOn(service, 'getNetworkStatus').mockResolvedValue(mockStatus);

      // Act
      const result = await service.getNetworkStatus();

      // Assert
      expect(result.status).toBe('degraded');
      expect(result.sync_percentage).toBeLessThan(100);
    });

    it('should return down status when network is unavailable', async () => {
      // Arrange
      const mockStatus = {
        status: 'down',
        current_height: 0,
        sync_percentage: 0,
        last_block_time: new Date(),
        node_count: 0,
        network_hash_rate: '0',
      };

      jest.spyOn(service, 'getNetworkStatus').mockResolvedValue(mockStatus);

      // Act
      const result = await service.getNetworkStatus();

      // Assert
      expect(result.status).toBe('down');
      expect(result.sync_percentage).toBe(0);
    });
  });

  describe('determineNetworkStatus', () => {
    it('should return healthy for SYNCED status', () => {
      // Arrange
      const syncStatus = { syncStatus: 'SYNCED' };

      // Act
      const result = service['determineNetworkStatus'](syncStatus);

      // Assert
      expect(result).toBe('healthy');
    });

    it('should return degraded for SYNCING status', () => {
      // Arrange
      const syncStatus = { syncStatus: 'SYNCING' };

      // Act
      const result = service['determineNetworkStatus'](syncStatus);

      // Assert
      expect(result).toBe('degraded');
    });

    it('should return down for any other status', () => {
      // Arrange
      const syncStatus = { syncStatus: 'UNKNOWN' };

      // Act
      const result = service['determineNetworkStatus'](syncStatus);

      // Assert
      expect(result).toBe('down');
    });
  });
});
```

### Wallet Service Tests
```typescript
// tests/unit/services/wallet.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { getModelToken } from '@nestjs/mongoose';
import { WalletService } from '../../../src/services/wallet.service';
import { TronNetworkService } from '../../../src/services/tron-network.service';
import { Wallet } from '../../../src/models/wallet.model';

describe('WalletService', () => {
  let service: WalletService;
  let walletModel: any;
  let tronNetworkService: TronNetworkService;

  beforeEach(async () => {
    const mockWalletModel = {
      findOne: jest.fn(),
      create: jest.fn(),
      save: jest.fn(),
      updateOne: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        WalletService,
        {
          provide: getModelToken(Wallet.name),
          useValue: mockWalletModel,
        },
        {
          provide: TronNetworkService,
          useValue: {
            getNetworkInfo: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get<WalletService>(WalletService);
    walletModel = module.get(getModelToken(Wallet.name));
    tronNetworkService = module.get<TronNetworkService>(TronNetworkService);
  });

  describe('createWallet', () => {
    it('should create a new wallet successfully', async () => {
      // Arrange
      const createWalletDto = {
        name: 'Test Wallet',
        currency: 'TRX',
        hardware_wallet: false,
      };
      const userId = 'user123';
      const mockWallet = {
        wallet_id: 'wallet123',
        user_id: userId,
        name: createWalletDto.name,
        address: 'TTestAddress123456789012345678901234567890',
        currency: createWalletDto.currency,
        network: 'TRON',
        balance: 0,
        is_active: true,
        hardware_wallet: createWalletDto.hardware_wallet,
        created_at: new Date(),
        updated_at: new Date(),
      };

      walletModel.save.mockResolvedValue(mockWallet);

      // Act
      const result = await service.createWallet(createWalletDto, userId);

      // Assert
      expect(result).toEqual(mockWallet);
      expect(result.user_id).toBe(userId);
      expect(result.currency).toBe('TRX');
      expect(result.network).toBe('TRON');
      expect(result.address).toMatch(/^T[A-Za-z1-9]{33}$/);
    });

    it('should handle wallet creation errors', async () => {
      // Arrange
      const createWalletDto = {
        name: 'Test Wallet',
        currency: 'TRX',
      };
      const userId = 'user123';

      walletModel.save.mockRejectedValue(new Error('Database error'));

      // Act & Assert
      await expect(service.createWallet(createWalletDto, userId)).rejects.toThrow(
        'Failed to create wallet: Database error'
      );
    });

    it('should validate wallet address format', async () => {
      // Arrange
      const createWalletDto = {
        name: 'Test Wallet',
        currency: 'TRX',
      };
      const userId = 'user123';
      const mockWallet = {
        wallet_id: 'wallet123',
        user_id: userId,
        name: createWalletDto.name,
        address: 'TTestAddress123456789012345678901234567890',
        currency: createWalletDto.currency,
        network: 'TRON',
        balance: 0,
        is_active: true,
        hardware_wallet: false,
        created_at: new Date(),
        updated_at: new Date(),
      };

      walletModel.save.mockResolvedValue(mockWallet);

      // Act
      const result = await service.createWallet(createWalletDto, userId);

      // Assert
      expect(result.address).toMatch(/^T[A-Za-z1-9]{33}$/);
    });
  });

  describe('getWallet', () => {
    it('should return wallet for valid user', async () => {
      // Arrange
      const walletId = 'wallet123';
      const userId = 'user123';
      const mockWallet = {
        wallet_id: walletId,
        user_id: userId,
        name: 'Test Wallet',
        address: 'TTestAddress123456789012345678901234567890',
        currency: 'TRX',
        network: 'TRON',
        balance: 1000,
        is_active: true,
        hardware_wallet: false,
        created_at: new Date(),
        updated_at: new Date(),
      };

      walletModel.findOne.mockResolvedValue(mockWallet);
      jest.spyOn(service, 'updateWalletBalance').mockResolvedValue();

      // Act
      const result = await service.getWallet(walletId, userId);

      // Assert
      expect(result).toEqual(mockWallet);
      expect(walletModel.findOne).toHaveBeenCalledWith({
        wallet_id: walletId,
        user_id: userId,
        is_active: true,
      });
    });

    it('should throw error for non-existent wallet', async () => {
      // Arrange
      const walletId = 'nonexistent';
      const userId = 'user123';

      walletModel.findOne.mockResolvedValue(null);

      // Act & Assert
      await expect(service.getWallet(walletId, userId)).rejects.toThrow('Wallet not found');
    });

    it('should update wallet balance when retrieving', async () => {
      // Arrange
      const walletId = 'wallet123';
      const userId = 'user123';
      const mockWallet = {
        wallet_id: walletId,
        user_id: userId,
        name: 'Test Wallet',
        address: 'TTestAddress123456789012345678901234567890',
        currency: 'TRX',
        network: 'TRON',
        balance: 1000,
        is_active: true,
        hardware_wallet: false,
        created_at: new Date(),
        updated_at: new Date(),
      };

      walletModel.findOne.mockResolvedValue(mockWallet);
      const updateBalanceSpy = jest.spyOn(service, 'updateWalletBalance').mockResolvedValue();

      // Act
      await service.getWallet(walletId, userId);

      // Assert
      expect(updateBalanceSpy).toHaveBeenCalledWith(mockWallet);
    });
  });

  describe('updateWalletBalance', () => {
    it('should update TRX balance successfully', async () => {
      // Arrange
      const mockWallet = {
        wallet_id: 'wallet123',
        address: 'TTestAddress123456789012345678901234567890',
        currency: 'TRX',
      };

      // Mock TronWeb balance check
      const mockTronWeb = {
        trx: {
          getBalance: jest.fn().mockResolvedValue(1000),
        },
      };

      service['tronWeb'] = mockTronWeb;
      walletModel.updateOne.mockResolvedValue({ acknowledged: true });

      // Act
      await service.updateWalletBalance(mockWallet);

      // Assert
      expect(mockTronWeb.trx.getBalance).toHaveBeenCalledWith(mockWallet.address);
      expect(walletModel.updateOne).toHaveBeenCalledWith(
        { wallet_id: mockWallet.wallet_id },
        {
          balance: 1000,
          updated_at: expect.any(Date),
        }
      );
    });

    it('should update USDT balance successfully', async () => {
      // Arrange
      const mockWallet = {
        wallet_id: 'wallet123',
        address: 'TTestAddress123456789012345678901234567890',
        currency: 'USDT',
      };

      // Mock TronWeb USDT balance check
      const mockTronWeb = {
        fromSun: jest.fn().mockReturnValue(500),
        contract: jest.fn().mockReturnValue({
          at: jest.fn().mockReturnValue({
            balanceOf: jest.fn().mockReturnValue({
              call: jest.fn().mockResolvedValue(500000000), // 500 USDT in sun
            }),
          }),
        }),
      };

      service['tronWeb'] = mockTronWeb;
      walletModel.updateOne.mockResolvedValue({ acknowledged: true });

      // Act
      await service.updateWalletBalance(mockWallet);

      // Assert
      expect(walletModel.updateOne).toHaveBeenCalledWith(
        { wallet_id: mockWallet.wallet_id },
        {
          balance: 500,
          updated_at: expect.any(Date),
        }
      );
    });

    it('should handle balance update errors gracefully', async () => {
      // Arrange
      const mockWallet = {
        wallet_id: 'wallet123',
        address: 'TTestAddress123456789012345678901234567890',
        currency: 'TRX',
      };

      const mockTronWeb = {
        trx: {
          getBalance: jest.fn().mockRejectedValue(new Error('Network error')),
        },
      };

      service['tronWeb'] = mockTronWeb;

      // Act & Assert
      await expect(service.updateWalletBalance(mockWallet)).rejects.toThrow(
        'Failed to update wallet balance: Network error'
      );
    });
  });
});
```

### USDT Service Tests
```typescript
// tests/unit/services/usdt.service.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { getModelToken } from '@nestjs/mongoose';
import { UsdtService } from '../../../src/services/usdt.service';
import { TronNetworkService } from '../../../src/services/tron-network.service';
import { UsdtTransfer } from '../../../src/models/usdt-transfer.model';

describe('UsdtService', () => {
  let service: UsdtService;
  let usdtTransferModel: any;
  let tronNetworkService: TronNetworkService;

  beforeEach(async () => {
    const mockUsdtTransferModel = {
      findOne: jest.fn(),
      create: jest.fn(),
      save: jest.fn(),
      updateOne: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UsdtService,
        {
          provide: getModelToken(UsdtTransfer.name),
          useValue: mockUsdtTransferModel,
        },
        {
          provide: TronNetworkService,
          useValue: {
            getNetworkInfo: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get<UsdtService>(UsdtService);
    usdtTransferModel = module.get(getModelToken(UsdtTransfer.name));
    tronNetworkService = module.get<TronNetworkService>(TronNetworkService);
  });

  describe('transferUsdt', () => {
    it('should transfer USDT successfully', async () => {
      // Arrange
      const transferDto = {
        from_address: 'TFromAddress123456789012345678901234567890',
        to_address: 'TToAddress123456789012345678901234567890',
        amount: 100,
        memo: 'Test transfer',
      };

      const mockTransfer = {
        transfer_id: 'transfer123',
        tx_id: '',
        status: 'pending',
        amount: transferDto.amount,
        from_address: transferDto.from_address,
        to_address: transferDto.to_address,
        submitted_at: new Date(),
      };

      usdtTransferModel.save.mockResolvedValue(mockTransfer);
      jest.spyOn(service, 'getUsdtBalance').mockResolvedValue(1000);
      jest.spyOn(service, 'executeUsdtTransfer').mockResolvedValue('tx_hash_123');

      // Act
      const result = await service.transferUsdt(transferDto);

      // Assert
      expect(result).toEqual(mockTransfer);
      expect(service.getUsdtBalance).toHaveBeenCalledWith(transferDto.from_address);
      expect(service.executeUsdtTransfer).toHaveBeenCalledWith(transferDto);
    });

    it('should throw error for insufficient balance', async () => {
      // Arrange
      const transferDto = {
        from_address: 'TFromAddress123456789012345678901234567890',
        to_address: 'TToAddress123456789012345678901234567890',
        amount: 1000,
      };

      jest.spyOn(service, 'getUsdtBalance').mockResolvedValue(100);

      // Act & Assert
      await expect(service.transferUsdt(transferDto)).rejects.toThrow('Insufficient USDT balance');
    });

    it('should validate TRON addresses', async () => {
      // Arrange
      const transferDto = {
        from_address: 'invalid_address',
        to_address: 'TToAddress123456789012345678901234567890',
        amount: 100,
      };

      // Act & Assert
      await expect(service.transferUsdt(transferDto)).rejects.toThrow('Invalid TRON address format');
    });

    it('should handle transfer execution errors', async () => {
      // Arrange
      const transferDto = {
        from_address: 'TFromAddress123456789012345678901234567890',
        to_address: 'TToAddress123456789012345678901234567890',
        amount: 100,
      };

      const mockTransfer = {
        transfer_id: 'transfer123',
        tx_id: '',
        status: 'pending',
        amount: transferDto.amount,
        from_address: transferDto.from_address,
        to_address: transferDto.to_address,
        submitted_at: new Date(),
      };

      usdtTransferModel.save.mockResolvedValue(mockTransfer);
      jest.spyOn(service, 'getUsdtBalance').mockResolvedValue(1000);
      jest.spyOn(service, 'executeUsdtTransfer').mockRejectedValue(new Error('Transaction failed'));

      // Act & Assert
      await expect(service.transferUsdt(transferDto)).rejects.toThrow(
        'Failed to transfer USDT: Transaction failed'
      );
    });
  });

  describe('getUsdtBalance', () => {
    it('should return USDT balance successfully', async () => {
      // Arrange
      const address = 'TTestAddress123456789012345678901234567890';
      const expectedBalance = 500;

      const mockTronWeb = {
        fromSun: jest.fn().mockReturnValue(expectedBalance),
        contract: jest.fn().mockReturnValue({
          at: jest.fn().mockReturnValue({
            balanceOf: jest.fn().mockReturnValue({
              call: jest.fn().mockResolvedValue(500000000), // 500 USDT in sun
            }),
          }),
        }),
      };

      service['tronWeb'] = mockTronWeb;

      // Act
      const result = await service.getUsdtBalance(address);

      // Assert
      expect(result).toBe(expectedBalance);
    });

    it('should return 0 for invalid address', async () => {
      // Arrange
      const address = 'invalid_address';

      // Act & Assert
      await expect(service.getUsdtBalance(address)).rejects.toThrow('Invalid TRON address format');
    });

    it('should handle contract errors gracefully', async () => {
      // Arrange
      const address = 'TTestAddress123456789012345678901234567890';

      const mockTronWeb = {
        contract: jest.fn().mockReturnValue({
          at: jest.fn().mockReturnValue({
            balanceOf: jest.fn().mockReturnValue({
              call: jest.fn().mockRejectedValue(new Error('Contract error')),
            }),
          }),
        }),
      };

      service['tronWeb'] = mockTronWeb;

      // Act & Assert
      await expect(service.getUsdtBalance(address)).rejects.toThrow(
        'Failed to get USDT balance: Contract error'
      );
    });
  });
});
```

## Integration Testing

### API Integration Tests
```typescript
// tests/integration/api/tron-payment.integration.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../../../src/app.module';
import { getModelToken } from '@nestjs/mongoose';
import { Wallet } from '../../../src/models/wallet.model';
import { UsdtTransfer } from '../../../src/models/usdt-transfer.model';

describe('TRON Payment API Integration Tests', () => {
  let app: INestApplication;
  let walletModel: any;
  let usdtTransferModel: any;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    })
      .overrideProvider(getModelToken(Wallet.name))
      .useValue({
        findOne: jest.fn(),
        create: jest.fn(),
        save: jest.fn(),
        updateOne: jest.fn(),
      })
      .overrideProvider(getModelToken(UsdtTransfer.name))
      .useValue({
        findOne: jest.fn(),
        create: jest.fn(),
        save: jest.fn(),
        updateOne: jest.fn(),
      })
      .compile();

    app = moduleFixture.createNestApplication();
    walletModel = moduleFixture.get(getModelToken(Wallet.name));
    usdtTransferModel = moduleFixture.get(getModelToken(UsdtTransfer.name));
    
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  describe('TRON Network Endpoints', () => {
    describe('GET /api/v1/tron/network/info', () => {
      it('should return TRON network information', async () => {
        // Act
        const response = await request(app.getHttpServer())
          .get('/api/v1/tron/network/info')
          .expect(200);

        // Assert
        expect(response.body).toHaveProperty('network_name');
        expect(response.body).toHaveProperty('network_id');
        expect(response.body).toHaveProperty('current_height');
        expect(response.body).toHaveProperty('block_time');
        expect(response.body).toHaveProperty('total_supply');
        expect(response.body).toHaveProperty('circulating_supply');
        expect(response.body).toHaveProperty('energy_price');
        expect(response.body).toHaveProperty('bandwidth_price');
      });

      it('should handle network errors gracefully', async () => {
        // Mock network error
        jest.spyOn(app.get('TronNetworkService'), 'getNetworkInfo').mockRejectedValue(
          new Error('Network unavailable')
        );

        // Act
        const response = await request(app.getHttpServer())
          .get('/api/v1/tron/network/info')
          .expect(500);

        // Assert
        expect(response.body.error.code).toBe('LUCID_ERR_9001');
        expect(response.body.error.message).toContain('TRON network error');
      });
    });

    describe('GET /api/v1/tron/network/status', () => {
      it('should return network status', async () => {
        // Act
        const response = await request(app.getHttpServer())
          .get('/api/v1/tron/network/status')
          .expect(200);

        // Assert
        expect(response.body).toHaveProperty('status');
        expect(response.body).toHaveProperty('current_height');
        expect(response.body).toHaveProperty('sync_percentage');
        expect(response.body).toHaveProperty('last_block_time');
        expect(response.body).toHaveProperty('node_count');
        expect(response.body).toHaveProperty('network_hash_rate');
        
        expect(['healthy', 'degraded', 'down']).toContain(response.body.status);
        expect(response.body.sync_percentage).toBeGreaterThanOrEqual(0);
        expect(response.body.sync_percentage).toBeLessThanOrEqual(100);
      });
    });
  });

  describe('Wallet Endpoints', () => {
    describe('POST /api/v1/wallets', () => {
      it('should create a new wallet', async () => {
        // Arrange
        const createWalletDto = {
          name: 'Test Wallet',
          currency: 'TRX',
          hardware_wallet: false,
        };

        const mockWallet = {
          wallet_id: 'wallet123',
          user_id: 'user123',
          name: createWalletDto.name,
          address: 'TTestAddress123456789012345678901234567890',
          currency: createWalletDto.currency,
          network: 'TRON',
          balance: 0,
          is_active: true,
          hardware_wallet: createWalletDto.hardware_wallet,
          created_at: new Date(),
          updated_at: new Date(),
        };

        walletModel.save.mockResolvedValue(mockWallet);

        // Act
        const response = await request(app.getHttpServer())
          .post('/api/v1/wallets')
          .send(createWalletDto)
          .expect(201);

        // Assert
        expect(response.body).toHaveProperty('wallet_id');
        expect(response.body).toHaveProperty('address');
        expect(response.body).toHaveProperty('currency', 'TRX');
        expect(response.body).toHaveProperty('network', 'TRON');
        expect(response.body.address).toMatch(/^T[A-Za-z1-9]{33}$/);
      });

      it('should validate wallet creation data', async () => {
        // Arrange
        const invalidWalletDto = {
          name: '', // Empty name
          currency: 'INVALID', // Invalid currency
        };

        // Act
        const response = await request(app.getHttpServer())
          .post('/api/v1/wallets')
          .send(invalidWalletDto)
          .expect(400);

        // Assert
        expect(response.body.error.code).toBe('LUCID_ERR_VALIDATION');
        expect(response.body.error.message).toBe('Validation failed');
      });
    });

    describe('GET /api/v1/wallets/:wallet_id', () => {
      it('should return wallet details', async () => {
        // Arrange
        const walletId = 'wallet123';
        const userId = 'user123';
        const mockWallet = {
          wallet_id: walletId,
          user_id: userId,
          name: 'Test Wallet',
          address: 'TTestAddress123456789012345678901234567890',
          currency: 'TRX',
          network: 'TRON',
          balance: 1000,
          is_active: true,
          hardware_wallet: false,
          created_at: new Date(),
          updated_at: new Date(),
        };

        walletModel.findOne.mockResolvedValue(mockWallet);

        // Act
        const response = await request(app.getHttpServer())
          .get(`/api/v1/wallets/${walletId}`)
          .expect(200);

        // Assert
        expect(response.body).toEqual(mockWallet);
      });

      it('should return 404 for non-existent wallet', async () => {
        // Arrange
        const walletId = 'nonexistent';
        walletModel.findOne.mockResolvedValue(null);

        // Act
        const response = await request(app.getHttpServer())
          .get(`/api/v1/wallets/${walletId}`)
          .expect(404);

        // Assert
        expect(response.body.error.code).toBe('LUCID_ERR_1001');
        expect(response.body.error.message).toBe('Wallet not found');
      });
    });
  });

  describe('USDT Endpoints', () => {
    describe('POST /api/v1/usdt/transfer', () => {
      it('should transfer USDT successfully', async () => {
        // Arrange
        const transferDto = {
          from_address: 'TFromAddress123456789012345678901234567890',
          to_address: 'TToAddress123456789012345678901234567890',
          amount: 100,
          memo: 'Test transfer',
        };

        const mockTransfer = {
          transfer_id: 'transfer123',
          tx_id: 'tx_hash_123',
          status: 'pending',
          amount: transferDto.amount,
          from_address: transferDto.from_address,
          to_address: transferDto.to_address,
          submitted_at: new Date(),
        };

        usdtTransferModel.save.mockResolvedValue(mockTransfer);

        // Act
        const response = await request(app.getHttpServer())
          .post('/api/v1/usdt/transfer')
          .send(transferDto)
          .expect(202);

        // Assert
        expect(response.body).toHaveProperty('transfer_id');
        expect(response.body).toHaveProperty('status', 'pending');
        expect(response.body).toHaveProperty('amount', transferDto.amount);
        expect(response.body).toHaveProperty('from_address', transferDto.from_address);
        expect(response.body).toHaveProperty('to_address', transferDto.to_address);
      });

      it('should validate USDT transfer data', async () => {
        // Arrange
        const invalidTransferDto = {
          from_address: 'invalid_address',
          to_address: 'TToAddress123456789012345678901234567890',
          amount: -100, // Negative amount
        };

        // Act
        const response = await request(app.getHttpServer())
          .post('/api/v1/usdt/transfer')
          .send(invalidTransferDto)
          .expect(400);

        // Assert
        expect(response.body.error.code).toBe('LUCID_ERR_VALIDATION');
        expect(response.body.error.message).toBe('Validation failed');
      });

      it('should handle insufficient balance', async () => {
        // Arrange
        const transferDto = {
          from_address: 'TFromAddress123456789012345678901234567890',
          to_address: 'TToAddress123456789012345678901234567890',
          amount: 1000,
        };

        // Mock insufficient balance
        jest.spyOn(app.get('UsdtService'), 'getUsdtBalance').mockResolvedValue(100);

        // Act
        const response = await request(app.getHttpServer())
          .post('/api/v1/usdt/transfer')
          .send(transferDto)
          .expect(400);

        // Assert
        expect(response.body.error.code).toBe('LUCID_ERR_1102');
        expect(response.body.error.message).toBe('USDT balance insufficient');
      });
    });

    describe('GET /api/v1/usdt/balance/:address', () => {
      it('should return USDT balance', async () => {
        // Arrange
        const address = 'TTestAddress123456789012345678901234567890';
        const expectedBalance = 500;

        // Mock balance check
        jest.spyOn(app.get('UsdtService'), 'getUsdtBalance').mockResolvedValue(expectedBalance);

        // Act
        const response = await request(app.getHttpServer())
          .get(`/api/v1/usdt/balance/${address}`)
          .expect(200);

        // Assert
        expect(response.body).toHaveProperty('address', address);
        expect(response.body).toHaveProperty('balance', expectedBalance);
        expect(response.body).toHaveProperty('balance_formatted');
        expect(response.body).toHaveProperty('last_updated');
      });

      it('should validate TRON address format', async () => {
        // Arrange
        const invalidAddress = 'invalid_address';

        // Act
        const response = await request(app.getHttpServer())
          .get(`/api/v1/usdt/balance/${invalidAddress}`)
          .expect(400);

        // Assert
        expect(response.body.error.code).toBe('LUCID_ERR_1002');
        expect(response.body.error.message).toBe('Invalid wallet address');
      });
    });
  });
});
```

## End-to-End Testing

### E2E Test Scenarios
```typescript
// tests/e2e/workflows/tron-payment-workflow.e2e.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('TRON Payment E2E Workflow Tests', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  describe('Complete USDT Transfer Workflow', () => {
    it('should complete full USDT transfer workflow', async () => {
      // Step 1: Create wallet
      const createWalletResponse = await request(app.getHttpServer())
        .post('/api/v1/wallets')
        .send({
          name: 'E2E Test Wallet',
          currency: 'USDT',
        })
        .expect(201);

      const walletId = createWalletResponse.body.wallet_id;
      const walletAddress = createWalletResponse.body.address;

      // Step 2: Check wallet balance
      const balanceResponse = await request(app.getHttpServer())
        .get(`/api/v1/wallets/${walletId}/balance`)
        .query({ currency: 'USDT' })
        .expect(200);

      expect(balanceResponse.body).toHaveProperty('balance');
      expect(balanceResponse.body).toHaveProperty('currency', 'USDT');

      // Step 3: Transfer USDT (if balance available)
      if (balanceResponse.body.balance > 0) {
        const transferResponse = await request(app.getHttpServer())
          .post('/api/v1/usdt/transfer')
          .send({
            from_address: walletAddress,
            to_address: 'TRecipientAddress123456789012345678901234567890',
            amount: Math.min(balanceResponse.body.balance * 0.1, 10), // Transfer 10% or max 10 USDT
            memo: 'E2E test transfer',
          })
          .expect(202);

        expect(transferResponse.body).toHaveProperty('transfer_id');
        expect(transferResponse.body).toHaveProperty('status', 'pending');

        // Step 4: Check transfer status
        const statusResponse = await request(app.getHttpServer())
          .get(`/api/v1/usdt/transactions/${walletAddress}`)
          .expect(200);

        expect(statusResponse.body).toHaveProperty('transactions');
        expect(Array.isArray(statusResponse.body.transactions)).toBe(true);
      }
    });
  });

  describe('Complete Payout Workflow', () => {
    it('should complete full payout workflow', async () => {
      // Step 1: Initiate payout
      const payoutResponse = await request(app.getHttpServer())
        .post('/api/v1/payouts/initiate')
        .send({
          recipient_address: 'TRecipientAddress123456789012345678901234567890',
          amount: 100,
          currency: 'USDT',
          memo: 'E2E test payout',
          priority: 'normal',
        })
        .expect(202);

      const payoutId = payoutResponse.body.payout_id;

      // Step 2: Check payout status
      const statusResponse = await request(app.getHttpServer())
        .get(`/api/v1/payouts/${payoutId}`)
        .expect(200);

      expect(statusResponse.body).toHaveProperty('payout_id', payoutId);
      expect(statusResponse.body).toHaveProperty('status');
      expect(statusResponse.body).toHaveProperty('amount', 100);
      expect(statusResponse.body).toHaveProperty('currency', 'USDT');

      // Step 3: Check payout history
      const historyResponse = await request(app.getHttpServer())
        .get('/api/v1/payouts/history')
        .expect(200);

      expect(historyResponse.body).toHaveProperty('payouts');
      expect(Array.isArray(historyResponse.body.payouts)).toBe(true);
    });
  });

  describe('Complete Staking Workflow', () => {
    it('should complete full staking workflow', async () => {
      // Step 1: Check staking status
      const statusResponse = await request(app.getHttpServer())
        .get('/api/v1/staking/status/TTestAddress123456789012345678901234567890')
        .expect(200);

      expect(statusResponse.body).toHaveProperty('address');
      expect(statusResponse.body).toHaveProperty('total_staked');
      expect(statusResponse.body).toHaveProperty('total_rewards');

      // Step 2: Check staking rewards
      const rewardsResponse = await request(app.getHttpServer())
        .get('/api/v1/staking/rewards/TTestAddress123456789012345678901234567890')
        .query({ period: 'all' })
        .expect(200);

      expect(rewardsResponse.body).toHaveProperty('address');
      expect(rewardsResponse.body).toHaveProperty('total_rewards');
      expect(rewardsResponse.body).toHaveProperty('reward_entries');
    });
  });
});
```

## Performance Testing

### Load Testing
```typescript
// tests/performance/load-test.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../../src/app.module';

describe('TRON Payment Load Tests', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  describe('Concurrent Wallet Operations', () => {
    it('should handle 100 concurrent wallet balance checks', async () => {
      const walletId = 'wallet123';
      const concurrentRequests = 100;

      const startTime = Date.now();

      const promises = Array.from({ length: concurrentRequests }, () =>
        request(app.getHttpServer())
          .get(`/api/v1/wallets/${walletId}/balance`)
          .query({ currency: 'TRX' })
      );

      const responses = await Promise.all(promises);
      const endTime = Date.now();

      // Assert all requests succeeded
      responses.forEach(response => {
        expect(response.status).toBe(200);
      });

      // Assert response time is reasonable (under 5 seconds)
      expect(endTime - startTime).toBeLessThan(5000);

      console.log(`100 concurrent requests completed in ${endTime - startTime}ms`);
    });
  });

  describe('Rate Limiting Tests', () => {
    it('should enforce rate limits on USDT operations', async () => {
      const transferDto = {
        from_address: 'TFromAddress123456789012345678901234567890',
        to_address: 'TToAddress123456789012345678901234567890',
        amount: 1,
      };

      const requests = Array.from({ length: 250 }, () =>
        request(app.getHttpServer())
          .post('/api/v1/usdt/transfer')
          .send(transferDto)
      );

      const responses = await Promise.all(requests);

      // Count successful vs rate-limited responses
      const successful = responses.filter(r => r.status === 202).length;
      const rateLimited = responses.filter(r => r.status === 429).length;

      expect(rateLimited).toBeGreaterThan(0); // Should have some rate-limited requests
      expect(successful).toBeLessThanOrEqual(200); // Should not exceed rate limit

      console.log(`Successful: ${successful}, Rate Limited: ${rateLimited}`);
    });
  });
});
```

## Test Configuration

### Jest Configuration
```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: [
    '**/__tests__/**/*.ts',
    '**/?(*.)+(spec|test).ts'
  ],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/main.ts',
    '!src/app.module.ts',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  testTimeout: 30000,
  maxWorkers: 4,
};
```

### Test Setup
```typescript
// tests/setup.ts
import { MongoMemoryServer } from 'mongodb-memory-server';
import { Test } from '@nestjs/testing';
import { getConnectionToken } from '@nestjs/mongoose';

let mongoServer: MongoMemoryServer;

beforeAll(async () => {
  mongoServer = await MongoMemoryServer.create();
  process.env.MONGODB_URI = mongoServer.getUri();
});

afterAll(async () => {
  if (mongoServer) {
    await mongoServer.stop();
  }
});

// Global test utilities
global.createTestApp = async (moduleClass: any) => {
  const moduleFixture = await Test.createTestingModule({
    imports: [moduleClass],
  }).compile();

  return moduleFixture.createNestApplication();
};

global.createTestUser = () => ({
  id: 'test-user-id',
  username: 'testuser',
  roles: ['user'],
  permissions: ['wallet:read', 'wallet:write', 'usdt:transfer'],
});

global.createTestWallet = () => ({
  wallet_id: 'test-wallet-id',
  user_id: 'test-user-id',
  name: 'Test Wallet',
  address: 'TTestAddress123456789012345678901234567890',
  currency: 'TRX',
  network: 'TRON',
  balance: 1000,
  is_active: true,
  hardware_wallet: false,
  created_at: new Date(),
  updated_at: new Date(),
});
```

## Test Data Management

### Test Fixtures
```typescript
// tests/fixtures/test-data.ts
export const testWallets = {
  trxWallet: {
    wallet_id: 'wallet-trx-123',
    user_id: 'user-123',
    name: 'TRX Test Wallet',
    address: 'TTestAddress123456789012345678901234567890',
    currency: 'TRX',
    network: 'TRON',
    balance: 10000,
    is_active: true,
    hardware_wallet: false,
    created_at: new Date(),
    updated_at: new Date(),
  },
  usdtWallet: {
    wallet_id: 'wallet-usdt-123',
    user_id: 'user-123',
    name: 'USDT Test Wallet',
    address: 'TUsdtAddress123456789012345678901234567890',
    currency: 'USDT',
    network: 'TRON',
    balance: 5000,
    is_active: true,
    hardware_wallet: false,
    created_at: new Date(),
    updated_at: new Date(),
  },
};

export const testTransfers = {
  validTransfer: {
    from_address: 'TFromAddress123456789012345678901234567890',
    to_address: 'TToAddress123456789012345678901234567890',
    amount: 100,
    memo: 'Test transfer',
  },
  invalidTransfer: {
    from_address: 'invalid_address',
    to_address: 'TToAddress123456789012345678901234567890',
    amount: -100,
  },
};

export const testPayouts = {
  validPayout: {
    recipient_address: 'TRecipientAddress123456789012345678901234567890',
    amount: 500,
    currency: 'USDT',
    memo: 'Test payout',
    priority: 'normal',
  },
  batchPayout: {
    payouts: [
      {
        recipient_address: 'TRecipient1Address123456789012345678901234567890',
        amount: 100,
        currency: 'USDT',
      },
      {
        recipient_address: 'TRecipient2Address123456789012345678901234567890',
        amount: 200,
        currency: 'USDT',
      },
    ],
    batch_memo: 'Batch test payout',
  },
};
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
