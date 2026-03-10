// blockchainStore.ts - Blockchain data state management
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Block, Transaction, ConsensusVote, BlockchainAnchor } from '../../../shared/types';

// Blockchain filter interface
interface BlockchainFilter {
  blockHeight?: number;
  transactionType?: Transaction['type'];
  dateRange?: {
    start: Date;
    end: Date;
  };
  searchQuery?: string;
  sortBy?: 'height' | 'timestamp' | 'transaction_count';
  sortOrder?: 'asc' | 'desc';
}

// Blockchain statistics interface
interface BlockchainStats {
  totalBlocks: number;
  totalTransactions: number;
  chainHeight: number;
  lastBlockTime: Date | null;
  averageBlockTime: number; // in seconds
  blocksPerHour: number;
  transactionsPerBlock: number;
  networkHashRate: number;
  difficulty: number;
  totalSupply: number;
  circulatingSupply: number;
  byTransactionType: Record<Transaction['type'], number>;
  recentBlocks: Block[];
  pendingTransactions: number;
}

// Anchoring queue interface
interface AnchoringQueueItem {
  id: string;
  sessionId: string;
  userId: string;
  merkleRoot: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  submittedAt: Date;
  estimatedBlockHeight: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  retryCount: number;
  maxRetries: number;
}

// Blockchain consensus interface
interface ConsensusInfo {
  totalNodes: number;
  participatingNodes: number;
  consensusThreshold: number;
  currentVotes: ConsensusVote[];
  lastConsensusTime: Date | null;
  consensusStatus: 'active' | 'inactive' | 'failed';
}

interface BlockchainState {
  // Core data
  blocks: Block[];
  recentBlocks: Block[];
  pendingBlocks: Block[];
  
  // Anchoring queue
  anchoringQueue: AnchoringQueueItem[];
  selectedQueueItems: string[];
  
  // Pagination
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalCount: number;
  
  // Filtering and sorting
  filters: BlockchainFilter;
  
  // Statistics
  stats: BlockchainStats;
  
  // Consensus information
  consensusInfo: ConsensusInfo;
  
  // Block details
  selectedBlock: Block | null;
  blockTransactions: Transaction[];
  blockConsensusVotes: ConsensusVote[];
  
  // Transaction details
  selectedTransaction: Transaction | null;
  
  // Anchoring operations
  anchoringOperation: {
    isProcessing: boolean;
    progress: number;
    error: string | null;
    selectedItems: string[];
  };
  
  // Block creation
  blockCreation: {
    isCreating: boolean;
    progress: number;
    error: string | null;
    newBlock: Block | null;
  };
  
  // Loading states
  isLoadingBlocks: boolean;
  isLoadingStats: boolean;
  isLoadingAnchoringQueue: boolean;
  isLoadingConsensusInfo: boolean;
  isLoadingBlockDetails: boolean;
  isLoadingTransactions: boolean;
  
  // Error states
  blocksError: string | null;
  statsError: string | null;
  anchoringQueueError: string | null;
  consensusError: string | null;
  blockDetailsError: string | null;
  transactionsError: string | null;
  
  // Real-time updates
  lastUpdated: Date | null;
  isLive: boolean;
  
  // View settings
  viewMode: 'table' | 'timeline' | 'blocks' | 'network';
  columnsVisible: Record<string, boolean>;
  
  // Network monitoring
  networkMonitoring: {
    enabled: boolean;
    refreshInterval: number; // in seconds
    selectedMetrics: string[];
  };
}

interface BlockchainActions {
  // Core data actions
  setBlocks: (blocks: Block[]) => void;
  addBlock: (block: Block) => void;
  updateBlock: (blockId: string, updates: Partial<Block>) => void;
  removeBlock: (blockId: string) => void;
  setRecentBlocks: (blocks: Block[]) => void;
  setPendingBlocks: (blocks: Block[]) => void;
  
  // Anchoring queue actions
  setAnchoringQueue: (queue: AnchoringQueueItem[]) => void;
  addAnchoringItem: (item: AnchoringQueueItem) => void;
  updateAnchoringItem: (itemId: string, updates: Partial<AnchoringQueueItem>) => void;
  removeAnchoringItem: (itemId: string) => void;
  setSelectedQueueItems: (itemIds: string[]) => void;
  toggleQueueItemSelection: (itemId: string) => void;
  
  // Pagination actions
  setCurrentPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTotalPages: (pages: number) => void;
  setTotalCount: (count: number) => void;
  goToNextPage: () => void;
  goToPreviousPage: () => void;
  
  // Filtering and sorting actions
  setFilters: (filters: Partial<BlockchainFilter>) => void;
  clearFilters: () => void;
  setSearchQuery: (query: string) => void;
  setSorting: (sortBy: BlockchainFilter['sortBy'], sortOrder: BlockchainFilter['sortOrder']) => void;
  
  // Statistics actions
  setStats: (stats: BlockchainStats) => void;
  updateStats: (updates: Partial<BlockchainStats>) => void;
  
  // Consensus actions
  setConsensusInfo: (info: ConsensusInfo) => void;
  updateConsensusVotes: (votes: ConsensusVote[]) => void;
  addConsensusVote: (vote: ConsensusVote) => void;
  
  // Block details actions
  setSelectedBlock: (block: Block | null) => void;
  setBlockTransactions: (transactions: Transaction[]) => void;
  setBlockConsensusVotes: (votes: ConsensusVote[]) => void;
  
  // Transaction details actions
  setSelectedTransaction: (transaction: Transaction | null) => void;
  
  // Anchoring operation actions
  setAnchoringOperation: (operation: BlockchainState['anchoringOperation']) => void;
  startAnchoringOperation: (itemIds: string[]) => void;
  updateAnchoringProgress: (progress: number) => void;
  setAnchoringError: (error: string | null) => void;
  completeAnchoringOperation: () => void;
  
  // Block creation actions
  setBlockCreation: (creation: BlockchainState['blockCreation']) => void;
  startBlockCreation: () => void;
  updateBlockCreationProgress: (progress: number) => void;
  setBlockCreationError: (error: string | null) => void;
  completeBlockCreation: (newBlock: Block) => void;
  
  // Loading actions
  setLoadingBlocks: (loading: boolean) => void;
  setLoadingStats: (loading: boolean) => void;
  setLoadingAnchoringQueue: (loading: boolean) => void;
  setLoadingConsensusInfo: (loading: boolean) => void;
  setLoadingBlockDetails: (loading: boolean) => void;
  setLoadingTransactions: (loading: boolean) => void;
  
  // Error actions
  setBlocksError: (error: string | null) => void;
  setStatsError: (error: string | null) => void;
  setAnchoringQueueError: (error: string | null) => void;
  setConsensusError: (error: string | null) => void;
  setBlockDetailsError: (error: string | null) => void;
  setTransactionsError: (error: string | null) => void;
  clearErrors: () => void;
  
  // Real-time actions
  setLastUpdated: (date: Date) => void;
  setIsLive: (isLive: boolean) => void;
  
  // View actions
  setViewMode: (mode: BlockchainState['viewMode']) => void;
  setColumnVisible: (column: string, visible: boolean) => void;
  setColumnsVisible: (columns: Record<string, boolean>) => void;
  
  // Network monitoring actions
  setNetworkMonitoring: (monitoring: Partial<BlockchainState['networkMonitoring']>) => void;
  toggleNetworkMonitoring: () => void;
  
  // Utility actions
  reset: () => void;
  refreshData: () => void;
}

// Initial state
const initialState: BlockchainState = {
  // Core data
  blocks: [],
  recentBlocks: [],
  pendingBlocks: [],
  
  // Anchoring queue
  anchoringQueue: [],
  selectedQueueItems: [],
  
  // Pagination
  currentPage: 1,
  pageSize: 25,
  totalPages: 0,
  totalCount: 0,
  
  // Filtering and sorting
  filters: {
    sortBy: 'height',
    sortOrder: 'desc',
  },
  
  // Statistics
  stats: {
    totalBlocks: 0,
    totalTransactions: 0,
    chainHeight: 0,
    lastBlockTime: null,
    averageBlockTime: 0,
    blocksPerHour: 0,
    transactionsPerBlock: 0,
    networkHashRate: 0,
    difficulty: 0,
    totalSupply: 0,
    circulatingSupply: 0,
    byTransactionType: {
      session_anchor: 0,
      payout: 0,
      governance: 0,
    },
    recentBlocks: [],
    pendingTransactions: 0,
  },
  
  // Consensus information
  consensusInfo: {
    totalNodes: 0,
    participatingNodes: 0,
    consensusThreshold: 0,
    currentVotes: [],
    lastConsensusTime: null,
    consensusStatus: 'inactive',
  },
  
  // Block details
  selectedBlock: null,
  blockTransactions: [],
  blockConsensusVotes: [],
  
  // Transaction details
  selectedTransaction: null,
  
  // Anchoring operations
  anchoringOperation: {
    isProcessing: false,
    progress: 0,
    error: null,
    selectedItems: [],
  },
  
  // Block creation
  blockCreation: {
    isCreating: false,
    progress: 0,
    error: null,
    newBlock: null,
  },
  
  // Loading states
  isLoadingBlocks: false,
  isLoadingStats: false,
  isLoadingAnchoringQueue: false,
  isLoadingConsensusInfo: false,
  isLoadingBlockDetails: false,
  isLoadingTransactions: false,
  
  // Error states
  blocksError: null,
  statsError: null,
  anchoringQueueError: null,
  consensusError: null,
  blockDetailsError: null,
  transactionsError: null,
  
  // Real-time updates
  lastUpdated: null,
  isLive: false,
  
  // View settings
  viewMode: 'table',
  columnsVisible: {
    height: true,
    timestamp: true,
    transaction_count: true,
    merkle_root: true,
    previous_hash: false,
    consensus_votes: true,
  },
  
  // Network monitoring
  networkMonitoring: {
    enabled: false,
    refreshInterval: 30,
    selectedMetrics: ['hash_rate', 'difficulty', 'block_time'],
  },
};

// Create the blockchain store
export const useBlockchainStore = create<BlockchainState & BlockchainActions>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Core data actions
      setBlocks: (blocks) => set({ blocks }),
      addBlock: (block) => set((state) => ({
        blocks: [block, ...state.blocks]
      })),
      updateBlock: (blockId, updates) => set((state) => ({
        blocks: state.blocks.map(block =>
          block.block_id === blockId ? { ...block, ...updates } : block
        )
      })),
      removeBlock: (blockId) => set((state) => ({
        blocks: state.blocks.filter(block => block.block_id !== blockId)
      })),
      setRecentBlocks: (blocks) => set({ recentBlocks: blocks }),
      setPendingBlocks: (blocks) => set({ pendingBlocks: blocks }),
      
      // Anchoring queue actions
      setAnchoringQueue: (queue) => set({ anchoringQueue: queue }),
      addAnchoringItem: (item) => set((state) => ({
        anchoringQueue: [...state.anchoringQueue, item]
      })),
      updateAnchoringItem: (itemId, updates) => set((state) => ({
        anchoringQueue: state.anchoringQueue.map(item =>
          item.id === itemId ? { ...item, ...updates } : item
        )
      })),
      removeAnchoringItem: (itemId) => set((state) => ({
        anchoringQueue: state.anchoringQueue.filter(item => item.id !== itemId),
        selectedQueueItems: state.selectedQueueItems.filter(id => id !== itemId),
      })),
      setSelectedQueueItems: (itemIds) => set({ selectedQueueItems: itemIds }),
      toggleQueueItemSelection: (itemId) => set((state) => ({
        selectedQueueItems: state.selectedQueueItems.includes(itemId)
          ? state.selectedQueueItems.filter(id => id !== itemId)
          : [...state.selectedQueueItems, itemId]
      })),
      
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
      
      // Consensus actions
      setConsensusInfo: (info) => set({ consensusInfo: info }),
      updateConsensusVotes: (votes) => set((state) => ({
        consensusInfo: { ...state.consensusInfo, currentVotes: votes }
      })),
      addConsensusVote: (vote) => set((state) => ({
        consensusInfo: {
          ...state.consensusInfo,
          currentVotes: [...state.consensusInfo.currentVotes, vote]
        }
      })),
      
      // Block details actions
      setSelectedBlock: (block) => set({ selectedBlock: block }),
      setBlockTransactions: (transactions) => set({ blockTransactions: transactions }),
      setBlockConsensusVotes: (votes) => set({ blockConsensusVotes: votes }),
      
      // Transaction details actions
      setSelectedTransaction: (transaction) => set({ selectedTransaction: transaction }),
      
      // Anchoring operation actions
      setAnchoringOperation: (operation) => set({ anchoringOperation: operation }),
      startAnchoringOperation: (itemIds) => set({
        anchoringOperation: {
          isProcessing: true,
          progress: 0,
          error: null,
          selectedItems: itemIds,
        }
      }),
      updateAnchoringProgress: (progress) => set((state) => ({
        anchoringOperation: { ...state.anchoringOperation, progress }
      })),
      setAnchoringError: (error) => set((state) => ({
        anchoringOperation: { ...state.anchoringOperation, error }
      })),
      completeAnchoringOperation: () => set((state) => ({
        anchoringOperation: { ...state.anchoringOperation, isProcessing: false }
      })),
      
      // Block creation actions
      setBlockCreation: (creation) => set({ blockCreation: creation }),
      startBlockCreation: () => set({
        blockCreation: {
          isCreating: true,
          progress: 0,
          error: null,
          newBlock: null,
        }
      }),
      updateBlockCreationProgress: (progress) => set((state) => ({
        blockCreation: { ...state.blockCreation, progress }
      })),
      setBlockCreationError: (error) => set((state) => ({
        blockCreation: { ...state.blockCreation, error }
      })),
      completeBlockCreation: (newBlock) => set((state) => ({
        blockCreation: { ...state.blockCreation, isCreating: false, newBlock },
        blocks: [newBlock, ...state.blocks]
      })),
      
      // Loading actions
      setLoadingBlocks: (loading) => set({ isLoadingBlocks: loading }),
      setLoadingStats: (loading) => set({ isLoadingStats: loading }),
      setLoadingAnchoringQueue: (loading) => set({ isLoadingAnchoringQueue: loading }),
      setLoadingConsensusInfo: (loading) => set({ isLoadingConsensusInfo: loading }),
      setLoadingBlockDetails: (loading) => set({ isLoadingBlockDetails: loading }),
      setLoadingTransactions: (loading) => set({ isLoadingTransactions: loading }),
      
      // Error actions
      setBlocksError: (error) => set({ blocksError: error }),
      setStatsError: (error) => set({ statsError: error }),
      setAnchoringQueueError: (error) => set({ anchoringQueueError: error }),
      setConsensusError: (error) => set({ consensusError: error }),
      setBlockDetailsError: (error) => set({ blockDetailsError: error }),
      setTransactionsError: (error) => set({ transactionsError: error }),
      clearErrors: () => set({
        blocksError: null,
        statsError: null,
        anchoringQueueError: null,
        consensusError: null,
        blockDetailsError: null,
        transactionsError: null,
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
      
      // Network monitoring actions
      setNetworkMonitoring: (monitoring) => set((state) => ({
        networkMonitoring: { ...state.networkMonitoring, ...monitoring }
      })),
      toggleNetworkMonitoring: () => set((state) => ({
        networkMonitoring: { 
          ...state.networkMonitoring, 
          enabled: !state.networkMonitoring.enabled 
        }
      })),
      
      // Utility actions
      reset: () => set(initialState),
      refreshData: () => set({
        isLoadingBlocks: true,
        isLoadingStats: true,
        isLoadingAnchoringQueue: true,
        isLoadingConsensusInfo: true,
        lastUpdated: new Date(),
      }),
    }),
    {
      name: 'lucid-admin-blockchain-store',
    }
  )
);

// Selectors for blockchain state access
export const useBlocks = () => useBlockchainStore((state) => state.blocks);
export const useRecentBlocks = () => useBlockchainStore((state) => state.recentBlocks);
export const usePendingBlocks = () => useBlockchainStore((state) => state.pendingBlocks);

export const useAnchoringQueue = () => useBlockchainStore((state) => state.anchoringQueue);
export const useSelectedQueueItems = () => useBlockchainStore((state) => state.selectedQueueItems);

export const useBlockchainPagination = () => useBlockchainStore((state) => ({
  currentPage: state.currentPage,
  pageSize: state.pageSize,
  totalPages: state.totalPages,
  totalCount: state.totalCount,
}));

export const useBlockchainFilters = () => useBlockchainStore((state) => state.filters);
export const useBlockchainStats = () => useBlockchainStore((state) => state.stats);

export const useConsensusInfo = () => useBlockchainStore((state) => state.consensusInfo);

export const useSelectedBlock = () => useBlockchainStore((state) => state.selectedBlock);
export const useBlockTransactions = () => useBlockchainStore((state) => state.blockTransactions);
export const useBlockConsensusVotes = () => useBlockchainStore((state) => state.blockConsensusVotes);

export const useSelectedTransaction = () => useBlockchainStore((state) => state.selectedTransaction);

export const useAnchoringOperation = () => useBlockchainStore((state) => state.anchoringOperation);
export const useBlockCreation = () => useBlockchainStore((state) => state.blockCreation);

export const useBlockchainLoading = () => useBlockchainStore((state) => ({
  isLoadingBlocks: state.isLoadingBlocks,
  isLoadingStats: state.isLoadingStats,
  isLoadingAnchoringQueue: state.isLoadingAnchoringQueue,
  isLoadingConsensusInfo: state.isLoadingConsensusInfo,
  isLoadingBlockDetails: state.isLoadingBlockDetails,
  isLoadingTransactions: state.isLoadingTransactions,
  isLoading: state.isLoadingBlocks || state.isLoadingStats || 
             state.isLoadingAnchoringQueue || state.isLoadingConsensusInfo || 
             state.isLoadingBlockDetails || state.isLoadingTransactions,
}));

export const useBlockchainErrors = () => useBlockchainStore((state) => ({
  blocksError: state.blocksError,
  statsError: state.statsError,
  anchoringQueueError: state.anchoringQueueError,
  consensusError: state.consensusError,
  blockDetailsError: state.blockDetailsError,
  transactionsError: state.transactionsError,
  hasErrors: !!(state.blocksError || state.statsError || state.anchoringQueueError || 
                state.consensusError || state.blockDetailsError || state.transactionsError),
}));

export const useBlockchainRealTime = () => useBlockchainStore((state) => ({
  lastUpdated: state.lastUpdated,
  isLive: state.isLive,
  timeSinceUpdate: state.lastUpdated ? Date.now() - state.lastUpdated.getTime() : 0,
}));

export const useBlockchainView = () => useBlockchainStore((state) => ({
  viewMode: state.viewMode,
  columnsVisible: state.columnsVisible,
}));

export const useNetworkMonitoring = () => useBlockchainStore((state) => state.networkMonitoring);

// Action selectors
export const useBlockchainActions = () => useBlockchainStore((state) => ({
  setBlocks: state.setBlocks,
  addBlock: state.addBlock,
  updateBlock: state.updateBlock,
  removeBlock: state.removeBlock,
  setRecentBlocks: state.setRecentBlocks,
  setPendingBlocks: state.setPendingBlocks,
  setAnchoringQueue: state.setAnchoringQueue,
  addAnchoringItem: state.addAnchoringItem,
  updateAnchoringItem: state.updateAnchoringItem,
  removeAnchoringItem: state.removeAnchoringItem,
  setSelectedQueueItems: state.setSelectedQueueItems,
  toggleQueueItemSelection: state.toggleQueueItemSelection,
  setFilters: state.setFilters,
  clearFilters: state.clearFilters,
  setSearchQuery: state.setSearchQuery,
  setSorting: state.setSorting,
  setStats: state.setStats,
  reset: state.reset,
  refreshData: state.refreshData,
}));

export const useBlockchainPaginationActions = () => useBlockchainStore((state) => ({
  setCurrentPage: state.setCurrentPage,
  setPageSize: state.setPageSize,
  setTotalPages: state.setTotalPages,
  setTotalCount: state.setTotalCount,
  goToNextPage: state.goToNextPage,
  goToPreviousPage: state.goToPreviousPage,
}));

export const useConsensusActions = () => useBlockchainStore((state) => ({
  setConsensusInfo: state.setConsensusInfo,
  updateConsensusVotes: state.updateConsensusVotes,
  addConsensusVote: state.addConsensusVote,
}));

export const useBlockDetailsActions = () => useBlockchainStore((state) => ({
  setSelectedBlock: state.setSelectedBlock,
  setBlockTransactions: state.setBlockTransactions,
  setBlockConsensusVotes: state.setBlockConsensusVotes,
}));

export const useAnchoringActions = () => useBlockchainStore((state) => ({
  setAnchoringOperation: state.setAnchoringOperation,
  startAnchoringOperation: state.startAnchoringOperation,
  updateAnchoringProgress: state.updateAnchoringProgress,
  setAnchoringError: state.setAnchoringError,
  completeAnchoringOperation: state.completeAnchoringOperation,
}));

export const useBlockCreationActions = () => useBlockchainStore((state) => ({
  setBlockCreation: state.setBlockCreation,
  startBlockCreation: state.startBlockCreation,
  updateBlockCreationProgress: state.updateBlockCreationProgress,
  setBlockCreationError: state.setBlockCreationError,
  completeBlockCreation: state.completeBlockCreation,
}));

export const useBlockchainLoadingActions = () => useBlockchainStore((state) => ({
  setLoadingBlocks: state.setLoadingBlocks,
  setLoadingStats: state.setLoadingStats,
  setLoadingAnchoringQueue: state.setLoadingAnchoringQueue,
  setLoadingConsensusInfo: state.setLoadingConsensusInfo,
  setLoadingBlockDetails: state.setLoadingBlockDetails,
  setLoadingTransactions: state.setLoadingTransactions,
}));

export const useBlockchainErrorActions = () => useBlockchainStore((state) => ({
  setBlocksError: state.setBlocksError,
  setStatsError: state.setStatsError,
  setAnchoringQueueError: state.setAnchoringQueueError,
  setConsensusError: state.setConsensusError,
  setBlockDetailsError: state.setBlockDetailsError,
  setTransactionsError: state.setTransactionsError,
  clearErrors: state.clearErrors,
}));

export const useBlockchainViewActions = () => useBlockchainStore((state) => ({
  setViewMode: state.setViewMode,
  setColumnVisible: state.setColumnVisible,
  setColumnsVisible: state.setColumnsVisible,
}));

export const useNetworkMonitoringActions = () => useBlockchainStore((state) => ({
  setNetworkMonitoring: state.setNetworkMonitoring,
  toggleNetworkMonitoring: state.toggleNetworkMonitoring,
}));

// Computed selectors
export const useFilteredBlocks = () => {
  const blocks = useBlocks();
  const filters = useBlockchainFilters();
  
  let filtered = [...blocks];
  
  if (filters.blockHeight !== undefined) {
    filtered = filtered.filter(block => block.height === filters.blockHeight);
  }
  
  if (filters.transactionType) {
    filtered = filtered.filter(block => 
      block.transactions.some(tx => tx.type === filters.transactionType)
    );
  }
  
  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(block => 
      block.block_id.toLowerCase().includes(query) ||
      block.merkle_root.toLowerCase().includes(query) ||
      block.previous_hash.toLowerCase().includes(query)
    );
  }
  
  if (filters.dateRange) {
    filtered = filtered.filter(block => {
      const blockDate = new Date(block.timestamp);
      return blockDate >= filters.dateRange!.start && blockDate <= filters.dateRange!.end;
    });
  }
  
  // Sort
  if (filters.sortBy) {
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (filters.sortBy) {
        case 'height':
          aValue = a.height;
          bValue = b.height;
          break;
        case 'timestamp':
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
          break;
        case 'transaction_count':
          aValue = a.transactions.length;
          bValue = b.transactions.length;
          break;
        default:
          return 0;
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

export const usePaginatedBlocks = () => {
  const filteredBlocks = useFilteredBlocks();
  const { currentPage, pageSize } = useBlockchainPagination();
  
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  
  return {
    blocks: filteredBlocks.slice(startIndex, endIndex),
    totalCount: filteredBlocks.length,
    hasNextPage: endIndex < filteredBlocks.length,
    hasPreviousPage: currentPage > 1,
  };
};

export const useAnchoringQueueByPriority = (priority: AnchoringQueueItem['priority']) => {
  const queue = useAnchoringQueue();
  return queue.filter(item => item.priority === priority);
};

export const usePendingAnchoringItems = () => {
  const queue = useAnchoringQueue();
  return queue.filter(item => item.status === 'pending');
};

export const useProcessingAnchoringItems = () => {
  const queue = useAnchoringQueue();
  return queue.filter(item => item.status === 'processing');
};

export const useSelectedQueueItemsCount = () => {
  const selectedItems = useSelectedQueueItems();
  return selectedItems.length;
};

export const useCanPerformAnchoringOperation = () => {
  const selectedItems = useSelectedQueueItems();
  const anchoringOperation = useAnchoringOperation();
  return selectedItems.length > 0 && !anchoringOperation.isProcessing;
};

export const useConsensusStatus = () => {
  const consensusInfo = useConsensusInfo();
  const participationRate = consensusInfo.totalNodes > 0 
    ? consensusInfo.participatingNodes / consensusInfo.totalNodes 
    : 0;
  
  return {
    status: consensusInfo.consensusStatus,
    participationRate,
    isActive: consensusInfo.consensusStatus === 'active',
    hasConsensus: participationRate >= consensusInfo.consensusThreshold,
  };
};

export const useBlockchainHealth = () => {
  const stats = useBlockchainStats();
  const consensusStatus = useConsensusStatus();
  
  const isHealthy = stats.averageBlockTime > 0 && 
                   stats.averageBlockTime < 60 && // Less than 1 minute
                   consensusStatus.hasConsensus;
  
  return {
    isHealthy,
    status: isHealthy ? 'healthy' : 'degraded',
    issues: [
      ...(stats.averageBlockTime > 60 ? ['Slow block times'] : []),
      ...(!consensusStatus.hasConsensus ? ['Consensus issues'] : []),
    ],
  };
};

export const useTransactionsByType = () => {
  const stats = useBlockchainStats();
  return stats.byTransactionType;
};

export const useNetworkMetrics = () => {
  const stats = useBlockchainStats();
  return {
    hashRate: stats.networkHashRate,
    difficulty: stats.difficulty,
    averageBlockTime: stats.averageBlockTime,
    blocksPerHour: stats.blocksPerHour,
    transactionsPerBlock: stats.transactionsPerBlock,
  };
};

export default useBlockchainStore;
