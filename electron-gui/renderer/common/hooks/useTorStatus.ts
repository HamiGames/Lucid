// renderer/common/hooks/useTorStatus.ts - Tor status monitoring hook
// Based on the electron-multi-gui-development.plan.md specifications

import { useState, useEffect, useCallback } from 'react';
import { TorStatus } from '../../../shared/tor-types';
import { MAIN_TO_RENDERER_CHANNELS, TorStatusMessage } from '../../../shared/ipc-channels';

export interface UseTorStatusReturn {
  torStatus: TorStatus | null;
  torError: string | null;
  isLoading: boolean;
  isConnected: boolean;
  bootstrapProgress: number;
  circuitCount: number;
  refreshStatus: () => Promise<void>;
  startTor: () => Promise<void>;
  stopTor: () => Promise<void>;
  restartTor: () => Promise<void>;
}

export const useTorStatus = (): UseTorStatusReturn => {
  const [torStatus, setTorStatus] = useState<TorStatus | null>(null);
  const [torError, setTorError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Derived state
  const isConnected = torStatus?.status === 'connected';
  const bootstrapProgress = torStatus?.bootstrap_progress || 0;
  const circuitCount = torStatus?.circuits?.length || 0;

  // IPC communication functions
  const sendIpcMessage = useCallback(async (channel: string, data: any = {}) => {
    try {
      if (window.electronAPI && window.electronAPI.invoke) {
        return await window.electronAPI.invoke(channel, data);
      }
      throw new Error('Electron API not available');
    } catch (error) {
      console.error(`IPC message failed for channel ${channel}:`, error);
      throw error;
    }
  }, []);

  // Listen for IPC messages from main process
  const listenForIpcMessages = useCallback(() => {
    if (window.electronAPI && window.electronAPI.on) {
      // Listen for Tor status updates
      window.electronAPI.on(MAIN_TO_RENDERER_CHANNELS.TOR_STATUS_UPDATE, (message: TorStatusMessage) => {
        setTorStatus(prev => ({
          ...prev,
          status: message.status,
          bootstrap_progress: message.progress || 0,
          circuits: prev?.circuits || [],
          is_connected: message.status === 'connected',
          error: message.error,
        } as TorStatus));
        
        if (message.error) {
          setTorError(message.error);
        } else {
          setTorError(null);
        }
      });

      // Listen for Tor connection updates
      window.electronAPI.on(MAIN_TO_RENDERER_CHANNELS.TOR_CONNECTION_UPDATE, (message: any) => {
        setTorStatus(prev => ({
          ...prev,
          is_connected: message.connected,
          status: message.connected ? 'connected' : 'disconnected',
          last_connected: message.connected ? new Date().toISOString() : prev?.last_connected,
          error: message.error,
        } as TorStatus));
        
        if (message.error) {
          setTorError(message.error);
        }
      });

      // Listen for Tor bootstrap updates
      window.electronAPI.on(MAIN_TO_RENDERER_CHANNELS.TOR_BOOTSTRAP_UPDATE, (message: any) => {
        setTorStatus(prev => ({
          ...prev,
          bootstrap_progress: message.progress,
          status: message.progress >= 1 ? 'connected' : 'connecting',
          is_connected: message.progress >= 1,
        } as TorStatus));
      });

      // Listen for Tor circuit updates
      window.electronAPI.on(MAIN_TO_RENDERER_CHANNELS.TOR_CIRCUIT_UPDATE, (message: any) => {
        setTorStatus(prev => {
          if (!prev) return prev;
          
          const circuits = [...(prev.circuits || [])];
          const existingIndex = circuits.findIndex(c => c.id === message.circuitId);
          
          if (existingIndex >= 0) {
            circuits[existingIndex] = {
              ...circuits[existingIndex],
              status: message.status,
              path: message.path,
              age: message.age,
            };
          } else {
            circuits.push({
              id: message.circuitId,
              path: message.path,
              status: message.status,
              age: message.age,
              purpose: message.purpose || 'general',
              flags: message.flags || [],
            });
          }
          
          return {
            ...prev,
            circuits,
          };
        });
      });
    }
  }, []);

  // Get initial Tor status
  const getTorStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setTorError(null);
      
      const response = await sendIpcMessage('TOR_GET_STATUS');
      
      if (response && !response.error) {
        setTorStatus({
          is_connected: response.connected,
          bootstrap_progress: response.bootstrapProgress || 0,
          circuits: response.circuits || [],
          proxy_port: response.proxyPort || 9050,
          status: response.connected ? 'connected' : 'disconnected',
          last_connected: response.connected ? new Date().toISOString() : undefined,
        });
      } else {
        setTorError(response?.error || 'Failed to get Tor status');
        setTorStatus(null);
      }
    } catch (error) {
      console.error('Failed to get Tor status:', error);
      setTorError(error instanceof Error ? error.message : 'Unknown error');
      setTorStatus(null);
    } finally {
      setIsLoading(false);
    }
  }, [sendIpcMessage]);

  // Start Tor
  const startTor = useCallback(async () => {
    try {
      setIsLoading(true);
      setTorError(null);
      
      const response = await sendIpcMessage('TOR_START');
      
      if (response && response.success) {
        // Status will be updated via IPC messages
        console.log('Tor start command sent successfully');
      } else {
        setTorError(response?.error || 'Failed to start Tor');
      }
    } catch (error) {
      console.error('Failed to start Tor:', error);
      setTorError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [sendIpcMessage]);

  // Stop Tor
  const stopTor = useCallback(async () => {
    try {
      setIsLoading(true);
      setTorError(null);
      
      const response = await sendIpcMessage('TOR_STOP');
      
      if (response && response.success) {
        // Status will be updated via IPC messages
        console.log('Tor stop command sent successfully');
      } else {
        setTorError(response?.error || 'Failed to stop Tor');
      }
    } catch (error) {
      console.error('Failed to stop Tor:', error);
      setTorError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [sendIpcMessage]);

  // Restart Tor
  const restartTor = useCallback(async () => {
    try {
      setIsLoading(true);
      setTorError(null);
      
      const response = await sendIpcMessage('TOR_RESTART');
      
      if (response && response.success) {
        // Status will be updated via IPC messages
        console.log('Tor restart command sent successfully');
      } else {
        setTorError(response?.error || 'Failed to restart Tor');
      }
    } catch (error) {
      console.error('Failed to restart Tor:', error);
      setTorError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [sendIpcMessage]);

  // Refresh status
  const refreshStatus = useCallback(async () => {
    await getTorStatus();
  }, [getTorStatus]);

  // Initialize on mount
  useEffect(() => {
    // Set up IPC listeners
    listenForIpcMessages();
    
    // Get initial status
    getTorStatus();
    
    // Set up periodic status refresh
    const interval = setInterval(() => {
      if (!isLoading) {
        getTorStatus();
      }
    }, 30000); // Refresh every 30 seconds
    
    return () => {
      clearInterval(interval);
    };
  }, [listenForIpcMessages, getTorStatus, isLoading]);

  // Handle window focus to refresh status
  useEffect(() => {
    const handleFocus = () => {
      if (!isLoading) {
        getTorStatus();
      }
    };
    
    window.addEventListener('focus', handleFocus);
    
    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, [getTorStatus, isLoading]);

  return {
    torStatus,
    torError,
    isLoading,
    isConnected,
    bootstrapProgress,
    circuitCount,
    refreshStatus,
    startTor,
    stopTor,
    restartTor,
  };
};

// Hook for Tor connection status only
export const useTorConnection = (): {
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
} => {
  const { isConnected, isLoading, torError } = useTorStatus();
  
  return {
    isConnected,
    isLoading,
    error: torError,
  };
};

// Hook for Tor bootstrap progress
export const useTorBootstrap = (): {
  progress: number;
  isComplete: boolean;
  isLoading: boolean;
} => {
  const { bootstrapProgress, isLoading } = useTorStatus();
  
  return {
    progress: bootstrapProgress,
    isComplete: bootstrapProgress >= 1,
    isLoading,
  };
};

// Hook for Tor circuits
export const useTorCircuits = (): {
  circuits: TorStatus['circuits'];
  count: number;
  isLoading: boolean;
} => {
  const { torStatus, isLoading } = useTorStatus();
  
  return {
    circuits: torStatus?.circuits || [],
    count: torStatus?.circuits?.length || 0,
    isLoading,
  };
};