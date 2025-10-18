/**
 * Lucid Admin Charts JavaScript
 * Chart.js integration for dashboard visualizations
 */

class LucidCharts {
    constructor() {
        this.charts = {};
        this.colors = {
            primary: '#3b82f6',
            secondary: '#6b7280',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#06b6d4'
        };
        
        this.init();
    }

    init() {
        this.setupCharts();
        this.setupEventListeners();
    }

    setupCharts() {
        // Resource Usage Chart
        this.createResourceChart();
        
        // Session Activity Chart
        this.createSessionChart();
    }

    setupEventListeners() {
        // Resource timeframe selector
        const resourceTimeframe = document.getElementById('resource-timeframe');
        if (resourceTimeframe) {
            resourceTimeframe.addEventListener('change', (e) => {
                this.updateResourceChart(e.target.value);
            });
        }

        // Session timeframe selector
        const sessionTimeframe = document.getElementById('session-timeframe');
        if (sessionTimeframe) {
            sessionTimeframe.addEventListener('change', (e) => {
                this.updateSessionChart(e.target.value);
            });
        }
    }

    createResourceChart() {
        const canvas = document.getElementById('resource-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.charts.resource = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU Usage (%)',
                        data: [],
                        borderColor: this.colors.primary,
                        backgroundColor: this.colors.primary + '20',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Memory Usage (%)',
                        data: [],
                        borderColor: this.colors.success,
                        backgroundColor: this.colors.success + '20',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Disk Usage (%)',
                        data: [],
                        borderColor: this.colors.warning,
                        backgroundColor: this.colors.warning + '20',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Usage (%)'
                        },
                        min: 0,
                        max: 100
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    createSessionChart() {
        const canvas = document.getElementById('session-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        this.charts.session = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Active Sessions',
                        data: [],
                        backgroundColor: this.colors.primary,
                        borderColor: this.colors.primary,
                        borderWidth: 1
                    },
                    {
                        label: 'New Sessions',
                        data: [],
                        backgroundColor: this.colors.success,
                        borderColor: this.colors.success,
                        borderWidth: 1
                    },
                    {
                        label: 'Terminated Sessions',
                        data: [],
                        backgroundColor: this.colors.danger,
                        borderColor: this.colors.danger,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Sessions'
                        },
                        beginAtZero: true
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    updateCharts(data) {
        if (data.resource_usage) {
            this.updateResourceChartData(data.resource_usage);
        }
        
        if (data.session_activity) {
            this.updateSessionChartData(data.session_activity);
        }
    }

    updateResourceChart(timeframe = '1h') {
        // This would typically make an API call to get data for the specified timeframe
        // For now, we'll simulate with random data
        this.loadResourceData(timeframe);
    }

    updateSessionChart(timeframe = '1h') {
        // This would typically make an API call to get data for the specified timeframe
        // For now, we'll simulate with random data
        this.loadSessionData(timeframe);
    }

    async loadResourceData(timeframe) {
        try {
            // Simulate API call
            const data = this.generateMockResourceData(timeframe);
            this.updateResourceChartData(data);
        } catch (error) {
            console.error('Failed to load resource data:', error);
        }
    }

    async loadSessionData(timeframe) {
        try {
            // Simulate API call
            const data = this.generateMockSessionData(timeframe);
            this.updateSessionChartData(data);
        } catch (error) {
            console.error('Failed to load session data:', error);
        }
    }

    updateResourceChartData(data) {
        if (!this.charts.resource) return;

        this.charts.resource.data.labels = data.labels;
        this.charts.resource.data.datasets[0].data = data.cpu;
        this.charts.resource.data.datasets[1].data = data.memory;
        this.charts.resource.data.datasets[2].data = data.disk;
        this.charts.resource.update();
    }

    updateSessionChartData(data) {
        if (!this.charts.session) return;

        this.charts.session.data.labels = data.labels;
        this.charts.session.data.datasets[0].data = data.active;
        this.charts.session.data.datasets[1].data = data.new;
        this.charts.session.data.datasets[2].data = data.terminated;
        this.charts.session.update();
    }

    generateMockResourceData(timeframe) {
        const points = this.getTimeframePoints(timeframe);
        const labels = [];
        const cpu = [];
        const memory = [];
        const disk = [];

        for (let i = 0; i < points; i++) {
            const time = new Date(Date.now() - (points - i) * this.getTimeframeInterval(timeframe));
            labels.push(time.toLocaleTimeString());
            
            // Generate realistic data with some variation
            cpu.push(Math.max(0, Math.min(100, 30 + Math.random() * 40 + Math.sin(i * 0.5) * 10)));
            memory.push(Math.max(0, Math.min(100, 40 + Math.random() * 30 + Math.sin(i * 0.3) * 15)));
            disk.push(Math.max(0, Math.min(100, 20 + Math.random() * 20 + Math.sin(i * 0.2) * 5)));
        }

        return { labels, cpu, memory, disk };
    }

    generateMockSessionData(timeframe) {
        const points = this.getTimeframePoints(timeframe);
        const labels = [];
        const active = [];
        const newSessions = [];
        const terminated = [];

        for (let i = 0; i < points; i++) {
            const time = new Date(Date.now() - (points - i) * this.getTimeframeInterval(timeframe));
            labels.push(time.toLocaleTimeString());
            
            // Generate realistic session data
            const baseActive = 50 + Math.sin(i * 0.1) * 20;
            active.push(Math.max(0, baseActive + Math.random() * 10));
            newSessions.push(Math.max(0, 5 + Math.random() * 15));
            terminated.push(Math.max(0, 3 + Math.random() * 12));
        }

        return { labels, active, new: newSessions, terminated };
    }

    getTimeframePoints(timeframe) {
        switch (timeframe) {
            case '1h': return 12; // 5-minute intervals
            case '6h': return 24; // 15-minute intervals
            case '24h': return 24; // 1-hour intervals
            case '7d': return 28; // 6-hour intervals
            default: return 12;
        }
    }

    getTimeframeInterval(timeframe) {
        switch (timeframe) {
            case '1h': return 5 * 60 * 1000; // 5 minutes
            case '6h': return 15 * 60 * 1000; // 15 minutes
            case '24h': return 60 * 60 * 1000; // 1 hour
            case '7d': return 6 * 60 * 60 * 1000; // 6 hours
            default: return 5 * 60 * 1000;
        }
    }

    createNodeDistributionChart(containerId, data) {
        const canvas = document.getElementById(containerId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        this.colors.primary,
                        this.colors.success,
                        this.colors.warning,
                        this.colors.danger
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                }
            }
        });
    }

    createBlockchainChart(containerId, data) {
        const canvas = document.getElementById(containerId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Block Height',
                    data: data.heights,
                    borderColor: this.colors.primary,
                    backgroundColor: this.colors.primary + '20',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Block Height'
                        }
                    }
                }
            }
        });
    }

    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.LucidCharts = new LucidCharts();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.LucidCharts) {
        window.LucidCharts.destroy();
    }
});
