/**
 * LUCID Window Manager - SPEC-1B Implementation
 * Manages multiple GUI windows (User, Developer, Node, Admin)
 */
import { BrowserWindow } from 'electron';
export interface WindowOptions {
    width?: number;
    height?: number;
    x?: number;
    y?: number;
    resizable?: boolean;
    minimizable?: boolean;
    maximizable?: boolean;
    alwaysOnTop?: boolean;
    fullscreen?: boolean;
    show?: boolean;
    title?: string;
    icon?: string;
}
export interface GUIWindow {
    id: string;
    type: 'user' | 'developer' | 'node' | 'admin';
    window: BrowserWindow;
    options: WindowOptions;
    createdAt: Date;
    lastActivity: Date;
}
export declare class WindowManager {
    private windows;
    private torManager;
    constructor();
    createWindow(windowType: 'user' | 'developer' | 'node' | 'admin', options?: WindowOptions): Promise<string>;
    closeWindow(windowId: string): Promise<boolean>;
    minimizeWindow(windowId: string): Promise<boolean>;
    maximizeWindow(windowId: string): Promise<boolean>;
    restoreWindow(windowId: string): Promise<boolean>;
    focusWindow(windowId: string): Promise<boolean>;
    getWindow(windowId: string): GUIWindow | undefined;
    broadcastToAllWindows(channel: string, data: unknown): void;
    getAllWindows(): GUIWindow[];
    getWindowsByType(type: 'user' | 'developer' | 'node' | 'admin'): GUIWindow[];
    getWindowCount(): number;
    getWindowCountByType(): Record<string, number>;
    private getDefaultOptions;
    private loadWindowContent;
    private setupWindowEventHandlers;
    private capitalize;
    cascadeWindows(): Promise<void>;
    tileWindows(): Promise<void>;
    minimizeAllWindows(): Promise<void>;
    restoreAllWindows(): Promise<void>;
    closeAllWindows(): Promise<void>;
    getWindowStatistics(): any;
}
