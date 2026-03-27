/**
 * Lucid Electron GUI IPC channel catalogue and payload contracts.
 * Channel naming follows the service layout documented in `plan/constants`.
 */
type ValueOf<T> = T[keyof T];
export declare const RENDERER_TO_MAIN_CHANNELS: {
    readonly TOR_START: "tor:start";
    readonly TOR_STOP: "tor:stop";
    readonly TOR_RESTART: "tor:restart";
    readonly TOR_GET_STATUS: "tor:get-status";
    readonly TOR_GET_METRICS: "tor:get-metrics";
    readonly TOR_TEST_CONNECTION: "tor:test-connection";
    readonly TOR_HEALTH_CHECK: "tor:health-check";
    readonly WINDOW_MINIMIZE: "window:minimize";
    readonly WINDOW_MAXIMIZE: "window:maximize";
    readonly WINDOW_RESTORE: "window:restore";
    readonly WINDOW_CLOSE: "window:close";
    readonly WINDOW_SET_SIZE: "window:set-size";
    readonly WINDOW_SET_POSITION: "window:set-position";
    readonly WINDOW_CENTER: "window:center";
    readonly WINDOW_SET_ALWAYS_ON_TOP: "window:set-always-on-top";
    readonly DOCKER_START_SERVICES: "docker:start-services";
    readonly DOCKER_STOP_SERVICES: "docker:stop-services";
    readonly DOCKER_RESTART_SERVICES: "docker:restart-services";
    readonly DOCKER_GET_SERVICE_STATUS: "docker:get-service-status";
    readonly DOCKER_GET_CONTAINER_LOGS: "docker:get-container-logs";
    readonly DOCKER_EXEC_COMMAND: "docker:exec-command";
    readonly API_REQUEST: "api:request";
    readonly API_GET: "api:get";
    readonly API_POST: "api:post";
    readonly API_PUT: "api:put";
    readonly API_DELETE: "api:delete";
    readonly API_UPLOAD: "api:upload";
    readonly API_DOWNLOAD: "api:download";
    readonly AUTH_LOGIN: "auth:login";
    readonly AUTH_LOGOUT: "auth:logout";
    readonly AUTH_VERIFY_TOKEN: "auth:verify-token";
    readonly AUTH_REFRESH_TOKEN: "auth:refresh-token";
    readonly CONFIG_GET: "config:get";
    readonly CONFIG_SET: "config:set";
    readonly CONFIG_RESET: "config:reset";
    readonly CONFIG_EXPORT: "config:export";
    readonly CONFIG_IMPORT: "config:import";
    readonly FILE_OPEN: "file:open";
    readonly FILE_SAVE: "file:save";
    readonly FILE_SAVE_AS: "file:save-as";
    readonly FILE_SELECT: "file:select";
    readonly FILE_DOWNLOAD: "file:download";
    readonly SYSTEM_GET_INFO: "system:get-info";
    readonly SYSTEM_GET_RESOURCES: "system:get-resources";
    readonly SYSTEM_GET_NETWORK_INFO: "system:get-network-info";
    readonly SYSTEM_SHOW_NOTIFICATION: "system:show-notification";
    readonly SYSTEM_OPEN_EXTERNAL: "system:open-external";
    readonly LOG_INFO: "log:info";
    readonly LOG_WARN: "log:warn";
    readonly LOG_ERROR: "log:error";
    readonly LOG_DEBUG: "log:debug";
    readonly UPDATE_CHECK: "update:check";
    readonly UPDATE_DOWNLOAD: "update:download";
    readonly UPDATE_INSTALL: "update:install";
    readonly UPDATE_RESTART: "update:restart";
};
export declare const MAIN_TO_RENDERER_CHANNELS: {
    readonly TOR_STATUS_UPDATE: "tor:status-update";
    readonly TOR_CONNECTION_CHANGED: "tor:connection-changed";
    readonly TOR_CONNECTION_UPDATE: "tor:connection-changed";
    readonly TOR_BOOTSTRAP_PROGRESS: "tor:bootstrap-progress";
    readonly TOR_BOOTSTRAP_UPDATE: "tor:bootstrap-progress";
    readonly TOR_CIRCUIT_UPDATE: "tor:circuit-update";
    readonly DOCKER_SERVICE_STATUS: "docker:service-status";
    readonly DOCKER_CONTAINER_UPDATE: "docker:container-update";
    readonly DOCKER_HEALTH_CHECK: "docker:health-check";
    readonly SYSTEM_NOTIFICATION: "system:notification";
    readonly ERROR_OCCURRED: "error:occurred";
    readonly AUTH_STATUS_CHANGED: "auth:status-changed";
    readonly AUTH_TOKEN_EXPIRED: "auth:token-expired";
    readonly CONFIG_UPDATED: "config:updated";
    readonly SETTINGS_CHANGED: "settings:changed";
    readonly UPDATE_AVAILABLE: "update:available";
    readonly UPDATE_PROGRESS: "update:progress";
    readonly UPDATE_COMPLETED: "update:completed";
    readonly LOG_EVENT: "log:event";
};
export declare const BIDIRECTIONAL_CHANNELS: {
    readonly WINDOW_SEND_MESSAGE: "window:send-message";
    readonly WINDOW_BROADCAST: "window:broadcast";
    readonly DATA_SYNC: "data:sync";
    readonly DATA_GET: "data:get";
    readonly DATA_SET: "data:set";
    readonly DATA_DELETE: "data:delete";
    readonly EVENT_SUBSCRIBE: "event:subscribe";
    readonly EVENT_UNSUBSCRIBE: "event:unsubscribe";
};
export declare const IPCChannels: {
    readonly WINDOW_CREATE: "window:create";
    readonly WINDOW_CLOSE: "window:close";
    readonly WINDOW_MINIMIZE: "window:minimize";
    readonly WINDOW_MAXIMIZE: "window:maximize";
    readonly WINDOW_RESTORE: "window:restore";
    readonly WINDOW_GET_LIST: "window:get-list";
    readonly WINDOW_GET_STATISTICS: "window:get-statistics";
    readonly DOCKER_GET_STATUS: "docker:get-status";
    readonly DOCKER_CONNECT_SSH: "docker:connect-ssh";
    readonly DOCKER_DISCONNECT: "docker:disconnect";
    readonly DOCKER_GET_CONTAINERS: "docker:get-containers";
    readonly DOCKER_GET_CONTAINER: "docker:get-container";
    readonly DOCKER_START_CONTAINER: "docker:start-container";
    readonly DOCKER_STOP_CONTAINER: "docker:stop-container";
    readonly DOCKER_RESTART_CONTAINER: "docker:restart-container";
    readonly DOCKER_REMOVE_CONTAINER: "docker:remove-container";
    readonly DOCKER_GET_LOGS: "docker:get-logs";
    readonly DOCKER_GET_STATS: "docker:get-stats";
    readonly DOCKER_GET_ALL_STATS: "docker:get-all-stats";
    readonly DOCKER_PULL_IMAGE: "docker:pull-image";
    readonly DOCKER_GET_IMAGES: "docker:get-images";
    readonly HARDWARE_WALLET_CONNECT: "hardware-wallet:connect";
    readonly HARDWARE_WALLET_SIGN: "hardware-wallet:sign";
    readonly WINDOW_SEND_MESSAGE: "window:send-message";
    readonly WINDOW_BROADCAST: "window:broadcast";
    readonly DATA_SYNC: "data:sync";
    readonly DATA_GET: "data:get";
    readonly DATA_SET: "data:set";
    readonly DATA_DELETE: "data:delete";
    readonly EVENT_SUBSCRIBE: "event:subscribe";
    readonly EVENT_UNSUBSCRIBE: "event:unsubscribe";
    readonly TOR_STATUS_UPDATE: "tor:status-update";
    readonly TOR_CONNECTION_CHANGED: "tor:connection-changed";
    readonly TOR_CONNECTION_UPDATE: "tor:connection-changed";
    readonly TOR_BOOTSTRAP_PROGRESS: "tor:bootstrap-progress";
    readonly TOR_BOOTSTRAP_UPDATE: "tor:bootstrap-progress";
    readonly TOR_CIRCUIT_UPDATE: "tor:circuit-update";
    readonly DOCKER_SERVICE_STATUS: "docker:service-status";
    readonly DOCKER_CONTAINER_UPDATE: "docker:container-update";
    readonly DOCKER_HEALTH_CHECK: "docker:health-check";
    readonly SYSTEM_NOTIFICATION: "system:notification";
    readonly ERROR_OCCURRED: "error:occurred";
    readonly AUTH_STATUS_CHANGED: "auth:status-changed";
    readonly AUTH_TOKEN_EXPIRED: "auth:token-expired";
    readonly CONFIG_UPDATED: "config:updated";
    readonly SETTINGS_CHANGED: "settings:changed";
    readonly UPDATE_AVAILABLE: "update:available";
    readonly UPDATE_PROGRESS: "update:progress";
    readonly UPDATE_COMPLETED: "update:completed";
    readonly LOG_EVENT: "log:event";
    readonly TOR_START: "tor:start";
    readonly TOR_STOP: "tor:stop";
    readonly TOR_RESTART: "tor:restart";
    readonly TOR_GET_STATUS: "tor:get-status";
    readonly TOR_GET_METRICS: "tor:get-metrics";
    readonly TOR_TEST_CONNECTION: "tor:test-connection";
    readonly TOR_HEALTH_CHECK: "tor:health-check";
    readonly WINDOW_SET_SIZE: "window:set-size";
    readonly WINDOW_SET_POSITION: "window:set-position";
    readonly WINDOW_CENTER: "window:center";
    readonly WINDOW_SET_ALWAYS_ON_TOP: "window:set-always-on-top";
    readonly DOCKER_START_SERVICES: "docker:start-services";
    readonly DOCKER_STOP_SERVICES: "docker:stop-services";
    readonly DOCKER_RESTART_SERVICES: "docker:restart-services";
    readonly DOCKER_GET_SERVICE_STATUS: "docker:get-service-status";
    readonly DOCKER_GET_CONTAINER_LOGS: "docker:get-container-logs";
    readonly DOCKER_EXEC_COMMAND: "docker:exec-command";
    readonly API_REQUEST: "api:request";
    readonly API_GET: "api:get";
    readonly API_POST: "api:post";
    readonly API_PUT: "api:put";
    readonly API_DELETE: "api:delete";
    readonly API_UPLOAD: "api:upload";
    readonly API_DOWNLOAD: "api:download";
    readonly AUTH_LOGIN: "auth:login";
    readonly AUTH_LOGOUT: "auth:logout";
    readonly AUTH_VERIFY_TOKEN: "auth:verify-token";
    readonly AUTH_REFRESH_TOKEN: "auth:refresh-token";
    readonly CONFIG_GET: "config:get";
    readonly CONFIG_SET: "config:set";
    readonly CONFIG_RESET: "config:reset";
    readonly CONFIG_EXPORT: "config:export";
    readonly CONFIG_IMPORT: "config:import";
    readonly FILE_OPEN: "file:open";
    readonly FILE_SAVE: "file:save";
    readonly FILE_SAVE_AS: "file:save-as";
    readonly FILE_SELECT: "file:select";
    readonly FILE_DOWNLOAD: "file:download";
    readonly SYSTEM_GET_INFO: "system:get-info";
    readonly SYSTEM_GET_RESOURCES: "system:get-resources";
    readonly SYSTEM_GET_NETWORK_INFO: "system:get-network-info";
    readonly SYSTEM_SHOW_NOTIFICATION: "system:show-notification";
    readonly SYSTEM_OPEN_EXTERNAL: "system:open-external";
    readonly LOG_INFO: "log:info";
    readonly LOG_WARN: "log:warn";
    readonly LOG_ERROR: "log:error";
    readonly LOG_DEBUG: "log:debug";
    readonly UPDATE_CHECK: "update:check";
    readonly UPDATE_DOWNLOAD: "update:download";
    readonly UPDATE_INSTALL: "update:install";
    readonly UPDATE_RESTART: "update:restart";
};
export type RendererToMainChannel = ValueOf<typeof RENDERER_TO_MAIN_CHANNELS>;
export type MainToRendererChannel = ValueOf<typeof MAIN_TO_RENDERER_CHANNELS>;
export type BidirectionalChannel = ValueOf<typeof BIDIRECTIONAL_CHANNELS>;
export type IpcChannel = ValueOf<typeof IPCChannels>;
export interface IPCMessage<T = unknown> {
    id: string;
    channel: string;
    payload: T;
    timestamp: string;
    replyChannel?: string;
}
export interface IPCResponse<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
    timestamp: string;
}
export interface TorStartRequest {
    config?: Record<string, unknown>;
}
export interface TorStartResponse {
    success: boolean;
    pid?: number;
    error?: string;
}
export interface TorStopRequest {
    force?: boolean;
}
export interface TorStopResponse {
    success: boolean;
    error?: string;
}
export interface TorRestartRequest {
    config?: Record<string, unknown>;
}
export interface TorRestartResponse {
    success: boolean;
    error?: string;
}
export interface TorCircuitDescriptor {
    id: string;
    status: 'building' | 'built' | 'extended' | 'closed';
    path: string[];
    age: number;
    purpose?: string;
    flags?: string[];
}
export interface TorGetStatusResponse {
    connected: boolean;
    connecting: boolean;
    bootstrapProgress: number;
    circuits: TorCircuitDescriptor[];
    proxyPort: number;
    controlPort: number;
    error?: string;
    lastConnected?: string;
}
export interface TorGetMetricsResponse {
    uptimeSeconds: number;
    bytesRead: number;
    bytesWritten: number;
    circuitsBuilt: number;
    circuitsFailed: number;
    lastUpdated: string;
}
export interface TorTestConnectionRequest {
    url: string;
    timeout?: number;
    expectedStatus?: number;
}
export interface TorTestConnectionResponse {
    success: boolean;
    responseTime: number;
    error?: string;
}
export interface TorHealthCheckResponse {
    healthy: boolean;
    lastCheck: string;
    responseTime: number;
    tests: {
        socksProxy: boolean;
        controlPort: boolean;
        bootstrap: boolean;
        circuitBuild: boolean;
    };
    error?: string;
}
export interface TorStatusMessage {
    status: 'connected' | 'connecting' | 'disconnected' | 'error';
    progress?: number;
    circuits?: number;
    proxyPort?: number;
    error?: string;
}
export interface TorConnectionMessage {
    connected: boolean;
    timestamp: string;
    error?: string;
}
export interface TorBootstrapMessage {
    progress: number;
    summary?: string;
    warning?: string;
}
export interface TorCircuitMessage {
    circuitId: string;
    status: TorCircuitDescriptor['status'];
    path: string[];
    age: number;
    purpose?: string;
    flags?: string[];
}
export type DockerServiceStatus = 'stopped' | 'starting' | 'running' | 'error';
export type DockerServiceHealth = 'healthy' | 'unhealthy' | 'starting';
export interface DockerServiceState {
    service: string;
    displayName: string;
    image: string;
    level: 'support' | 'core' | 'application' | 'admin' | 'developer' | 'user' | 'node';
    plane: 'support' | 'core' | 'application' | 'ops';
    status: DockerServiceStatus;
    containerId?: string;
    ports: string[];
    health?: DockerServiceHealth;
    error?: string;
    updatedAt: string;
}
export interface DockerStartServicesRequest {
    services: string[];
    level?: string;
}
export interface DockerServiceOperationFailure {
    service: string;
    error: string;
}
export interface DockerStartServicesResponse {
    success: boolean;
    started: string[];
    failed: DockerServiceOperationFailure[];
    services: DockerServiceState[];
    level?: string;
    timestamp: string;
}
export interface DockerStopServicesRequest {
    services: string[];
}
export interface DockerStopServicesResponse {
    success: boolean;
    stopped: string[];
    failed: DockerServiceOperationFailure[];
    services: DockerServiceState[];
    timestamp: string;
}
export interface DockerRestartServicesResponse {
    success: boolean;
    restarted: string[];
    failed: DockerServiceOperationFailure[];
    services: DockerServiceState[];
    timestamp: string;
}
export interface DockerGetServiceStatusResponse {
    services: DockerServiceState[];
    generatedAt: string;
}
export interface DockerGetContainerLogsRequest {
    containerId: string;
    lines?: number;
    follow?: boolean;
}
export interface DockerGetContainerLogsResponse {
    containerId: string;
    logs: string[];
    error?: string;
    generatedAt: string;
}
export interface DockerExecCommandRequest {
    containerId: string;
    command: string[];
    workingDir?: string;
    env?: Record<string, string>;
}
export interface DockerExecCommandResponse {
    success: boolean;
    containerId: string;
    output: string;
    error?: string;
    exitCode: number;
    startedAt: string;
    finishedAt: string;
}
export interface DockerServiceMessage {
    service: string;
    status: DockerServiceStatus;
    containerId?: string;
    error?: string;
    level?: string;
    plane?: string;
    timestamp: string;
}
export interface DockerContainerMessage {
    containerId: string;
    status: DockerServiceStatus | string;
    name: string;
    image: string;
    ports: string[];
    health?: DockerServiceHealth | string;
    updatedAt: string;
}
export interface DockerHealthMessage {
    service: string;
    healthy: boolean;
    lastCheck: string;
    responseTime: number;
    error?: string;
}
export interface AuthLoginRequest {
    email: string;
    signature: string;
}
export interface AuthLoginResponse {
    success: boolean;
    token?: string;
    user?: {
        id: string;
        email: string;
        role: string;
    };
    expiresAt?: string;
    error?: string;
}
export interface AuthLogoutRequest {
    token: string;
}
export interface AuthLogoutResponse {
    success: boolean;
    error?: string;
}
export interface AuthVerifyTokenRequest {
    token: string;
}
export interface AuthVerifyTokenResponse {
    success: boolean;
    user?: {
        id: string;
        email: string;
        role: string;
    };
    expiresAt?: string;
    error?: string;
}
export interface AuthStatusMessage {
    authenticated: boolean;
    user?: {
        id: string;
        email: string;
        role: string;
    };
    token?: string;
    expiresAt?: string;
    timestamp?: string;
}
export interface AuthTokenExpiredMessage {
    reason: string;
    timestamp: string;
}
export interface ConfigUpdatedMessage {
    key: string;
    value: unknown;
    scope: 'user' | 'system' | 'session';
    updatedAt: string;
    updatedBy?: string;
}
export interface SettingsChangedMessage {
    category: string;
    changes: Record<string, unknown>;
    timestamp: string;
}
export interface SystemNotificationMessage {
    title: string;
    body: string;
    level?: 'info' | 'success' | 'warning' | 'error';
    icon?: string;
    actions?: Array<{
        label: string;
        action: string;
    }>;
    timeout?: number;
}
export interface WarningMessage {
    code: string;
    message: string;
    timestamp: string;
    details?: Record<string, unknown>;
}
export interface ErrorMessage {
    code: string;
    message: string;
    timestamp: string;
    severity?: 'info' | 'warning' | 'error' | 'critical';
    details?: Record<string, unknown>;
    stack?: string;
}
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
export interface APIRequestMessage {
    method: HttpMethod;
    url: string;
    data?: unknown;
    headers?: Record<string, string>;
    timeout?: number;
}
export interface APIResponseMessage {
    requestId: string;
    data: unknown;
    status: number;
    headers?: Record<string, string>;
}
export interface APIErrorMessage {
    requestId: string;
    error: string;
    status: number;
    details?: unknown;
}
export interface LogEventMessage {
    level: 'info' | 'warn' | 'error' | 'debug';
    message: string;
    timestamp: string;
    context?: Record<string, unknown>;
}
export declare function isValidChannel(channel: string): channel is IpcChannel;
export declare function isValidMessage(message: unknown): message is IPCMessage;
export declare function isValidResponse(response: unknown): response is IPCResponse;
export {};
