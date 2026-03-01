// electron-gui/renderer/admin/pages/DashboardPage.tsx
// Admin Dashboard Page - System overview, metrics, and quick actions

import React, { useState, useEffect } from 'react';
import { DashboardLayout, GridLayout, CardLayout } from '../../common/components/Layout';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { useSystemHealth, useAllUsers, useAllSessions, useAllNodes, useBlockchainInfo } from '../../common/hooks/useApi';
import { SystemHealth, User, Session, Node, Block } from '../../../shared/types';
import { TorStatus } from '../../../shared/tor-types';

interface DashboardMetrics {
  totalUsers: number;
  activeUsers: number;
  totalSessions: number;
  activeSessions: number;
  totalNodes: number;
  activeNodes: number;
  totalBlocks: number;
  systemUptime: number;
  torConnected: boolean;
}

interface QuickAction {
  id: string;
  label: string;
  icon: string;
  description: string;
  action: () => void;
  disabled?: boolean;
}

const DashboardPage: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    totalUsers: 0,
    activeUsers: 0,
    totalSessions: 0,
    activeSessions: 0,
    totalNodes: 0,
    activeNodes: 0,
    totalBlocks: 0,
    systemUptime: 0,
    torConnected: false,
  });

  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  // API hooks
  const { data: systemHealth, loading: healthLoading } = useSystemHealth();
  const { data: users, loading: usersLoading } = useAllUsers();
  const { data: sessions, loading: sessionsLoading } = useAllSessions();
  const { data: nodes, loading: nodesLoading } = useAllNodes();
  const { data: blockchainInfo, loading: blockchainLoading } = useBlockchainInfo();

  // Update metrics when data changes
  useEffect(() => {
    if (users && sessions && nodes && blockchainInfo) {
      const activeUsers = users.filter((user: User) => 
        sessions.some((session: Session) => session.user_id === user.user_id && session.status === 'active')
      ).length;

      const activeSessions = sessions.filter((session: Session) => session.status === 'active').length;
      const activeNodes = nodes.filter((node: Node) => node.status === 'active').length;

      setMetrics({
        totalUsers: users.length,
        activeUsers,
        totalSessions: sessions.length,
        activeSessions,
        totalNodes: nodes.length,
        activeNodes,
        totalBlocks: blockchainInfo.latest_block_height || 0,
        systemUptime: systemHealth?.uptime || 0,
        torConnected: torStatus.is_connected,
      });
    }
  }, [users, sessions, nodes, blockchainInfo, systemHealth, torStatus]);

  // Quick actions
  const quickActions: QuickAction[] = [
    {
      id: 'restart-tor',
      label: 'Restart Tor',
      icon: '🔄',
      description: 'Restart Tor connection',
      action: () => handleRestartTor(),
      disabled: !torStatus.is_connected,
    },
    {
      id: 'refresh-data',
      label: 'Refresh Data',
      icon: '🔄',
      description: 'Refresh all system data',
      action: () => handleRefreshData(),
    },
    {
      id: 'export-logs',
      label: 'Export Logs',
      icon: '📄',
      description: 'Export system logs',
      action: () => handleExportLogs(),
    },
    {
      id: 'system-backup',
      label: 'System Backup',
      icon: '💾',
      description: 'Create system backup',
      action: () => handleSystemBackup(),
    },
  ];

  const handleRestartTor = async () => {
    try {
      await window.electronAPI.tor.restart();
      showToast({
        type: 'success',
        title: 'Tor Restarted',
        message: 'Tor connection has been restarted successfully',
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Tor Restart Failed',
        message: error instanceof Error ? error.message : 'Failed to restart Tor',
      });
    }
  };

  const handleRefreshData = () => {
    // Trigger data refresh
    window.location.reload();
  };

  const handleExportLogs = () => {
    // Implement log export
    showToast({
      type: 'info',
      title: 'Export Logs',
      message: 'Log export functionality will be implemented',
    });
  };

  const handleSystemBackup = () => {
    // Implement system backup
    showToast({
      type: 'info',
      title: 'System Backup',
      message: 'System backup functionality will be implemented',
    });
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  if (loading || healthLoading || usersLoading || sessionsLoading || nodesLoading || blockchainLoading) {
    return (
      <DashboardLayout
        title="Admin Dashboard"
        torStatus={torStatus}
        headerActions={
          <div className="flex items-center space-x-4">
            <TorIndicator status={torStatus} size="small" />
          </div>
        }
      >
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading dashboard data...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Admin Dashboard"
      torStatus={torStatus}
      headerActions={
        <div className="flex items-center space-x-4">
          <TorIndicator status={torStatus} size="small" />
        </div>
      }
    >
      <div className="space-y-6">
        {/* System Overview Cards */}
        <GridLayout columns={4} gap="lg">
          <CardLayout
            title="Total Users"
            subtitle={`${formatNumber(metrics.activeUsers)} active`}
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white"
          >
            <div className="text-3xl font-bold">{formatNumber(metrics.totalUsers)}</div>
            <div className="text-blue-100 text-sm">Registered users</div>
          </CardLayout>

          <CardLayout
            title="Active Sessions"
            subtitle={`${formatNumber(metrics.totalSessions)} total`}
            className="bg-gradient-to-r from-green-500 to-green-600 text-white"
          >
            <div className="text-3xl font-bold">{formatNumber(metrics.activeSessions)}</div>
            <div className="text-green-100 text-sm">Currently active</div>
          </CardLayout>

          <CardLayout
            title="Active Nodes"
            subtitle={`${formatNumber(metrics.totalNodes)} total`}
            className="bg-gradient-to-r from-purple-500 to-purple-600 text-white"
          >
            <div className="text-3xl font-bold">{formatNumber(metrics.activeNodes)}</div>
            <div className="text-purple-100 text-sm">Node operators</div>
          </CardLayout>

          <CardLayout
            title="Blockchain Blocks"
            subtitle="Latest block height"
            className="bg-gradient-to-r from-orange-500 to-orange-600 text-white"
          >
            <div className="text-3xl font-bold">{formatNumber(metrics.totalBlocks)}</div>
            <div className="text-orange-100 text-sm">Blocks mined</div>
          </CardLayout>
        </GridLayout>

        {/* System Health and Tor Status */}
        <GridLayout columns={2} gap="lg">
          <CardLayout
            title="System Health"
            subtitle="Overall system status"
            className="bg-white border border-gray-200"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">System Uptime</span>
                <span className="font-medium">{formatUptime(metrics.systemUptime)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Tor Connection</span>
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${metrics.torConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="text-sm font-medium">
                    {metrics.torConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Health Status</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  systemHealth?.overall === 'healthy' ? 'bg-green-100 text-green-800' :
                  systemHealth?.overall === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {systemHealth?.overall || 'Unknown'}
                </span>
              </div>
            </div>
          </CardLayout>

          <CardLayout
            title="Quick Actions"
            subtitle="Common administrative tasks"
            className="bg-white border border-gray-200"
          >
            <div className="grid grid-cols-2 gap-3">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  onClick={action.action}
                  disabled={action.disabled}
                  className={`p-3 rounded-lg border text-left transition-colors ${
                    action.disabled
                      ? 'bg-gray-50 border-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-white border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                  }`}
                >
                  <div className="text-lg mb-1">{action.icon}</div>
                  <div className="text-sm font-medium">{action.label}</div>
                  <div className="text-xs text-gray-500">{action.description}</div>
                </button>
              ))}
            </div>
          </CardLayout>
        </GridLayout>

        {/* Recent Activity */}
        <CardLayout
          title="Recent Activity"
          subtitle="Latest system events"
          className="bg-white border border-gray-200"
        >
          <div className="space-y-3">
            {recentActivity.length > 0 ? (
              recentActivity.map((activity, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{activity.title}</div>
                    <div className="text-xs text-gray-500">{activity.timestamp}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">📊</div>
                <p>No recent activity to display</p>
                <p className="text-sm">Activity will appear here as the system is used</p>
              </div>
            )}
          </div>
        </CardLayout>

        {/* Resource Usage Charts */}
        <GridLayout columns={2} gap="lg">
          <CardLayout
            title="Resource Usage"
            subtitle="System resource consumption"
            className="bg-white border border-gray-200"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">CPU Usage</span>
                <span className="text-sm font-medium">45%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{ width: '45%' }}></div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Memory Usage</span>
                <span className="text-sm font-medium">62%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-green-600 h-2 rounded-full" style={{ width: '62%' }}></div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Disk Usage</span>
                <span className="text-sm font-medium">38%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-purple-600 h-2 rounded-full" style={{ width: '38%' }}></div>
              </div>
            </div>
          </CardLayout>

          <CardLayout
            title="Network Status"
            subtitle="Tor and network connectivity"
            className="bg-white border border-gray-200"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Tor Status</span>
                <div className="flex items-center space-x-2">
                  <TorIndicator status={torStatus} size="small" showText={false} />
                  <span className="text-sm font-medium">
                    {torStatus.is_connected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Bootstrap Progress</span>
                <span className="text-sm font-medium">{Math.round(torStatus.bootstrap_progress * 100)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full" 
                  style={{ width: `${torStatus.bootstrap_progress * 100}%` }}
                ></div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Active Circuits</span>
                <span className="text-sm font-medium">{torStatus.circuits.length}</span>
              </div>
            </div>
          </CardLayout>
        </GridLayout>
      </div>
    </DashboardLayout>
  );
};

export default DashboardPage;
