// usersStore.ts - Users data state management
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { User, HardwareWallet } from '../../../shared/types';

// User filter interface
interface UserFilter {
  role?: User['role'];
  status?: 'active' | 'suspended' | 'pending' | 'inactive';
  dateRange?: {
    start: Date;
    end: Date;
  };
  searchQuery?: string;
  sortBy?: 'created_at' | 'email' | 'role' | 'status';
  sortOrder?: 'asc' | 'desc';
}

// User statistics interface
interface UserStats {
  total: number;
  active: number;
  suspended: number;
  pending: number;
  inactive: number;
  byRole: {
    user: number;
    node_operator: number;
    admin: number;
    super_admin: number;
  };
  withHardwareWallet: number;
  averageSessionsPerUser: number;
  newUsersThisMonth: number;
  newUsersThisWeek: number;
  newUsersToday: number;
}

// User bulk operation interface
interface UserBulkOperation {
  type: 'suspend' | 'activate' | 'delete' | 'export' | 'assign_role' | null;
  selectedIds: string[];
  isProcessing: boolean;
  progress: number;
  error: string | null;
  metadata?: {
    role?: User['role'];
    suspensionReason?: string;
    suspensionDuration?: number; // in days
  };
}

// User creation/editing interface
interface UserFormData {
  email: string;
  role: User['role'];
  tron_address: string;
  hardware_wallet?: {
    type: HardwareWallet['type'];
    device_id: string;
    public_key: string;
  };
  status: 'active' | 'suspended' | 'pending' | 'inactive';
  metadata?: Record<string, any>;
}

interface UsersState {
  // Core data
  users: User[];
  selectedUsers: string[];
  
  // Pagination
  currentPage: number;
  pageSize: number;
  totalPages: number;
  totalCount: number;
  
  // Filtering and sorting
  filters: UserFilter;
  
  // Statistics
  stats: UserStats;
  
  // Bulk operations
  bulkOperation: UserBulkOperation;
  
  // User details
  selectedUser: User | null;
  
  // User creation/editing
  isCreatingUser: boolean;
  isEditingUser: boolean;
  userFormData: UserFormData | null;
  userFormErrors: Record<string, string>;
  
  // User suspension
  suspensionModal: {
    isOpen: boolean;
    userId: string | null;
    reason: string;
    duration: number; // in days
  };
  
  // Loading states
  isLoadingUsers: boolean;
  isLoadingStats: boolean;
  isLoadingUserDetails: boolean;
  isCreating: boolean;
  isUpdating: boolean;
  isDeleting: boolean;
  
  // Error states
  usersError: string | null;
  statsError: string | null;
  userDetailsError: string | null;
  createError: string | null;
  updateError: string | null;
  deleteError: string | null;
  
  // Real-time updates
  lastUpdated: Date | null;
  isLive: boolean;
  
  // View settings
  viewMode: 'table' | 'cards' | 'grid';
  columnsVisible: Record<string, boolean>;
  
  // Export settings
  exportSettings: {
    format: 'json' | 'csv' | 'xml';
    includeSensitiveData: boolean;
    includeHardwareWallet: boolean;
    includeMetadata: boolean;
  };
}

interface UsersActions {
  // Core data actions
  setUsers: (users: User[]) => void;
  addUser: (user: User) => void;
  updateUser: (userId: string, updates: Partial<User>) => void;
  removeUser: (userId: string) => void;
  removeUsers: (userIds: string[]) => void;
  
  // Selection actions
  setSelectedUsers: (userIds: string[]) => void;
  toggleUserSelection: (userId: string) => void;
  selectAllUsers: () => void;
  clearSelection: () => void;
  
  // Pagination actions
  setCurrentPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTotalPages: (pages: number) => void;
  setTotalCount: (count: number) => void;
  goToNextPage: () => void;
  goToPreviousPage: () => void;
  
  // Filtering and sorting actions
  setFilters: (filters: Partial<UserFilter>) => void;
  clearFilters: () => void;
  setSearchQuery: (query: string) => void;
  setSorting: (sortBy: UserFilter['sortBy'], sortOrder: UserFilter['sortOrder']) => void;
  
  // Statistics actions
  setStats: (stats: UserStats) => void;
  updateStats: (updates: Partial<UserStats>) => void;
  
  // Bulk operation actions
  setBulkOperation: (operation: UserBulkOperation) => void;
  startBulkOperation: (type: UserBulkOperation['type'], userIds: string[], metadata?: UserBulkOperation['metadata']) => void;
  updateBulkProgress: (progress: number) => void;
  setBulkError: (error: string | null) => void;
  completeBulkOperation: () => void;
  
  // User details actions
  setSelectedUser: (user: User | null) => void;
  
  // User creation/editing actions
  setIsCreatingUser: (isCreating: boolean) => void;
  setIsEditingUser: (isEditing: boolean) => void;
  setUserFormData: (data: UserFormData | null) => void;
  setUserFormErrors: (errors: Record<string, string>) => void;
  clearUserForm: () => void;
  
  // User suspension actions
  setSuspensionModal: (modal: UsersState['suspensionModal']) => void;
  openSuspensionModal: (userId: string) => void;
  closeSuspensionModal: () => void;
  
  // Loading actions
  setLoadingUsers: (loading: boolean) => void;
  setLoadingStats: (loading: boolean) => void;
  setLoadingUserDetails: (loading: boolean) => void;
  setCreating: (creating: boolean) => void;
  setUpdating: (updating: boolean) => void;
  setDeleting: (deleting: boolean) => void;
  
  // Error actions
  setUsersError: (error: string | null) => void;
  setStatsError: (error: string | null) => void;
  setUserDetailsError: (error: string | null) => void;
  setCreateError: (error: string | null) => void;
  setUpdateError: (error: string | null) => void;
  setDeleteError: (error: string | null) => void;
  clearErrors: () => void;
  
  // Real-time actions
  setLastUpdated: (date: Date) => void;
  setIsLive: (isLive: boolean) => void;
  
  // View actions
  setViewMode: (mode: UsersState['viewMode']) => void;
  setColumnVisible: (column: string, visible: boolean) => void;
  setColumnsVisible: (columns: Record<string, boolean>) => void;
  
  // Export actions
  setExportSettings: (settings: Partial<UsersState['exportSettings']>) => void;
  
  // Utility actions
  reset: () => void;
  refreshData: () => void;
}

// Initial state
const initialState: UsersState = {
  // Core data
  users: [],
  selectedUsers: [],
  
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
    suspended: 0,
    pending: 0,
    inactive: 0,
    byRole: {
      user: 0,
      node_operator: 0,
      admin: 0,
      super_admin: 0,
    },
    withHardwareWallet: 0,
    averageSessionsPerUser: 0,
    newUsersThisMonth: 0,
    newUsersThisWeek: 0,
    newUsersToday: 0,
  },
  
  // Bulk operations
  bulkOperation: {
    type: null,
    selectedIds: [],
    isProcessing: false,
    progress: 0,
    error: null,
  },
  
  // User details
  selectedUser: null,
  
  // User creation/editing
  isCreatingUser: false,
  isEditingUser: false,
  userFormData: null,
  userFormErrors: {},
  
  // User suspension
  suspensionModal: {
    isOpen: false,
    userId: null,
    reason: '',
    duration: 30, // 30 days default
  },
  
  // Loading states
  isLoadingUsers: false,
  isLoadingStats: false,
  isLoadingUserDetails: false,
  isCreating: false,
  isUpdating: false,
  isDeleting: false,
  
  // Error states
  usersError: null,
  statsError: null,
  userDetailsError: null,
  createError: null,
  updateError: null,
  deleteError: null,
  
  // Real-time updates
  lastUpdated: null,
  isLive: false,
  
  // View settings
  viewMode: 'table',
  columnsVisible: {
    user_id: true,
    email: true,
    role: true,
    tron_address: true,
    hardware_wallet: true,
    created_at: true,
    status: true,
  },
  
  // Export settings
  exportSettings: {
    format: 'json',
    includeSensitiveData: false,
    includeHardwareWallet: true,
    includeMetadata: true,
  },
};

// Create the users store
export const useUsersStore = create<UsersState & UsersActions>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Core data actions
      setUsers: (users) => set({ users }),
      addUser: (user) => set((state) => ({
        users: [user, ...state.users]
      })),
      updateUser: (userId, updates) => set((state) => ({
        users: state.users.map(user =>
          user.user_id === userId ? { ...user, ...updates } : user
        )
      })),
      removeUser: (userId) => set((state) => ({
        users: state.users.filter(user => user.user_id !== userId),
        selectedUsers: state.selectedUsers.filter(id => id !== userId),
      })),
      removeUsers: (userIds) => set((state) => ({
        users: state.users.filter(user => !userIds.includes(user.user_id)),
        selectedUsers: state.selectedUsers.filter(id => !userIds.includes(id)),
      })),
      
      // Selection actions
      setSelectedUsers: (userIds) => set({ selectedUsers: userIds }),
      toggleUserSelection: (userId) => set((state) => ({
        selectedUsers: state.selectedUsers.includes(userId)
          ? state.selectedUsers.filter(id => id !== userId)
          : [...state.selectedUsers, userId]
      })),
      selectAllUsers: () => set((state) => ({
        selectedUsers: state.users.map(user => user.user_id)
      })),
      clearSelection: () => set({ selectedUsers: [] }),
      
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
      startBulkOperation: (type, userIds, metadata) => set({
        bulkOperation: {
          type,
          selectedIds: userIds,
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
      
      // User details actions
      setSelectedUser: (user) => set({ selectedUser: user }),
      
      // User creation/editing actions
      setIsCreatingUser: (isCreating) => set({ isCreatingUser: isCreating }),
      setIsEditingUser: (isEditing) => set({ isEditingUser: isEditing }),
      setUserFormData: (data) => set({ userFormData: data }),
      setUserFormErrors: (errors) => set({ userFormErrors: errors }),
      clearUserForm: () => set({
        userFormData: null,
        userFormErrors: {},
        isCreatingUser: false,
        isEditingUser: false,
      }),
      
      // User suspension actions
      setSuspensionModal: (modal) => set({ suspensionModal: modal }),
      openSuspensionModal: (userId) => set({
        suspensionModal: {
          isOpen: true,
          userId,
          reason: '',
          duration: 30,
        }
      }),
      closeSuspensionModal: () => set({
        suspensionModal: {
          isOpen: false,
          userId: null,
          reason: '',
          duration: 30,
        }
      }),
      
      // Loading actions
      setLoadingUsers: (loading) => set({ isLoadingUsers: loading }),
      setLoadingStats: (loading) => set({ isLoadingStats: loading }),
      setLoadingUserDetails: (loading) => set({ isLoadingUserDetails: loading }),
      setCreating: (creating) => set({ isCreating: creating }),
      setUpdating: (updating) => set({ isUpdating: updating }),
      setDeleting: (deleting) => set({ isDeleting: deleting }),
      
      // Error actions
      setUsersError: (error) => set({ usersError: error }),
      setStatsError: (error) => set({ statsError: error }),
      setUserDetailsError: (error) => set({ userDetailsError: error }),
      setCreateError: (error) => set({ createError: error }),
      setUpdateError: (error) => set({ updateError: error }),
      setDeleteError: (error) => set({ deleteError: error }),
      clearErrors: () => set({
        usersError: null,
        statsError: null,
        userDetailsError: null,
        createError: null,
        updateError: null,
        deleteError: null,
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
      
      // Export actions
      setExportSettings: (settings) => set((state) => ({
        exportSettings: { ...state.exportSettings, ...settings }
      })),
      
      // Utility actions
      reset: () => set(initialState),
      refreshData: () => set({
        isLoadingUsers: true,
        isLoadingStats: true,
        lastUpdated: new Date(),
      }),
    }),
    {
      name: 'lucid-admin-users-store',
    }
  )
);

// Selectors for users state access
export const useUsers = () => useUsersStore((state) => state.users);
export const useSelectedUsers = () => useUsersStore((state) => state.selectedUsers);
export const useUserPagination = () => useUsersStore((state) => ({
  currentPage: state.currentPage,
  pageSize: state.pageSize,
  totalPages: state.totalPages,
  totalCount: state.totalCount,
}));

export const useUserFilters = () => useUsersStore((state) => state.filters);
export const useUserStats = () => useUsersStore((state) => state.stats);

export const useUserBulkOperation = () => useUsersStore((state) => state.bulkOperation);
export const useSelectedUser = () => useUsersStore((state) => state.selectedUser);

export const useUserForm = () => useUsersStore((state) => ({
  isCreatingUser: state.isCreatingUser,
  isEditingUser: state.isEditingUser,
  userFormData: state.userFormData,
  userFormErrors: state.userFormErrors,
}));

export const useSuspensionModal = () => useUsersStore((state) => state.suspensionModal);

export const useUsersLoading = () => useUsersStore((state) => ({
  isLoadingUsers: state.isLoadingUsers,
  isLoadingStats: state.isLoadingStats,
  isLoadingUserDetails: state.isLoadingUserDetails,
  isCreating: state.isCreating,
  isUpdating: state.isUpdating,
  isDeleting: state.isDeleting,
  isLoading: state.isLoadingUsers || state.isLoadingStats || 
             state.isLoadingUserDetails || state.isCreating || 
             state.isUpdating || state.isDeleting,
}));

export const useUsersErrors = () => useUsersStore((state) => ({
  usersError: state.usersError,
  statsError: state.statsError,
  userDetailsError: state.userDetailsError,
  createError: state.createError,
  updateError: state.updateError,
  deleteError: state.deleteError,
  hasErrors: !!(state.usersError || state.statsError || state.userDetailsError || 
                state.createError || state.updateError || state.deleteError),
}));

export const useUsersRealTime = () => useUsersStore((state) => ({
  lastUpdated: state.lastUpdated,
  isLive: state.isLive,
  timeSinceUpdate: state.lastUpdated ? Date.now() - state.lastUpdated.getTime() : 0,
}));

export const useUsersView = () => useUsersStore((state) => ({
  viewMode: state.viewMode,
  columnsVisible: state.columnsVisible,
}));

export const useExportSettings = () => useUsersStore((state) => state.exportSettings);

// Action selectors
export const useUsersActions = () => useUsersStore((state) => ({
  setUsers: state.setUsers,
  addUser: state.addUser,
  updateUser: state.updateUser,
  removeUser: state.removeUser,
  removeUsers: state.removeUsers,
  setSelectedUsers: state.setSelectedUsers,
  toggleUserSelection: state.toggleUserSelection,
  selectAllUsers: state.selectAllUsers,
  clearSelection: state.clearSelection,
  setFilters: state.setFilters,
  clearFilters: state.clearFilters,
  setSearchQuery: state.setSearchQuery,
  setSorting: state.setSorting,
  setStats: state.setStats,
  reset: state.reset,
  refreshData: state.refreshData,
}));

export const useUserPaginationActions = () => useUsersStore((state) => ({
  setCurrentPage: state.setCurrentPage,
  setPageSize: state.setPageSize,
  setTotalPages: state.setTotalPages,
  setTotalCount: state.setTotalCount,
  goToNextPage: state.goToNextPage,
  goToPreviousPage: state.goToPreviousPage,
}));

export const useUserBulkOperationActions = () => useUsersStore((state) => ({
  setBulkOperation: state.setBulkOperation,
  startBulkOperation: state.startBulkOperation,
  updateBulkProgress: state.updateBulkProgress,
  setBulkError: state.setBulkError,
  completeBulkOperation: state.completeBulkOperation,
}));

export const useUserFormActions = () => useUsersStore((state) => ({
  setIsCreatingUser: state.setIsCreatingUser,
  setIsEditingUser: state.setIsEditingUser,
  setUserFormData: state.setUserFormData,
  setUserFormErrors: state.setUserFormErrors,
  clearUserForm: state.clearUserForm,
}));

export const useSuspensionModalActions = () => useUsersStore((state) => ({
  setSuspensionModal: state.setSuspensionModal,
  openSuspensionModal: state.openSuspensionModal,
  closeSuspensionModal: state.closeSuspensionModal,
}));

export const useUsersLoadingActions = () => useUsersStore((state) => ({
  setLoadingUsers: state.setLoadingUsers,
  setLoadingStats: state.setLoadingStats,
  setLoadingUserDetails: state.setLoadingUserDetails,
  setCreating: state.setCreating,
  setUpdating: state.setUpdating,
  setDeleting: state.setDeleting,
}));

export const useUsersErrorActions = () => useUsersStore((state) => ({
  setUsersError: state.setUsersError,
  setStatsError: state.setStatsError,
  setUserDetailsError: state.setUserDetailsError,
  setCreateError: state.setCreateError,
  setUpdateError: state.setUpdateError,
  setDeleteError: state.setDeleteError,
  clearErrors: state.clearErrors,
}));

export const useUsersViewActions = () => useUsersStore((state) => ({
  setViewMode: state.setViewMode,
  setColumnVisible: state.setColumnVisible,
  setColumnsVisible: state.setColumnsVisible,
}));

export const useExportSettingsActions = () => useUsersStore((state) => ({
  setExportSettings: state.setExportSettings,
}));

// Computed selectors
export const useFilteredUsers = () => {
  const users = useUsers();
  const filters = useUserFilters();
  
  let filtered = [...users];
  
  if (filters.role) {
    filtered = filtered.filter(user => user.role === filters.role);
  }
  
  if (filters.status) {
    // Note: This assumes we have a status field on User, which might need to be added
    // filtered = filtered.filter(user => user.status === filters.status);
  }
  
  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(user => 
      user.email.toLowerCase().includes(query) ||
      user.user_id.toLowerCase().includes(query) ||
      user.role.toLowerCase().includes(query) ||
      user.tron_address.toLowerCase().includes(query)
    );
  }
  
  if (filters.dateRange) {
    filtered = filtered.filter(user => {
      const userDate = new Date(user.created_at);
      return userDate >= filters.dateRange!.start && userDate <= filters.dateRange!.end;
    });
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

export const usePaginatedUsers = () => {
  const filteredUsers = useFilteredUsers();
  const { currentPage, pageSize } = useUserPagination();
  
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  
  return {
    users: filteredUsers.slice(startIndex, endIndex),
    totalCount: filteredUsers.length,
    hasNextPage: endIndex < filteredUsers.length,
    hasPreviousPage: currentPage > 1,
  };
};

export const useUsersByRole = (role: User['role']) => {
  const users = useUsers();
  return users.filter(user => user.role === role);
};

export const useActiveUsers = () => {
  const users = useUsers();
  // Note: This assumes we have a status field on User
  // return users.filter(user => user.status === 'active');
  return users; // For now, return all users
};

export const useUsersWithHardwareWallet = () => {
  const users = useUsers();
  return users.filter(user => user.hardware_wallet);
};

export const useSelectedUsersCount = () => {
  const selectedUsers = useSelectedUsers();
  return selectedUsers.length;
};

export const useCanPerformBulkOperation = () => {
  const selectedUsers = useSelectedUsers();
  const bulkOperation = useUserBulkOperation();
  return selectedUsers.length > 0 && !bulkOperation.isProcessing;
};

export const useUsersByRoleStats = () => {
  const stats = useUserStats();
  return stats.byRole;
};

export const useNewUsersStats = () => {
  const stats = useUserStats();
  return {
    today: stats.newUsersToday,
    thisWeek: stats.newUsersThisWeek,
    thisMonth: stats.newUsersThisMonth,
  };
};

export default useUsersStore;
