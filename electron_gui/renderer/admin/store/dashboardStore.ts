// dashboardStore.ts - Dashboard data state management
// Based on the electron-multi-gui-development.plan.md specifications

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { SystemHealth, ServiceStatus } from '../../../shared/types';

// Dashboard metrics interfaces
interface DashboardMetrics {
  // System overview
  totalUsers: number;
  totalSessions: number;
  totalNodes: number;
  totalBlocks: number;
  
  // Active counts
  activeUsers: number;
  activeSessions: number;
  activeNodes: number;
  
  // Session metrics
  sessionsToday: number;
  sessionsThisWeek: number;
  sessionsThisMonth: number;
  averageSessionDuration: number; // in minutes
  
  // Node metrics
  nodeUptime: number; // average uptime percentage
  totalPootScore: number;
  averagePootScore: number;
  
  // Blockchain metrics
  blocksPerHour: number;
  averageBlockTime: number; // in seconds
  chainHeight: number;
  lastBlockTime: Date | null;
  
  // Storage metrics
  totalStorageUsed: number; // in bytes
  storageGrowthRate: number; // bytes per hour
  
  // Network metrics
  networkLatency: number; // in milliseconds
  bandwidthUsage: number; // in bytes per second
  torConnections: number;
}

interface ChartDataPoint {
  timestamp: Date;
  value: number;
  label?: string;
}

interface ChartData {
  id: string;
  title: string;
  type: 'line' | 'bar' | 'pie' | 'area';
  data: ChartDataPoint[];
  color?: string;
}

interface ActivityItem {
  id: string;
  type: 'user' | 'session' | 'node' | 'blockchain' | 'system';
  action: string;
  description: string;
  timestamp: Date;
  userId?: string;
  sessionId?: string;
  nodeId?: string;
  severity: 'info' | 'warning' | 'error' | 'success';
}

interface DashboardState {
  // Core metrics
  metrics: DashboardMetrics;
  
  // Chart data
  charts: ChartData[];
  
  // Activity feed
  activities: ActivityItem[];
  
  // System health
  systemHealth: SystemHealth | null;
  services: ServiceStatus[];
  
  // Real-time data
  lastUpdated: Date | null;
  isLive: boolean;
  
  // Loading states
  isLoadingMetrics: boolean;
  isLoadingCharts: boolean;
  isLoadingActivities: boolean;
  isLoadingSystemHealth: boolean;
  
  // Error states
  metricsError: string | null;
  chartsError: string | null;
  activitiesError: string | null;
  systemHealthError: string | null;
  
  // Refresh settings
  refreshInterval: number; // in milliseconds
  autoRefresh: boolean;
  
  // Filters
  timeRange: '1h' | '6h' | '24h' | '7d' | '30d' | 'custom';
  customTimeRange: {
    start: Date | null;
    end: Date | null;
  };
  
  // View settings
  selectedCharts: string[];
  chartView: 'grid' | 'list';
  activitiesLimit: number;
}

interface DashboardActions {
  // Metrics actions
  setMetrics: (metrics: DashboardMetrics) => void;
  updateMetric: (key: keyof DashboardMetrics, value: any) => void;
  
  // Chart actions
  setCharts: (charts: ChartData[]) => void;
  addChart: (chart: ChartData) => void;
  updateChart: (chartId: string, updates: Partial<ChartData>) => void;
  removeChart: (chartId: string) => void;
  
  // Activity actions
  setActivities: (activities: ActivityItem[]) => void;
  addActivity: (activity: ActivityItem) => void;
  updateActivity: (activityId: string, updates: Partial<ActivityItem>) => void;
  removeActivity: (activityId: string) => void;
  clearActivities: () => void;
  
  // System health actions
  setSystemHealth: (health: SystemHealth) => void;
  setServices: (services: ServiceStatus[]) => void;
  updateServiceStatus: (serviceName: string, status: ServiceStatus) => void;
  
  // Real-time actions
  setLastUpdated: (date: Date) => void;
  setIsLive: (isLive: boolean) => void;
  
  // Loading actions
  setLoadingMetrics: (loading: boolean) => void;
  setLoadingCharts: (loading: boolean) => void;
  setLoadingActivities: (loading: boolean) => void;
  setLoadingSystemHealth: (loading: boolean) => void;
  
  // Error actions
  setMetricsError: (error: string | null) => void;
  setChartsError: (error: string | null) => void;
  setActivitiesError: (error: string | null) => void;
  setSystemHealthError: (error: string | null) => void;
  clearErrors: () => void;
  
  // Refresh actions
  setRefreshInterval: (interval: number) => void;
  setAutoRefresh: (autoRefresh: boolean) => void;
  
  // Filter actions
  setTimeRange: (range: DashboardState['timeRange']) => void;
  setCustomTimeRange: (start: Date | null, end: Date | null) => void;
  
  // View actions
  setSelectedCharts: (chartIds: string[]) => void;
  setChartView: (view: 'grid' | 'list') => void;
  setActivitiesLimit: (limit: number) => void;
  
  // Utility actions
  reset: () => void;
  refreshAll: () => void;
}

// Initial state
const initialState: DashboardState = {
  // Core metrics
  metrics: {
    totalUsers: 0,
    totalSessions: 0,
    totalNodes: 0,
    totalBlocks: 0,
    activeUsers: 0,
    activeSessions: 0,
    activeNodes: 0,
    sessionsToday: 0,
    sessionsThisWeek: 0,
    sessionsThisMonth: 0,
    averageSessionDuration: 0,
    nodeUptime: 0,
    totalPootScore: 0,
    averagePootScore: 0,
    blocksPerHour: 0,
    averageBlockTime: 0,
    chainHeight: 0,
    lastBlockTime: null,
    totalStorageUsed: 0,
    storageGrowthRate: 0,
    networkLatency: 0,
    bandwidthUsage: 0,
    torConnections: 0,
  },
  
  // Chart data
  charts: [],
  
  // Activity feed
  activities: [],
  
  // System health
  systemHealth: null,
  services: [],
  
  // Real-time data
  lastUpdated: null,
  isLive: false,
  
  // Loading states
  isLoadingMetrics: false,
  isLoadingCharts: false,
  isLoadingActivities: false,
  isLoadingSystemHealth: false,
  
  // Error states
  metricsError: null,
  chartsError: null,
  activitiesError: null,
  systemHealthError: null,
  
  // Refresh settings
  refreshInterval: 30000, // 30 seconds
  autoRefresh: true,
  
  // Filters
  timeRange: '24h',
  customTimeRange: {
    start: null,
    end: null,
  },
  
  // View settings
  selectedCharts: [],
  chartView: 'grid',
  activitiesLimit: 50,
};

// Create the dashboard store
export const useDashboardStore = create<DashboardState & DashboardActions>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Metrics actions
      setMetrics: (metrics) => set({ metrics }),
      updateMetric: (key, value) => set((state) => ({
        metrics: { ...state.metrics, [key]: value }
      })),
      
      // Chart actions
      setCharts: (charts) => set({ charts }),
      addChart: (chart) => set((state) => ({
        charts: [...state.charts, chart]
      })),
      updateChart: (chartId, updates) => set((state) => ({
        charts: state.charts.map(chart =>
          chart.id === chartId ? { ...chart, ...updates } : chart
        )
      })),
      removeChart: (chartId) => set((state) => ({
        charts: state.charts.filter(chart => chart.id !== chartId)
      })),
      
      // Activity actions
      setActivities: (activities) => set({ activities }),
      addActivity: (activity) => set((state) => ({
        activities: [activity, ...state.activities].slice(0, state.activitiesLimit)
      })),
      updateActivity: (activityId, updates) => set((state) => ({
        activities: state.activities.map(activity =>
          activity.id === activityId ? { ...activity, ...updates } : activity
        )
      })),
      removeActivity: (activityId) => set((state) => ({
        activities: state.activities.filter(activity => activity.id !== activityId)
      })),
      clearActivities: () => set({ activities: [] }),
      
      // System health actions
      setSystemHealth: (health) => set({ systemHealth: health }),
      setServices: (services) => set({ services }),
      updateServiceStatus: (serviceName, status) => set((state) => ({
        services: state.services.map(service =>
          service.name === serviceName ? status : service
        )
      })),
      
      // Real-time actions
      setLastUpdated: (date) => set({ lastUpdated: date }),
      setIsLive: (isLive) => set({ isLive }),
      
      // Loading actions
      setLoadingMetrics: (loading) => set({ isLoadingMetrics: loading }),
      setLoadingCharts: (loading) => set({ isLoadingCharts: loading }),
      setLoadingActivities: (loading) => set({ isLoadingActivities: loading }),
      setLoadingSystemHealth: (loading) => set({ isLoadingSystemHealth: loading }),
      
      // Error actions
      setMetricsError: (error) => set({ metricsError: error }),
      setChartsError: (error) => set({ chartsError: error }),
      setActivitiesError: (error) => set({ activitiesError: error }),
      setSystemHealthError: (error) => set({ systemHealthError: error }),
      clearErrors: () => set({
        metricsError: null,
        chartsError: null,
        activitiesError: null,
        systemHealthError: null,
      }),
      
      // Refresh actions
      setRefreshInterval: (interval) => set({ refreshInterval: interval }),
      setAutoRefresh: (autoRefresh) => set({ autoRefresh }),
      
      // Filter actions
      setTimeRange: (range) => set({ timeRange: range }),
      setCustomTimeRange: (start, end) => set({
        customTimeRange: { start, end }
      }),
      
      // View actions
      setSelectedCharts: (chartIds) => set({ selectedCharts: chartIds }),
      setChartView: (view) => set({ chartView: view }),
      setActivitiesLimit: (limit) => set({ activitiesLimit: limit }),
      
      // Utility actions
      reset: () => set(initialState),
      refreshAll: () => set({
        lastUpdated: new Date(),
        isLoadingMetrics: true,
        isLoadingCharts: true,
        isLoadingActivities: true,
        isLoadingSystemHealth: true,
      }),
    }),
    {
      name: 'lucid-admin-dashboard-store',
    }
  )
);

// Selectors for dashboard state access
export const useDashboardMetrics = () => useDashboardStore((state) => state.metrics);
export const useDashboardCharts = () => useDashboardStore((state) => state.charts);
export const useDashboardActivities = () => useDashboardStore((state) => state.activities);
export const useSystemHealth = () => useDashboardStore((state) => state.systemHealth);
export const useServices = () => useDashboardStore((state) => state.services);

export const useDashboardLoading = () => useDashboardStore((state) => ({
  isLoadingMetrics: state.isLoadingMetrics,
  isLoadingCharts: state.isLoadingCharts,
  isLoadingActivities: state.isLoadingActivities,
  isLoadingSystemHealth: state.isLoadingSystemHealth,
  isLoading: state.isLoadingMetrics || state.isLoadingCharts || 
             state.isLoadingActivities || state.isLoadingSystemHealth,
}));

export const useDashboardErrors = () => useDashboardStore((state) => ({
  metricsError: state.metricsError,
  chartsError: state.chartsError,
  activitiesError: state.activitiesError,
  systemHealthError: state.systemHealthError,
  hasErrors: !!(state.metricsError || state.chartsError || 
                state.activitiesError || state.systemHealthError),
}));

export const useDashboardSettings = () => useDashboardStore((state) => ({
  refreshInterval: state.refreshInterval,
  autoRefresh: state.autoRefresh,
  timeRange: state.timeRange,
  customTimeRange: state.customTimeRange,
  selectedCharts: state.selectedCharts,
  chartView: state.chartView,
  activitiesLimit: state.activitiesLimit,
}));

export const useDashboardRealTime = () => useDashboardStore((state) => ({
  lastUpdated: state.lastUpdated,
  isLive: state.isLive,
  timeSinceUpdate: state.lastUpdated ? Date.now() - state.lastUpdated.getTime() : 0,
}));

// Action selectors
export const useDashboardActions = () => useDashboardStore((state) => ({
  setMetrics: state.setMetrics,
  updateMetric: state.updateMetric,
  setCharts: state.setCharts,
  addChart: state.addChart,
  updateChart: state.updateChart,
  removeChart: state.removeChart,
  setActivities: state.setActivities,
  addActivity: state.addActivity,
  updateActivity: state.updateActivity,
  removeActivity: state.removeActivity,
  clearActivities: state.clearActivities,
  setSystemHealth: state.setSystemHealth,
  setServices: state.setServices,
  updateServiceStatus: state.updateServiceStatus,
  setLastUpdated: state.setLastUpdated,
  setIsLive: state.setIsLive,
  reset: state.reset,
  refreshAll: state.refreshAll,
}));

export const useDashboardLoadingActions = () => useDashboardStore((state) => ({
  setLoadingMetrics: state.setLoadingMetrics,
  setLoadingCharts: state.setLoadingCharts,
  setLoadingActivities: state.setLoadingActivities,
  setLoadingSystemHealth: state.setLoadingSystemHealth,
}));

export const useDashboardErrorActions = () => useDashboardStore((state) => ({
  setMetricsError: state.setMetricsError,
  setChartsError: state.setChartsError,
  setActivitiesError: state.setActivitiesError,
  setSystemHealthError: state.setSystemHealthError,
  clearErrors: state.clearErrors,
}));

export const useDashboardSettingsActions = () => useDashboardStore((state) => ({
  setRefreshInterval: state.setRefreshInterval,
  setAutoRefresh: state.setAutoRefresh,
  setTimeRange: state.setTimeRange,
  setCustomTimeRange: state.setCustomTimeRange,
  setSelectedCharts: state.setSelectedCharts,
  setChartView: state.setChartView,
  setActivitiesLimit: state.setActivitiesLimit,
}));

// Computed selectors
export const useSystemHealthStatus = () => {
  const systemHealth = useSystemHealth();
  const services = useServices();
  
  if (!systemHealth) return 'unknown';
  
  const unhealthyServices = services.filter(s => s.status !== 'healthy');
  const criticalServices = services.filter(s => s.status === 'stopped');
  
  if (criticalServices.length > 0) return 'critical';
  if (unhealthyServices.length > services.length * 0.3) return 'degraded';
  return 'healthy';
};

export const useRecentActivities = (limit: number = 10) => {
  const activities = useDashboardActivities();
  return activities.slice(0, limit);
};

export const useActivitiesByType = (type: ActivityItem['type']) => {
  const activities = useDashboardActivities();
  return activities.filter(activity => activity.type === type);
};

export const useActivitiesBySeverity = (severity: ActivityItem['severity']) => {
  const activities = useDashboardActivities();
  return activities.filter(activity => activity.severity === severity);
};

export const useChartById = (chartId: string) => {
  const charts = useDashboardCharts();
  return charts.find(chart => chart.id === chartId);
};

export const useSelectedCharts = () => {
  const charts = useDashboardCharts();
  const selectedCharts = useDashboardStore((state) => state.selectedCharts);
  return charts.filter(chart => selectedCharts.includes(chart.id));
};

export const useSystemUptime = () => {
  const services = useServices();
  const avgUptime = services.length > 0 
    ? services.reduce((sum, service) => sum + service.uptime, 0) / services.length
    : 0;
  return avgUptime;
};

export const useStorageUsagePercentage = () => {
  const metrics = useDashboardMetrics();
  const maxStorage = 1000 * 1024 * 1024 * 1024; // 1TB
  return (metrics.totalStorageUsed / maxStorage) * 100;
};

export const useNetworkStatus = () => {
  const metrics = useDashboardMetrics();
  const systemHealth = useSystemHealth();
  
  return {
    latency: metrics.networkLatency,
    bandwidth: metrics.bandwidthUsage,
    torConnections: metrics.torConnections,
    torStatus: systemHealth?.tor_status || 'disconnected',
    dockerStatus: systemHealth?.docker_status || 'stopped',
  };
};

export default useDashboardStore;
