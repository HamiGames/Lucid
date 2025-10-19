// electron-gui/renderer/admin/pages/AuditPage.tsx
// Admin Audit Logs Page - Audit log query interface, log filtering and export

import React, { useState, useEffect, useMemo } from 'react';
import { DashboardLayout, GridLayout, CardLayout } from '../../common/components/Layout';
import { Modal, ConfirmModal } from '../../common/components/Modal';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { TorStatus } from '../../../shared/tor-types';

interface AuditLogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  category: 'authentication' | 'authorization' | 'session' | 'node' | 'blockchain' | 'system' | 'security';
  action: string;
  user_id?: string;
  session_id?: string;
  node_id?: string;
  ip_address?: string;
  user_agent?: string;
  details: Record<string, any>;
  status: 'success' | 'failure' | 'pending';
  message: string;
}

interface AuditFilters {
  dateRange: {
    start: string;
    end: string;
  };
  level: 'all' | 'info' | 'warning' | 'error' | 'debug';
  category: 'all' | 'authentication' | 'authorization' | 'session' | 'node' | 'blockchain' | 'system' | 'security';
  status: 'all' | 'success' | 'failure' | 'pending';
  userId: string;
  sessionId: string;
  nodeId: string;
  search: string;
}

interface AuditStatistics {
  totalLogs: number;
  logsByLevel: Record<string, number>;
  logsByCategory: Record<string, number>;
  logsByStatus: Record<string, number>;
  recentActivity: number;
  errorRate: number;
  topUsers: Array<{ user_id: string; count: number }>;
  topActions: Array<{ action: string; count: number }>;
}

interface BulkAction {
  id: string;
  label: string;
  icon: string;
  action: (logIds: string[]) => Promise<void>;
  requiresConfirmation: boolean;
  confirmationMessage: string;
}

const AuditPage: React.FC = () => {
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [statistics, setStatistics] = useState<AuditStatistics>({
    totalLogs: 0,
    logsByLevel: {},
    logsByCategory: {},
    logsByStatus: {},
    recentActivity: 0,
    errorRate: 0,
    topUsers: [],
    topActions: [],
  });
  const [loading, setLoading] = useState(true);
  const [selectedLogs, setSelectedLogs] = useState<Set<string>>(new Set());
  const [showLogDetails, setShowLogDetails] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingBulkAction, setPendingBulkAction] = useState<BulkAction | null>(null);

  const [filters, setFilters] = useState<AuditFilters>({
    dateRange: {
      start: '',
      end: '',
    },
    level: 'all',
    category: 'all',
    status: 'all',
    userId: '',
    sessionId: '',
    nodeId: '',
    search: '',
  });

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  // Mock data for demonstration
  useEffect(() => {
    const mockLogs: AuditLogEntry[] = [
      {
        id: 'audit_001',
        timestamp: new Date(Date.now() - 300000).toISOString(),
        level: 'info',
        category: 'authentication',
        action: 'user_login',
        user_id: 'user_001',
        ip_address: '192.168.1.100',
        user_agent: 'Mozilla/5.0...',
        details: { method: 'email', success: true },
        status: 'success',
        message: 'User logged in successfully',
      },
      {
        id: 'audit_002',
        timestamp: new Date(Date.now() - 600000).toISOString(),
        level: 'warning',
        category: 'authorization',
        action: 'access_denied',
        user_id: 'user_002',
        ip_address: '192.168.1.101',
        user_agent: 'Mozilla/5.0...',
        details: { resource: '/admin/users', reason: 'insufficient_permissions' },
        status: 'failure',
        message: 'Access denied to admin users page',
      },
      {
        id: 'audit_003',
        timestamp: new Date(Date.now() - 900000).toISOString(),
        level: 'error',
        category: 'session',
        action: 'session_creation_failed',
        user_id: 'user_003',
        session_id: 'session_003',
        ip_address: '192.168.1.102',
        user_agent: 'Mozilla/5.0...',
        details: { error: 'insufficient_resources', node_id: 'node_001' },
        status: 'failure',
        message: 'Failed to create session due to insufficient node resources',
      },
      {
        id: 'audit_004',
        timestamp: new Date(Date.now() - 1200000).toISOString(),
        level: 'info',
        category: 'node',
        action: 'node_registration',
        user_id: 'user_004',
        node_id: 'node_004',
        ip_address: '192.168.1.103',
        user_agent: 'NodeAgent/1.0',
        details: { resources: { cpu: 8, memory: 16, disk: 500 } },
        status: 'success',
        message: 'Node registered successfully',
      },
      {
        id: 'audit_005',
        timestamp: new Date(Date.now() - 1500000).toISOString(),
        level: 'debug',
        category: 'blockchain',
        action: 'block_validation',
        ip_address: '192.168.1.104',
        details: { block_height: 12345, validation_time: 150 },
        status: 'success',
        message: 'Block validation completed',
      },
      {
        id: 'audit_006',
        timestamp: new Date(Date.now() - 1800000).toISOString(),
        level: 'info',
        category: 'security',
        action: 'suspicious_activity',
        user_id: 'user_005',
        ip_address: '192.168.1.105',
        user_agent: 'Mozilla/5.0...',
        details: { pattern: 'multiple_failed_logins', threshold: 5 },
        status: 'failure',
        message: 'Suspicious activity detected - multiple failed login attempts',
      },
    ];

    setAuditLogs(mockLogs);

    // Calculate statistics
    const stats: AuditStatistics = {
      totalLogs: mockLogs.length,
      logsByLevel: mockLogs.reduce((acc, log) => {
        acc[log.level] = (acc[log.level] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
      logsByCategory: mockLogs.reduce((acc, log) => {
        acc[log.category] = (acc[log.category] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
      logsByStatus: mockLogs.reduce((acc, log) => {
        acc[log.status] = (acc[log.status] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
      recentActivity: mockLogs.filter(log => 
        new Date(log.timestamp) > new Date(Date.now() - 3600000)
      ).length,
      errorRate: mockLogs.filter(log => log.level === 'error').length / mockLogs.length * 100,
      topUsers: Object.entries(
        mockLogs.reduce((acc, log) => {
          if (log.user_id) {
            acc[log.user_id] = (acc[log.user_id] || 0) + 1;
          }
          return acc;
        }, {} as Record<string, number>)
      ).map(([user_id, count]) => ({ user_id, count })).slice(0, 5),
      topActions: Object.entries(
        mockLogs.reduce((acc, log) => {
          acc[log.action] = (acc[log.action] || 0) + 1;
          return acc;
        }, {} as Record<string, number>)
      ).map(([action, count]) => ({ action, count })).slice(0, 5),
    };

    setStatistics(stats);
    setLoading(false);
  }, []);

  // Filter logs based on current filters
  const filteredLogs = useMemo(() => {
    return auditLogs.filter(log => {
      // Date range filter
      if (filters.dateRange.start && new Date(log.timestamp) < new Date(filters.dateRange.start)) {
        return false;
      }
      if (filters.dateRange.end && new Date(log.timestamp) > new Date(filters.dateRange.end)) {
        return false;
      }

      // Level filter
      if (filters.level !== 'all' && log.level !== filters.level) {
        return false;
      }

      // Category filter
      if (filters.category !== 'all' && log.category !== filters.category) {
        return false;
      }

      // Status filter
      if (filters.status !== 'all' && log.status !== filters.status) {
        return false;
      }

      // User ID filter
      if (filters.userId && log.user_id !== filters.userId) {
        return false;
      }

      // Session ID filter
      if (filters.sessionId && log.session_id !== filters.sessionId) {
        return false;
      }

      // Node ID filter
      if (filters.nodeId && log.node_id !== filters.nodeId) {
        return false;
      }

      // Search filter
      if (filters.search && !log.message.toLowerCase().includes(filters.search.toLowerCase()) &&
          !log.action.toLowerCase().includes(filters.search.toLowerCase())) {
        return false;
      }

      return true;
    });
  }, [auditLogs, filters]);

  // Bulk actions
  const bulkActions: BulkAction[] = [
    {
      id: 'export',
      label: 'Export Logs',
      icon: '📄',
      action: handleExportLogs,
      requiresConfirmation: false,
      confirmationMessage: '',
    },
    {
      id: 'archive',
      label: 'Archive Logs',
      icon: '📦',
      action: handleArchiveLogs,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to archive the selected logs? They will be moved to long-term storage.',
    },
    {
      id: 'delete',
      label: 'Delete Logs',
      icon: '🗑️',
      action: handleDeleteLogs,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to delete the selected logs? This action cannot be undone.',
    },
  ];

  async function handleExportLogs(logIds: string[]): Promise<void> {
    try {
      // Implement log export logic
      showToast({
        type: 'success',
        title: 'Logs Exported',
        message: `${logIds.length} audit logs have been exported successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Export Failed',
        message: error instanceof Error ? error.message : 'Failed to export logs',
      });
    }
  }

  async function handleArchiveLogs(logIds: string[]): Promise<void> {
    try {
      // Implement log archiving logic
      showToast({
        type: 'success',
        title: 'Logs Archived',
        message: `${logIds.length} audit logs have been archived successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Archive Failed',
        message: error instanceof Error ? error.message : 'Failed to archive logs',
      });
    }
  }

  async function handleDeleteLogs(logIds: string[]): Promise<void> {
    try {
      // Implement log deletion logic
      showToast({
        type: 'success',
        title: 'Logs Deleted',
        message: `${logIds.length} audit logs have been deleted successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Delete Failed',
        message: error instanceof Error ? error.message : 'Failed to delete logs',
      });
    }
  }

  const handleLogSelect = (logId: string) => {
    const newSelected = new Set(selectedLogs);
    if (newSelected.has(logId)) {
      newSelected.delete(logId);
    } else {
      newSelected.add(logId);
    }
    setSelectedLogs(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedLogs.size === filteredLogs.length) {
      setSelectedLogs(new Set());
    } else {
      setSelectedLogs(new Set(filteredLogs.map(log => log.id)));
    }
  };

  const handleBulkAction = (action: BulkAction) => {
    if (selectedLogs.size === 0) {
      showToast({
        type: 'warning',
        title: 'No Logs Selected',
        message: 'Please select at least one log to perform this action',
      });
      return;
    }

    if (action.requiresConfirmation) {
      setPendingBulkAction(action);
      setShowConfirmModal(true);
    } else {
      action.action(Array.from(selectedLogs));
    }
  };

  const confirmBulkAction = async () => {
    if (pendingBulkAction) {
      await pendingBulkAction.action(Array.from(selectedLogs));
      setShowConfirmModal(false);
      setPendingBulkAction(null);
    }
  };

  const handleLogClick = (log: AuditLogEntry) => {
    setSelectedLog(log);
    setShowLogDetails(true);
  };

  const getLevelColor = (level: string): string => {
    switch (level) {
      case 'error': return 'bg-red-100 text-red-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'info': return 'bg-blue-100 text-blue-800';
      case 'debug': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string): string => {
    switch (category) {
      case 'authentication': return 'bg-green-100 text-green-800';
      case 'authorization': return 'bg-blue-100 text-blue-800';
      case 'session': return 'bg-purple-100 text-purple-800';
      case 'node': return 'bg-orange-100 text-orange-800';
      case 'blockchain': return 'bg-indigo-100 text-indigo-800';
      case 'system': return 'bg-gray-100 text-gray-800';
      case 'security': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-800';
      case 'failure': return 'bg-red-100 text-red-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const formatRelativeTime = (dateString: string): string => {
    const now = new Date();
    const logTime = new Date(dateString);
    const diffMs = now.getTime() - logTime.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMinutes > 0) return `${diffMinutes}m ago`;
    return 'Just now';
  };

  if (loading) {
    return (
      <DashboardLayout
        title="Audit Logs"
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
            <p className="text-gray-600">Loading audit logs...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Audit Logs"
      torStatus={torStatus}
      headerActions={
        <div className="flex items-center space-x-4">
          <TorIndicator status={torStatus} size="small" />
        </div>
      }
    >
      <div className="space-y-6">
        {/* Audit Statistics */}
        <GridLayout columns={4} gap="lg">
          <CardLayout
            title="Total Logs"
            subtitle="All audit entries"
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white"
          >
            <div className="text-3xl font-bold">{statistics.totalLogs.toLocaleString()}</div>
            <div className="text-blue-100 text-sm">Audit entries</div>
          </CardLayout>

          <CardLayout
            title="Recent Activity"
            subtitle="Last hour"
            className="bg-gradient-to-r from-green-500 to-green-600 text-white"
          >
            <div className="text-3xl font-bold">{statistics.recentActivity}</div>
            <div className="text-green-100 text-sm">Events logged</div>
          </CardLayout>

          <CardLayout
            title="Error Rate"
            subtitle="System errors"
            className="bg-gradient-to-r from-red-500 to-red-600 text-white"
          >
            <div className="text-3xl font-bold">{statistics.errorRate.toFixed(1)}%</div>
            <div className="text-red-100 text-sm">Error percentage</div>
          </CardLayout>

          <CardLayout
            title="Top Category"
            subtitle="Most active"
            className="bg-gradient-to-r from-purple-500 to-purple-600 text-white"
          >
            <div className="text-3xl font-bold">
              {Object.entries(statistics.logsByCategory).reduce((a, b) => 
                statistics.logsByCategory[a[0]] > statistics.logsByCategory[b[0]] ? a : b
              )?.[0] || 'N/A'}
            </div>
            <div className="text-purple-100 text-sm">Category</div>
          </CardLayout>
        </GridLayout>

        {/* Filters */}
        <CardLayout
          title="Filters"
          subtitle="Filter audit logs by various criteria"
          className="bg-white border border-gray-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date Range</label>
              <div className="space-y-2">
                <input
                  type="datetime-local"
                  value={filters.dateRange.start}
                  onChange={(e) => setFilters(prev => ({ 
                    ...prev, 
                    dateRange: { ...prev.dateRange, start: e.target.value }
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="datetime-local"
                  value={filters.dateRange.end}
                  onChange={(e) => setFilters(prev => ({ 
                    ...prev, 
                    dateRange: { ...prev.dateRange, end: e.target.value }
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Level</label>
              <select
                value={filters.level}
                onChange={(e) => setFilters(prev => ({ ...prev, level: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Levels</option>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="debug">Debug</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={filters.category}
                onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Categories</option>
                <option value="authentication">Authentication</option>
                <option value="authorization">Authorization</option>
                <option value="session">Session</option>
                <option value="node">Node</option>
                <option value="blockchain">Blockchain</option>
                <option value="system">System</option>
                <option value="security">Security</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Statuses</option>
                <option value="success">Success</option>
                <option value="failure">Failure</option>
                <option value="pending">Pending</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">User ID</label>
              <input
                type="text"
                value={filters.userId}
                onChange={(e) => setFilters(prev => ({ ...prev, userId: e.target.value }))}
                placeholder="Filter by user ID"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Session ID</label>
              <input
                type="text"
                value={filters.sessionId}
                onChange={(e) => setFilters(prev => ({ ...prev, sessionId: e.target.value }))}
                placeholder="Filter by session ID"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Node ID</label>
              <input
                type="text"
                value={filters.nodeId}
                onChange={(e) => setFilters(prev => ({ ...prev, nodeId: e.target.value }))}
                placeholder="Filter by node ID"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() => setFilters({
                  dateRange: { start: '', end: '' },
                  level: 'all',
                  category: 'all',
                  status: 'all',
                  userId: '',
                  sessionId: '',
                  nodeId: '',
                  search: '',
                })}
                className="w-full px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              placeholder="Search in messages and actions"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </CardLayout>

        {/* Bulk Actions */}
        {selectedLogs.size > 0 && (
          <CardLayout
            title={`Bulk Actions (${selectedLogs.size} selected)`}
            subtitle="Perform actions on multiple logs"
            className="bg-blue-50 border border-blue-200"
          >
            <div className="flex flex-wrap gap-2">
              {bulkActions.map((action) => (
                <button
                  key={action.id}
                  onClick={() => handleBulkAction(action)}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  <span>{action.icon}</span>
                  <span>{action.label}</span>
                </button>
              ))}
              <button
                onClick={() => setSelectedLogs(new Set())}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear Selection
              </button>
            </div>
          </CardLayout>
        )}

        {/* Audit Logs Table */}
        <CardLayout
          title={`Audit Logs (${filteredLogs.length})`}
          subtitle="System audit trail"
          className="bg-white border border-gray-200"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left p-3">
                    <input
                      type="checkbox"
                      checked={selectedLogs.size === filteredLogs.length && filteredLogs.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-gray-300"
                    />
                  </th>
                  <th className="text-left p-3 font-medium">Timestamp</th>
                  <th className="text-left p-3 font-medium">Level</th>
                  <th className="text-left p-3 font-medium">Category</th>
                  <th className="text-left p-3 font-medium">Action</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">User ID</th>
                  <th className="text-left p-3 font-medium">Message</th>
                  <th className="text-left p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedLogs.has(log.id)}
                        onChange={() => handleLogSelect(log.id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleLogClick(log)}>
                      <div>{formatDate(log.timestamp)}</div>
                      <div className="text-xs text-gray-500">{formatRelativeTime(log.timestamp)}</div>
                    </td>
                    <td className="p-3" onClick={() => handleLogClick(log)}>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getLevelColor(log.level)}`}>
                        {log.level}
                      </span>
                    </td>
                    <td className="p-3" onClick={() => handleLogClick(log)}>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(log.category)}`}>
                        {log.category}
                      </span>
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleLogClick(log)}>
                      {log.action.replace(/_/g, ' ')}
                    </td>
                    <td className="p-3" onClick={() => handleLogClick(log)}>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(log.status)}`}>
                        {log.status}
                      </span>
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleLogClick(log)}>
                      {log.user_id ? (
                        <span className="font-mono">{log.user_id.substring(0, 8)}...</span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="p-3 text-sm max-w-xs truncate" onClick={() => handleLogClick(log)}>
                      {log.message}
                    </td>
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleLogClick(log)}
                        className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredLogs.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">📋</div>
                <p>No audit logs found</p>
                <p className="text-sm">Try adjusting your filters</p>
              </div>
            )}
          </div>
        </CardLayout>
      </div>

      {/* Log Details Modal */}
      <Modal
        isOpen={showLogDetails}
        onClose={() => setShowLogDetails(false)}
        title="Audit Log Details"
        size="lg"
      >
        {selectedLog && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Log ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedLog.id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Timestamp</label>
                <p className="mt-1 text-sm text-gray-900">{formatDate(selectedLog.timestamp)}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Level</label>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${getLevelColor(selectedLog.level)}`}>
                  {selectedLog.level}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Category</label>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(selectedLog.category)}`}>
                  {selectedLog.category}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Action</label>
                <p className="mt-1 text-sm text-gray-900">{selectedLog.action.replace(/_/g, ' ')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedLog.status)}`}>
                  {selectedLog.status}
                </span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Message</label>
              <p className="mt-1 text-sm text-gray-900">{selectedLog.message}</p>
            </div>

            {selectedLog.user_id && (
              <div>
                <label className="block text-sm font-medium text-gray-700">User ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedLog.user_id}</p>
              </div>
            )}

            {selectedLog.session_id && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Session ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedLog.session_id}</p>
              </div>
            )}

            {selectedLog.node_id && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Node ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedLog.node_id}</p>
              </div>
            )}

            {selectedLog.ip_address && (
              <div>
                <label className="block text-sm font-medium text-gray-700">IP Address</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedLog.ip_address}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Details</label>
              <pre className="bg-gray-50 p-3 rounded-md text-sm overflow-x-auto">
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Modal>

      {/* Bulk Action Confirmation Modal */}
      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={confirmBulkAction}
        title="Confirm Bulk Action"
        message={pendingBulkAction?.confirmationMessage || ''}
        confirmText="Confirm"
        cancelText="Cancel"
        type="warning"
      />
    </DashboardLayout>
  );
};

export default AuditPage;
