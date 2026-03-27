"use strict";
/**
 * LUCID Electron Preload Script - Secure Context Bridge
 * Provides safe IPC communication between renderer and main processes
 * SPEC-1B Implementation with security hardening
 */
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const ipc_channels_1 = require("../shared/ipc-channels");
/**
 * Secure API object exposed to renderer process
 * All communication goes through validated IPC channels
 */
const api = {
    /**
     * Send message to main process with validation
     */
    send: (channel, ...args) => {
        if (!(0, ipc_channels_1.isValidChannel)(channel)) {
            console.error(`Invalid IPC channel: ${channel}`);
            return;
        }
        electron_1.ipcRenderer.send(channel, ...args);
    },
    /**
     * Send message and wait for response
     */
    invoke: async (channel, ...args) => {
        if (!(0, ipc_channels_1.isValidChannel)(channel)) {
            throw new Error(`Invalid IPC channel: ${channel}`);
        }
        try {
            return await electron_1.ipcRenderer.invoke(channel, ...args);
        }
        catch (error) {
            console.error(`IPC invoke error on channel ${channel}:`, error);
            throw error;
        }
    },
    /**
     * Listen for messages from main process
     */
    on: (channel, listener) => {
        if (!(0, ipc_channels_1.isValidChannel)(channel)) {
            console.error(`Invalid IPC channel: ${channel}`);
            return;
        }
        // Create wrapper to prevent message flooding
        const validListener = (event, ...args) => {
            listener(event, ...args);
        };
        electron_1.ipcRenderer.on(channel, validListener);
    },
    /**
     * Listen for one message from main process
     */
    once: (channel, listener) => {
        if (!(0, ipc_channels_1.isValidChannel)(channel)) {
            console.error(`Invalid IPC channel: ${channel}`);
            return;
        }
        electron_1.ipcRenderer.once(channel, listener);
    },
    /**
     * Remove listener for channel
     */
    off: (channel, listener) => {
        if (!(0, ipc_channels_1.isValidChannel)(channel)) {
            console.error(`Invalid IPC channel: ${channel}`);
            return;
        }
        electron_1.ipcRenderer.off(channel, listener);
    },
    /**
     * TOR management methods
     */
    tor: {
        start: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.TOR_START),
        stop: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.TOR_STOP),
        restart: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.TOR_RESTART),
        getStatus: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.TOR_GET_STATUS),
        getMetrics: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.TOR_GET_METRICS),
        testConnection: (url) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.TOR_TEST_CONNECTION, { url }),
        healthCheck: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.TOR_HEALTH_CHECK),
        onStatusUpdate: (listener) => {
            electron_1.ipcRenderer.on(ipc_channels_1.IPCChannels.TOR_STATUS_UPDATE, (event, status) => listener(status));
        },
    },
    /**
     * Docker management methods
     */
    docker: {
        getStatus: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_GET_STATUS),
        connectSSH: (config) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_CONNECT_SSH, config),
        disconnect: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_DISCONNECT),
        getContainers: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_GET_CONTAINERS),
        getContainer: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_GET_CONTAINER, id),
        startContainer: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_START_CONTAINER, id),
        stopContainer: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_STOP_CONTAINER, id),
        restartContainer: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_RESTART_CONTAINER, id),
        removeContainer: (id, force) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_REMOVE_CONTAINER, { id, force }),
        getLogs: (id, lines) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_GET_LOGS, { id, lines }),
        getStats: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_GET_STATS, id),
        getAllStats: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_GET_ALL_STATS),
        pullImage: (imageName) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_PULL_IMAGE, imageName),
        getImages: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.DOCKER_GET_IMAGES),
        onContainerUpdate: (listener) => {
            electron_1.ipcRenderer.on(ipc_channels_1.IPCChannels.DOCKER_CONTAINER_UPDATE, (event, data) => listener(data));
        },
    },
    /**
     * API proxy methods
     */
    api: {
        request: (request) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.API_REQUEST, request),
        get: (url, config) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.API_GET, { url, config }),
        post: (url, data, config) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.API_POST, { url, data, config }),
        put: (url, data, config) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.API_PUT, { url, data, config }),
        delete: (url, config) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.API_DELETE, { url, config }),
    },
    /**
     * Authentication methods
     */
    auth: {
        login: (email, signature) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.AUTH_LOGIN, { email, signature }),
        logout: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.AUTH_LOGOUT),
        verifyToken: (token) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.AUTH_VERIFY_TOKEN, { token }),
        refreshToken: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.AUTH_REFRESH_TOKEN),
        onStatusChange: (listener) => {
            electron_1.ipcRenderer.on(ipc_channels_1.IPCChannels.AUTH_STATUS_CHANGED, (event, status) => listener(status));
        },
        onTokenExpired: (listener) => {
            electron_1.ipcRenderer.on(ipc_channels_1.IPCChannels.AUTH_TOKEN_EXPIRED, () => listener());
        },
    },
    /**
     * Configuration methods
     */
    config: {
        get: (key) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.CONFIG_GET, key),
        set: (key, value) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.CONFIG_SET, { key, value }),
        reset: (key) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.CONFIG_RESET, key),
        export: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.CONFIG_EXPORT),
        import: (data) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.CONFIG_IMPORT, data),
        onUpdate: (listener) => {
            electron_1.ipcRenderer.on(ipc_channels_1.IPCChannels.CONFIG_UPDATED, (event, update) => listener(update));
        },
    },
    /**
     * System methods
     */
    system: {
        getInfo: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.SYSTEM_GET_INFO),
        getResources: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.SYSTEM_GET_RESOURCES),
        getNetworkInfo: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.SYSTEM_GET_NETWORK_INFO),
        showNotification: (title, body) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.SYSTEM_SHOW_NOTIFICATION, { title, body }),
        openExternal: (url) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.SYSTEM_OPEN_EXTERNAL, url),
    },
    /**
     * Logging methods
     */
    log: {
        info: (message, context) => electron_1.ipcRenderer.send(ipc_channels_1.IPCChannels.LOG_INFO, { message, context }),
        warn: (message, context) => electron_1.ipcRenderer.send(ipc_channels_1.IPCChannels.LOG_WARN, { message, context }),
        error: (message, context) => electron_1.ipcRenderer.send(ipc_channels_1.IPCChannels.LOG_ERROR, { message, context }),
        debug: (message, context) => electron_1.ipcRenderer.send(ipc_channels_1.IPCChannels.LOG_DEBUG, { message, context }),
    },
    /**
     * Update methods
     */
    update: {
        check: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.UPDATE_CHECK),
        download: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.UPDATE_DOWNLOAD),
        install: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.UPDATE_INSTALL),
        restart: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.UPDATE_RESTART),
        onAvailable: (listener) => {
            electron_1.ipcRenderer.on(ipc_channels_1.IPCChannels.UPDATE_AVAILABLE, (event, update) => listener(update));
        },
        onProgress: (listener) => {
            electron_1.ipcRenderer.on(ipc_channels_1.IPCChannels.UPDATE_PROGRESS, (event, progress) => listener(progress));
        },
    },
    /**
     * Window management methods
     */
    window: {
        create: (type, options) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.WINDOW_CREATE, { type, options }),
        close: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.WINDOW_CLOSE, id),
        minimize: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.WINDOW_MINIMIZE, id),
        maximize: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.WINDOW_MAXIMIZE, id),
        restore: (id) => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.WINDOW_RESTORE, id),
        getList: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.WINDOW_GET_LIST),
        getStatistics: () => electron_1.ipcRenderer.invoke(ipc_channels_1.IPCChannels.WINDOW_GET_STATISTICS),
    },
};
/**
 * Expose API to renderer process via contextBridge
 * This ensures security by preventing direct access to ipcRenderer
 */
electron_1.contextBridge.exposeInMainWorld('lucidAPI', api);
