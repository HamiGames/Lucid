import { LucidAPIClient } from '../../../shared/api-client';

export interface WalletInfo {
  tron_address: string;
  balance_trx: number;
  balance_usd: number;
  balance_usdt: number;
  hardware_wallet?: {
    type: 'ledger' | 'trezor' | 'keepkey';
    device_id: string;
    public_key: string;
    is_connected: boolean;
  };
}

export interface PaymentTransaction {
  id: string;
  type: 'session_payment' | 'withdrawal' | 'deposit' | 'refund';
  amount: number;
  currency: 'TRX' | 'USDT';
  status: 'pending' | 'confirmed' | 'failed';
  transaction_hash?: string;
  from_address?: string;
  to_address?: string;
  session_id?: string;
  description: string;
  timestamp: string;
  block_height?: number;
  gas_used?: number;
  gas_price?: number;
}

export interface WithdrawalRequest {
  amount: number;
  currency: 'TRX' | 'USDT';
  to_address: string;
  memo?: string;
}

export interface DepositInfo {
  address: string;
  qr_code?: string;
  minimum_amount: number;
  confirmation_blocks: number;
}

export interface TransactionFilters {
  type?: 'session_payment' | 'withdrawal' | 'deposit' | 'refund';
  status?: 'pending' | 'confirmed' | 'failed';
  currency?: 'TRX' | 'USDT';
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface HardwareWalletInfo {
  type: 'ledger' | 'trezor' | 'keepkey';
  device_id: string;
  public_key: string;
  is_connected: boolean;
  firmware_version?: string;
  app_version?: string;
}

class WalletService {
  private apiClient: LucidAPIClient;

  constructor() {
    this.apiClient = new LucidAPIClient('/api/user');
  }

  // Get wallet information
  async getWalletInfo(): Promise<WalletInfo> {
    try {
      const response = await this.apiClient.get('/wallet/info');
      return response.wallet;
    } catch (error) {
      console.error('Failed to get wallet info:', error);
      throw error;
    }
  }

  // Get wallet balance
  async getWalletBalance(): Promise<{
    trx_balance: number;
    usdt_balance: number;
    usd_value: number;
    last_updated: string;
  }> {
    try {
      const response = await this.apiClient.get('/wallet/balance');
      return response.balance;
    } catch (error) {
      console.error('Failed to get wallet balance:', error);
      throw error;
    }
  }

  // Get transaction history
  async getTransactions(filters: TransactionFilters = {}): Promise<PaymentTransaction[]> {
    try {
      const params = new URLSearchParams();
      
      if (filters.type) params.append('type', filters.type);
      if (filters.status) params.append('status', filters.status);
      if (filters.currency) params.append('currency', filters.currency);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);
      if (filters.limit) params.append('limit', filters.limit.toString());
      if (filters.offset) params.append('offset', filters.offset.toString());

      const response = await this.apiClient.get(`/wallet/transactions?${params}`);
      return response.transactions || [];
    } catch (error) {
      console.error('Failed to get transactions:', error);
      throw error;
    }
  }

  // Get transaction details
  async getTransactionDetails(transactionId: string): Promise<PaymentTransaction> {
    try {
      const response = await this.apiClient.get(`/wallet/transactions/${transactionId}`);
      return response.transaction;
    } catch (error) {
      console.error('Failed to get transaction details:', error);
      throw error;
    }
  }

  // Request withdrawal
  async requestWithdrawal(request: WithdrawalRequest): Promise<{
    success: boolean;
    transaction_id: string;
    estimated_fee: number;
    estimated_confirmation_time: number;
  }> {
    try {
      const response = await this.apiClient.post('/wallet/withdraw', request);
      return response;
    } catch (error) {
      console.error('Failed to request withdrawal:', error);
      throw error;
    }
  }

  // Get deposit information
  async getDepositInfo(currency: 'TRX' | 'USDT' = 'TRX'): Promise<DepositInfo> {
    try {
      const response = await this.apiClient.get(`/wallet/deposit/${currency}`);
      return response.deposit_info;
    } catch (error) {
      console.error('Failed to get deposit info:', error);
      throw error;
    }
  }

  // Validate TRON address
  async validateAddress(address: string): Promise<{
    valid: boolean;
    address_type: 'TRON' | 'ETH' | 'BTC' | 'unknown';
    is_contract?: boolean;
  }> {
    try {
      const response = await this.apiClient.post('/wallet/validate-address', { address });
      return response.validation;
    } catch (error) {
      console.error('Failed to validate address:', error);
      throw error;
    }
  }

  // Get transaction fees
  async getTransactionFees(): Promise<{
    trx_fee: number;
    usdt_fee: number;
    gas_price: number;
    bandwidth_cost: number;
  }> {
    try {
      const response = await this.apiClient.get('/wallet/fees');
      return response.fees;
    } catch (error) {
      console.error('Failed to get transaction fees:', error);
      throw error;
    }
  }

  // Estimate withdrawal cost
  async estimateWithdrawalCost(amount: number, currency: 'TRX' | 'USDT'): Promise<{
    total_cost: number;
    network_fee: number;
    service_fee: number;
    estimated_time: number;
  }> {
    try {
      const response = await this.apiClient.post('/wallet/estimate-withdrawal', {
        amount,
        currency
      });
      return response.estimation;
    } catch (error) {
      console.error('Failed to estimate withdrawal cost:', error);
      throw error;
    }
  }

  // Hardware wallet operations
  async connectHardwareWallet(): Promise<HardwareWalletInfo> {
    try {
      const response = await this.apiClient.post('/wallet/hardware/connect');
      return response.hardware_wallet;
    } catch (error) {
      console.error('Failed to connect hardware wallet:', error);
      throw error;
    }
  }

  async disconnectHardwareWallet(): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/wallet/hardware/disconnect');
      return response;
    } catch (error) {
      console.error('Failed to disconnect hardware wallet:', error);
      throw error;
    }
  }

  async getHardwareWalletInfo(): Promise<HardwareWalletInfo | null> {
    try {
      const response = await this.apiClient.get('/wallet/hardware/info');
      return response.hardware_wallet || null;
    } catch (error) {
      console.error('Failed to get hardware wallet info:', error);
      return null;
    }
  }

  // Sign transaction with hardware wallet
  async signTransactionWithHardware(transactionData: any): Promise<{
    success: boolean;
    signed_transaction: string;
    signature: string;
  }> {
    try {
      const response = await this.apiClient.post('/wallet/hardware/sign', transactionData);
      return response;
    } catch (error) {
      console.error('Failed to sign transaction with hardware wallet:', error);
      throw error;
    }
  }

  // Get wallet statistics
  async getWalletStats(): Promise<{
    total_transactions: number;
    total_deposits: number;
    total_withdrawals: number;
    total_fees_paid: number;
    average_transaction_value: number;
    first_transaction_date: string;
    last_transaction_date: string;
  }> {
    try {
      const response = await this.apiClient.get('/wallet/stats');
      return response.stats;
    } catch (error) {
      console.error('Failed to get wallet stats:', error);
      throw error;
    }
  }

  // Get price history
  async getPriceHistory(currency: 'TRX' | 'USDT', period: '1d' | '7d' | '30d' | '90d' = '7d'): Promise<Array<{
    timestamp: string;
    price: number;
    volume: number;
  }>> {
    try {
      const response = await this.apiClient.get(`/wallet/price-history/${currency}?period=${period}`);
      return response.price_history;
    } catch (error) {
      console.error('Failed to get price history:', error);
      throw error;
    }
  }

  // Get current prices
  async getCurrentPrices(): Promise<{
    trx_usd: number;
    usdt_usd: number;
    last_updated: string;
  }> {
    try {
      const response = await this.apiClient.get('/wallet/prices');
      return response.prices;
    } catch (error) {
      console.error('Failed to get current prices:', error);
      throw error;
    }
  }

  // Generate new wallet address (if supported)
  async generateNewAddress(): Promise<{
    address: string;
    private_key?: string; // Only for testing, never in production
    mnemonic?: string; // Only for testing, never in production
  }> {
    try {
      const response = await this.apiClient.post('/wallet/generate-address');
      return response;
    } catch (error) {
      console.error('Failed to generate new address:', error);
      throw error;
    }
  }

  // Backup wallet
  async backupWallet(): Promise<{
    backup_data: string;
    encrypted: boolean;
    backup_id: string;
  }> {
    try {
      const response = await this.apiClient.post('/wallet/backup');
      return response;
    } catch (error) {
      console.error('Failed to backup wallet:', error);
      throw error;
    }
  }

  // Restore wallet from backup
  async restoreWallet(backupData: string, password?: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/wallet/restore', {
        backup_data: backupData,
        password
      });
      return response;
    } catch (error) {
      console.error('Failed to restore wallet:', error);
      throw error;
    }
  }

  // Get wallet security status
  async getSecurityStatus(): Promise<{
    two_factor_enabled: boolean;
    hardware_wallet_connected: boolean;
    last_security_check: string;
    security_score: number;
    recommendations: string[];
  }> {
    try {
      const response = await this.apiClient.get('/wallet/security');
      return response.security;
    } catch (error) {
      console.error('Failed to get security status:', error);
      throw error;
    }
  }

  // Monitor transaction status
  async monitorTransaction(transactionId: string): Promise<{
    status: 'pending' | 'confirmed' | 'failed';
    confirmations: number;
    block_height?: number;
    estimated_confirmation_time?: number;
  }> {
    try {
      const response = await this.apiClient.get(`/wallet/transactions/${transactionId}/status`);
      return response.status;
    } catch (error) {
      console.error('Failed to monitor transaction:', error);
      throw error;
    }
  }
}

export const walletService = new WalletService();
