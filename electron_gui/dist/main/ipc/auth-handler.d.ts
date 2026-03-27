import { WindowManager } from '../window-manager';
import { AuthStatusMessage, AuthTokenExpiredMessage } from '../../shared/ipc-channels';
export declare function setupAuthHandlers(windowManager: WindowManager): void;
declare function broadcastAuthStatus(windowManager: WindowManager, status: AuthStatusMessage): void;
declare function broadcastTokenExpired(windowManager: WindowManager, message: AuthTokenExpiredMessage): void;
export { broadcastAuthStatus, broadcastTokenExpired };
