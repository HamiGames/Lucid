#!/usr/bin/env node
/**
 * LUCID Electron GUI Main Process - SPEC-1B Implementation
 * Multi-window Electron application with 4 distinct GUI frames
 */
declare class LucidElectronApp {
    private mainWindow;
    private windows;
    private torManager;
    private windowManager;
    private dockerService;
    private isQuitting;
    constructor();
    initialize(): Promise<void>;
    private setupIpcHandlers;
    private setupAppEventHandlers;
    private createMainWindow;
    private handleApiRequest;
    private makeTorRequest;
    private makeDirectRequest;
    private connectHardwareWallet;
    private connectLedgerWallet;
    private connectTrezorWallet;
    private connectKeepKeyWallet;
    private signWithHardwareWallet;
    private cleanup;
    private config;
    private getConfig;
    private setConfig;
    private resetConfig;
    private exportConfig;
    private importConfig;
    private authToken;
    private authTokenExpiry;
    private tokenRefreshTimer;
    private handleAuthLogin;
    private handleAuthLogout;
    private verifyAuthToken;
    private refreshAuthToken;
    private scheduleTokenRefresh;
    private broadcastAuthStatusChange;
    createGUIWindow(guiType: 'user' | 'developer' | 'node' | 'admin', options?: any): Promise<string>;
    closeGUIWindow(windowId: string): Promise<void>;
    getTorStatus(): any;
    getDockerStatus(): any;
}
export { LucidElectronApp };
