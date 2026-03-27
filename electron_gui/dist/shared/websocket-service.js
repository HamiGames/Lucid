"use strict";
/**
 * WebSocket Service - Real-time updates from payment services
 * SPEC-1B Implementation with reconnection and error recovery
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.LucidWebSocketService = void 0;
const events_1 = require("events");
class LucidWebSocketService extends events_1.EventEmitter {
    constructor(config) {
        super();
        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
        this.messageHandlers = new Map();
        this.config = {
            reconnectInterval: 5000,
            maxReconnectAttempts: 10,
            timeout: 30000,
            heartbeatInterval: 30000,
            ...config,
        };
    }
    /**
     * Connect to WebSocket server
     */
    async connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }
        if (this.isConnecting) {
            console.log('WebSocket connection already in progress');
            return;
        }
        this.isConnecting = true;
        try {
            console.log(`Connecting to WebSocket: ${this.config.url}`);
            this.ws = new WebSocket(this.config.url);
            this.ws.onopen = () => this.handleOpen();
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onerror = (event) => this.handleError(event);
            this.ws.onclose = () => this.handleClose();
            // Set connection timeout
            const timeout = setTimeout(() => {
                if (this.isConnecting) {
                    console.error('WebSocket connection timeout');
                    this.disconnect();
                }
            }, this.config.timeout);
            // Wait for connection
            await new Promise((resolve, reject) => {
                const onOpen = () => {
                    clearTimeout(timeout);
                    this.ws?.removeEventListener('open', onOpen);
                    resolve();
                };
                const onError = (error) => {
                    clearTimeout(timeout);
                    this.ws?.removeEventListener('error', onError);
                    reject(new Error('WebSocket connection failed'));
                };
                this.ws?.addEventListener('open', onOpen);
                this.ws?.addEventListener('error', onError);
            });
            this.reconnectAttempts = 0;
            this.isConnecting = false;
            this.emit('connected');
        }
        catch (error) {
            this.isConnecting = false;
            console.error('Failed to connect WebSocket:', error);
            this.reconnect();
            throw error;
        }
    }
    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        console.log('Disconnecting WebSocket...');
        // Clear timers
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        // Close WebSocket
        if (this.ws) {
            this.ws.onopen = null;
            this.ws.onmessage = null;
            this.ws.onerror = null;
            this.ws.onclose = null;
            if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
                this.ws.close();
            }
            this.ws = null;
        }
        this.isConnecting = false;
        this.emit('disconnected');
    }
    /**
     * Send message to WebSocket server
     */
    send(message) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            throw new Error('WebSocket not connected');
        }
        try {
            this.ws.send(JSON.stringify(message));
        }
        catch (error) {
            console.error('Failed to send WebSocket message:', error);
            throw error;
        }
    }
    /**
     * Subscribe to service updates
     */
    subscribe(service, handler) {
        if (!this.messageHandlers.has(service)) {
            this.messageHandlers.set(service, []);
        }
        this.messageHandlers.get(service)?.push(handler);
        // Send subscription message
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.send({
                type: 'subscribe',
                service,
                data: {},
                timestamp: new Date().toISOString(),
            });
        }
    }
    /**
     * Unsubscribe from service updates
     */
    unsubscribe(service, handler) {
        if (!handler) {
            this.messageHandlers.delete(service);
        }
        else {
            const handlers = this.messageHandlers.get(service);
            if (handlers) {
                const index = handlers.indexOf(handler);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
                if (handlers.length === 0) {
                    this.messageHandlers.delete(service);
                }
            }
        }
        // Send unsubscription message
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.send({
                type: 'unsubscribe',
                service,
                data: {},
                timestamp: new Date().toISOString(),
            });
        }
    }
    /**
     * Get connection status
     */
    isConnected() {
        return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
    }
    /**
     * Private methods
     */
    handleOpen() {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.emit('open');
        // Start heartbeat
        this.startHeartbeat();
        // Re-subscribe to services
        this.resubscribeAll();
    }
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log(`WebSocket message from ${message.service}:`, message.type);
            // Call registered handlers
            const handlers = this.messageHandlers.get(message.service);
            if (handlers) {
                handlers.forEach((handler) => {
                    try {
                        handler(message.data);
                    }
                    catch (error) {
                        console.error(`Error in WebSocket handler for ${message.service}:`, error);
                    }
                });
            }
            // Emit generic message event
            this.emit('message', message);
        }
        catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }
    handleError(event) {
        console.error('WebSocket error:', event);
        this.emit('error', event);
    }
    handleClose() {
        console.log('WebSocket closed');
        this.ws = null;
        this.stopHeartbeat();
        this.emit('close');
        // Attempt reconnection
        if (!this.isConnecting) {
            this.reconnect();
        }
    }
    reconnect() {
        if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
            console.error('Maximum reconnection attempts reached');
            this.emit('reconnect_failed');
            return;
        }
        this.reconnectAttempts++;
        const delay = Math.min(this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1), 30000 // Max 30 seconds
        );
        console.log(`Reconnecting WebSocket in ${delay}ms (attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
        this.reconnectTimer = setTimeout(() => {
            this.connect().catch((error) => {
                console.error('Reconnection failed:', error);
            });
        }, delay);
    }
    startHeartbeat() {
        this.stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                try {
                    this.send({
                        type: 'ping',
                        service: 'system',
                        data: {},
                        timestamp: new Date().toISOString(),
                    });
                }
                catch (error) {
                    console.error('Failed to send heartbeat:', error);
                }
            }
        }, this.config.heartbeatInterval);
    }
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    resubscribeAll() {
        this.messageHandlers.forEach((_, service) => {
            this.send({
                type: 'subscribe',
                service,
                data: {},
                timestamp: new Date().toISOString(),
            });
        });
    }
}
exports.LucidWebSocketService = LucidWebSocketService;
exports.default = LucidWebSocketService;
