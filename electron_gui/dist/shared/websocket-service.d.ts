/**
 * WebSocket Service - Real-time updates from payment services
 * SPEC-1B Implementation with reconnection and error recovery
 */
import { EventEmitter } from 'events';
export interface WebSocketConfig {
    url: string;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
    timeout?: number;
    heartbeatInterval?: number;
}
export interface WebSocketMessage {
    type: string;
    service: string;
    data: any;
    timestamp: string;
}
export type WebSocketEventHandler = (data: any) => void;
export declare class LucidWebSocketService extends EventEmitter {
    private ws;
    private config;
    private reconnectAttempts;
    private isConnecting;
    private heartbeatTimer;
    private reconnectTimer;
    private messageHandlers;
    constructor(config: WebSocketConfig);
    /**
     * Connect to WebSocket server
     */
    connect(): Promise<void>;
    /**
     * Disconnect from WebSocket
     */
    disconnect(): void;
    /**
     * Send message to WebSocket server
     */
    send(message: WebSocketMessage): void;
    /**
     * Subscribe to service updates
     */
    subscribe(service: string, handler: WebSocketEventHandler): void;
    /**
     * Unsubscribe from service updates
     */
    unsubscribe(service: string, handler?: WebSocketEventHandler): void;
    /**
     * Get connection status
     */
    isConnected(): boolean;
    /**
     * Private methods
     */
    private handleOpen;
    private handleMessage;
    private handleError;
    private handleClose;
    private reconnect;
    private startHeartbeat;
    private stopHeartbeat;
    private resubscribeAll;
}
export default LucidWebSocketService;
