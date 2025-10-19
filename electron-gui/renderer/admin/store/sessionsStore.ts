// sessionsStore.ts - Sessions data state management
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Session, Chunk, BlockchainAnchor } from '../../../shared/types';

// Session filter interface
interface SessionFilter {
  status?: Session['status'];
  userId?: string;
  nodeId?: string;
  dateRange?: {
    start: Date;
    end: Date;
  };
  searchQuery?: string;
  sortBy?: 'created_at' | 'updated_at' | 'status' | 'user_id';
  sortOrder?: 'asc' | 'desc';
}

// Session statistics interface
interface SessionStats {
  total: number;
  active: number;
  completed: number;
  failed: number;
  anchored: number;
  averageDuration: number; // in minutes
  totalDataSize: number; // in bytes
  averageChunkSize: number; // in bytes
  successRate: number; // percentage
}

// Session export options interface
interface SessionExportOptions {
  format: 'json' | 'csv' | 'xml';
  includeChunks: boolean;
  includeMetadata: boolean;
  includeAnchors: boolean;
  dateRange?: {
    start: Date;
    end: Date;
  };
  filters?: SessionFilter;
}

interface SessionsState {
  // Core data
  sessions: Session[];
  selectedSessions: string[];
  
  // Pagination
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalCount: number;
  
  // Filtering and sorting
  filters: SessionFilter;
  
  // Statistics
  stats: SessionStats;
  
  // Bulk operations
  bulkOperation: {
    type: 'delete' | 'export' | 'anchor' | 'terminate' | null;
    selectedIds: string[];
    isProcessing: boolean;
    progress: number;
    error: string | null;
  };
  
  // Session details
  selectedSession: Session | null;
  sessionChunks: Chunk[];
  sessionAnchor: BlockchainAnchor | null;
  
  // Export operations
  exportOperation: {
    isExporting: boolean;
    progress: number;
    error: string | null;
    options: SessionExportOptions;
  };
  
  // Loading states
  isLoadingSessions: boolean;
  isLoadingStats: boolean;
  isLoadingSessionDetails: boolean;
  isLoadingChunks: boolean;
  isLoadingAnchor: boolean;
  
  // Error states
  sessionsError: string | null;
  statsError: string | null;
  sessionDetailsError: string | null;
  chunksError: string | null;
  anchorError: string | null;
  
  // Real-time updates
  lastUpdated: Date | null;
  isLive: boolean;
  
  // View settings
  viewMode: 'table' | 'cards' | 'timeline';
  columnsVisible: Record<string, boolean>;
}

interface SessionsActions {
  // Core data actions
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  removeSession: (sessionId: string) => void;
  removeSessions: (sessionIds: string[]) => void;
  
  // Selection actions
  setSelectedSessions: (sessionIds: string[]) => void;
  toggleSessionSelection: (sessionId: string) => void;
  selectAllSessions: () => void;
  clearSelection: () => void;
  
  // Pagination actions
  setCurrentPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTotalPages: (pages: number) => void;
  setTotalCount: (count: number) => void;
  goToNextPage: () => void;
  goToPreviousPage: () => void;
  
  // Filtering and sorting actions
  setFilters: (filters: Partial<SessionFilter>) => void;
  clearFilters: () => void;
  setSearchQuery: (query: string) => void;
  setSorting: (sortBy: SessionFilter['sortBy'], sortOrder: SessionFilter['sortOrder']) => void;
  
  // Statistics actions
  setStats: (stats: SessionStats) => void;
  updateStats: (updates: Partial<SessionStats>) => void;
  
  // Bulk operation actions
  setBulkOperation: (operation: SessionsState['bulkOperation']) => void;
  startBulkOperation: (type: SessionsState['bulkOperation']['type'], sessionIds: string[]) => void;
  updateBulkProgress: (progress: number) => void;
  setBulkError: (error: string | null) => void;
  completeBulkOperation: () => void;
  
  // Session details actions
  setSelectedSession: (session: Session | null) => void;
  setSessionChunks: (chunks: Chunk[]) => void;
  setSessionAnchor: (anchor: BlockchainAnchor | null) => void;
  
  // Export actions
  setExportOperation: (operation: SessionsState['exportOperation']) => void;
  startExport: (options: SessionExportOptions) => void;
  updateExportProgress: (progress: number) => void;
  setExportError: (error: string | null) => void;
  completeExport: () => void;
  
  // Loading actions
  setLoadingSessions: (loading: boolean) => void;
  setLoadingStats: (loading: boolean) => void;
  setLoadingSessionDetails: (loading: boolean) => void;
  setLoadingChunks: (loading: boolean) => void;
  setLoadingAnchor: (loading: boolean) => void;
  
  // Error actions
  setSessionsError: (error: string | null) => void;
  setStatsError: (error: string | null) => void;
  setSessionDetailsError: (error: string | null) => void;
  setChunksError: (error: string | null) => void;
  setAnchorError: (error: string | null) => void;
  clearErrors: () => void;
  
  // Real-time actions
  setLastUpdated: (date: Date) => void;
  setIsLive: (isLive: boolean) => void;
  
  // View actions
  setViewMode: (mode: SessionsState['viewMode']) => void;
  setColumnVisible: (column: string, visible: boolean) => void;
  setColumnsVisible: (columns: Record<string, boolean>) => void;
  
  // Utility actions
  reset: () => void;
  refreshData: () => void;
}

// Initial state
const initialState: SessionsState = {
  // Core data
  sessions: [],
  selectedSessions: [],
  
  // Pagination
  currentPage: 1,
  pageSize: 25,
  totalPages: 0,
  totalCount: 0,
  
  // Filtering and sorting
  filters: {
    sortBy: 'created_at',
    sortOrder: 'desc',
  },
  
  // Statistics
  stats: {
    total: 0,
    active: 0,
    completed: 0,
    failed: 0,
    anchored: 0,
    averageDuration: 0,
    totalDataSize: 0,
    averageChunkSize: 0,
    successRate: 0,
  },
  
  // Bulk operations
  bulkOperation: {
    type: null,
    selectedIds: [],
    isProcessing: false,
    progress: 0,
    error: null,
  },
  
  // Session details
  selectedSession: null,
  sessionChunks: [],
  sessionAnchor: null,
  
  // Export operations
  exportOperation: {
    isExporting: false,
    progress: 0,
    error: null,
    options: {
      format: 'json',
      includeChunks: false,
      includeMetadata: true,
      includeAnchors: false,
    },
  },
  
  // Loading states
  isLoadingSessions: false,
  isLoadingStats: false,
  isLoadingSessionDetails: false,
  isLoadingChunks: false,
  isLoadingAnchor: false,
  
  // Error states
  sessionsError: null,
  statsError: null,
  sessionDetailsError: null,
  chunksError: null,
  anchorError: null,
  
  // Real-time updates
  lastUpdated: null,
  isLive: false,
  
  // View settings
  viewMode: 'table',
  columnsVisible: {
    session_id: true,
    user_id: true,
    status: true,
    created_at: true,
    updated_at: true,
    chunks_count: true,
    merkle_root: false,
    blockchain_anchor: false,
  },
};

// Create the sessions store
export const useSessionsStore = create<SessionsState & SessionsActions>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Core data actions
      setSessions: (sessions) => set({ sessions }),
      addSession: (session) => set((state) => ({
        sessions: [session, ...state.sessions]
      })),
      updateSession: (sessionId, updates) => set((state) => ({
        sessions: state.sessions.map(session =>
          session.session_id === sessionId ? { ...session, ...updates } : session
        )
      })),
      removeSession: (sessionId) => set((state) => ({
        sessions: state.sessions.filter(session => session.session_id !== sessionId),
        selectedSessions: state.selectedSessions.filter(id => id !== sessionId),
      })),
      removeSessions: (sessionIds) => set((state) => ({
        sessions: state.sessions.filter(session => !sessionIds.includes(session.session_id)),
        selectedSessions: state.selectedSessions.filter(id => !sessionIds.includes(id)),
      })),
      
      // Selection actions
      setSelectedSessions: (sessionIds) => set({ selectedSessions: sessionIds }),
      toggleSessionSelection: (sessionId) => set((state) => ({
        selectedSessions: state.selectedSessions.includes(sessionId)
          ? state.selectedSessions.filter(id => id !== sessionId)
          : [...state.selectedSessions, sessionId]
      })),
      selectAllSessions: () => set((state) => ({
        selectedSessions: state.sessions.map(session => session.session_id)
      })),
      clearSelection: () => set({ selectedSessions: [] }),
      
      // Pagination actions
      setCurrentPage: (page) => set({ currentPage: page }),
      setPageSize: (size) => set({ pageSize: size, currentPage: 1 }),
      setTotalPages: (pages) => set({ totalPages: pages }),
      setTotalCount: (count) => set({ totalCount: count }),
      goToNextPage: () => set((state) => ({
        currentPage: Math.min(state.currentPage + 1, state.totalPages)
      })),
      goToPreviousPage: () => set((state) => ({
        currentPage: Math.max(state.currentPage - 1, 1)
      })),
      
      // Filtering and sorting actions
      setFilters: (filters) => set((state) => ({
        filters: { ...state.filters, ...filters },
        currentPage: 1, // Reset to first page when filters change
      })),
      clearFilters: () => set((state) => ({
        filters: {
          sortBy: state.filters.sortBy,
          sortOrder: state.filters.sortOrder,
        },
        currentPage: 1,
      })),
      setSearchQuery: (query) => set((state) => ({
        filters: { ...state.filters, searchQuery: query },
        currentPage: 1,
      })),
      setSorting: (sortBy, sortOrder) => set((state) => ({
        filters: { ...state.filters, sortBy, sortOrder },
      })),
      
      // Statistics actions
      setStats: (stats) => set({ stats }),
      updateStats: (updates) => set((state) => ({
        stats: { ...state.stats, ...updates }
      })),
      
      // Bulk operation actions
      setBulkOperation: (operation) => set({ bulkOperation: operation }),
      startBulkOperation: (type, sessionIds) => set({
        bulkOperation: {
          type,
          selectedIds: sessionIds,
          isProcessing: true,
          progress: 0,
          error: null,
        }
      }),
      updateBulkProgress: (progress) => set((state) => ({
        bulkOperation: { ...state.bulkOperation, progress }
      })),
      setBulkError: (error) => set((state) => ({
        bulkOperation: { ...state.bulkOperation, error }
      })),
      completeBulkOperation: () => set((state) => ({
        bulkOperation: { ...state.bulkOperation, isProcessing: false }
      })),
      
      // Session details actions
      setSelectedSession: (session) => set({ selectedSession: session }),
      setSessionChunks: (chunks) => set({ sessionChunks: chunks }),
      setSessionAnchor: (anchor) => set({ sessionAnchor: anchor }),
      
      // Export actions
      setExportOperation: (operation) => set({ exportOperation: operation }),
      startExport: (options) => set({
        exportOperation: {
          isExporting: true,
          progress: 0,
          error: null,
          options,
        }
      }),
      updateExportProgress: (progress) => set((state) => ({
        exportOperation: { ...state.exportOperation, progress }
      })),
      setExportError: (error) => set((state) => ({
        exportOperation: { ...state.exportOperation, error }
      })),
      completeExport: () => set((state) => ({
        exportOperation: { ...state.exportOperation, isExporting: false }
      })),
      
      // Loading actions
      setLoadingSessions: (loading) => set({ isLoadingSessions: loading }),
      setLoadingStats: (loading) => set({ isLoadingStats: loading }),
      setLoadingSessionDetails: (loading) => set({ isLoadingSessionDetails: loading }),
      setLoadingChunks: (loading) => set({ isLoadingChunks: loading }),
      setLoadingAnchor: (loading) => set({ isLoadingAnchor: loading }),
      
      // Error actions
      setSessionsError: (error) => set({ sessionsError: error }),
      setStatsError: (error) => set({ statsError: error }),
      setSessionDetailsError: (error) => set({ sessionDetailsError: error }),
      setChunksError: (error) => set({ chunksError: error }),
      setAnchorError: (error) => set({ anchorError: error }),
      clearErrors: () => set({
        sessionsError: null,
        statsError: null,
        sessionDetailsError: null,
        chunksError: null,
        anchorError: null,
      }),
      
      // Real-time actions
      setLastUpdated: (date) => set({ lastUpdated: date }),
      setIsLive: (isLive) => set({ isLive }),
      
      // View actions
      setViewMode: (mode) => set({ viewMode: mode }),
      setColumnVisible: (column, visible) => set((state) => ({
        columnsVisible: { ...state.columnsVisible, [column]: visible }
      })),
      setColumnsVisible: (columns) => set({ columnsVisible: columns }),
      
      // Utility actions
      reset: () => set(initialState),
      refreshData: () => set({
        isLoadingSessions: true,
        isLoadingStats: true,
        lastUpdated: new Date(),
      }),
    }),
    {
      name: 'lucid-admin-sessions-store',
    }
  )
);

// Selectors for sessions state access
export const useSessions = () => useSessionsStore((state) => state.sessions);
export const useSelectedSessions = () => useSessionsStore((state) => state.selectedSessions);
export const useSessionPagination = () => useSessionsStore((state) => ({
  currentPage: state.currentPage,
  pageSize: state.pageSize,
  totalPages: state.totalPages,
  totalCount: state.totalCount,
}));

export const useSessionFilters = () => useSessionsStore((state) => state.filters);
export const useSessionStats = () => useSessionsStore((state) => state.stats);

export const useBulkOperation = () => useSessionsStore((state) => state.bulkOperation);
export const useSelectedSession = () => useSessionsStore((state) => state.selectedSession);
export const useSessionChunks = () => useSessionsStore((state) => state.sessionChunks);
export const useSessionAnchor = () => useSessionsStore((state) => state.sessionAnchor);

export const useExportOperation = () => useSessionsStore((state) => state.exportOperation);

export const useSessionsLoading = () => useSessionsStore((state) => ({
  isLoadingSessions: state.isLoadingSessions,
  isLoadingStats: state.isLoadingStats,
  isLoadingSessionDetails: state.isLoadingSessionDetails,
  isLoadingChunks: state.isLoadingChunks,
  isLoadingAnchor: state.isLoadingAnchor,
  isLoading: state.isLoadingSessions || state.isLoadingStats || 
             state.isLoadingSessionDetails || state.isLoadingChunks || state.isLoadingAnchor,
}));

export const useSessionsErrors = () => useSessionsStore((state) => ({
  sessionsError: state.sessionsError,
  statsError: state.statsError,
  sessionDetailsError: state.sessionDetailsError,
  chunksError: state.chunksError,
  anchorError: state.anchorError,
  hasErrors: !!(state.sessionsError || state.statsError || state.sessionDetailsError || 
                state.chunksError || state.anchorError),
}));

export const useSessionsRealTime = () => useSessionsStore((state) => ({
  lastUpdated: state.lastUpdated,
  isLive: state.isLive,
  timeSinceUpdate: state.lastUpdated ? Date.now() - state.lastUpdated.getTime() : 0,
}));

export const useSessionsView = () => useSessionsStore((state) => ({
  viewMode: state.viewMode,
  columnsVisible: state.columnsVisible,
}));

// Action selectors
export const useSessionsActions = () => useSessionsStore((state) => ({
  setSessions: state.setSessions,
  addSession: state.addSession,
  updateSession: state.updateSession,
  removeSession: state.removeSession,
  removeSessions: state.removeSessions,
  setSelectedSessions: state.setSelectedSessions,
  toggleSessionSelection: state.toggleSessionSelection,
  selectAllSessions: state.selectAllSessions,
  clearSelection: state.clearSelection,
  setFilters: state.setFilters,
  clearFilters: state.clearFilters,
  setSearchQuery: state.setSearchQuery,
  setSorting: state.setSorting,
  setStats: state.setStats,
  reset: state.reset,
  refreshData: state.refreshData,
}));

export const useSessionPaginationActions = () => useSessionsStore((state) => ({
  setCurrentPage: state.setCurrentPage,
  setPageSize: state.setPageSize,
  setTotalPages: state.setTotalPages,
  setTotalCount: state.setTotalCount,
  goToNextPage: state.goToNextPage,
  goToPreviousPage: state.goToPreviousPage,
}));

export const useBulkOperationActions = () => useSessionsStore((state) => ({
  setBulkOperation: state.setBulkOperation,
  startBulkOperation: state.startBulkOperation,
  updateBulkProgress: state.updateBulkProgress,
  setBulkError: state.setBulkError,
  completeBulkOperation: state.completeBulkOperation,
}));

export const useSessionDetailsActions = () => useSessionsStore((state) => ({
  setSelectedSession: state.setSelectedSession,
  setSessionChunks: state.setSessionChunks,
  setSessionAnchor: state.setSessionAnchor,
}));

export const useExportActions = () => useSessionsStore((state) => ({
  setExportOperation: state.setExportOperation,
  startExport: state.startExport,
  updateExportProgress: state.updateExportProgress,
  setExportError: state.setExportError,
  completeExport: state.completeExport,
}));

export const useSessionsLoadingActions = () => useSessionsStore((state) => ({
  setLoadingSessions: state.setLoadingSessions,
  setLoadingStats: state.setLoadingStats,
  setLoadingSessionDetails: state.setLoadingSessionDetails,
  setLoadingChunks: state.setLoadingChunks,
  setLoadingAnchor: state.setLoadingAnchor,
}));

export const useSessionsErrorActions = () => useSessionsStore((state) => ({
  setSessionsError: state.setSessionsError,
  setStatsError: state.setStatsError,
  setSessionDetailsError: state.setSessionDetailsError,
  setChunksError: state.setChunksError,
  setAnchorError: state.setAnchorError,
  clearErrors: state.clearErrors,
}));

export const useSessionsViewActions = () => useSessionsStore((state) => ({
  setViewMode: state.setViewMode,
  setColumnVisible: state.setColumnVisible,
  setColumnsVisible: state.setColumnsVisible,
}));

// Computed selectors
export const useFilteredSessions = () => {
  const sessions = useSessions();
  const filters = useSessionFilters();
  
  let filtered = [...sessions];
  
  if (filters.status) {
    filtered = filtered.filter(session => session.status === filters.status);
  }
  
  if (filters.userId) {
    filtered = filtered.filter(session => session.user_id === filters.userId);
  }
  
  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(session => 
      session.session_id.toLowerCase().includes(query) ||
      session.user_id.toLowerCase().includes(query) ||
      session.status.toLowerCase().includes(query)
    );
  }
  
  if (filters.dateRange) {
    filtered = filtered.filter(session => {
      const sessionDate = new Date(session.created_at);
      return sessionDate >= filters.dateRange!.start && sessionDate <= filters.dateRange!.end;
    });
  }
  
  // Sort
  if (filters.sortBy) {
    filtered.sort((a, b) => {
      let aValue: any = a[filters.sortBy!];
      let bValue: any = b[filters.sortBy!];
      
      if (filters.sortBy === 'created_at' || filters.sortBy === 'updated_at') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }
      
      if (filters.sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  }
  
  return filtered;
};

export const usePaginatedSessions = () => {
  const filteredSessions = useFilteredSessions();
  const { currentPage, pageSize } = useSessionPagination();
  
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  
  return {
    sessions: filteredSessions.slice(startIndex, endIndex),
    totalCount: filteredSessions.length,
    hasNextPage: endIndex < filteredSessions.length,
    hasPreviousPage: currentPage > 1,
  };
};

export const useSessionsByStatus = (status: Session['status']) => {
  const sessions = useSessions();
  return sessions.filter(session => session.status === status);
};

export const useActiveSessions = () => {
  const sessions = useSessions();
  return sessions.filter(session => session.status === 'active');
};

export const useCompletedSessions = () => {
  const sessions = useSessions();
  return sessions.filter(session => session.status === 'completed');
};

export const useFailedSessions = () => {
  const sessions = useSessions();
  return sessions.filter(session => session.status === 'failed');
};

export const useAnchoredSessions = () => {
  const sessions = useSessions();
  return sessions.filter(session => session.status === 'anchored');
};

export const useSessionsByUser = (userId: string) => {
  const sessions = useSessions();
  return sessions.filter(session => session.user_id === userId);
};

export const useSessionsByNode = (nodeId: string) => {
  const sessions = useSessions();
  return sessions.filter(session => session.node_id === nodeId);
};

export const useSelectedSessionsCount = () => {
  const selectedSessions = useSelectedSessions();
  return selectedSessions.length;
};

export const useCanPerformBulkOperation = () => {
  const selectedSessions = useSelectedSessions();
  const bulkOperation = useBulkOperation();
  return selectedSessions.length > 0 && !bulkOperation.isProcessing;
};

export const useSessionSuccessRate = () => {
  const stats = useSessionStats();
  return stats.successRate;
};

export const useAverageSessionDuration = () => {
  const stats = useSessionStats();
  return stats.averageDuration;
};

export const useTotalDataSize = () => {
  const stats = useSessionStats();
  return stats.totalDataSize;
};

export const useAverageChunkSize = () => {
  const stats = useSessionStats();
  return stats.averageChunkSize;
};

export default useSessionsStore;
