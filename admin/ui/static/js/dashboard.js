/**
 * Lucid Admin Dashboard JavaScript
 * Main dashboard functionality and API interactions
 */

class LucidAdminDashboard {
    constructor() {
        this.apiBase = '/api/v1/admin';
        this.wsConnection = null;
        this.refreshInterval = null;
        this.isAuthenticated = false;
        this.currentUser = null;
        
        this.init();
    }

    async init() {
        try {
            await this.checkAuthentication();
            this.setupEventListeners();
            this.startRealTimeUpdates();
            this.loadDashboardData();
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showError('Failed to initialize dashboard');
        }
    }

    async checkAuthentication() {
        try {
            const response = await this.apiRequest('/auth/me');
            if (response.ok) {
                this.currentUser = await response.json();
                this.isAuthenticated = true;
                this.updateUserInterface();
            } else {
                this.redirectToLogin();
            }
        } catch (error) {
            console.error('Authentication check failed:', error);
            this.redirectToLogin();
        }
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateTo(link.getAttribute('href'));
            });
        });

        // Logout
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }

        // Refresh buttons
        const refreshBtns = document.querySelectorAll('.refresh-btn');
        refreshBtns.forEach(btn => {
            btn.addEventListener('click', () => this.loadDashboardData());
        });

        // Emergency controls
        const emergencyStop = document.getElementById('emergency-stop');
        if (emergencyStop) {
            emergencyStop.addEventListener('click', () => this.emergencyStopAllSessions());
        }

        const anchorSessions = document.getElementById('anchor-sessions');
        if (anchorSessions) {
            anchorSessions.addEventListener('click', () => this.anchorSessions());
        }

        const triggerPayouts = document.getElementById('trigger-payouts');
        if (triggerPayouts) {
            triggerPayouts.addEventListener('click', () => this.triggerPayouts());
        }

        const systemLockdown = document.getElementById('system-lockdown');
        if (systemLockdown) {
            systemLockdown.addEventListener('click', () => this.systemLockdown());
        }

        // View buttons
        const viewSessions = document.getElementById('view-sessions');
        if (viewSessions) {
            viewSessions.addEventListener('click', () => this.navigateTo('/admin/sessions'));
        }

        const viewNodes = document.getElementById('view-nodes');
        if (viewNodes) {
            viewNodes.addEventListener('click', () => this.navigateTo('/admin/nodes'));
        }

        const viewBlockchain = document.getElementById('view-blockchain');
        if (viewBlockchain) {
            viewBlockchain.addEventListener('click', () => this.navigateTo('/admin/blockchain'));
        }
    }

    startRealTimeUpdates() {
        // WebSocket connection for real-time updates
        this.connectWebSocket();
        
        // Periodic refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, 30000);
    }

    connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/v1/admin/dashboard/stream`;
            
            this.wsConnection = new WebSocket(wsUrl);
            
            this.wsConnection.onopen = () => {
                console.log('WebSocket connected');
            };
            
            this.wsConnection.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.wsConnection.onclose = () => {
                console.log('WebSocket disconnected, attempting to reconnect...');
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
            this.wsConnection.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'metric_update':
                this.updateMetrics(data.data);
                break;
            case 'system_alert':
                this.showAlert(data.data);
                break;
            case 'session_change':
                this.updateSessionData(data.data);
                break;
            case 'node_status_change':
                this.updateNodeData(data.data);
                break;
            case 'blockchain_update':
                this.updateBlockchainData(data.data);
                break;
        }
    }

    async loadDashboardData() {
        try {
            this.showLoading(true);
            
            const [overview, metrics] = await Promise.all([
                this.apiRequest('/dashboard/overview'),
                this.apiRequest('/dashboard/metrics?timeframe=1h')
            ]);

            if (overview.ok && metrics.ok) {
                const overviewData = await overview.json();
                const metricsData = await metrics.json();
                
                this.updateOverview(overviewData);
                this.updateCharts(metricsData);
            }
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showError('Failed to load dashboard data');
        } finally {
            this.showLoading(false);
        }
    }

    updateOverview(data) {
        // System status
        this.updateElement('system-uptime', data.system_status.uptime);
        this.updateElement('system-version', data.system_status.version);
        this.updateElement('last-update', new Date().toLocaleString());
        
        // Update status indicator
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        if (statusIndicator && statusText) {
            statusIndicator.className = `status-indicator ${data.system_status.status}`;
            statusText.textContent = data.system_status.status.toUpperCase();
        }

        // Sessions
        this.updateElement('total-sessions', data.active_sessions.total);
        this.updateElement('active-sessions', data.active_sessions.active);
        this.updateElement('idle-sessions', data.active_sessions.idle);

        // Nodes
        this.updateElement('total-nodes', data.node_status.total_nodes);
        this.updateElement('online-nodes', data.node_status.online_nodes);
        this.updateElement('load-average', data.node_status.load_average.toFixed(2));

        // Blockchain
        this.updateElement('network-height', data.blockchain_status.network_height);
        this.updateElement('sync-status', data.blockchain_status.sync_status);
        this.updateElement('pending-txs', data.blockchain_status.pending_transactions);
    }

    updateCharts(data) {
        // This will be implemented by the charts.js file
        if (window.LucidCharts) {
            window.LucidCharts.updateCharts(data);
        }
    }

    updateMetrics(data) {
        // Update real-time metrics
        if (data.cpu !== undefined) {
            this.updateElement('cpu-usage', `${data.cpu.toFixed(1)}%`);
        }
        if (data.memory !== undefined) {
            this.updateElement('memory-usage', `${data.memory.toFixed(1)}%`);
        }
        if (data.disk !== undefined) {
            this.updateElement('disk-usage', `${data.disk.toFixed(1)}%`);
        }
    }

    updateSessionData(data) {
        this.updateElement('active-sessions', data.active);
        this.updateElement('idle-sessions', data.idle);
        this.updateElement('total-sessions', data.total);
    }

    updateNodeData(data) {
        this.updateElement('online-nodes', data.online);
        this.updateElement('total-nodes', data.total);
        this.updateElement('load-average', data.load_average.toFixed(2));
    }

    updateBlockchainData(data) {
        this.updateElement('network-height', data.network_height);
        this.updateElement('sync-status', data.sync_status);
        this.updateElement('pending-txs', data.pending_transactions);
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    async emergencyStopAllSessions() {
        if (!confirm('Are you sure you want to stop ALL active sessions? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await this.apiRequest('/emergency/stop-all-sessions', {
                method: 'POST'
            });

            if (response.ok) {
                this.showSuccess('All sessions have been stopped');
                this.loadDashboardData();
            } else {
                this.showError('Failed to stop sessions');
            }
        } catch (error) {
            console.error('Failed to stop sessions:', error);
            this.showError('Failed to stop sessions');
        }
    }

    async anchorSessions() {
        try {
            const response = await this.apiRequest('/blockchain/anchor-sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_ids: [],
                    priority: 'normal',
                    force: false
                })
            });

            if (response.ok) {
                this.showSuccess('Sessions anchoring initiated');
            } else {
                this.showError('Failed to anchor sessions');
            }
        } catch (error) {
            console.error('Failed to anchor sessions:', error);
            this.showError('Failed to anchor sessions');
        }
    }

    async triggerPayouts() {
        try {
            const response = await this.apiRequest('/payouts/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_ids: [],
                    amount: '0',
                    currency: 'USDT',
                    reason: 'Manual trigger from admin dashboard'
                })
            });

            if (response.ok) {
                this.showSuccess('Payout processing triggered');
            } else {
                this.showError('Failed to trigger payouts');
            }
        } catch (error) {
            console.error('Failed to trigger payouts:', error);
            this.showError('Failed to trigger payouts');
        }
    }

    async systemLockdown() {
        if (!confirm('Are you sure you want to put the system in lockdown mode? This will disable all new sessions.')) {
            return;
        }

        try {
            const response = await this.apiRequest('/emergency/system-lockdown', {
                method: 'POST'
            });

            if (response.ok) {
                this.showSuccess('System lockdown activated');
            } else {
                this.showError('Failed to activate system lockdown');
            }
        } catch (error) {
            console.error('Failed to activate lockdown:', error);
            this.showError('Failed to activate system lockdown');
        }
    }

    async logout() {
        try {
            await this.apiRequest('/auth/logout', {
                method: 'POST'
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.redirectToLogin();
        }
    }

    redirectToLogin() {
        window.location.href = '/admin/login';
    }

    navigateTo(path) {
        window.location.href = path;
    }

    updateUserInterface() {
        const userName = document.getElementById('user-name');
        if (userName && this.currentUser) {
            userName.textContent = this.currentUser.username;
        }
    }

    async apiRequest(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        };

        return fetch(url, { ...defaultOptions, ...options });
    }

    getAuthToken() {
        return localStorage.getItem('admin_token') || sessionStorage.getItem('admin_token');
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showAlert(data) {
        this.showToast(data.message, data.severity || 'warning');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.wsConnection) {
            this.wsConnection.close();
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.lucidDashboard = new LucidAdminDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.lucidDashboard) {
        window.lucidDashboard.destroy();
    }
});
