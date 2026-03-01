import { LucidAPIClient } from '../../../shared/api-client';

export interface PaymentMethod {
  id: string;
  type: 'credit_card' | 'bank_transfer' | 'crypto' | 'paypal';
  name: string;
  details: Record<string, any>;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
}

export interface PaymentRequest {
  amount: number;
  currency: 'USD' | 'EUR' | 'TRX' | 'USDT';
  description: string;
  payment_method_id?: string;
  session_id?: string;
  metadata?: Record<string, any>;
}

export interface PaymentResponse {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  amount: number;
  currency: string;
  payment_method: string;
  transaction_id?: string;
  created_at: string;
  completed_at?: string;
  failure_reason?: string;
}

export interface Invoice {
  id: string;
  amount: number;
  currency: string;
  description: string;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  due_date: string;
  created_at: string;
  paid_at?: string;
  payment_method?: string;
  metadata?: Record<string, any>;
}

export interface BillingInfo {
  name: string;
  email: string;
  address: {
    street: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
  tax_id?: string;
}

export interface Subscription {
  id: string;
  plan_id: string;
  plan_name: string;
  status: 'active' | 'inactive' | 'cancelled' | 'past_due';
  current_period_start: string;
  current_period_end: string;
  amount: number;
  currency: string;
  interval: 'monthly' | 'yearly';
  next_billing_date: string;
  auto_renew: boolean;
}

export interface PaymentHistory {
  payments: PaymentResponse[];
  total_count: number;
  total_amount: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface PaymentFilters {
  status?: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  payment_method?: string;
  currency?: string;
  date_from?: string;
  date_to?: string;
  amount_min?: number;
  amount_max?: number;
  search?: string;
}

class PaymentService {
  private apiClient: LucidAPIClient;

  constructor() {
    this.apiClient = new LucidAPIClient('/api/user');
  }

  // Create payment
  async createPayment(request: PaymentRequest): Promise<PaymentResponse> {
    try {
      const response = await this.apiClient.post('/payments', request);
      return response.payment;
    } catch (error) {
      console.error('Failed to create payment:', error);
      throw error;
    }
  }

  // Get payment details
  async getPayment(paymentId: string): Promise<PaymentResponse> {
    try {
      const response = await this.apiClient.get(`/payments/${paymentId}`);
      return response.payment;
    } catch (error) {
      console.error('Failed to get payment:', error);
      throw error;
    }
  }

  // Get payment history
  async getPaymentHistory(
    page: number = 1,
    limit: number = 20,
    filters: PaymentFilters = {}
  ): Promise<PaymentHistory> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        ...filters
      });

      const response = await this.apiClient.get(`/payments/history?${params}`);
      return response.history;
    } catch (error) {
      console.error('Failed to get payment history:', error);
      throw error;
    }
  }

  // Cancel payment
  async cancelPayment(paymentId: string, reason?: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post(`/payments/${paymentId}/cancel`, { reason });
      return response;
    } catch (error) {
      console.error('Failed to cancel payment:', error);
      throw error;
    }
  }

  // Refund payment
  async refundPayment(paymentId: string, amount?: number, reason?: string): Promise<{
    success: boolean;
    refund_id: string;
    amount: number;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post(`/payments/${paymentId}/refund`, {
        amount,
        reason
      });
      return response;
    } catch (error) {
      console.error('Failed to refund payment:', error);
      throw error;
    }
  }

  // Get payment methods
  async getPaymentMethods(): Promise<PaymentMethod[]> {
    try {
      const response = await this.apiClient.get('/payments/methods');
      return response.payment_methods;
    } catch (error) {
      console.error('Failed to get payment methods:', error);
      throw error;
    }
  }

  // Add payment method
  async addPaymentMethod(method: Omit<PaymentMethod, 'id' | 'created_at'>): Promise<PaymentMethod> {
    try {
      const response = await this.apiClient.post('/payments/methods', method);
      return response.payment_method;
    } catch (error) {
      console.error('Failed to add payment method:', error);
      throw error;
    }
  }

  // Update payment method
  async updatePaymentMethod(methodId: string, updates: Partial<PaymentMethod>): Promise<PaymentMethod> {
    try {
      const response = await this.apiClient.put(`/payments/methods/${methodId}`, updates);
      return response.payment_method;
    } catch (error) {
      console.error('Failed to update payment method:', error);
      throw error;
    }
  }

  // Delete payment method
  async deletePaymentMethod(methodId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.delete(`/payments/methods/${methodId}`);
      return response;
    } catch (error) {
      console.error('Failed to delete payment method:', error);
      throw error;
    }
  }

  // Set default payment method
  async setDefaultPaymentMethod(methodId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post(`/payments/methods/${methodId}/set-default`);
      return response;
    } catch (error) {
      console.error('Failed to set default payment method:', error);
      throw error;
    }
  }

  // Get invoices
  async getInvoices(page: number = 1, limit: number = 20): Promise<{
    invoices: Invoice[];
    total_count: number;
    has_more: boolean;
  }> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });

      const response = await this.apiClient.get(`/payments/invoices?${params}`);
      return response;
    } catch (error) {
      console.error('Failed to get invoices:', error);
      throw error;
    }
  }

  // Get invoice details
  async getInvoice(invoiceId: string): Promise<Invoice> {
    try {
      const response = await this.apiClient.get(`/payments/invoices/${invoiceId}`);
      return response.invoice;
    } catch (error) {
      console.error('Failed to get invoice:', error);
      throw error;
    }
  }

  // Download invoice
  async downloadInvoice(invoiceId: string, format: 'pdf' | 'html' = 'pdf'): Promise<Blob> {
    try {
      const response = await this.apiClient.get(`/payments/invoices/${invoiceId}/download?format=${format}`, {
        responseType: 'blob'
      });
      return response;
    } catch (error) {
      console.error('Failed to download invoice:', error);
      throw error;
    }
  }

  // Get billing information
  async getBillingInfo(): Promise<BillingInfo> {
    try {
      const response = await this.apiClient.get('/payments/billing');
      return response.billing_info;
    } catch (error) {
      console.error('Failed to get billing info:', error);
      throw error;
    }
  }

  // Update billing information
  async updateBillingInfo(billingInfo: Partial<BillingInfo>): Promise<BillingInfo> {
    try {
      const response = await this.apiClient.put('/payments/billing', billingInfo);
      return response.billing_info;
    } catch (error) {
      console.error('Failed to update billing info:', error);
      throw error;
    }
  }

  // Get subscription
  async getSubscription(): Promise<Subscription | null> {
    try {
      const response = await this.apiClient.get('/payments/subscription');
      return response.subscription || null;
    } catch (error) {
      console.error('Failed to get subscription:', error);
      return null;
    }
  }

  // Create subscription
  async createSubscription(planId: string, paymentMethodId?: string): Promise<Subscription> {
    try {
      const response = await this.apiClient.post('/payments/subscription', {
        plan_id: planId,
        payment_method_id: paymentMethodId
      });
      return response.subscription;
    } catch (error) {
      console.error('Failed to create subscription:', error);
      throw error;
    }
  }

  // Update subscription
  async updateSubscription(planId: string): Promise<Subscription> {
    try {
      const response = await this.apiClient.put('/payments/subscription', { plan_id: planId });
      return response.subscription;
    } catch (error) {
      console.error('Failed to update subscription:', error);
      throw error;
    }
  }

  // Cancel subscription
  async cancelSubscription(reason?: string): Promise<{
    success: boolean;
    message: string;
    cancellation_date: string;
  }> {
    try {
      const response = await this.apiClient.post('/payments/subscription/cancel', { reason });
      return response;
    } catch (error) {
      console.error('Failed to cancel subscription:', error);
      throw error;
    }
  }

  // Get payment statistics
  async getPaymentStats(): Promise<{
    total_payments: number;
    total_amount: number;
    successful_payments: number;
    failed_payments: number;
    average_payment_amount: number;
    monthly_payment_trend: Array<{
      month: string;
      amount: number;
      count: number;
    }>;
  }> {
    try {
      const response = await this.apiClient.get('/payments/stats');
      return response.stats;
    } catch (error) {
      console.error('Failed to get payment stats:', error);
      throw error;
    }
  }

  // Validate payment method
  async validatePaymentMethod(methodData: any): Promise<{
    valid: boolean;
    message: string;
    required_fields: string[];
  }> {
    try {
      const response = await this.apiClient.post('/payments/validate-method', methodData);
      return response.validation;
    } catch (error) {
      console.error('Failed to validate payment method:', error);
      throw error;
    }
  }

  // Get payment limits
  async getPaymentLimits(): Promise<{
    daily_limit: number;
    monthly_limit: number;
    transaction_limit: number;
    currency_limits: Record<string, number>;
  }> {
    try {
      const response = await this.apiClient.get('/payments/limits');
      return response.limits;
    } catch (error) {
      console.error('Failed to get payment limits:', error);
      throw error;
    }
  }

  // Calculate fees
  async calculateFees(amount: number, currency: string, paymentMethod: string): Promise<{
    base_amount: number;
    fee_amount: number;
    total_amount: number;
    fee_percentage: number;
    fee_breakdown: Array<{
      type: string;
      amount: number;
      description: string;
    }>;
  }> {
    try {
      const response = await this.apiClient.post('/payments/calculate-fees', {
        amount,
        currency,
        payment_method: paymentMethod
      });
      return response.calculation;
    } catch (error) {
      console.error('Failed to calculate fees:', error);
      throw error;
    }
  }

  // Process webhook
  async processWebhook(payload: any, signature: string): Promise<{
    processed: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post('/payments/webhook', payload, {
        headers: {
          'X-Signature': signature
        }
      });
      return response;
    } catch (error) {
      console.error('Failed to process webhook:', error);
      throw error;
    }
  }
}

export const paymentService = new PaymentService();
