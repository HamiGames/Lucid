export interface MetricData {
  id: string;
  name: string;
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  change: number;
  timestamp: string;
}

export interface ChartData {
  id: string;
  title: string;
  type: 'line' | 'bar' | 'area' | 'pie';
  data: Array<{
    timestamp: string;
    value: number;
    label?: string;
  }>;
  color: string;
  description: string;
}

export interface MetricsFilters {
  timeRange: '1h' | '6h' | '24h' | '7d' | '30d';
  category: string;
  refreshInterval: number;
}

export interface MetricsStatistics {
  totalMetrics: number;
  metricsByCategory: Record<string, number>;
  averageValue: number;
  highestValue: number;
  lowestValue: number;
  trendAnalysis: {
    improving: number;
    declining: number;
    stable: number;
  };
}

class MetricsService {
  private metrics: MetricData[] = [];
  private charts: ChartData[] = [];
  private subscribers: Array<(metrics: MetricData[], charts: ChartData[]) => void> = [];
  private isLive: boolean = false;
  private liveInterval: NodeJS.Timeout | null = null;
  private lastUpdate: number = 0;

  constructor() {
    this.startLiveUpdates();
  }

  async getMetrics(filters: MetricsFilters = {
    timeRange: '24h',
    category: 'all',
    refreshInterval: 30
  }): Promise<MetricData[]> {
    try {
      // Load metrics from the system
      const allMetrics = await this.loadMetricsFromSystem();
      this.metrics = allMetrics;
      this.lastUpdate = Date.now();
      
      // Apply filters
      let filteredMetrics = this.applyFilters(allMetrics, filters);
      
      return filteredMetrics;
    } catch (error) {
      console.error('Failed to load metrics:', error);
      throw new Error('Failed to load metrics');
    }
  }

  async getCharts(filters: MetricsFilters = {
    timeRange: '24h',
    category: 'all',
    refreshInterval: 30
  }): Promise<ChartData[]> {
    try {
      // Load charts from the system
      const allCharts = await this.loadChartsFromSystem();
      this.charts = allCharts;
      
      // Apply filters
      let filteredCharts = this.applyChartFilters(allCharts, filters);
      
      return filteredCharts;
    } catch (error) {
      console.error('Failed to load charts:', error);
      throw new Error('Failed to load charts');
    }
  }

  private async loadMetricsFromSystem(): Promise<MetricData[]> {
    // Mock metrics data - in real implementation, these would come from the metrics service
    const mockMetrics: MetricData[] = [
      {
        id: 'cpu-usage',
        name: 'CPU Usage',
        value: 45.2,
        unit: '%',
        trend: 'up',
        change: 2.1,
        timestamp: new Date().toISOString()
      },
      {
        id: 'memory-usage',
        name: 'Memory Usage',
        value: 68.7,
        unit: '%',
        trend: 'stable',
        change: 0.3,
        timestamp: new Date().toISOString()
      },
      {
        id: 'disk-usage',
        name: 'Disk Usage',
        value: 23.4,
        unit: '%',
        trend: 'down',
        change: -1.2,
        timestamp: new Date().toISOString()
      },
      {
        id: 'network-throughput',
        name: 'Network Throughput',
        value: 125.6,
        unit: 'Mbps',
        trend: 'up',
        change: 5.8,
        timestamp: new Date().toISOString()
      },
      {
        id: 'active-sessions',
        name: 'Active Sessions',
        value: 42,
        unit: 'sessions',
        trend: 'up',
        change: 3,
        timestamp: new Date().toISOString()
      },
      {
        id: 'tor-circuits',
        name: 'Tor Circuits',
        value: 8,
        unit: 'circuits',
        trend: 'stable',
        change: 0,
        timestamp: new Date().toISOString()
      },
      {
        id: 'api-requests',
        name: 'API Requests',
        value: 1250,
        unit: 'requests/min',
        trend: 'up',
        change: 45,
        timestamp: new Date().toISOString()
      },
      {
        id: 'error-rate',
        name: 'Error Rate',
        value: 0.8,
        unit: '%',
        trend: 'down',
        change: -0.2,
        timestamp: new Date().toISOString()
      }
    ];

    return mockMetrics;
  }

  private async loadChartsFromSystem(): Promise<ChartData[]> {
    // Mock charts data
    const now = Date.now();
    const generateDataPoints = (hours: number, interval: number = 5) => {
      const points = [];
      for (let i = hours * 12; i >= 0; i -= interval) {
        points.push({
          timestamp: new Date(now - i * 5 * 60 * 1000).toISOString(),
          value: Math.random() * 100,
          label: new Date(now - i * 5 * 60 * 1000).toLocaleTimeString()
        });
      }
      return points;
    };

    const mockCharts: ChartData[] = [
      {
        id: 'cpu-trend',
        title: 'CPU Usage Trend',
        type: 'line',
        data: generateDataPoints(24),
        color: '#3b82f6',
        description: 'CPU usage over time'
      },
      {
        id: 'memory-trend',
        title: 'Memory Usage Trend',
        type: 'area',
        data: generateDataPoints(24),
        color: '#10b981',
        description: 'Memory usage over time'
      },
      {
        id: 'network-io',
        title: 'Network I/O',
        type: 'bar',
        data: generateDataPoints(24),
        color: '#f59e0b',
        description: 'Network input/output over time'
      },
      {
        id: 'session-distribution',
        title: 'Session Distribution',
        type: 'pie',
        data: [
          { timestamp: new Date().toISOString(), value: 60, label: 'Active' },
          { timestamp: new Date().toISOString(), value: 25, label: 'Idle' },
          { timestamp: new Date().toISOString(), value: 15, label: 'Terminated' }
        ],
        color: '#8b5cf6',
        description: 'Distribution of session states'
      },
      {
        id: 'api-response-times',
        title: 'API Response Times',
        type: 'line',
        data: generateDataPoints(24),
        color: '#06b6d4',
        description: 'Average API response times'
      },
      {
        id: 'error-rates',
        title: 'Error Rates',
        type: 'area',
        data: generateDataPoints(24),
        color: '#ef4444',
        description: 'Error rates over time'
      }
    ];

    return mockCharts;
  }

  private applyFilters(metrics: MetricData[], filters: MetricsFilters): MetricData[] {
    let filtered = [...metrics];

    // Filter by category
    if (filters.category !== 'all') {
      // In a real implementation, metrics would have categories
      // For now, we'll filter by name patterns
      const categoryPatterns: Record<string, string[]> = {
        'system': ['cpu', 'memory', 'disk'],
        'network': ['network', 'tor'],
        'sessions': ['session'],
        'api': ['api', 'request', 'response']
      };

      if (categoryPatterns[filters.category]) {
        const patterns = categoryPatterns[filters.category];
        filtered = filtered.filter(metric => 
          patterns.some(pattern => metric.name.toLowerCase().includes(pattern))
        );
      }
    }

    // Filter by time range
    const timeRangeMs = this.getTimeRangeMs(filters.timeRange);
    const cutoffTime = Date.now() - timeRangeMs;
    filtered = filtered.filter(metric => 
      new Date(metric.timestamp).getTime() >= cutoffTime
    );

    return filtered;
  }

  private applyChartFilters(charts: ChartData[], filters: MetricsFilters): ChartData[] {
    let filtered = [...charts];

    // Filter by category
    if (filters.category !== 'all') {
      const categoryPatterns: Record<string, string[]> = {
        'system': ['cpu', 'memory', 'disk'],
        'network': ['network', 'tor'],
        'sessions': ['session'],
        'api': ['api', 'request', 'response']
      };

      if (categoryPatterns[filters.category]) {
        const patterns = categoryPatterns[filters.category];
        filtered = filtered.filter(chart => 
          patterns.some(pattern => chart.title.toLowerCase().includes(pattern))
        );
      }
    }

    // Filter by time range
    const timeRangeMs = this.getTimeRangeMs(filters.timeRange);
    const cutoffTime = Date.now() - timeRangeMs;
    
    filtered = filtered.map(chart => ({
      ...chart,
      data: chart.data.filter(point => 
        new Date(point.timestamp).getTime() >= cutoffTime
      )
    }));

    return filtered;
  }

  private getTimeRangeMs(timeRange: string): number {
    switch (timeRange) {
      case '1h': return 60 * 60 * 1000;
      case '6h': return 6 * 60 * 60 * 1000;
      case '24h': return 24 * 60 * 60 * 1000;
      case '7d': return 7 * 24 * 60 * 60 * 1000;
      case '30d': return 30 * 24 * 60 * 60 * 1000;
      default: return 24 * 60 * 60 * 1000;
    }
  }

  async getMetricsStatistics(filters: MetricsFilters = {}): Promise<MetricsStatistics> {
    const metrics = await this.getMetrics(filters);
    
    const metricsByCategory: Record<string, number> = {};
    let totalValue = 0;
    let highestValue = 0;
    let lowestValue = Infinity;
    const trendAnalysis = {
      improving: 0,
      declining: 0,
      stable: 0
    };

    metrics.forEach(metric => {
      // Count by category (simplified)
      const category = this.getMetricCategory(metric);
      metricsByCategory[category] = (metricsByCategory[category] || 0) + 1;
      
      // Calculate statistics
      totalValue += metric.value;
      highestValue = Math.max(highestValue, metric.value);
      lowestValue = Math.min(lowestValue, metric.value);
      
      // Analyze trends
      switch (metric.trend) {
        case 'up':
          trendAnalysis.improving++;
          break;
        case 'down':
          trendAnalysis.declining++;
          break;
        case 'stable':
          trendAnalysis.stable++;
          break;
      }
    });

    return {
      totalMetrics: metrics.length,
      metricsByCategory,
      averageValue: metrics.length > 0 ? totalValue / metrics.length : 0,
      highestValue,
      lowestValue: lowestValue === Infinity ? 0 : lowestValue,
      trendAnalysis
    };
  }

  private getMetricCategory(metric: MetricData): string {
    const name = metric.name.toLowerCase();
    if (name.includes('cpu') || name.includes('memory') || name.includes('disk')) {
      return 'system';
    }
    if (name.includes('network') || name.includes('tor')) {
      return 'network';
    }
    if (name.includes('session')) {
      return 'sessions';
    }
    if (name.includes('api') || name.includes('request') || name.includes('response')) {
      return 'api';
    }
    return 'other';
  }

  startLiveUpdates(): void {
    if (this.isLive) return;
    
    this.isLive = true;
    this.liveInterval = setInterval(async () => {
      try {
        const newMetrics = await this.loadMetricsFromSystem();
        const newCharts = await this.loadChartsFromSystem();
        
        this.metrics = newMetrics;
        this.charts = newCharts;
        this.lastUpdate = Date.now();
        
        this.notifySubscribers();
      } catch (error) {
        console.error('Failed to load new metrics:', error);
      }
    }, 30000); // Update every 30 seconds
  }

  stopLiveUpdates(): void {
    if (this.liveInterval) {
      clearInterval(this.liveInterval);
      this.liveInterval = null;
    }
    this.isLive = false;
  }

  subscribe(callback: (metrics: MetricData[], charts: ChartData[]) => void): () => void {
    this.subscribers.push(callback);
    
    return () => {
      this.subscribers = this.subscribers.filter(sub => sub !== callback);
    };
  }

  private notifySubscribers(): void {
    this.subscribers.forEach(callback => callback(this.metrics, this.charts));
  }

  getLastUpdate(): Date | null {
    return this.lastUpdate > 0 ? new Date(this.lastUpdate) : null;
  }

  isLiveUpdatesEnabled(): boolean {
    return this.isLive;
  }

  async exportMetrics(format: 'json' | 'csv' = 'json'): Promise<Blob> {
    const metrics = await this.getMetrics();
    const charts = await this.getCharts();
    
    const data = {
      metrics,
      charts,
      timestamp: new Date().toISOString(),
      statistics: await this.getMetricsStatistics()
    };

    let content: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify(data, null, 2);
      mimeType = 'application/json';
    } else {
      content = this.exportToCSV(metrics);
      mimeType = 'text/csv';
    }

    return new Blob([content], { type: mimeType });
  }

  private exportToCSV(metrics: MetricData[]): string {
    const headers = ['timestamp', 'name', 'value', 'unit', 'trend', 'change'];
    const rows = metrics.map(metric => [
      metric.timestamp,
      metric.name,
      metric.value.toString(),
      metric.unit,
      metric.trend,
      metric.change.toString()
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(field => `"${field}"`).join(','))
    ].join('\n');

    return csvContent;
  }

  clearMetrics(): void {
    this.metrics = [];
    this.charts = [];
    this.notifySubscribers();
  }

  destroy(): void {
    this.stopLiveUpdates();
    this.subscribers = [];
  }
}

export const metricsService = new MetricsService();
