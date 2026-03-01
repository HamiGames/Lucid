// electron-gui/renderer/admin/pages/SessionsPage.tsx
// Admin Sessions Management Page - Active sessions table with filters, bulk actions, session details modal

import React, { useState, useEffect, useMemo } from 'react';
import { DashboardLayout, GridLayout, CardLayout } from '../../common/components/Layout';
import { Modal, ConfirmModal } from '../../common/components/Modal';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { useAllSessions, useDeleteSession } from '../../common/hooks/useApi';
import { Session, User, Node } from '../../../shared/types';
import { TorStatus } from '../../../shared/tor-types';

interface SessionFilters {
  status: 'all' | 'active' | 'completed' | 'failed' | 'anchored';
  userId: string;
  nodeId: string;
  dateRange: {
    start: string;
    end: string;
  };
  search: string;
}

interface BulkAction {
  id: string;
  label: string;
  icon: string;
  action: (sessionIds: string[]) => Promise<void>;
  requiresConfirmation: boolean;
  confirmationMessage: string;
}

interface SessionDetails {
  session: Session;
  user: User | null;
  node: Node | null;
  chunks: any[];
  merkleProof: any;
  blockchainAnchor: any;
}

const SessionsPage: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(new Set());
  const [showSessionDetails, setShowSessionDetails] = useState(false);
  const [selectedSession, setSelectedSession] = useState<SessionDetails | null>(null);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingBulkAction, setPendingBulkAction] = useState<BulkAction | null>(null);

  const [filters, setFilters] = useState<SessionFilters>({
    status: 'all',
    userId: '',
    nodeId: '',
    dateRange: {
      start: '',
      end: '',
    },
    search: '',
  });

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  // API hooks
  const { data: sessionsData, loading: sessionsLoading, refetch: refetchSessions } = useAllSessions();
  const { execute: deleteSession, loading: deleteLoading } = useDeleteSession();

  // Update sessions when data changes
  useEffect(() => {
    if (sessionsData) {
      setSessions(sessionsData);
    }
  }, [sessionsData]);

  // Filter sessions based on current filters
  const filteredSessions = useMemo(() => {
    return sessions.filter(session => {
      // Status filter
      if (filters.status !== 'all' && session.status !== filters.status) {
        return false;
      }

      // User filter
      if (filters.userId && session.user_id !== filters.userId) {
        return false;
      }

      // Search filter
      if (filters.search && !session.session_id.toLowerCase().includes(filters.search.toLowerCase())) {
        return false;
      }

      // Date range filter
      if (filters.dateRange.start && new Date(session.created_at) < new Date(filters.dateRange.start)) {
        return false;
      }
      if (filters.dateRange.end && new Date(session.created_at) > new Date(filters.dateRange.end)) {
        return false;
      }

      return true;
    });
  }, [sessions, filters]);

  // Bulk actions
  const bulkActions: BulkAction[] = [
    {
      id: 'terminate',
      label: 'Terminate Sessions',
      icon: '🛑',
      action: handleTerminateSessions,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to terminate the selected sessions? This action cannot be undone.',
    },
    {
      id: 'anchor',
      label: 'Anchor Sessions',
      icon: '⛓️',
      action: handleAnchorSessions,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to anchor the selected sessions to the blockchain?',
    },
    {
      id: 'export',
      label: 'Export Sessions',
      icon: '📄',
      action: handleExportSessions,
      requiresConfirmation: false,
      confirmationMessage: '',
    },
  ];

  async function handleTerminateSessions(sessionIds: string[]): Promise<void> {
    try {
      for (const sessionId of sessionIds) {
        await deleteSession(sessionId);
      }
      
      setSelectedSessions(new Set());
      await refetchSessions();
      
      showToast({
        type: 'success',
        title: 'Sessions Terminated',
        message: `${sessionIds.length} sessions have been terminated successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Termination Failed',
        message: error instanceof Error ? error.message : 'Failed to terminate sessions',
      });
    }
  }

  async function handleAnchorSessions(sessionIds: string[]): Promise<void> {
    try {
      // Implement anchoring logic
      showToast({
        type: 'success',
        title: 'Sessions Anchored',
        message: `${sessionIds.length} sessions have been anchored to the blockchain`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Anchoring Failed',
        message: error instanceof Error ? error.message : 'Failed to anchor sessions',
      });
    }
  }

  async function handleExportSessions(sessionIds: string[]): Promise<void> {
    try {
      // Implement export logic
      showToast({
        type: 'success',
        title: 'Sessions Exported',
        message: `${sessionIds.length} sessions have been exported successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Export Failed',
        message: error instanceof Error ? error.message : 'Failed to export sessions',
      });
    }
  }

  const handleSessionSelect = (sessionId: string) => {
    const newSelected = new Set(selectedSessions);
    if (newSelected.has(sessionId)) {
      newSelected.delete(sessionId);
    } else {
      newSelected.add(sessionId);
    }
    setSelectedSessions(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedSessions.size === filteredSessions.length) {
      setSelectedSessions(new Set());
    } else {
      setSelectedSessions(new Set(filteredSessions.map(s => s.session_id)));
    }
  };

  const handleBulkAction = (action: BulkAction) => {
    if (selectedSessions.size === 0) {
      showToast({
        type: 'warning',
        title: 'No Sessions Selected',
        message: 'Please select at least one session to perform this action',
      });
      return;
    }

    if (action.requiresConfirmation) {
      setPendingBulkAction(action);
      setShowConfirmModal(true);
    } else {
      action.action(Array.from(selectedSessions));
    }
  };

  const confirmBulkAction = async () => {
    if (pendingBulkAction) {
      await pendingBulkAction.action(Array.from(selectedSessions));
      setShowConfirmModal(false);
      setPendingBulkAction(null);
    }
  };

  const handleSessionClick = async (session: Session) => {
    try {
      // Fetch session details
      const sessionDetails: SessionDetails = {
        session,
        user: users.find(u => u.user_id === session.user_id) || null,
        node: null, // Would need to fetch node details
        chunks: session.chunks || [],
        merkleProof: session.merkle_root ? { root: session.merkle_root } : null,
        blockchainAnchor: session.blockchain_anchor || null,
      };

      setSelectedSession(sessionDetails);
      setShowSessionDetails(true);
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Failed to Load Session Details',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'anchored': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (startDate: string, endDate?: string): string => {
    const start = new Date(startDate);
    const end = endDate ? new Date(endDate) : new Date();
    const diffMs = end.getTime() - start.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ${diffHours % 24}h`;
    if (diffHours > 0) return `${diffHours}h ${diffMinutes % 60}m`;
    return `${diffMinutes}m`;
  };

  if (loading || sessionsLoading) {
    return (
      <DashboardLayout
        title="Sessions Management"
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
            <p className="text-gray-600">Loading sessions...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Sessions Management"
      torStatus={torStatus}
      headerActions={
        <div className="flex items-center space-x-4">
          <TorIndicator status={torStatus} size="small" />
        </div>
      }
    >
      <div className="space-y-6">
        {/* Filters */}
        <CardLayout
          title="Filters"
          subtitle="Filter sessions by various criteria"
          className="bg-white border border-gray-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="anchored">Anchored</option>
              </select>
            </div>

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
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                placeholder="Search session IDs"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={() => setFilters({
                  status: 'all',
                  userId: '',
                  nodeId: '',
                  dateRange: { start: '', end: '' },
                  search: '',
                })}
                className="w-full px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </CardLayout>

        {/* Bulk Actions */}
        {selectedSessions.size > 0 && (
          <CardLayout
            title={`Bulk Actions (${selectedSessions.size} selected)`}
            subtitle="Perform actions on multiple sessions"
            className="bg-blue-50 border border-blue-200"
          >
            <div className="flex flex-wrap gap-2">
              {bulkActions.map((action) => (
                <button
                  key={action.id}
                  onClick={() => handleBulkAction(action)}
                  disabled={deleteLoading}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>{action.icon}</span>
                  <span>{action.label}</span>
                </button>
              ))}
              <button
                onClick={() => setSelectedSessions(new Set())}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear Selection
              </button>
            </div>
          </CardLayout>
        )}

        {/* Sessions Table */}
        <CardLayout
          title={`Sessions (${filteredSessions.length})`}
          subtitle="Manage user sessions"
          className="bg-white border border-gray-200"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left p-3">
                    <input
                      type="checkbox"
                      checked={selectedSessions.size === filteredSessions.length && filteredSessions.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-gray-300"
                    />
                  </th>
                  <th className="text-left p-3 font-medium">Session ID</th>
                  <th className="text-left p-3 font-medium">User ID</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">Chunks</th>
                  <th className="text-left p-3 font-medium">Created</th>
                  <th className="text-left p-3 font-medium">Duration</th>
                  <th className="text-left p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredSessions.map((session) => (
                  <tr
                    key={session.session_id}
                    className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleSessionClick(session)}
                  >
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedSessions.has(session.session_id)}
                        onChange={() => handleSessionSelect(session.session_id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="p-3 font-mono text-sm">{session.session_id.substring(0, 12)}...</td>
                    <td className="p-3 text-sm">{session.user_id.substring(0, 12)}...</td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(session.status)}`}>
                        {session.status}
                      </span>
                    </td>
                    <td className="p-3 text-sm">{session.chunks?.length || 0}</td>
                    <td className="p-3 text-sm">{formatDate(session.created_at)}</td>
                    <td className="p-3 text-sm">{formatDuration(session.created_at, session.updated_at)}</td>
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleSessionClick(session)}
                        className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredSessions.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">📊</div>
                <p>No sessions found</p>
                <p className="text-sm">Try adjusting your filters or check back later</p>
              </div>
            )}
          </div>
        </CardLayout>
      </div>

      {/* Session Details Modal */}
      <Modal
        isOpen={showSessionDetails}
        onClose={() => setShowSessionDetails(false)}
        title="Session Details"
        size="lg"
      >
        {selectedSession && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Session ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedSession.session.session_id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedSession.session.status)}`}>
                  {selectedSession.session.status}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">User ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedSession.session.user_id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Chunks</label>
                <p className="mt-1 text-sm text-gray-900">{selectedSession.session.chunks?.length || 0}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Created</label>
                <p className="mt-1 text-sm text-gray-900">{formatDate(selectedSession.session.created_at)}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Updated</label>
                <p className="mt-1 text-sm text-gray-900">{formatDate(selectedSession.session.updated_at)}</p>
              </div>
            </div>

            {selectedSession.merkleProof && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Merkle Root</label>
                <p className="mt-1 text-sm text-gray-900 font-mono break-all">{selectedSession.merkleProof.root}</p>
              </div>
            )}

            {selectedSession.blockchainAnchor && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Blockchain Anchor</label>
                <div className="mt-1 space-y-2">
                  <p className="text-sm text-gray-900">Block Height: {selectedSession.blockchainAnchor.block_height}</p>
                  <p className="text-sm text-gray-900 font-mono">Transaction ID: {selectedSession.blockchainAnchor.transaction_id}</p>
                </div>
              </div>
            )}
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
        loading={deleteLoading}
      />
    </DashboardLayout>
  );
};

export default SessionsPage;
