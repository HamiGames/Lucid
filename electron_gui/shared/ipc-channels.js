"use strict";
// File: electron-gui/shared/ipc-channels.ts
Object.defineProperty(exports, "__esModule", { value: true });
exports.isValidResponse = exports.isValidMessage = exports.isValidChannel = exports.IPCChannels = exports.BIDIRECTIONAL_CHANNELS = exports.MAIN_TO_RENDERER_CHANNELS = exports.RENDERER_TO_MAIN_CHANNELS = void 0;
exports.RENDERER_TO_MAIN_CHANNELS = {
    TOR_START: 'tor:start',
    TOR_STOP: 'tor:stop',
    TOR_RESTART: 'tor:restart',
    TOR_GET_STATUS: 'tor:get-status',
    TOR_GET_METRICS: 'tor:get-metrics',
    TOR_TEST_CONNECTION: 'tor:test-connection',
    TOR_HEALTH_CHECK: 'tor:health-check',
    WINDOW_MINIMIZE: 'window:minimize',
    WINDOW_MAXIMIZE: 'window:maximize',
    WINDOW_RESTORE: 'window:restore',
    WINDOW_CLOSE: 'window:close',
    WINDOW_SET_SIZE: 'window:set-size',
    WINDOW_SET_POSITION: 'window:set-position',
    WINDOW_CENTER: 'window:center',
    WINDOW_SET_ALWAYS_ON_TOP: 'window:set-always-on-top',
    DOCKER_START_SERVICES: 'docker:start-services',
    DOCKER_STOP_SERVICES: 'docker:stop-services',
    DOCKER_RESTART_SERVICES: 'docker:restart-services',
    DOCKER_GET_SERVICE_STATUS: 'docker:get-service-status',
    DOCKER_GET_CONTAINER_LOGS: 'docker:get-container-logs',
    DOCKER_EXEC_COMMAND: 'docker:exec-command',
    API_REQUEST: 'api:request',
    API_GET: 'api:get',
    API_POST: 'api:post',
    API_PUT: 'api:put',
    API_DELETE: 'api:delete',
    API_UPLOAD: 'api:upload',
    API_DOWNLOAD: 'api:download',
    AUTH_LOGIN: 'auth:login',
    AUTH_LOGOUT: 'auth:logout',
    AUTH_VERIFY_TOKEN: 'auth:verify-token',
    AUTH_REFRESH_TOKEN: 'auth:refresh-token',
    CONFIG_GET: 'config:get',
    CONFIG_SET: 'config:set',
    CONFIG_RESET: 'config:reset',
    CONFIG_EXPORT: 'config:export',
    CONFIG_IMPORT: 'config:import',
    FILE_OPEN: 'file:open',
    FILE_SAVE: 'file:save',
    FILE_SAVE_AS: 'file:save-as',
    FILE_SELECT: 'file:select',
    FILE_DOWNLOAD: 'file:download',
    SYSTEM_GET_INFO: 'system:get-info',
    SYSTEM_GET_RESOURCES: 'system:get-resources',
    SYSTEM_GET_NETWORK_INFO: 'system:get-network-info',
    SYSTEM_SHOW_NOTIFICATION: 'system:show-notification',
    SYSTEM_OPEN_EXTERNAL: 'system:open-external',
    LOG_INFO: 'log:info',
    LOG_WARN: 'log:warn',
    LOG_ERROR: 'log:error',
    LOG_DEBUG: 'log:debug',
    UPDATE_CHECK: 'update:check',
    UPDATE_DOWNLOAD: 'update:download',
    UPDATE_INSTALL: 'update:install',
    UPDATE_RESTART: 'update:restart',
};
exports.MAIN_TO_RENDERER_CHANNELS = {
    TOR_STATUS_UPDATE: 'tor:status-update',
    TOR_CONNECTION_CHANGED: 'tor:connection-changed',
    TOR_CONNECTION_UPDATE: 'tor:connection-changed',
    TOR_BOOTSTRAP_PROGRESS: 'tor:bootstrap-progress',
    TOR_BOOTSTRAP_UPDATE: 'tor:bootstrap-progress',
    TOR_CIRCUIT_UPDATE: 'tor:circuit-update',
    DOCKER_SERVICE_STATUS: 'docker:service-status',
    DOCKER_CONTAINER_UPDATE: 'docker:container-update',
    DOCKER_HEALTH_CHECK: 'docker:health-check',
    SYSTEM_NOTIFICATION: 'system:notification',
    ERROR_OCCURRED: 'error:occurred',
    AUTH_STATUS_CHANGED: 'auth:status-changed',
    AUTH_TOKEN_EXPIRED: 'auth:token-expired',
    CONFIG_UPDATED: 'config:updated',
    SETTINGS_CHANGED: 'settings:changed',
    UPDATE_AVAILABLE: 'update:available',
    UPDATE_PROGRESS: 'update:progress',
    UPDATE_COMPLETED: 'update:completed',
    LOG_EVENT: 'log:event',
};
exports.BIDIRECTIONAL_CHANNELS = {
    WINDOW_SEND_MESSAGE: 'window:send-message',
    WINDOW_BROADCAST: 'window:broadcast',
    DATA_SYNC: 'data:sync',
    DATA_GET: 'data:get',
    DATA_SET: 'data:set',
    DATA_DELETE: 'data:delete',
    EVENT_SUBSCRIBE: 'event:subscribe',
    EVENT_UNSUBSCRIBE: 'event:unsubscribe',
};
exports.IPCChannels = {
    ...exports.RENDERER_TO_MAIN_CHANNELS,
    ...exports.MAIN_TO_RENDERER_CHANNELS,
    ...exports.BIDIRECTIONAL_CHANNELS,
    WINDOW_CREATE: 'window:create',
    WINDOW_CLOSE: 'window:close',
    WINDOW_MINIMIZE: 'window:minimize',
    WINDOW_MAXIMIZE: 'window:maximize',
    WINDOW_RESTORE: 'window:restore',
    WINDOW_GET_LIST: 'window:get-list',
    WINDOW_GET_STATISTICS: 'window:get-statistics',
    DOCKER_GET_STATUS: 'docker:get-status',
    DOCKER_CONNECT_SSH: 'docker:connect-ssh',
    DOCKER_DISCONNECT: 'docker:disconnect',
    DOCKER_GET_CONTAINERS: 'docker:get-containers',
    DOCKER_GET_CONTAINER: 'docker:get-container',
    DOCKER_START_CONTAINER: 'docker:start-container',
    DOCKER_STOP_CONTAINER: 'docker:stop-container',
    DOCKER_RESTART_CONTAINER: 'docker:restart-container',
    DOCKER_REMOVE_CONTAINER: 'docker:remove-container',
    DOCKER_GET_LOGS: 'docker:get-logs',
    DOCKER_GET_STATS: 'docker:get-stats',
    DOCKER_GET_ALL_STATS: 'docker:get-all-stats',
    DOCKER_PULL_IMAGE: 'docker:pull-image',
    DOCKER_GET_IMAGES: 'docker:get-images',
};
/* ------------------------------------------------------------------------ */
/* Validation helpers                                                       */
/* ------------------------------------------------------------------------ */
function isValidChannel(channel) {
    return Object.values(exports.IPCChannels).includes(channel);
}
exports.isValidChannel = isValidChannel;
function isValidMessage(message) {
    if (!message || typeof message !== 'object') {
        return false;
    }
    const candidate = message;
    return (typeof candidate.id === 'string' &&
        typeof candidate.channel === 'string' &&
        typeof candidate.timestamp === 'string' &&
        isValidChannel(candidate.channel));
}
exports.isValidMessage = isValidMessage;
function isValidResponse(response) {
    if (!response || typeof response !== 'object') {
        return false;
    }
    const candidate = response;
    return typeof candidate.success === 'boolean' && typeof candidate.timestamp === 'string';
}
exports.isValidResponse = isValidResponse;
