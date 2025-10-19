// nodesStore.ts - Nodes data state management
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Node, NodeResources, Pool } from '../../../shared/types';

// Node filter interface
interface NodeFilter {
  status?: Node['status'];
  poolId?: string;
  operatorId?: string;
  minPootScore?: number;
  maxPootScore?: number;
  searchQuery?: string;
  sortBy?: 'created_at' | 'poot_score' | 'status' | 'operator_id';
  sortOrder?: 'asc' | 'desc';
}

// Node statistics interface
interface NodeStats {
  total: number;
  active: number;
  inactive: number;
  suspended: number;
  registered: number;
  averagePootScore: number;
  totalPootScore: number;
  averageUptime: number;
  totalResources: {
    cpu: number;
    memory: number;
    disk: number;
    bandwidth: number;
  };
  byPool: Record<string, number>;
  newNodesThisMonth: number;
  newNodesThisWeek: number;
  newNodesToday: number;
}

// Node bulk operation interface
interface NodeBulkOperation {
  type: 'suspend' | 'activate' | 'delete' | 'assign_pool' | 'remove_pool' | 'maintenance' | null;
  selectedIds: string[];
  isProcessing: boolean;
  progress: number;
  error: string | null;
  metadata?: {
    poolId?: string;
    suspensionReason?: string;
    maintenanceDuration?: number; // in hours
  };
}

// Node maintenance interface
interface NodeMaintenance {
  nodeId: string;
  startTime: Date;
  endTime: Date | null;
  reason: string;
  isActive: boolean;
  estimatedDuration: number; // in hours
}

interface NodesState {
  // Core data
  nodes: Node[];
  selectedNodes: string[];
  
  // Pagination
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalCount: number;
  
  // Filtering and sorting
  filters: NodeFilter;
  
  // Statistics
  stats: NodeStats;
  
  // Bulk operations
  bulkOperation: NodeBulkOperation;
  
  // Node details
  selectedNode: Node | null;
  nodeResources: NodeResources | null;
  
  // Pool management
  pools: Pool[];
  selectedPool: Pool | null;
  
  // Maintenance
  maintenanceNodes: NodeMaintenance[];
  maintenanceModal: {
    isOpen: boolean;
    nodeId: string | null;
    reason: string;
    estimatedDuration: number;
  };
  
  // Loading states
  isLoadingNodes: boolean;
  isLoadingStats: boolean;
  isLoadingNodeDetails: boolean;
  isLoadingPools: boolean;
  isLoadingResources: boolean;
  
  // Error states
  nodesError: string | null;
  statsError: string | null;
  nodeDetailsError: string | null;
  poolsError: string | null;
  resourcesError: string | null;
  
  // Real-time updates
  lastUpdated: Date | null;
  isLive: boolean;
  
  // View settings
  viewMode: 'table' | 'cards' | 'grid' | 'map';
  columnsVisible: Record<string, boolean>;
  
  // Resource monitoring
  resourceMonitoring: {
    enabled: boolean;
    refreshInterval: number; // in seconds
    selectedMetrics: string[];
  };
}

interface NodesActions {
  // Core data actions
  setNodes: (nodes: Node[]) => void;
  addNode: (node: Node) => void;
  updateNode: (nodeId: string, updates: Partial<Node>) => void;
  removeNode: (nodeId: string) => void;
  removeNodes: (nodeIds: string[]) => void;
  
  // Selection actions
  setSelectedNodes: (nodeIds: string[]) => void;
  toggleNodeSelection: (nodeId: string) => void;
  selectAllNodes: () => void;
  clearSelection: () => void;
  
  // Pagination actions
  setCurrentPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTotalPages: (pages: number) => void;
  setTotalCount: (count: number) => void;
  goToNextPage: () => void;
  goToPreviousPage: () => void;
  
  // Filtering and sorting actions
  setFilters: (filters: Partial<NodeFilter>) => void;
  clearFilters: () => void;
  setSearchQuery: (query: string) => void;
  setSorting: (sortBy: NodeFilter['sortBy'], sortOrder: NodeFilter['sortOrder']) => void;
  
  // Statistics actions
  setStats: (stats: NodeStats) => void;
  updateStats: (updates: Partial<NodeStats>) => void;
  
  // Bulk operation actions
  setBulkOperation: (operation: NodeBulkOperation) => void;
  startBulkOperation: (type: NodeBulkOperation['type'], nodeIds: string[], metadata?: NodeBulkOperation['metadata']) => void;
  updateBulkProgress: (progress: number) => void;
  setBulkError: (error: string | null) => void;
  completeBulkOperation: () => void;
  
  // Node details actions
  setSelectedNode: (node: Node | null) => void;
  setNodeResources: (resources: NodeResources | null) => void;
  
  // Pool actions
  setPools: (pools: Pool[]) => void;
  setSelectedPool: (pool: Pool | null) => void;
  addPool: (pool: Pool) => void;
  updatePool: (poolId: string, updates: Partial<Pool>) => void;
  removePool: (poolId: string) => void;
  
  // Maintenance actions
  setMaintenanceNodes: (maintenance: NodeMaintenance[]) => void;
  addMaintenanceNode: (maintenance: NodeMaintenance) => void;
  updateMaintenanceNode: (nodeId: string, updates: Partial<NodeMaintenance>) => void;
  removeMaintenanceNode: (nodeId: string) => void;
  setMaintenanceModal: (modal: NodesState['maintenanceModal']) => void;
  openMaintenanceModal: (nodeId: string) => void;
  closeMaintenanceModal: () => void;
  
  // Loading actions
  setLoadingNodes: (loading: boolean) => void;
  setLoadingStats: (loading: boolean) => void;
  setLoadingNodeDetails: (loading: boolean) => void;
  setLoadingPools: (loading: boolean) => void;
  setLoadingResources: (loading: boolean) => void;
  
  // Error actions
  setNodesError: (error: string | null) => void;
  setStatsError: (error: string | null) => void;
  setNodeDetailsError: (error: string | null) => void;
  setPoolsError: (error: string | null) => void;
  setResourcesError: (error: string | null) => void;
  clearErrors: () => void;
  
  // Real-time actions
  setLastUpdated: (date: Date) => void;
  setIsLive: (isLive: boolean) => void;
  
  // View actions
  setViewMode: (mode: NodesState['viewMode']) => void;
  setColumnVisible: (column: string, visible: boolean) => void;
  setColumnsVisible: (columns: Record<string, boolean>) => void;
  
  // Resource monitoring actions
  setResourceMonitoring: (monitoring: Partial<NodesState['resourceMonitoring']>) => void;
  toggleResourceMonitoring: () => void;
  
  // Utility actions
  reset: () => void;
  refreshData: () => void;
}

// Initial state
const initialState: NodesState = {
  // Core data
  nodes: [],
  selectedNodes: [],
  
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
    inactive: 0,
    suspended: 0,
    registered: 0,
    averagePootScore: 0,
    totalPootScore: 0,
    averageUptime: 0,
    totalResources: {
      cpu: 0,
      memory: 0,
      disk: 0,
      bandwidth: 0,
    },
    byPool: {},
    newNodesThisMonth: 0,
    newNodesThisWeek: 0,
    newNodesToday: 0,
  },
  
  // Bulk operations
  bulkOperation: {
    type: null,
    selectedIds: [],
    isProcessing: false,
    progress: 0,
    error: null,
  },
  
  // Node details
  selectedNode: null,
  nodeResources: null,
  
  // Pool management
  pools: [],
  selectedPool: null,
  
  // Maintenance
  maintenanceNodes: [],
  maintenanceModal: {
    isOpen: false,
    nodeId: null,
    reason: '',
    estimatedDuration: 2, // 2 hours default
  },
  
  // Loading states
  isLoadingNodes: false,
  isLoadingStats: false,
  isLoadingNodeDetails: false,
  isLoadingPools: false,
  isLoadingResources: false,
  
  // Error states
  nodesError: null,
  statsError: null,
  nodeDetailsError: null,
  poolsError: null,
  resourcesError: null,
  
  // Real-time updates
  lastUpdated: null,
  isLive: false,
  
  // View settings
  viewMode: 'table',
  columnsVisible: {
    node_id: true,
    operator_id: true,
    status: true,
    pool_id: true,
    poot_score: true,
    resources: true,
    created_at: true,
  },
  
  // Resource monitoring
  resourceMonitoring: {
    enabled: false,
    refreshInterval: 30,
    selectedMetrics: ['cpu_usage', 'memory_usage', 'disk_usage'],
  },
};

// Create the nodes store
export const useNodesStore = create<NodesState & NodesActions>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Core data actions
      setNodes: (nodes) => set({ nodes }),
      addNode: (node) => set((state) => ({
        nodes: [node, ...state.nodes]
      })),
      updateNode: (nodeId, updates) => set((state) => ({
        nodes: state.nodes.map(node =>
          node.node_id === nodeId ? { ...node, ...updates } : node
        )
      })),
      removeNode: (nodeId) => set((state) => ({
        nodes: state.nodes.filter(node => node.node_id !== nodeId),
        selectedNodes: state.selectedNodes.filter(id => id !== nodeId),
      })),
      removeNodes: (nodeIds) => set((state) => ({
        nodes: state.nodes.filter(node => !nodeIds.includes(node.node_id)),
        selectedNodes: state.selectedNodes.filter(id => !nodeIds.includes(id)),
      })),
      
      // Selection actions
      setSelectedNodes: (nodeIds) => set({ selectedNodes: nodeIds }),
      toggleNodeSelection: (nodeId) => set((state) => ({
        selectedNodes: state.selectedNodes.includes(nodeId)
          ? state.selectedNodes.filter(id => id !== nodeId)
          : [...state.selectedNodes, nodeId]
      })),
      selectAllNodes: () => set((state) => ({
        selectedNodes: state.nodes.map(node => node.node_id)
      })),
      clearSelection: () => set({ selectedNodes: [] }),
      
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
        currentPage: 1,
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
      startBulkOperation: (type, nodeIds, metadata) => set({
        bulkOperation: {
          type,
          selectedIds: nodeIds,
          isProcessing: true,
          progress: 0,
          error: null,
          metadata,
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
      
      // Node details actions
      setSelectedNode: (node) => set({ selectedNode: node }),
      setNodeResources: (resources) => set({ nodeResources: resources }),
      
      // Pool actions
      setPools: (pools) => set({ pools }),
      setSelectedPool: (pool) => set({ selectedPool: pool }),
      addPool: (pool) => set((state) => ({
        pools: [...state.pools, pool]
      })),
      updatePool: (poolId, updates) => set((state) => ({
        pools: state.pools.map(pool =>
          pool.pool_id === poolId ? { ...pool, ...updates } : pool
        )
      })),
      removePool: (poolId) => set((state) => ({
        pools: state.pools.filter(pool => pool.pool_id !== poolId)
      })),
      
      // Maintenance actions
      setMaintenanceNodes: (maintenance) => set({ maintenanceNodes: maintenance }),
      addMaintenanceNode: (maintenance) => set((state) => ({
        maintenanceNodes: [...state.maintenanceNodes, maintenance]
      })),
      updateMaintenanceNode: (nodeId, updates) => set((state) => ({
        maintenanceNodes: state.maintenanceNodes.map(maintenance =>
          maintenance.nodeId === nodeId ? { ...maintenance, ...updates } : maintenance
        )
      })),
      removeMaintenanceNode: (nodeId) => set((state) => ({
        maintenanceNodes: state.maintenanceNodes.filter(maintenance => maintenance.nodeId !== nodeId)
      })),
      setMaintenanceModal: (modal) => set({ maintenanceModal: modal }),
      openMaintenanceModal: (nodeId) => set({
        maintenanceModal: {
          isOpen: true,
          nodeId,
          reason: '',
          estimatedDuration: 2,
        }
      }),
      closeMaintenanceModal: () => set({
        maintenanceModal: {
          isOpen: false,
          nodeId: null,
          reason: '',
          estimatedDuration: 2,
        }
      }),
      
      // Loading actions
      setLoadingNodes: (loading) => set({ isLoadingNodes: loading }),
      setLoadingStats: (loading) => set({ isLoadingStats: loading }),
      setLoadingNodeDetails: (loading) => set({ isLoadingNodeDetails: loading }),
      setLoadingPools: (loading) => set({ isLoadingPools: loading }),
      setLoadingResources: (loading) => set({ isLoadingResources: loading }),
      
      // Error actions
      setNodesError: (error) => set({ nodesError: error }),
      setStatsError: (error) => set({ statsError: error }),
      setNodeDetailsError: (error) => set({ nodeDetailsError: error }),
      setPoolsError: (error) => set({ poolsError: error }),
      setResourcesError: (error) => set({ resourcesError: error }),
      clearErrors: () => set({
        nodesError: null,
        statsError: null,
        nodeDetailsError: null,
        poolsError: null,
        resourcesError: null,
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
      
      // Resource monitoring actions
      setResourceMonitoring: (monitoring) => set((state) => ({
        resourceMonitoring: { ...state.resourceMonitoring, ...monitoring }
      })),
      toggleResourceMonitoring: () => set((state) => ({
        resourceMonitoring: { 
          ...state.resourceMonitoring, 
          enabled: !state.resourceMonitoring.enabled 
        }
      })),
      
      // Utility actions
      reset: () => set(initialState),
      refreshData: () => set({
        isLoadingNodes: true,
        isLoadingStats: true,
        isLoadingPools: true,
        lastUpdated: new Date(),
      }),
    }),
    {
      name: 'lucid-admin-nodes-store',
    }
  )
);

// Selectors for nodes state access
export const useNodes = () => useNodesStore((state) => state.nodes);
export const useSelectedNodes = () => useNodesStore((state) => state.selectedNodes);
export const useNodePagination = () => useNodesStore((state) => ({
  currentPage: state.currentPage,
  pageSize: state.pageSize,
  totalPages: state.totalPages,
  totalCount: state.totalCount,
}));

export const useNodeFilters = () => useNodesStore((state) => state.filters);
export const useNodeStats = () => useNodesStore((state) => state.stats);

export const useNodeBulkOperation = () => useNodesStore((state) => state.bulkOperation);
export const useSelectedNode = () => useNodesStore((state) => state.selectedNode);
export const useNodeResources = () => useNodesStore((state) => state.nodeResources);

export const usePools = () => useNodesStore((state) => state.pools);
export const useSelectedPool = () => useNodesStore((state) => state.selectedPool);

export const useMaintenanceNodes = () => useNodesStore((state) => state.maintenanceNodes);
export const useMaintenanceModal = () => useNodesStore((state) => state.maintenanceModal);

export const useNodesLoading = () => useNodesStore((state) => ({
  isLoadingNodes: state.isLoadingNodes,
  isLoadingStats: state.isLoadingStats,
  isLoadingNodeDetails: state.isLoadingNodeDetails,
  isLoadingPools: state.isLoadingPools,
  isLoadingResources: state.isLoadingResources,
  isLoading: state.isLoadingNodes || state.isLoadingStats || 
             state.isLoadingNodeDetails || state.isLoadingPools || state.isLoadingResources,
}));

export const useNodesErrors = () => useNodesStore((state) => ({
  nodesError: state.nodesError,
  statsError: state.statsError,
  nodeDetailsError: state.nodeDetailsError,
  poolsError: state.poolsError,
  resourcesError: state.resourcesError,
  hasErrors: !!(state.nodesError || state.statsError || state.nodeDetailsError || 
                state.poolsError || state.resourcesError),
}));

export const useNodesRealTime = () => useNodesStore((state) => ({
  lastUpdated: state.lastUpdated,
  isLive: state.isLive,
  timeSinceUpdate: state.lastUpdated ? Date.now() - state.lastUpdated.getTime() : 0,
}));

export const useNodesView = () => useNodesStore((state) => ({
  viewMode: state.viewMode,
  columnsVisible: state.columnsVisible,
}));

export const useResourceMonitoring = () => useNodesStore((state) => state.resourceMonitoring);

// Action selectors
export const useNodesActions = () => useNodesStore((state) => ({
  setNodes: state.setNodes,
  addNode: state.addNode,
  updateNode: state.updateNode,
  removeNode: state.removeNode,
  removeNodes: state.removeNodes,
  setSelectedNodes: state.setSelectedNodes,
  toggleNodeSelection: state.toggleNodeSelection,
  selectAllNodes: state.selectAllNodes,
  clearSelection: state.clearSelection,
  setFilters: state.setFilters,
  clearFilters: state.clearFilters,
  setSearchQuery: state.setSearchQuery,
  setSorting: state.setSorting,
  setStats: state.setStats,
  reset: state.reset,
  refreshData: state.refreshData,
}));

export const useNodePaginationActions = () => useNodesStore((state) => ({
  setCurrentPage: state.setCurrentPage,
  setPageSize: state.setPageSize,
  setTotalPages: state.setTotalPages,
  setTotalCount: state.setTotalCount,
  goToNextPage: state.goToNextPage,
  goToPreviousPage: state.goToPreviousPage,
}));

export const useNodeBulkOperationActions = () => useNodesStore((state) => ({
  setBulkOperation: state.setBulkOperation,
  startBulkOperation: state.startBulkOperation,
  updateBulkProgress: state.updateBulkProgress,
  setBulkError: state.setBulkError,
  completeBulkOperation: state.completeBulkOperation,
}));

export const useNodeDetailsActions = () => useNodesStore((state) => ({
  setSelectedNode: state.setSelectedNode,
  setNodeResources: state.setNodeResources,
}));

export const usePoolActions = () => useNodesStore((state) => ({
  setPools: state.setPools,
  setSelectedPool: state.setSelectedPool,
  addPool: state.addPool,
  updatePool: state.updatePool,
  removePool: state.removePool,
}));

export const useMaintenanceActions = () => useNodesStore((state) => ({
  setMaintenanceNodes: state.setMaintenanceNodes,
  addMaintenanceNode: state.addMaintenanceNode,
  updateMaintenanceNode: state.updateMaintenanceNode,
  removeMaintenanceNode: state.removeMaintenanceNode,
  setMaintenanceModal: state.setMaintenanceModal,
  openMaintenanceModal: state.openMaintenanceModal,
  closeMaintenanceModal: state.closeMaintenanceModal,
}));

export const useNodesLoadingActions = () => useNodesStore((state) => ({
  setLoadingNodes: state.setLoadingNodes,
  setLoadingStats: state.setLoadingStats,
  setLoadingNodeDetails: state.setLoadingNodeDetails,
  setLoadingPools: state.setLoadingPools,
  setLoadingResources: state.setLoadingResources,
}));

export const useNodesErrorActions = () => useNodesStore((state) => ({
  setNodesError: state.setNodesError,
  setStatsError: state.setStatsError,
  setNodeDetailsError: state.setNodeDetailsError,
  setPoolsError: state.setPoolsError,
  setResourcesError: state.setResourcesError,
  clearErrors: state.clearErrors,
}));

export const useNodesViewActions = () => useNodesStore((state) => ({
  setViewMode: state.setViewMode,
  setColumnVisible: state.setColumnVisible,
  setColumnsVisible: state.setColumnsVisible,
}));

export const useResourceMonitoringActions = () => useNodesStore((state) => ({
  setResourceMonitoring: state.setResourceMonitoring,
  toggleResourceMonitoring: state.toggleResourceMonitoring,
}));

// Computed selectors
export const useFilteredNodes = () => {
  const nodes = useNodes();
  const filters = useNodeFilters();
  
  let filtered = [...nodes];
  
  if (filters.status) {
    filtered = filtered.filter(node => node.status === filters.status);
  }
  
  if (filters.poolId) {
    filtered = filtered.filter(node => node.pool_id === filters.poolId);
  }
  
  if (filters.operatorId) {
    filtered = filtered.filter(node => node.operator_id === filters.operatorId);
  }
  
  if (filters.minPootScore !== undefined) {
    filtered = filtered.filter(node => node.poot_score >= filters.minPootScore!);
  }
  
  if (filters.maxPootScore !== undefined) {
    filtered = filtered.filter(node => node.poot_score <= filters.maxPootScore!);
  }
  
  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(node => 
      node.node_id.toLowerCase().includes(query) ||
      node.operator_id.toLowerCase().includes(query) ||
      node.status.toLowerCase().includes(query) ||
      node.pool_id?.toLowerCase().includes(query)
    );
  }
  
  // Sort
  if (filters.sortBy) {
    filtered.sort((a, b) => {
      let aValue: any = a[filters.sortBy!];
      let bValue: any = b[filters.sortBy!];
      
      if (filters.sortBy === 'created_at') {
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

export const usePaginatedNodes = () => {
  const filteredNodes = useFilteredNodes();
  const { currentPage, pageSize } = useNodePagination();
  
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  
  return {
    nodes: filteredNodes.slice(startIndex, endIndex),
    totalCount: filteredNodes.length,
    hasNextPage: endIndex < filteredNodes.length,
    hasPreviousPage: currentPage > 1,
  };
};

export const useNodesByStatus = (status: Node['status']) => {
  const nodes = useNodes();
  return nodes.filter(node => node.status === status);
};

export const useActiveNodes = () => {
  const nodes = useNodes();
  return nodes.filter(node => node.status === 'active');
};

export const useNodesByPool = (poolId: string) => {
  const nodes = useNodes();
  return nodes.filter(node => node.pool_id === poolId);
};

export const useNodesByOperator = (operatorId: string) => {
  const nodes = useNodes();
  return nodes.filter(node => node.operator_id === operatorId);
};

export const useSelectedNodesCount = () => {
  const selectedNodes = useSelectedNodes();
  return selectedNodes.length;
};

export const useCanPerformBulkOperation = () => {
  const selectedNodes = useSelectedNodes();
  const bulkOperation = useNodeBulkOperation();
  return selectedNodes.length > 0 && !bulkOperation.isProcessing;
};

export const useNodeStatsByPool = () => {
  const stats = useNodeStats();
  return stats.byPool;
};

export const useNewNodesStats = () => {
  const stats = useNodeStats();
  return {
    today: stats.newNodesToday,
    thisWeek: stats.newNodesThisWeek,
    thisMonth: stats.newNodesThisMonth,
  };
};

export const useNodesInMaintenance = () => {
  const maintenanceNodes = useMaintenanceNodes();
  return maintenanceNodes.filter(maintenance => maintenance.isActive);
};

export const useNodeResourceUtilization = () => {
  const nodes = useNodes();
  const stats = useNodeStats();
  
  if (nodes.length === 0) return { cpu: 0, memory: 0, disk: 0, bandwidth: 0 };
  
  const totalResources = nodes.reduce((acc, node) => ({
    cpu: acc.cpu + node.resources.cpu_usage,
    memory: acc.memory + node.resources.memory_usage,
    disk: acc.disk + node.resources.disk_usage,
    bandwidth: acc.bandwidth + node.resources.network_bandwidth,
  }), { cpu: 0, memory: 0, disk: 0, bandwidth: 0 });
  
  return {
    cpu: totalResources.cpu / nodes.length,
    memory: totalResources.memory / nodes.length,
    disk: totalResources.disk / nodes.length,
    bandwidth: totalResources.bandwidth / nodes.length,
  };
};

export default useNodesStore;
