export declare const API_ENDPOINTS: {
    readonly AUTH: "http://192.168.0.75:8089";
    readonly MONGODB: "mongodb://192.168.0.75:27017";
    readonly REDIS: "redis://192.168.0.75:6379";
    readonly ELASTICSEARCH: "http://192.168.0.75:9200";
    readonly API_GATEWAY: "http://192.168.0.75:8080";
    readonly SERVICE_MESH: "http://192.168.0.75:8086";
    readonly BLOCKCHAIN_ENGINE: "http://192.168.0.75:8084";
    readonly SESSION_ANCHORING: "http://192.168.0.75:8085";
    readonly BLOCK_MANAGER: "http://192.168.0.75:8086";
    readonly DATA_CHAIN: "http://192.168.0.75:8087";
    readonly SESSION_API: "http://192.168.0.75:8087";
    readonly RDP_SERVER: "http://192.168.0.75:8081";
    readonly SESSION_CONTROLLER: "http://192.168.0.75:8082";
    readonly RESOURCE_MONITOR: "http://192.168.0.75:8090";
    readonly NODE_MANAGEMENT: "http://192.168.0.75:8095";
    readonly ADMIN: "http://192.168.0.75:8083";
    readonly TRON_CLIENT: "http://192.168.0.75:8091";
    readonly PAYOUT_ROUTER: "http://192.168.0.75:8092";
    readonly WALLET_MANAGER: "http://192.168.0.75:8093";
    readonly USDT_MANAGER: "http://192.168.0.75:8094";
    readonly TRX_STAKING: "http://192.168.0.75:8096";
    readonly PAYMENT_GATEWAY: "http://192.168.0.75:8097";
};
export declare const SERVICE_PORTS: {
    readonly API_GATEWAY: 8080;
    readonly API_GATEWAY_HTTPS: 8081;
    readonly ADMIN_INTERFACE: 8083;
    readonly BLOCKCHAIN_CORE: 8084;
    readonly TRON_PAYMENT: 8085;
    readonly BLOCK_MANAGER: 8086;
    readonly SESSION_API: 8087;
    readonly STORAGE_DATABASE: 8088;
    readonly AUTHENTICATION: 8089;
    readonly RDP_SERVER_MANAGER: 8090;
    readonly XRDP_INTEGRATION: 8091;
    readonly SESSION_CONTROLLER: 8092;
    readonly RESOURCE_MONITOR: 8093;
    readonly NODE_MANAGEMENT: 8095;
};
export declare const TOR_CONFIG: {
    readonly SOCKS_PORT: 9050;
    readonly CONTROL_PORT: 9051;
    readonly DATA_DIR: "tor-data";
    readonly CONFIG_FILE: "torrc";
    readonly BOOTSTRAP_TIMEOUT: 60000;
    readonly CIRCUIT_BUILD_TIMEOUT: 60000;
};
export declare const DOCKER_CONFIG: {
    readonly PI_HOST: "192.168.0.75";
    readonly SSH_USER: "pickme";
    readonly SSH_PORT: 22;
    readonly DEPLOY_DIR: "/opt/lucid/production";
};
export declare const DOCKER_COMPOSE_FILES: {
    readonly admin: readonly ["configs/docker/docker-compose.foundation.yml", "configs/docker/docker-compose.core.yml", "configs/docker/docker-compose.application.yml", "configs/docker/docker-compose.support.yml"];
    readonly developer: readonly ["configs/docker/docker-compose.foundation.yml", "configs/docker/docker-compose.core.yml", "configs/docker/docker-compose.application.yml"];
    readonly user: readonly [];
    readonly node: readonly [];
};
export declare const SERVICE_NAMES: {
    readonly API_GATEWAY: "api-gateway";
    readonly BLOCKCHAIN_CORE: "lucid-blocks";
    readonly AUTHENTICATION: "auth-service";
    readonly SESSION_MANAGEMENT: "session-api";
    readonly NODE_MANAGEMENT: "node-management";
    readonly ADMIN_INTERFACE: "admin-interface";
    readonly TRON_PAYMENT: "tron-payment-service";
};
export declare const WINDOW_CONFIGS: {
    readonly user: {
        readonly name: "user";
        readonly title: "Lucid User Interface";
        readonly width: 1200;
        readonly height: 800;
        readonly level: "user";
    };
    readonly developer: {
        readonly name: "developer";
        readonly title: "Lucid Developer Console";
        readonly width: 1400;
        readonly height: 900;
        readonly level: "developer";
    };
    readonly node: {
        readonly name: "node";
        readonly title: "Lucid Node Operator";
        readonly width: 1200;
        readonly height: 800;
        readonly level: "node";
    };
    readonly admin: {
        readonly name: "admin";
        readonly title: "Lucid System Administration";
        readonly width: 1600;
        readonly height: 1000;
        readonly level: "admin";
    };
};
export declare const LUCID_ERROR_CODES: {
    readonly VALIDATION_ERROR: "LUCID_ERR_1001";
    readonly INVALID_USER_ID: "LUCID_ERR_1002";
    readonly INVALID_SESSION_ID: "LUCID_ERR_1003";
    readonly INVALID_CHUNK_ID: "LUCID_ERR_1004";
    readonly AUTHENTICATION_FAILED: "LUCID_ERR_2001";
    readonly AUTHORIZATION_DENIED: "LUCID_ERR_2002";
    readonly TOKEN_EXPIRED: "LUCID_ERR_2003";
    readonly INVALID_TOKEN: "LUCID_ERR_2004";
    readonly RATE_LIMIT_EXCEEDED: "LUCID_ERR_3001";
    readonly TOO_MANY_REQUESTS: "LUCID_ERR_3002";
    readonly SESSION_NOT_FOUND: "LUCID_ERR_4001";
    readonly SESSION_ALREADY_ANCHORED: "LUCID_ERR_4002";
    readonly NODE_NOT_REGISTERED: "LUCID_ERR_4003";
    readonly POOL_FULL: "LUCID_ERR_4004";
    readonly INTERNAL_SERVER_ERROR: "LUCID_ERR_5001";
    readonly DATABASE_ERROR: "LUCID_ERR_5002";
    readonly BLOCKCHAIN_ERROR: "LUCID_ERR_5003";
    readonly TOR_CONNECTION_ERROR: "LUCID_ERR_5004";
};
export declare const PATHS: {
    readonly TOR_BINARY_WIN: "assets/tor/tor.exe";
    readonly TOR_BINARY_LINUX: "assets/tor/tor";
    readonly TOR_BINARY_MAC: "assets/tor/tor";
    readonly TOR_CONFIG_TEMPLATE: "assets/tor/torrc.template";
    readonly APP_ICON: "assets/icons/icon.ico";
};
export declare const TIMEOUTS: {
    readonly API_REQUEST: 30000;
    readonly TOR_BOOTSTRAP: 60000;
    readonly DOCKER_STARTUP: 120000;
    readonly FILE_UPLOAD: 300000;
    readonly BLOCKCHAIN_CONFIRMATION: 60000;
};
export declare const CHUNK_CONFIG: {
    readonly MAX_SIZE_MB: 10;
    readonly MAX_SESSION_SIZE_GB: 100;
    readonly COMPRESSION_LEVEL: 6;
    readonly ENCRYPTION_ALGORITHM: "AES-256-GCM";
};
export declare const HARDWARE_WALLET_TYPES: {
    readonly LEDGER: "ledger";
    readonly TREZOR: "trezor";
    readonly KEEPKEY: "keepkey";
};
export declare const USER_ROLES: {
    readonly USER: "user";
    readonly NODE_OPERATOR: "node_operator";
    readonly ADMIN: "admin";
    readonly SUPER_ADMIN: "super_admin";
};
export declare const SESSION_STATUSES: {
    readonly ACTIVE: "active";
    readonly COMPLETED: "completed";
    readonly FAILED: "failed";
    readonly ANCHORED: "anchored";
};
export declare const NODE_STATUSES: {
    readonly REGISTERED: "registered";
    readonly ACTIVE: "active";
    readonly INACTIVE: "inactive";
    readonly SUSPENDED: "suspended";
};
export declare const PAYOUT_STATUSES: {
    readonly PENDING: "pending";
    readonly PROCESSING: "processing";
    readonly COMPLETED: "completed";
    readonly FAILED: "failed";
};
