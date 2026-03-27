/**
 * LUCID Electron Preload Script - Secure Context Bridge
 * Provides safe IPC communication between renderer and main processes
 * SPEC-1B Implementation with security hardening
 */
/**
 * Secure API object exposed to renderer process
 * All communication goes through validated IPC channels
 */
declare const api: {
    /**
     * Send message to main process with validation
     */
    send: (channel: string, ...args: any[]) => void;
    /**
     * Send message and wait for response
     */
    invoke: (channel: string, ...args: any[]) => Promise<any>;
    /**
     * Listen for messages from main process
     */
    on: (channel: string, listener: (event: any, ...args: any[]) => void) => void;
    /**
     * Listen for one message from main process
     */
    once: (channel: string, listener: (event: any, ...args: any[]) => void) => void;
    /**
     * Remove listener for channel
     */
    off: (channel: string, listener: (event: any, ...args: any[]) => void) => void;
    /**
     * TOR management methods
     */
    tor: {
        start: () => Promise<any>;
        stop: () => Promise<any>;
        restart: () => Promise<any>;
        getStatus: () => Promise<any>;
        getMetrics: () => Promise<any>;
        testConnection: (url: string) => Promise<any>;
        healthCheck: () => Promise<any>;
        onStatusUpdate: (listener: (status: any) => void) => void;
    };
    /**
     * Docker management methods
     */
    docker: {
        getStatus: () => Promise<any>;
        connectSSH: (config: any) => Promise<any>;
        disconnect: () => Promise<any>;
        getContainers: () => Promise<any>;
        getContainer: (id: string) => Promise<any>;
        startContainer: (id: string) => Promise<any>;
        stopContainer: (id: string) => Promise<any>;
        restartContainer: (id: string) => Promise<any>;
        removeContainer: (id: string, force?: boolean) => Promise<any>;
        getLogs: (id: string, lines?: number) => Promise<any>;
        getStats: (id: string) => Promise<any>;
        getAllStats: () => Promise<any>;
        pullImage: (imageName: string) => Promise<any>;
        getImages: () => Promise<any>;
        onContainerUpdate: (listener: (data: any) => void) => void;
    };
    /**
     * API proxy methods
     */
    api: {
        request: (request: any) => Promise<any>;
        get: (url: string, config?: any) => Promise<any>;
        post: (url: string, data?: any, config?: any) => Promise<any>;
        put: (url: string, data?: any, config?: any) => Promise<any>;
        delete: (url: string, config?: any) => Promise<any>;
    };
    /**
     * Authentication methods
     */
    auth: {
        login: (email: string, signature: string) => Promise<any>;
        logout: () => Promise<any>;
        verifyToken: (token: string) => Promise<any>;
        refreshToken: () => Promise<any>;
        onStatusChange: (listener: (status: any) => void) => void;
        onTokenExpired: (listener: () => void) => void;
    };
    /**
     * Configuration methods
     */
    config: {
        get: (key?: string) => Promise<any>;
        set: (key: string, value: any) => Promise<any>;
        reset: (key?: string) => Promise<any>;
        export: () => Promise<any>;
        import: (data: any) => Promise<any>;
        onUpdate: (listener: (update: any) => void) => void;
    };
    /**
     * System methods
     */
    system: {
        getInfo: () => Promise<any>;
        getResources: () => Promise<any>;
        getNetworkInfo: () => Promise<any>;
        showNotification: (title: string, body: string) => Promise<any>;
        openExternal: (url: string) => Promise<any>;
    };
    /**
     * Logging methods
     */
    log: {
        info: (message: string, context?: any) => void;
        warn: (message: string, context?: any) => void;
        error: (message: string, context?: any) => void;
        debug: (message: string, context?: any) => void;
    };
    /**
     * Update methods
     */
    update: {
        check: () => Promise<any>;
        download: () => Promise<any>;
        install: () => Promise<any>;
        restart: () => Promise<any>;
        onAvailable: (listener: (update: any) => void) => void;
        onProgress: (listener: (progress: any) => void) => void;
    };
    /**
     * Window management methods
     */
    window: {
        create: (type: string, options?: any) => Promise<string>;
        close: (id: string) => Promise<any>;
        minimize: (id: string) => Promise<any>;
        maximize: (id: string) => Promise<any>;
        restore: (id: string) => Promise<any>;
        getList: () => Promise<any>;
        getStatistics: () => Promise<any>;
    };
};
export type LucidAPI = typeof api;
export {};
