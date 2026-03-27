import { TorManager } from '../tor-manager';
import { WindowManager } from '../window-manager';
import { TorGetStatusResponse, TorStatusMessage } from '../../shared/ipc-channels';
export declare function torBootstrapProgress(status: import('../tor-manager').TorStatus): number;
export declare function mapTorStatusForIpc(status: import('../tor-manager').TorStatus): TorGetStatusResponse;
export declare function setupTorHandlers(torManager: TorManager, windowManager: WindowManager): void;
declare function setupTorEventListeners(torManager: TorManager, windowManager: WindowManager): void;
declare function broadcastTorStatus(windowManager: WindowManager, status: TorStatusMessage): void;
export { broadcastTorStatus, setupTorEventListeners };
