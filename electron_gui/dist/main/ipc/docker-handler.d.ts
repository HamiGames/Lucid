import { DockerService } from '../docker-service';
import { WindowManager } from '../window-manager';
import { DockerServiceMessage } from '../../shared/ipc-channels';
declare function broadcastDockerServiceStatus(windowManager: WindowManager, status: Omit<DockerServiceMessage, 'timestamp'>): void;
export declare function setupDockerHandlers(dockerService: DockerService, windowManager: WindowManager): void;
declare function setupDockerEventListeners(dockerService: DockerService, windowManager: WindowManager): void;
export { broadcastDockerServiceStatus, setupDockerEventListeners };
