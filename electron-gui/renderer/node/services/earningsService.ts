import { LucidAPIClient } from '../../../shared/api-client';

// Types
interface EarningsData {
  total_earnings: number;
  pending_earnings: number;
  paid_earnings: number;
  current_period_earnings: number;
  last_payment_date: string | null;
  next_payment_date: string | null;
  payment_frequency: 'daily' | 'weekly' | 'monthly';
  payment_method: 'tron' | 'bitcoin' | 'ethereum';
  wallet_address: string;
}

interface EarningsHistory {
  id: string;
  date: string;
  amount: number;
  type: 'session' | 'block_reward' | 'pool_share' | 'bonus';
  status: 'pending' | 'confirmed' | 'paid';
  transaction_hash?: string;
  description: string;
  metadata?: Record<string, any>;
}

interface PayoutHistory {
  id: string;
  date: string;
  amount: number;
  transaction_hash: string;
  status: 'pending' | 'confirmed' | 'failed';
  fee: number;
  net_amount: number;
  payment_method: string;
  wallet_address: string;
}

interface EarningsStats {
  total_sessions: number;
  average_earnings_per_session: number;
  best_day_earnings: number;
  best_day_date: string;
  total_payouts: number;
  average_payout_amount: number;
  earnings_growth_rate: number;
  earnings_trend: 'up' | 'down' | 'stable';
}

interface PaymentSettings {
  payment_frequency: 'daily' | 'weekly' | 'monthly';
  payment_method: 'tron' | 'bitcoin' | 'ethereum';
  wallet_address: string;
  minimum_payout_threshold: number;
  auto_payout_enabled: boolean;
  payout_notifications: boolean;
}

interface PayoutRequest {
  amount: number;
  payment_method: 'tron' | 'bitcoin' | 'ethereum';
  wallet_address: string;
  reason?: string;
}

interface PayoutResponse {
  success: boolean;
  message: string;
  payout_id?: string;
  estimated_processing_time?: number;
  transaction_hash?: string;
}

class EarningsService {
  private apiClient: LucidAPIClient;
  private earningsCache: EarningsData | null = null;
  private historyCache: EarningsHistory[] = [];
  private payoutsCache: PayoutHistory[] = [];
  private lastCacheUpdate: number = 0;
  private readonly CACHE_DURATION = 300000; // 5 minutes

  constructor(apiClient: LucidAPIClient) {
    this.apiClient = apiClient;
  }

  // Earnings Overview
  async getEarningsOverview(forceRefresh: boolean = false): Promise<EarningsData> {
    const now = Date.now();
    
    if (!forceRefresh && this.earningsCache && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.earningsCache;
    }

    try {
      const response = await this.apiClient.get('/node/earnings');
      this.earningsCache = response.data;
      this.lastCacheUpdate = now;
      return this.earningsCache;
    } catch (error) {
      throw new Error(`Failed to get earnings overview: ${error}`);
    }
  }

  async getEarningsSummary(timeRange: '7d' | '30d' | '90d' | '1y' = '30d'): Promise<{
    total_earnings: number;
    earnings_by_period: Array<{
      period: string;
      earnings: number;
      session_count: number;
      average_per_session: number;
    }>;
    earnings_breakdown: {
      session_earnings: number;
      pool_earnings: number;
      bonus_earnings: number;
      referral_earnings: number;
    };
  }> {
    try {
      const response = await this.apiClient.get(`/node/earnings/summary?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get earnings summary: ${error}`);
    }
  }

  // Earnings History
  async getEarningsHistory(
    filters?: {
      type?: EarningsHistory['type'];
      status?: EarningsHistory['status'];
      date_from?: string;
      date_to?: string;
      limit?: number;
      offset?: number;
    },
    forceRefresh: boolean = false
  ): Promise<EarningsHistory[]> {
    const now = Date.now();
    
    if (!forceRefresh && this.historyCache.length > 0 && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.historyCache;
    }

    try {
      const params = new URLSearchParams();
      if (filters?.type) params.append('type', filters.type);
      if (filters?.status) params.append('status', filters.status);
      if (filters?.date_from) params.append('date_from', filters.date_from);
      if (filters?.date_to) params.append('date_to', filters.date_to);
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.offset) params.append('offset', filters.offset.toString());

      const response = await this.apiClient.get(`/node/earnings/history?${params.toString()}`);
      this.historyCache = response.data;
      this.lastCacheUpdate = now;
      return this.historyCache;
    } catch (error) {
      throw new Error(`Failed to get earnings history: ${error}`);
    }
  }

  async getEarningsByType(type: EarningsHistory['type'], limit: number = 50): Promise<EarningsHistory[]> {
    return this.getEarningsHistory({ type, limit });
  }

  async getEarningsByDateRange(startDate: string, endDate: string): Promise<EarningsHistory[]> {
    return this.getEarningsHistory({
      date_from: startDate,
      date_to: endDate,
    });
  }

  // Payout Management
  async getPayoutHistory(
    filters?: {
      status?: PayoutHistory['status'];
      date_from?: string;
      date_to?: string;
      limit?: number;
      offset?: number;
    },
    forceRefresh: boolean = false
  ): Promise<PayoutHistory[]> {
    const now = Date.now();
    
    if (!forceRefresh && this.payoutsCache.length > 0 && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.payoutsCache;
    }

    try {
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.date_from) params.append('date_from', filters.date_from);
      if (filters?.date_to) params.append('date_to', filters.date_to);
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.offset) params.append('offset', filters.offset.toString());

      const response = await this.apiClient.get(`/node/payouts?${params.toString()}`);
      this.payoutsCache = response.data;
      this.lastCacheUpdate = now;
      return this.payoutsCache;
    } catch (error) {
      throw new Error(`Failed to get payout history: ${error}`);
    }
  }

  async requestPayout(request: PayoutRequest): Promise<PayoutResponse> {
    try {
      const response = await this.apiClient.post('/node/payouts/request', request);
      this.earningsCache = null; // Invalidate cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to request payout: ${error}`);
    }
  }

  async cancelPayout(payoutId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post(`/node/payouts/${payoutId}/cancel`);
      this.payoutsCache = []; // Invalidate cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to cancel payout: ${error}`);
    }
  }

  async getPayoutStatus(payoutId: string): Promise<{
    payout_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
    amount: number;
    fee: number;
    net_amount: number;
    created_at: string;
    processed_at?: string;
    transaction_hash?: string;
    error_message?: string;
  }> {
    try {
      const response = await this.apiClient.get(`/node/payouts/${payoutId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get payout status: ${error}`);
    }
  }

  // Payment Settings
  async getPaymentSettings(): Promise<PaymentSettings> {
    try {
      const response = await this.apiClient.get('/node/payment/settings');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get payment settings: ${error}`);
    }
  }

  async updatePaymentSettings(settings: Partial<PaymentSettings>): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.put('/node/payment/settings', settings);
      this.earningsCache = null; // Invalidate cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update payment settings: ${error}`);
    }
  }

  async validateWalletAddress(address: string, paymentMethod: PaymentSettings['payment_method']): Promise<{
    is_valid: boolean;
    message: string;
    normalized_address?: string;
  }> {
    try {
      const response = await this.apiClient.post('/node/payment/validate-wallet', {
        address,
        payment_method: paymentMethod,
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to validate wallet address: ${error}`);
    }
  }

  // Earnings Statistics
  async getEarningsStatistics(timeRange: '7d' | '30d' | '90d' | '1y' = '30d'): Promise<EarningsStats> {
    try {
      const response = await this.apiClient.get(`/node/earnings/statistics?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get earnings statistics: ${error}`);
    }
  }

  async getEarningsTrend(timeRange: '7d' | '30d' | '90d' = '30d'): Promise<{
    trend: 'up' | 'down' | 'stable';
    trend_percentage: number;
    trend_data: Array<{
      date: string;
      earnings: number;
      sessions: number;
    }>;
  }> {
    try {
      const response = await this.apiClient.get(`/node/earnings/trend?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get earnings trend: ${error}`);
    }
  }

  async getEarningsProjection(): Promise<{
    daily_projection: number;
    weekly_projection: number;
    monthly_projection: number;
    yearly_projection: number;
    confidence_level: number;
    factors: Array<{
      factor: string;
      impact: 'positive' | 'negative' | 'neutral';
      weight: number;
    }>;
  }> {
    try {
      const response = await this.apiClient.get('/node/earnings/projection');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get earnings projection: ${error}`);
    }
  }

  // Earnings Analytics
  async getEarningsAnalytics(): Promise<{
    performance_metrics: {
      average_daily_earnings: number;
      earnings_volatility: number;
      consistency_score: number;
      growth_rate: number;
    };
    session_analytics: {
      total_sessions: number;
      average_earnings_per_session: number;
      best_performing_session_type: string;
      session_success_rate: number;
    };
    time_analytics: {
      peak_earnings_hours: number[];
      best_earnings_day: string;
      seasonal_trends: Array<{
        month: string;
        earnings: number;
      }>;
    };
  }> {
    try {
      const response = await this.apiClient.get('/node/earnings/analytics');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get earnings analytics: ${error}`);
    }
  }

  // Earnings Reports
  async generateEarningsReport(
    options: {
      format: 'json' | 'csv' | 'pdf';
      date_from: string;
      date_to: string;
      include_details: boolean;
      include_projections: boolean;
    }
  ): Promise<Blob> {
    try {
      const response = await this.apiClient.post('/node/earnings/report', options, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to generate earnings report: ${error}`);
    }
  }

  async exportEarningsData(
    format: 'json' | 'csv' = 'csv',
    filters?: {
      type?: EarningsHistory['type'];
      status?: EarningsHistory['status'];
      date_from?: string;
      date_to?: string;
    }
  ): Promise<Blob> {
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      if (filters?.type) params.append('type', filters.type);
      if (filters?.status) params.append('status', filters.status);
      if (filters?.date_from) params.append('date_from', filters.date_from);
      if (filters?.date_to) params.append('date_to', filters.date_to);

      const response = await this.apiClient.get(`/node/earnings/export?${params.toString()}`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to export earnings data: ${error}`);
    }
  }

  // Earnings Notifications
  async getEarningsNotifications(): Promise<Array<{
    id: string;
    type: 'payout' | 'earnings_update' | 'payment_settings' | 'threshold_reached';
    title: string;
    message: string;
    timestamp: string;
    is_read: boolean;
    action_required: boolean;
  }>> {
    try {
      const response = await this.apiClient.get('/node/earnings/notifications');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get earnings notifications: ${error}`);
    }
  }

  async markNotificationAsRead(notificationId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post(`/node/earnings/notifications/${notificationId}/read`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to mark notification as read: ${error}`);
    }
  }

  async updateNotificationPreferences(preferences: {
    payout_notifications: boolean;
    earnings_updates: boolean;
    threshold_alerts: boolean;
    payment_reminders: boolean;
  }): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.put('/node/earnings/notifications/preferences', preferences);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update notification preferences: ${error}`);
    }
  }

  // Cache Management
  clearCache(): void {
    this.earningsCache = null;
    this.historyCache = [];
    this.payoutsCache = [];
    this.lastCacheUpdate = 0;
  }

  getCachedEarnings(): EarningsData | null {
    return this.earningsCache;
  }

  getCachedHistory(): EarningsHistory[] {
    return this.historyCache;
  }

  getCachedPayouts(): PayoutHistory[] {
    return this.payoutsCache;
  }

  isCacheValid(): boolean {
    const now = Date.now();
    return (now - this.lastCacheUpdate) < this.CACHE_DURATION;
  }

  // Utility Methods
  async getTotalEarnings(): Promise<number> {
    const earnings = await this.getEarningsOverview();
    return earnings.total_earnings;
  }

  async getPendingEarnings(): Promise<number> {
    const earnings = await this.getEarningsOverview();
    return earnings.pending_earnings;
  }

  async canRequestPayout(minimumAmount?: number): Promise<boolean> {
    const earnings = await this.getEarningsOverview();
    const threshold = minimumAmount || (await this.getPaymentSettings()).minimum_payout_threshold;
    return earnings.pending_earnings >= threshold;
  }

  async getNextPaymentDate(): Promise<string | null> {
    const earnings = await this.getEarningsOverview();
    return earnings.next_payment_date;
  }

  async getEarningsGrowthRate(timeRange: '7d' | '30d' | '90d' = '30d'): Promise<number> {
    const stats = await this.getEarningsStatistics(timeRange);
    return stats.earnings_growth_rate;
  }
}

export { EarningsService };
export type {
  EarningsData,
  EarningsHistory,
  PayoutHistory,
  EarningsStats,
  PaymentSettings,
  PayoutRequest,
  PayoutResponse,
};
