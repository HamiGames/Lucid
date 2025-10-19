// uiStore.ts - UI state management (modals, loading, etc.)
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Modal types
type ModalType = 
  | 'sessionDetails'
  | 'userDetails'
  | 'createUser'
  | 'nodeDetails'
  | 'addNode'
  | 'anchoring'
  | 'blockDetails'
  | 'bulkActions'
  | 'configBackup'
  | 'emergencyControl'
  | 'auditExport'
  | 'confirmation'
  | 'error'
  | 'success'
  | 'info';

// Toast notification interface
interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number; // in milliseconds, 0 = persistent
  actions?: Array<{
    label: string;
    action: () => void;
    style?: 'primary' | 'secondary' | 'danger';
  }>;
  timestamp: Date;
  read: boolean;
}

// Loading state interface
interface LoadingState {
  id: string;
  message: string;
  progress?: number;
  cancellable: boolean;
  onCancel?: () => void;
}

// Modal state interface
interface ModalState {
  type: ModalType | null;
  isOpen: boolean;
  data: any;
  options: {
    closable: boolean;
    size: 'small' | 'medium' | 'large' | 'fullscreen';
    position: 'center' | 'top' | 'bottom';
  };
}

// Sidebar state interface
interface SidebarState {
  isCollapsed: boolean;
  activeItem: string | null;
  expandedItems: string[];
}

// Theme interface
interface ThemeState {
  mode: 'light' | 'dark' | 'system';
  primaryColor: string;
  accentColor: string;
  customCSS: string;
}

// Layout interface
interface LayoutState {
  sidebarWidth: number;
  headerHeight: number;
  footerHeight: number;
  contentPadding: number;
  gridColumns: number;
  gridGap: number;
}

interface UIState {
  // Modal state
  modal: ModalState;
  
  // Toast notifications
  toasts: ToastNotification[];
  
  // Loading states
  loadingStates: LoadingState[];
  
  // Sidebar state
  sidebar: SidebarState;
  
  // Theme state
  theme: ThemeState;
  
  // Layout state
  layout: LayoutState;
  
  // UI settings
  settings: {
    animations: boolean;
    transitions: boolean;
    soundEffects: boolean;
    hapticFeedback: boolean;
    reducedMotion: boolean;
    highContrast: boolean;
    fontSize: 'small' | 'medium' | 'large';
    density: 'compact' | 'comfortable' | 'spacious';
  };
  
  // Viewport state
  viewport: {
    width: number;
    height: number;
    isMobile: boolean;
    isTablet: boolean;
    isDesktop: boolean;
    orientation: 'portrait' | 'landscape';
  };
  
  // Keyboard shortcuts
  shortcuts: {
    enabled: boolean;
    custom: Record<string, string>;
  };
  
  // Accessibility
  accessibility: {
    screenReader: boolean;
    keyboardNavigation: boolean;
    focusVisible: boolean;
    ariaLabels: boolean;
  };
  
  // Error boundaries
  errors: Array<{
    id: string;
    error: Error;
    componentStack: string;
    timestamp: Date;
    resolved: boolean;
  }>;
}

interface UIActions {
  // Modal actions
  openModal: (type: ModalType, data?: any, options?: Partial<ModalState['options']>) => void;
  closeModal: () => void;
  updateModalData: (data: any) => void;
  
  // Toast actions
  addToast: (toast: Omit<ToastNotification, 'id' | 'timestamp' | 'read'>) => void;
  removeToast: (id: string) => void;
  markToastRead: (id: string) => void;
  clearAllToasts: () => void;
  
  // Loading actions
  addLoadingState: (loading: Omit<LoadingState, 'id'>) => string;
  removeLoadingState: (id: string) => void;
  updateLoadingProgress: (id: string, progress: number) => void;
  clearAllLoadingStates: () => void;
  
  // Sidebar actions
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveSidebarItem: (item: string | null) => void;
  toggleSidebarItem: (item: string) => void;
  setExpandedSidebarItems: (items: string[]) => void;
  
  // Theme actions
  setThemeMode: (mode: ThemeState['mode']) => void;
  setPrimaryColor: (color: string) => void;
  setAccentColor: (color: string) => void;
  setCustomCSS: (css: string) => void;
  
  // Layout actions
  setSidebarWidth: (width: number) => void;
  setHeaderHeight: (height: number) => void;
  setFooterHeight: (height: number) => void;
  setContentPadding: (padding: number) => void;
  setGridColumns: (columns: number) => void;
  setGridGap: (gap: number) => void;
  
  // Settings actions
  updateSettings: (settings: Partial<UIState['settings']>) => void;
  resetSettings: () => void;
  
  // Viewport actions
  setViewport: (viewport: Partial<UIState['viewport']>) => void;
  updateViewport: () => void;
  
  // Keyboard shortcuts actions
  setShortcutsEnabled: (enabled: boolean) => void;
  setCustomShortcut: (key: string, shortcut: string) => void;
  removeCustomShortcut: (key: string) => void;
  
  // Accessibility actions
  updateAccessibility: (accessibility: Partial<UIState['accessibility']>) => void;
  
  // Error actions
  addError: (error: Error, componentStack: string) => void;
  resolveError: (id: string) => void;
  clearErrors: () => void;
  
  // Utility actions
  reset: () => void;
  exportSettings: () => string;
  importSettings: (settings: string) => void;
}

// Initial state
const initialState: UIState = {
  // Modal state
  modal: {
    type: null,
    isOpen: false,
    data: null,
    options: {
      closable: true,
      size: 'medium',
      position: 'center',
    },
  },
  
  // Toast notifications
  toasts: [],
  
  // Loading states
  loadingStates: [],
  
  // Sidebar state
  sidebar: {
    isCollapsed: false,
    activeItem: null,
    expandedItems: [],
  },
  
  // Theme state
  theme: {
    mode: 'system',
    primaryColor: '#3b82f6',
    accentColor: '#10b981',
    customCSS: '',
  },
  
  // Layout state
  layout: {
    sidebarWidth: 256,
    headerHeight: 64,
    footerHeight: 48,
    contentPadding: 24,
    gridColumns: 12,
    gridGap: 16,
  },
  
  // UI settings
  settings: {
    animations: true,
    transitions: true,
    soundEffects: false,
    hapticFeedback: false,
    reducedMotion: false,
    highContrast: false,
    fontSize: 'medium',
    density: 'comfortable',
  },
  
  // Viewport state
  viewport: {
    width: 1920,
    height: 1080,
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    orientation: 'landscape',
  },
  
  // Keyboard shortcuts
  shortcuts: {
    enabled: true,
    custom: {
      'toggleSidebar': 'Ctrl+B',
      'openSearch': 'Ctrl+K',
      'closeModal': 'Escape',
      'refreshData': 'F5',
    },
  },
  
  // Accessibility
  accessibility: {
    screenReader: false,
    keyboardNavigation: true,
    focusVisible: true,
    ariaLabels: true,
  },
  
  // Error boundaries
  errors: [],
};

// Create the UI store
export const useUIStore = create<UIState & UIActions>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Modal actions
      openModal: (type, data = null, options = {}) => set((state) => ({
        modal: {
          type,
          isOpen: true,
          data,
          options: {
            ...state.modal.options,
            ...options,
          },
        }
      })),
      closeModal: () => set((state) => ({
        modal: {
          ...state.modal,
          isOpen: false,
          type: null,
          data: null,
        }
      })),
      updateModalData: (data) => set((state) => ({
        modal: { ...state.modal, data }
      })),
      
      // Toast actions
      addToast: (toast) => set((state) => ({
        toasts: [
          ...state.toasts,
          {
            ...toast,
            id: Math.random().toString(36).substring(2, 9),
            timestamp: new Date(),
            read: false,
          }
        ]
      })),
      removeToast: (id) => set((state) => ({
        toasts: state.toasts.filter(toast => toast.id !== id)
      })),
      markToastRead: (id) => set((state) => ({
        toasts: state.toasts.map(toast =>
          toast.id === id ? { ...toast, read: true } : toast
        )
      })),
      clearAllToasts: () => set({ toasts: [] }),
      
      // Loading actions
      addLoadingState: (loading) => {
        const id = Math.random().toString(36).substring(2, 9);
        set((state) => ({
          loadingStates: [...state.loadingStates, { ...loading, id }]
        }));
        return id;
      },
      removeLoadingState: (id) => set((state) => ({
        loadingStates: state.loadingStates.filter(loading => loading.id !== id)
      })),
      updateLoadingProgress: (id, progress) => set((state) => ({
        loadingStates: state.loadingStates.map(loading =>
          loading.id === id ? { ...loading, progress } : loading
        )
      })),
      clearAllLoadingStates: () => set({ loadingStates: [] }),
      
      // Sidebar actions
      setSidebarCollapsed: (collapsed) => set((state) => ({
        sidebar: { ...state.sidebar, isCollapsed: collapsed }
      })),
      setActiveSidebarItem: (item) => set((state) => ({
        sidebar: { ...state.sidebar, activeItem: item }
      })),
      toggleSidebarItem: (item) => set((state) => ({
        sidebar: {
          ...state.sidebar,
          expandedItems: state.sidebar.expandedItems.includes(item)
            ? state.sidebar.expandedItems.filter(i => i !== item)
            : [...state.sidebar.expandedItems, item]
        }
      })),
      setExpandedSidebarItems: (items) => set((state) => ({
        sidebar: { ...state.sidebar, expandedItems: items }
      })),
      
      // Theme actions
      setThemeMode: (mode) => set((state) => ({
        theme: { ...state.theme, mode }
      })),
      setPrimaryColor: (color) => set((state) => ({
        theme: { ...state.theme, primaryColor: color }
      })),
      setAccentColor: (color) => set((state) => ({
        theme: { ...state.theme, accentColor: color }
      })),
      setCustomCSS: (css) => set((state) => ({
        theme: { ...state.theme, customCSS: css }
      })),
      
      // Layout actions
      setSidebarWidth: (width) => set((state) => ({
        layout: { ...state.layout, sidebarWidth: width }
      })),
      setHeaderHeight: (height) => set((state) => ({
        layout: { ...state.layout, headerHeight: height }
      })),
      setFooterHeight: (height) => set((state) => ({
        layout: { ...state.layout, footerHeight: height }
      })),
      setContentPadding: (padding) => set((state) => ({
        layout: { ...state.layout, contentPadding: padding }
      })),
      setGridColumns: (columns) => set((state) => ({
        layout: { ...state.layout, gridColumns: columns }
      })),
      setGridGap: (gap) => set((state) => ({
        layout: { ...state.layout, gridGap: gap }
      })),
      
      // Settings actions
      updateSettings: (settings) => set((state) => ({
        settings: { ...state.settings, ...settings }
      })),
      resetSettings: () => set({ settings: initialState.settings }),
      
      // Viewport actions
      setViewport: (viewport) => set((state) => ({
        viewport: { ...state.viewport, ...viewport }
      })),
      updateViewport: () => {
        const width = window.innerWidth;
        const height = window.innerHeight;
        const isMobile = width < 768;
        const isTablet = width >= 768 && width < 1024;
        const isDesktop = width >= 1024;
        const orientation = height > width ? 'portrait' : 'landscape';
        
        set((state) => ({
          viewport: {
            ...state.viewport,
            width,
            height,
            isMobile,
            isTablet,
            isDesktop,
            orientation,
          }
        }));
      },
      
      // Keyboard shortcuts actions
      setShortcutsEnabled: (enabled) => set((state) => ({
        shortcuts: { ...state.shortcuts, enabled }
      })),
      setCustomShortcut: (key, shortcut) => set((state) => ({
        shortcuts: {
          ...state.shortcuts,
          custom: { ...state.shortcuts.custom, [key]: shortcut }
        }
      })),
      removeCustomShortcut: (key) => set((state) => {
        const { [key]: removed, ...custom } = state.shortcuts.custom;
        return {
          shortcuts: { ...state.shortcuts, custom }
        };
      }),
      
      // Accessibility actions
      updateAccessibility: (accessibility) => set((state) => ({
        accessibility: { ...state.accessibility, ...accessibility }
      })),
      
      // Error actions
      addError: (error, componentStack) => set((state) => ({
        errors: [
          ...state.errors,
          {
            id: Math.random().toString(36).substring(2, 9),
            error,
            componentStack,
            timestamp: new Date(),
            resolved: false,
          }
        ]
      })),
      resolveError: (id) => set((state) => ({
        errors: state.errors.map(err =>
          err.id === id ? { ...err, resolved: true } : err
        )
      })),
      clearErrors: () => set({ errors: [] }),
      
      // Utility actions
      reset: () => set(initialState),
      exportSettings: () => {
        const state = get();
        return JSON.stringify({
          theme: state.theme,
          layout: state.layout,
          settings: state.settings,
          shortcuts: state.shortcuts,
          accessibility: state.accessibility,
        });
      },
      importSettings: (settingsJson) => {
        try {
          const settings = JSON.parse(settingsJson);
          set((state) => ({
            theme: { ...state.theme, ...settings.theme },
            layout: { ...state.layout, ...settings.layout },
            settings: { ...state.settings, ...settings.settings },
            shortcuts: { ...state.shortcuts, ...settings.shortcuts },
            accessibility: { ...state.accessibility, ...settings.accessibility },
          }));
        } catch (error) {
          console.error('Failed to import settings:', error);
        }
      },
    }),
    {
      name: 'lucid-admin-ui-store',
    }
  )
);

// Selectors for UI state access
export const useModal = () => useUIStore((state) => state.modal);
export const useToasts = () => useUIStore((state) => state.toasts);
export const useLoadingStates = () => useUIStore((state) => state.loadingStates);
export const useSidebar = () => useUIStore((state) => state.sidebar);
export const useTheme = () => useUIStore((state) => state.theme);
export const useLayout = () => useUIStore((state) => state.layout);
export const useUISettings = () => useUIStore((state) => state.settings);
export const useViewport = () => useUIStore((state) => state.viewport);
export const useShortcuts = () => useUIStore((state) => state.shortcuts);
export const useAccessibility = () => useUIStore((state) => state.accessibility);
export const useErrors = () => useUIStore((state) => state.errors);

// Action selectors
export const useModalActions = () => useUIStore((state) => ({
  openModal: state.openModal,
  closeModal: state.closeModal,
  updateModalData: state.updateModalData,
}));

export const useToastActions = () => useUIStore((state) => ({
  addToast: state.addToast,
  removeToast: state.removeToast,
  markToastRead: state.markToastRead,
  clearAllToasts: state.clearAllToasts,
}));

export const useLoadingActions = () => useUIStore((state) => ({
  addLoadingState: state.addLoadingState,
  removeLoadingState: state.removeLoadingState,
  updateLoadingProgress: state.updateLoadingProgress,
  clearAllLoadingStates: state.clearAllLoadingStates,
}));

export const useSidebarActions = () => useUIStore((state) => ({
  setSidebarCollapsed: state.setSidebarCollapsed,
  setActiveSidebarItem: state.setActiveSidebarItem,
  toggleSidebarItem: state.toggleSidebarItem,
  setExpandedSidebarItems: state.setExpandedSidebarItems,
}));

export const useThemeActions = () => useUIStore((state) => ({
  setThemeMode: state.setThemeMode,
  setPrimaryColor: state.setPrimaryColor,
  setAccentColor: state.setAccentColor,
  setCustomCSS: state.setCustomCSS,
}));

export const useLayoutActions = () => useUIStore((state) => ({
  setSidebarWidth: state.setSidebarWidth,
  setHeaderHeight: state.setHeaderHeight,
  setFooterHeight: state.setFooterHeight,
  setContentPadding: state.setContentPadding,
  setGridColumns: state.setGridColumns,
  setGridGap: state.setGridGap,
}));

export const useSettingsActions = () => useUIStore((state) => ({
  updateSettings: state.updateSettings,
  resetSettings: state.resetSettings,
}));

export const useViewportActions = () => useUIStore((state) => ({
  setViewport: state.setViewport,
  updateViewport: state.updateViewport,
}));

export const useShortcutActions = () => useUIStore((state) => ({
  setShortcutsEnabled: state.setShortcutsEnabled,
  setCustomShortcut: state.setCustomShortcut,
  removeCustomShortcut: state.removeCustomShortcut,
}));

export const useAccessibilityActions = () => useUIStore((state) => ({
  updateAccessibility: state.updateAccessibility,
}));

export const useErrorActions = () => useUIStore((state) => ({
  addError: state.addError,
  resolveError: state.resolveError,
  clearErrors: state.clearErrors,
}));

export const useUIActions = () => useUIStore((state) => ({
  reset: state.reset,
  exportSettings: state.exportSettings,
  importSettings: state.importSettings,
}));

// Computed selectors
export const useIsModalOpen = () => {
  const modal = useModal();
  return modal.isOpen;
};

export const useModalType = () => {
  const modal = useModal();
  return modal.type;
};

export const useUnreadToasts = () => {
  const toasts = useToasts();
  return toasts.filter(toast => !toast.read);
};

export const useUnreadToastCount = () => {
  const unreadToasts = useUnreadToasts();
  return unreadToasts.length;
};

export const useActiveLoadingStates = () => {
  const loadingStates = useLoadingStates();
  return loadingStates;
};

export const useIsLoading = () => {
  const loadingStates = useLoadingStates();
  return loadingStates.length > 0;
};

export const useIsSidebarCollapsed = () => {
  const sidebar = useSidebar();
  return sidebar.isCollapsed;
};

export const useActiveSidebarItem = () => {
  const sidebar = useSidebar();
  return sidebar.activeItem;
};

export const useExpandedSidebarItems = () => {
  const sidebar = useSidebar();
  return sidebar.expandedItems;
};

export const useEffectiveTheme = () => {
  const theme = useTheme();
  const viewport = useViewport();
  
  if (theme.mode === 'system') {
    // In a real implementation, this would detect system preference
    return viewport.isMobile ? 'light' : 'dark';
  }
  
  return theme.mode;
};

export const useResponsiveLayout = () => {
  const layout = useLayout();
  const viewport = useViewport();
  
  return {
    ...layout,
    isResponsive: viewport.isMobile || viewport.isTablet,
    sidebarWidth: viewport.isMobile ? 0 : layout.sidebarWidth,
    contentPadding: viewport.isMobile ? 16 : layout.contentPadding,
    gridColumns: viewport.isMobile ? 1 : viewport.isTablet ? 6 : layout.gridColumns,
  };
};

export const useUnresolvedErrors = () => {
  const errors = useErrors();
  return errors.filter(error => !error.resolved);
};

export const useErrorCount = () => {
  const unresolvedErrors = useUnresolvedErrors();
  return unresolvedErrors.length;
};

export const useIsAccessible = () => {
  const accessibility = useAccessibility();
  return accessibility.screenReader || accessibility.keyboardNavigation;
};

export const useEffectiveSettings = () => {
  const settings = useUISettings();
  const accessibility = useAccessibility();
  
  return {
    ...settings,
    animations: settings.animations && !settings.reducedMotion,
    transitions: settings.transitions && !settings.reducedMotion,
    soundEffects: settings.soundEffects && !accessibility.screenReader,
  };
};

// Hook for managing modal state
export const useModalManager = () => {
  const modal = useModal();
  const { openModal, closeModal, updateModalData } = useModalActions();
  
  return {
    ...modal,
    open: openModal,
    close: closeModal,
    updateData: updateModalData,
  };
};

// Hook for managing toast notifications
export const useToastManager = () => {
  const toasts = useToasts();
  const { addToast, removeToast, markToastRead, clearAllToasts } = useToastActions();
  
  const showSuccess = (title: string, message?: string, duration?: number) => {
    addToast({ type: 'success', title, message, duration });
  };
  
  const showError = (title: string, message?: string, duration?: number) => {
    addToast({ type: 'error', title, message, duration });
  };
  
  const showWarning = (title: string, message?: string, duration?: number) => {
    addToast({ type: 'warning', title, message, duration });
  };
  
  const showInfo = (title: string, message?: string, duration?: number) => {
    addToast({ type: 'info', title, message, duration });
  };
  
  return {
    toasts,
    addToast,
    removeToast,
    markToastRead,
    clearAllToasts,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
};

// Hook for managing loading states
export const useLoadingManager = () => {
  const loadingStates = useLoadingStates();
  const { addLoadingState, removeLoadingState, updateLoadingProgress, clearAllLoadingStates } = useLoadingActions();
  
  const startLoading = (message: string, cancellable = false, onCancel?: () => void) => {
    return addLoadingState({ message, cancellable, onCancel });
  };
  
  const stopLoading = (id: string) => {
    removeLoadingState(id);
  };
  
  const updateProgress = (id: string, progress: number) => {
    updateLoadingProgress(id, progress);
  };
  
  return {
    loadingStates,
    isLoading: loadingStates.length > 0,
    startLoading,
    stopLoading,
    updateProgress,
    clearAll: clearAllLoadingStates,
  };
};

export default useUIStore;
