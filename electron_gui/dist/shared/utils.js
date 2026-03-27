"use strict";
// Shared utility functions for Lucid Electron GUI
// Based on the electron-multi-gui-development.plan.md specifications
Object.defineProperty(exports, "__esModule", { value: true });
exports.isLinux = exports.isMac = exports.isWindows = exports.getPlatform = exports.isElectron = exports.isProduction = exports.isDevelopment = exports.retry = exports.createPerformanceTimer = exports.measureTime = exports.hashString = exports.generateUUID = exports.generateId = exports.parseUrl = exports.buildUrl = exports.throttle = exports.debounce = exports.removeLocalStorage = exports.getLocalStorage = exports.setLocalStorage = exports.pick = exports.omit = exports.deepClone = exports.uniqueBy = exports.sortBy = exports.groupBy = exports.kebabToCamel = exports.camelToKebab = exports.capitalizeFirst = exports.truncateString = exports.isValidNodeId = exports.isValidSessionId = exports.isValidTronAddress = exports.isValidEmail = exports.formatError = exports.isLucidError = exports.createLucidError = exports.getActiveCircuits = exports.getTorCircuitCount = exports.getTorBootstrapProgress = exports.getTorStatusText = exports.getTorStatusColor = exports.formatBandwidth = exports.formatBytes = exports.formatDuration = exports.formatRelativeTime = exports.formatDate = void 0;
// Date and time utilities
const formatDate = (date) => {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
};
exports.formatDate = formatDate;
const formatRelativeTime = (date) => {
    const now = new Date();
    const target = new Date(date);
    const diffInSeconds = Math.floor((now.getTime() - target.getTime()) / 1000);
    if (diffInSeconds < 60)
        return `${diffInSeconds}s ago`;
    if (diffInSeconds < 3600)
        return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400)
        return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
};
exports.formatRelativeTime = formatRelativeTime;
const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    }
    else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    }
    else {
        return `${secs}s`;
    }
};
exports.formatDuration = formatDuration;
// File size utilities
const formatBytes = (bytes) => {
    if (bytes === 0)
        return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
exports.formatBytes = formatBytes;
const formatBandwidth = (bytesPerSecond) => {
    return `${(0, exports.formatBytes)(bytesPerSecond)}/s`;
};
exports.formatBandwidth = formatBandwidth;
// Tor status utilities
const getTorStatusColor = (status) => {
    if (status.is_connected)
        return '#10B981'; // green
    if (status.status === 'connecting')
        return '#F59E0B'; // yellow
    return '#EF4444'; // red
};
exports.getTorStatusColor = getTorStatusColor;
const getTorStatusText = (status) => {
    if (status.is_connected)
        return 'Connected';
    if (status.status === 'connecting')
        return 'Connecting...';
    return 'Disconnected';
};
exports.getTorStatusText = getTorStatusText;
const getTorBootstrapProgress = (status) => {
    return Math.round(status.bootstrap_progress * 100);
};
exports.getTorBootstrapProgress = getTorBootstrapProgress;
const getTorCircuitCount = (status) => {
    return status.circuits.length;
};
exports.getTorCircuitCount = getTorCircuitCount;
const getActiveCircuits = (status) => {
    return status.circuits.filter(circuit => circuit.status === 'built');
};
exports.getActiveCircuits = getActiveCircuits;
// Error handling utilities
const createLucidError = (code, message, details) => {
    return {
        code,
        message,
        details,
        timestamp: new Date().toISOString(),
        service: 'electron-gui',
        version: '1.0.0',
    };
};
exports.createLucidError = createLucidError;
const isLucidError = (error) => {
    return error && typeof error === 'object' && 'code' in error && 'message' in error;
};
exports.isLucidError = isLucidError;
const formatError = (error) => {
    if ((0, exports.isLucidError)(error)) {
        return `${error.code}: ${error.message}`;
    }
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
};
exports.formatError = formatError;
// Validation utilities
const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
};
exports.isValidEmail = isValidEmail;
const isValidTronAddress = (address) => {
    // TRON addresses are 34 characters long and start with 'T'
    return address.length === 34 && address.startsWith('T');
};
exports.isValidTronAddress = isValidTronAddress;
const isValidSessionId = (sessionId) => {
    // Session IDs are UUIDs
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(sessionId);
};
exports.isValidSessionId = isValidSessionId;
const isValidNodeId = (nodeId) => {
    // Node IDs are UUIDs
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(nodeId);
};
exports.isValidNodeId = isValidNodeId;
// String utilities
const truncateString = (str, maxLength) => {
    if (str.length <= maxLength)
        return str;
    return str.substring(0, maxLength - 3) + '...';
};
exports.truncateString = truncateString;
const capitalizeFirst = (str) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
};
exports.capitalizeFirst = capitalizeFirst;
const camelToKebab = (str) => {
    return str.replace(/([A-Z])/g, '-$1').toLowerCase();
};
exports.camelToKebab = camelToKebab;
const kebabToCamel = (str) => {
    return str.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
};
exports.kebabToCamel = kebabToCamel;
// Array utilities
const groupBy = (array, key) => {
    return array.reduce((groups, item) => {
        const groupKey = key(item);
        if (!groups[groupKey]) {
            groups[groupKey] = [];
        }
        groups[groupKey].push(item);
        return groups;
    }, {});
};
exports.groupBy = groupBy;
const sortBy = (array, key, direction = 'asc') => {
    return [...array].sort((a, b) => {
        const aVal = key(a);
        const bVal = key(b);
        if (aVal < bVal)
            return direction === 'asc' ? -1 : 1;
        if (aVal > bVal)
            return direction === 'asc' ? 1 : -1;
        return 0;
    });
};
exports.sortBy = sortBy;
const uniqueBy = (array, key) => {
    const seen = new Set();
    return array.filter(item => {
        const keyValue = key(item);
        if (seen.has(keyValue)) {
            return false;
        }
        seen.add(keyValue);
        return true;
    });
};
exports.uniqueBy = uniqueBy;
// Object utilities
const deepClone = (obj) => {
    if (obj === null || typeof obj !== 'object')
        return obj;
    if (obj instanceof Date)
        return new Date(obj.getTime());
    if (obj instanceof Array)
        return obj.map(item => (0, exports.deepClone)(item));
    if (typeof obj === 'object') {
        const cloned = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                cloned[key] = (0, exports.deepClone)(obj[key]);
            }
        }
        return cloned;
    }
    return obj;
};
exports.deepClone = deepClone;
const omit = (obj, keys) => {
    const result = { ...obj };
    keys.forEach(key => delete result[key]);
    return result;
};
exports.omit = omit;
const pick = (obj, keys) => {
    const result = {};
    keys.forEach(key => {
        if (key in obj) {
            result[key] = obj[key];
        }
    });
    return result;
};
exports.pick = pick;
// Local storage utilities
const setLocalStorage = (key, value) => {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    }
    catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
};
exports.setLocalStorage = setLocalStorage;
const getLocalStorage = (key, defaultValue) => {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    }
    catch (error) {
        console.error('Failed to read from localStorage:', error);
        return defaultValue;
    }
};
exports.getLocalStorage = getLocalStorage;
const removeLocalStorage = (key) => {
    try {
        localStorage.removeItem(key);
    }
    catch (error) {
        console.error('Failed to remove from localStorage:', error);
    }
};
exports.removeLocalStorage = removeLocalStorage;
// Debounce and throttle utilities
const debounce = (func, wait) => {
    let timeout;
    return ((...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    });
};
exports.debounce = debounce;
const throttle = (func, limit) => {
    let inThrottle;
    return ((...args) => {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    });
};
exports.throttle = throttle;
// URL utilities
const buildUrl = (base, params) => {
    const url = new URL(base);
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
            url.searchParams.set(key, String(value));
        }
    });
    return url.toString();
};
exports.buildUrl = buildUrl;
const parseUrl = (url) => {
    const urlObj = new URL(url);
    const params = {};
    urlObj.searchParams.forEach((value, key) => {
        params[key] = value;
    });
    return {
        base: urlObj.origin + urlObj.pathname,
        params,
    };
};
exports.parseUrl = parseUrl;
// Crypto utilities
const generateId = () => {
    return Math.random().toString(36).substring(2) + Date.now().toString(36);
};
exports.generateId = generateId;
const generateUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
};
exports.generateUUID = generateUUID;
const hashString = async (str) => {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
};
exports.hashString = hashString;
// Performance utilities
const measureTime = async (fn) => {
    const start = performance.now();
    const result = await fn();
    const time = performance.now() - start;
    return { result, time };
};
exports.measureTime = measureTime;
const createPerformanceTimer = () => {
    const start = performance.now();
    return {
        elapsed: () => performance.now() - start,
        reset: () => start = performance.now(),
    };
};
exports.createPerformanceTimer = createPerformanceTimer;
// Retry utilities
const retry = async (fn, maxAttempts = 3, delay = 1000) => {
    let lastError;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            return await fn();
        }
        catch (error) {
            lastError = error;
            if (attempt === maxAttempts) {
                throw lastError;
            }
            await new Promise(resolve => setTimeout(resolve, delay * attempt));
        }
    }
    throw lastError;
};
exports.retry = retry;
// Environment utilities
const isDevelopment = () => {
    return process.env.NODE_ENV === 'development';
};
exports.isDevelopment = isDevelopment;
const isProduction = () => {
    return process.env.NODE_ENV === 'production';
};
exports.isProduction = isProduction;
const isElectron = () => {
    return typeof window !== 'undefined' && window.process && window.process.type;
};
exports.isElectron = isElectron;
// Platform utilities
const getPlatform = () => {
    if (typeof process !== 'undefined') {
        return process.platform;
    }
    return 'linux'; // default fallback
};
exports.getPlatform = getPlatform;
const isWindows = () => {
    return (0, exports.getPlatform)() === 'win32';
};
exports.isWindows = isWindows;
const isMac = () => {
    return (0, exports.getPlatform)() === 'darwin';
};
exports.isMac = isMac;
const isLinux = () => {
    return (0, exports.getPlatform)() === 'linux';
};
exports.isLinux = isLinux;
