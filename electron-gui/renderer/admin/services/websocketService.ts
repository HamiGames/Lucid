/**
 * WebSocket Service - Handles real-time updates for admin interface
 * Provides WebSocket connections for live data streaming and notifications
 */

import { EventEmitter } from 'events';

export interface WebSocketConfig {
  url: string;
  reconnectInterval: number;
  maxReconnectAttempts: number;
  heartbeatInterval: number;
  timeout: number;
}

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
  id?: string;
}

export interface WebSocketSubscription {
  id: string;
  channel: string;
  callback: (data: any) => void;
}

export interface RealTimeData {
  type: 'dashboard' | 'sessions' | 'users' | 'nodes' | 'blockchain' | 'audit' | 'system';
  data: any;
  timestamp: string;
}

export interface NotificationMessage {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  persistent: boolean;
  actions?: Array<{
    label: string;
    action: string;
    data?: any;
  }>;
}

export interface ConnectionStatus {
  connected: boolean;
  reconnecting: boolean;
  lastConnected: string | null;
  reconnectAttempts: number;
  latency: number;
}

class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private subscriptions: Map<string, WebSocketSubscription> = new Map();
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private reconnectAttempts: number = 0;
  private connectionStatus: ConnectionStatus = {
    connected: false,
    reconnecting: false,
    lastConnected: null,
    reconnectAttempts: 0,
    latency: 0
  };

  constructor(config: Partial<WebSocketConfig> = {}) {
    super();
    
    this.config = {
      url: config.url || 'ws://localhost:8080/ws/admin',
      reconnectInterval: config.reconnectInterval || 5000,
      maxReconnectAttempts: config.maxReconnectAttempts || 10,
      heartbeatInterval: config.heartbeatInterval || 30000,
      timeout: config.timeout || 10000
    };

    this.setupEventListeners();
  }

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.url);
        
        const timeout = setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            reject(new Error('Connection timeout'));
          }
        }, this.config.timeout);

        this.ws.onopen = () => {
          clearTimeout(timeout);
          this.onConnectionOpen();
          resolve();
        };

        this.ws.onclose = (event) => {
          clearTimeout(timeout);
          this.onConnectionClose(event);
        };

        this.ws.onerror = (error) => {
          clearTimeout(timeout);
          this.onConnectionError(error);
          reject(error);
        };

        this.ws.onmessage = (event) => {
          this.onMessage(event);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.clearTimers();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.connectionStatus.connected = false;
    this.connectionStatus.reconnecting = false;
    this.emit('disconnected');
  }

  /**
   * Subscribe to a channel
   */
  subscribe(channel: string, callback: (data: any) => void): string {
    const subscriptionId = this.generateSubscriptionId();
    
    const subscription: WebSocketSubscription = {
      id: subscriptionId,
      channel,
      callback
    };
    
    this.subscriptions.set(subscriptionId, subscription);
    
    // Send subscription message to server
    this.sendMessage({
      type: 'subscribe',
      data: { channel },
      timestamp: new Date().toISOString(),
      id: subscriptionId
    });
    
    return subscriptionId;
  }

  /**
   * Unsubscribe from a channel
   */
  unsubscribe(subscriptionId: string): void {
    const subscription = this.subscriptions.get(subscriptionId);
    if (subscription) {
      this.subscriptions.delete(subscriptionId);
      
      // Send unsubscription message to server
      this.sendMessage({
        type: 'unsubscribe',
        data: { channel: subscription.channel },
        timestamp: new Date().toISOString(),
        id: subscriptionId
      });
    }
  }

  /**
   * Send message to server
   */
  sendMessage(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, message not sent:', message);
    }
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): ConnectionStatus {
    return { ...this.connectionStatus };
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connectionStatus.connected;
  }

  /**
   * Get subscriptions
   */
  getSubscriptions(): WebSocketSubscription[] {
    return Array.from(this.subscriptions.values());
  }

  // Event handlers
  private onConnectionOpen(): void {
    this.connectionStatus.connected = true;
    this.connectionStatus.reconnecting = false;
    this.connectionStatus.lastConnected = new Date().toISOString();
    this.connectionStatus.reconnectAttempts = 0;
    
    this.clearTimers();
    this.startHeartbeat();
    
    // Resubscribe to all channels
    this.resubscribeAll();
    
    this.emit('connected');
    console.log('WebSocket connected');
  }

  private onConnectionClose(event: CloseEvent): void {
    this.connectionStatus.connected = false;
    this.clearTimers();
    
    this.emit('disconnected', event);
    console.log('WebSocket disconnected:', event.code, event.reason);
    
    // Attempt to reconnect if not manually closed
    if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.attemptReconnect();
    }
  }

  private onConnectionError(error: Event): void {
    this.connectionStatus.connected = false;
    this.emit('error', error);
    console.error('WebSocket error:', error);
  }

  private onMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'heartbeat':
          this.handleHeartbeat(message);
          break;
        case 'notification':
          this.handleNotification(message);
          break;
        case 'realtime_data':
          this.handleRealTimeData(message);
          break;
        case 'subscription_update':
          this.handleSubscriptionUpdate(message);
          break;
        default:
          this.emit('message', message);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleHeartbeat(message: WebSocketMessage): void {
    // Calculate latency
    const now = Date.now();
    const sentTime = message.data.timestamp;
    this.connectionStatus.latency = now - sentTime;
    
    // Echo heartbeat
    this.sendMessage({
      type: 'heartbeat_echo',
      data: { timestamp: now },
      timestamp: new Date().toISOString(),
      id: message.id
    });
  }

  private handleNotification(message: WebSocketMessage): void {
    const notification: NotificationMessage = message.data;
    this.emit('notification', notification);
  }

  private handleRealTimeData(message: WebSocketMessage): void {
    const realTimeData: RealTimeData = message.data;
    
    // Route to specific subscribers
    this.subscriptions.forEach(subscription => {
      if (subscription.channel === realTimeData.type || 
          subscription.channel === 'all') {
        subscription.callback(realTimeData.data);
      }
    });
    
    this.emit('realtime_data', realTimeData);
  }

  private handleSubscriptionUpdate(message: WebSocketMessage): void {
    const subscriptionId = message.id;
    const subscription = this.subscriptions.get(subscriptionId);
    
    if (subscription) {
      subscription.callback(message.data);
    }
  }

  // Connection management
  private attemptReconnect(): void {
    if (this.connectionStatus.reconnecting) return;
    
    this.connectionStatus.reconnecting = true;
    this.reconnectAttempts++;
    
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
    
    this.reconnectTimer = setTimeout(async () => {
      try {
        await this.connect();
      } catch (error) {
        console.error('Reconnection failed:', error);
        this.connectionStatus.reconnecting = false;
        
        if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
          this.attemptReconnect();
        } else {
          this.emit('reconnect_failed');
        }
      }
    }, this.config.reconnectInterval);
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendMessage({
          type: 'heartbeat',
          data: { timestamp: Date.now() },
          timestamp: new Date().toISOString()
        });
      }
    }, this.config.heartbeatInterval);
  }

  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private resubscribeAll(): void {
    this.subscriptions.forEach(subscription => {
      this.sendMessage({
        type: 'subscribe',
        data: { channel: subscription.channel },
        timestamp: new Date().toISOString(),
        id: subscription.id
      });
    });
  }

  private setupEventListeners(): void {
    // Handle window close
    window.addEventListener('beforeunload', () => {
      this.disconnect();
    });

    // Handle visibility change
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        // Pause some subscriptions when tab is hidden
        this.pauseNonCriticalSubscriptions();
      } else {
        // Resume subscriptions when tab becomes visible
        this.resumeAllSubscriptions();
      }
    });
  }

  private pauseNonCriticalSubscriptions(): void {
    // Pause non-critical subscriptions to save bandwidth
    this.subscriptions.forEach(subscription => {
      if (subscription.channel !== 'system' && subscription.channel !== 'notifications') {
        this.sendMessage({
          type: 'pause_subscription',
          data: { channel: subscription.channel },
          timestamp: new Date().toISOString(),
          id: subscription.id
        });
      }
    });
  }

  private resumeAllSubscriptions(): void {
    // Resume all subscriptions
    this.subscriptions.forEach(subscription => {
      this.sendMessage({
        type: 'resume_subscription',
        data: { channel: subscription.channel },
        timestamp: new Date().toISOString(),
        id: subscription.id
      });
    });
  }

  private generateSubscriptionId(): string {
    return `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Export class for custom instances
export { WebSocketService };
