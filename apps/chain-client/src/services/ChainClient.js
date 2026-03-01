/**
 * Chain Client Service
 * Handles blockchain interactions and status monitoring
 */

export class ChainClient {
  constructor(web3, provider, logger) {
    this.web3 = web3;
    this.provider = provider;
    this.logger = logger;
    this.isConnected = false;
    this.chainId = null;
    this.networkId = null;
    this.lastBlockNumber = 0;
    this.connectionRetries = 0;
    this.maxRetries = 5;
  }

  async initialize() {
    try {
      this.logger.info('Initializing Chain Client...');
      
      // Test connection
      await this.testConnection();
      
      // Get chain info
      await this.updateChainInfo();
      
      // Start monitoring
      this.startMonitoring();
      
      this.logger.info('Chain Client initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize Chain Client:', error);
      throw error;
    }
  }

  async testConnection() {
    try {
      // Test Web3 connection
      const isListening = await this.web3.eth.net.isListening();
      if (!isListening) {
        throw new Error('Web3 connection failed');
      }

      // Test provider connection
      const blockNumber = await this.provider.getBlockNumber();
      
      this.isConnected = true;
      this.lastBlockNumber = blockNumber;
      this.connectionRetries = 0;
      
      this.logger.info('Chain connection successful', { blockNumber });
    } catch (error) {
      this.isConnected = false;
      this.connectionRetries++;
      
      this.logger.error('Chain connection failed:', error);
      
      if (this.connectionRetries >= this.maxRetries) {
        throw new Error(`Chain connection failed after ${this.maxRetries} retries`);
      }
      
      // Retry after delay
      setTimeout(() => this.testConnection(), 5000);
    }
  }

  async updateChainInfo() {
    try {
      // Get chain ID
      this.chainId = await this.web3.eth.getChainId();
      
      // Get network ID
      this.networkId = await this.web3.eth.net.getId();
      
      this.logger.info('Chain info updated', {
        chainId: this.chainId,
        networkId: this.networkId
      });
    } catch (error) {
      this.logger.error('Failed to update chain info:', error);
    }
  }

  startMonitoring() {
    // Monitor new blocks
    setInterval(async () => {
      try {
        const currentBlockNumber = await this.web3.eth.getBlockNumber();
        
        if (currentBlockNumber > this.lastBlockNumber) {
          this.lastBlockNumber = currentBlockNumber;
          this.logger.info('New block detected', { blockNumber: currentBlockNumber });
        }
      } catch (error) {
        this.logger.error('Block monitoring error:', error);
      }
    }, 10000); // Check every 10 seconds
  }

  async getChainStatus() {
    try {
      const blockNumber = await this.web3.eth.getBlockNumber();
      const gasPrice = await this.web3.eth.getGasPrice();
      const peerCount = await this.web3.eth.net.getPeerCount();
      
      return {
        connected: this.isConnected,
        chainId: this.chainId,
        networkId: this.networkId,
        blockNumber,
        gasPrice: this.web3.utils.fromWei(gasPrice, 'gwei'),
        peerCount,
        lastUpdate: new Date().toISOString()
      };
    } catch (error) {
      this.logger.error('Failed to get chain status:', error);
      throw error;
    }
  }

  async getLatestBlock() {
    try {
      const blockNumber = await this.web3.eth.getBlockNumber();
      const block = await this.web3.eth.getBlock(blockNumber);
      
      return {
        number: block.number,
        hash: block.hash,
        parentHash: block.parentHash,
        timestamp: block.timestamp,
        gasLimit: block.gasLimit,
        gasUsed: block.gasUsed,
        transactions: block.transactions.length
      };
    } catch (error) {
      this.logger.error('Failed to get latest block:', error);
      throw error;
    }
  }

  async getBlock(blockNumber) {
    try {
      const block = await this.web3.eth.getBlock(blockNumber);
      
      if (!block) {
        throw new Error('Block not found');
      }
      
      return block;
    } catch (error) {
      this.logger.error('Failed to get block:', error);
      throw error;
    }
  }

  async getTransaction(transactionHash) {
    try {
      const transaction = await this.web3.eth.getTransaction(transactionHash);
      
      if (!transaction) {
        throw new Error('Transaction not found');
      }
      
      return transaction;
    } catch (error) {
      this.logger.error('Failed to get transaction:', error);
      throw error;
    }
  }

  async getTransactionReceipt(transactionHash) {
    try {
      const receipt = await this.web3.eth.getTransactionReceipt(transactionHash);
      
      if (!receipt) {
        throw new Error('Transaction receipt not found');
      }
      
      return receipt;
    } catch (error) {
      this.logger.error('Failed to get transaction receipt:', error);
      throw error;
    }
  }

  async getBalance(address) {
    try {
      const balance = await this.web3.eth.getBalance(address);
      return this.web3.utils.fromWei(balance, 'ether');
    } catch (error) {
      this.logger.error('Failed to get balance:', error);
      throw error;
    }
  }

  async getGasPrice() {
    try {
      const gasPrice = await this.web3.eth.getGasPrice();
      return this.web3.utils.fromWei(gasPrice, 'gwei');
    } catch (error) {
      this.logger.error('Failed to get gas price:', error);
      throw error;
    }
  }

  async estimateGas(transaction) {
    try {
      const gasEstimate = await this.web3.eth.estimateGas(transaction);
      return gasEstimate;
    } catch (error) {
      this.logger.error('Failed to estimate gas:', error);
      throw error;
    }
  }

  async waitForTransaction(transactionHash, confirmations = 1) {
    try {
      const receipt = await this.web3.eth.waitForTransactionReceipt(transactionHash, confirmations);
      return receipt;
    } catch (error) {
      this.logger.error('Failed to wait for transaction:', error);
      throw error;
    }
  }

  async subscribeToNewBlocks(callback) {
    try {
      const subscription = this.web3.eth.subscribe('newBlockHeaders');
      
      subscription.on('data', (blockHeader) => {
        callback(null, blockHeader);
      });
      
      subscription.on('error', (error) => {
        callback(error, null);
      });
      
      return subscription;
    } catch (error) {
      this.logger.error('Failed to subscribe to new blocks:', error);
      throw error;
    }
  }

  async subscribeToPendingTransactions(callback) {
    try {
      const subscription = this.web3.eth.subscribe('pendingTransactions');
      
      subscription.on('data', (transactionHash) => {
        callback(null, transactionHash);
      });
      
      subscription.on('error', (error) => {
        callback(error, null);
      });
      
      return subscription;
    } catch (error) {
      this.logger.error('Failed to subscribe to pending transactions:', error);
      throw error;
    }
  }

  async getNetworkInfo() {
    try {
      const chainId = await this.web3.eth.getChainId();
      const networkId = await this.web3.eth.net.getId();
      const peerCount = await this.web3.eth.net.getPeerCount();
      
      return {
        chainId,
        networkId,
        peerCount
      };
    } catch (error) {
      this.logger.error('Failed to get network info:', error);
      throw error;
    }
  }

  async isConnected() {
    try {
      await this.web3.eth.net.isListening();
      return true;
    } catch (error) {
      return false;
    }
  }

  async reconnect() {
    try {
      this.logger.info('Attempting to reconnect to chain...');
      await this.testConnection();
      await this.updateChainInfo();
      this.logger.info('Successfully reconnected to chain');
    } catch (error) {
      this.logger.error('Failed to reconnect to chain:', error);
      throw error;
    }
  }
}
