// useApi.ts - API calling hook
// Based on the electron-multi-gui-development.plan.md specifications

import { useState, useCallback, useRef, useEffect } from 'react';
import { LucidAPIClient } from '../../../shared/api-client';
import { LucidError } from '../../../shared/types';
import { formatError } from '../../../shared/utils';

export interface ApiState<T = any> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastFetch: Date | null;
}

export interface ApiOptions {
  immediate?: boolean;
  retry?: boolean;
  retryAttempts?: number;
  retryDelay?: number;
  timeout?: number;
  onSuccess?: (data: any) => void;
  onError?: (error: string) => void;
}

export interface UseApiReturn<T = any> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastFetch: Date | null;
  execute: (...args: any[]) => Promise<T>;
  reset: () => void;
  refetch: () => Promise<T>;
}

// Generic API hook
export const useApi = <T = any>(
  apiFunction: (...args: any[]) => Promise<T>,
  options: ApiOptions = {}
): UseApiReturn<T> => {
  const {
    immediate = false,
    retry = false,
    retryAttempts = 3,
    retryDelay = 1000,
    timeout = 30000,
    onSuccess,
    onError,
  } = options;

  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
    lastFetch: null,
  });

  const retryCountRef = useRef(0);
  const timeoutRef = useRef<NodeJS.Timeout>();

  const execute = useCallback(async (...args: any[]): Promise<T> => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      // Set timeout
      if (timeout > 0) {
        timeoutRef.current = setTimeout(() => {
          setState(prev => ({
            ...prev,
            loading: false,
            error: 'Request timeout',
          }));
        }, timeout);
      }

      const result = await apiFunction(...args);
      
      // Clear timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      setState(prev => ({
        ...prev,
        data: result,
        loading: false,
        error: null,
        lastFetch: new Date(),
      }));

      onSuccess?.(result);
      return result;
    } catch (error) {
      // Clear timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      const errorMessage = formatError(error);
      
      // Retry logic
      if (retry && retryCountRef.current < retryAttempts) {
        retryCountRef.current++;
        setTimeout(() => {
          execute(...args);
        }, retryDelay * retryCountRef.current);
        return Promise.reject(error);
      }

      setState(prev => ({
        ...prev,
        loading: false,
        error: errorMessage,
      }));

      onError?.(errorMessage);
      throw error;
    }
  }, [apiFunction, retry, retryAttempts, retryDelay, timeout, onSuccess, onError]);

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
      lastFetch: null,
    });
    retryCountRef.current = 0;
  }, []);

  const refetch = useCallback(() => {
    return execute();
  }, [execute]);

  // Execute immediately if requested
  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [immediate, execute]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    ...state,
    execute,
    reset,
    refetch,
  };
};

// Specific API hooks for common operations
export const useApiGet = <T = any>(
  url: string,
  options: ApiOptions = {}
) => {
  const apiClient = new LucidAPIClient();
  
  return useApi<T>(
    () => apiClient.get<T>(url),
    options
  );
};

export const useApiPost = <T = any>(
  url: string,
  options: ApiOptions = {}
) => {
  const apiClient = new LucidAPIClient();
  
  return useApi<T>(
    (data: any) => apiClient.post<T>(url, data),
    options
  );
};

export const useApiPut = <T = any>(
  url: string,
  options: ApiOptions = {}
) => {
  const apiClient = new LucidAPIClient();
  
  return useApi<T>(
    (data: any) => apiClient.put<T>(url, data),
    options
  );
};

export const useApiDelete = <T = any>(
  url: string,
  options: ApiOptions = {}
) => {
  const apiClient = new LucidAPIClient();
  
  return useApi<T>(
    () => apiClient.delete<T>(url),
    options
  );
};

// Lucid-specific API hooks
export const useUserProfile = (userId: string, options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getUserProfile(userId),
    { immediate: true, ...options }
  );
};

export const useUserSessions = (userId: string, options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getUserSessions(userId),
    { immediate: true, ...options }
  );
};

export const useSession = (sessionId: string, options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getSession(sessionId),
    { immediate: true, ...options }
  );
};

export const useNode = (nodeId: string, options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getNode(nodeId),
    { immediate: true, ...options }
  );
};

export const useNodeStatus = (nodeId: string, options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getNodeStatus(nodeId),
    { immediate: true, ...options }
  );
};

export const useBlockchainInfo = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getBlockchainInfo(),
    { immediate: true, ...options }
  );
};

export const useLatestBlock = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getLatestBlock(),
    { immediate: true, ...options }
  );
};

export const useSystemHealth = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getSystemHealth(),
    { immediate: true, ...options }
  );
};

export const useAllUsers = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getAllUsers(),
    { immediate: true, ...options }
  );
};

export const useAllSessions = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getAllSessions(),
    { immediate: true, ...options }
  );
};

export const useAllNodes = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getAllNodes(),
    { immediate: true, ...options }
  );
};

// Mutation hooks for data modification
export const useCreateSession = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (data: any) => apiClient.createSession(data),
    options
  );
};

export const useUpdateSession = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (sessionId: string, data: any) => apiClient.updateSession(sessionId, data),
    options
  );
};

export const useDeleteSession = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (sessionId: string) => apiClient.deleteSession(sessionId),
    options
  );
};

export const useRegisterNode = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (data: any) => apiClient.registerNode(data),
    options
  );
};

export const useJoinPool = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (nodeId: string, poolId: string) => apiClient.joinPool(nodeId, poolId),
    options
  );
};

export const useLeavePool = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (nodeId: string) => apiClient.leavePool(nodeId),
    options
  );
};

export const useLogin = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (email: string, signature: string) => apiClient.login(email, signature),
    options
  );
};

export const useLogout = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.logout(),
    options
  );
};

export const useVerifyToken = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (token: string) => apiClient.verifyToken(token),
    options
  );
};

// File upload hook
export const useFileUpload = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (sessionId: string, file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.uploadChunk(sessionId, formData);
    },
    options
  );
};

// File download hook
export const useFileDownload = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (chunkId: string) => apiClient.downloadChunk(chunkId),
    options
  );
};

// TRON payment hooks
export const useWalletBalance = (address: string, options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    () => apiClient.getWalletBalance(address),
    { immediate: true, ...options }
  );
};

export const useTransferUSDT = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (fromAddress: string, toAddress: string, amount: number) => 
      apiClient.transferUSDT(fromAddress, toAddress, amount),
    options
  );
};

// Proof verification hooks
export const useVerifySessionProof = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (sessionId: string) => apiClient.verifySessionProof(sessionId),
    options
  );
};

export const useGetMerkleProof = (options: ApiOptions = {}) => {
  const apiClient = new LucidAPIClient();
  
  return useApi(
    (chunkId: string) => apiClient.getMerkleProof(chunkId),
    options
  );
};

// Pagination hook
export interface PaginationOptions {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  filters?: Record<string, any>;
}

export const usePaginatedApi = <T = any>(
  apiFunction: (options: PaginationOptions) => Promise<{ data: T[]; total: number; page: number; limit: number }>,
  initialOptions: PaginationOptions = { page: 1, limit: 10 }
) => {
  const [options, setOptions] = useState<PaginationOptions>(initialOptions);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    limit: 10,
    totalPages: 0,
  });

  const { data, loading, error, execute } = useApi(
    () => apiFunction(options),
    { immediate: true }
  );

  const updateOptions = useCallback((newOptions: Partial<PaginationOptions>) => {
    setOptions(prev => ({ ...prev, ...newOptions }));
  }, []);

  const setPage = useCallback((page: number) => {
    updateOptions({ page });
  }, [updateOptions]);

  const setLimit = useCallback((limit: number) => {
    updateOptions({ limit, page: 1 });
  }, [updateOptions]);

  const setSort = useCallback((sortBy: string, sortOrder: 'asc' | 'desc' = 'asc') => {
    updateOptions({ sortBy, sortOrder });
  }, [updateOptions]);

  const setFilters = useCallback((filters: Record<string, any>) => {
    updateOptions({ filters, page: 1 });
  }, [updateOptions]);

  // Update pagination info when data changes
  useEffect(() => {
    if (data) {
      setPagination({
        total: data.total,
        page: data.page,
        limit: data.limit,
        totalPages: Math.ceil(data.total / data.limit),
      });
    }
  }, [data]);

  return {
    data: data?.data || [],
    loading,
    error,
    pagination,
    options,
    setPage,
    setLimit,
    setSort,
    setFilters,
    refetch: execute,
  };
};

export default useApi;
