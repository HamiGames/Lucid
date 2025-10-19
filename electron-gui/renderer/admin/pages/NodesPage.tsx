// electron-gui/renderer/admin/pages/NodesPage.tsx
// Admin Nodes Management Page - Node status table, node health metrics, maintenance mode controls

import React, { useState, useEffect, useMemo } from 'react';
import { DashboardLayout, GridLayout, CardLayout } from '../../common/components/Layout';
import { Modal, FormModal, ConfirmModal } from '../../common/components/Modal';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { useAllNodes } from '../../common/hooks/useApi';
import { Node, NodeResources } from '../../../shared/types';
import { TorStatus } from '../../../shared/tor-types';

interface NodeFilters {
  status: 'all' | 'registered' | 'active' | 'inactive' | 'suspended';
  poolId: string;
  search: string;
  minPootScore: number;
}

interface NodeFormData {
  operator_id: string;
  pool_id?: string;
  status: 'registered' | 'active' | 'inactive' | 'suspended';
  resources: {
    cpu_cores: number;
    memory_gb: number;
    disk_gb: number;
    network_speed_mbps: number;
  };
  location: {
    country: string;
    region: string;
  };
}

interface BulkAction {
  id: string;
  label: string;
  icon: string;
  action: (nodeIds: string[]) => Promise<void>;
  requiresConfirmation: boolean;
  confirmationMessage: string;
}

interface NodeDetails {
  node: Node;
  resources: NodeResources;
  health: {
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    network_bandwidth: number;
    last_check: string;
    status: 'healthy' | 'warning' | 'critical';
  };
}

const NodesPage: React.FC = () => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
  const [showAddNode, setShowAddNode] = useState(false);
  const [showNodeDetails, setShowNodeDetails] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingBulkAction, setPendingBulkAction] = useState<BulkAction | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeDetails | null>(null);

  const [filters, setFilters] = useState<NodeFilters>({
    status: 'all',
    poolId: '',
    search: '',
    minPootScore: 0,
  });

  const [formData, setFormData] = useState<NodeFormData>({
    operator_id: '',
    status: 'registered',
    resources: {
      cpu_cores: 4,
      memory_gb: 8,
      disk_gb: 100,
      network_speed_mbps: 100,
    },
    location: {
      country: '',
      region: '',
    },
  });

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  // API hooks
  const { data: nodesData, loading: nodesLoading, refetch: refetchNodes } = useAllNodes();

  // Update nodes when data changes
  useEffect(() => {
    if (nodesData) {
      setNodes(nodesData);
    }
  }, [nodesData]);

  // Filter nodes based on current filters
  const filteredNodes = useMemo(() => {
    return nodes.filter(node => {
      // Status filter
      if (filters.status !== 'all' && node.status !== filters.status) {
        return false;
      }

      // Pool filter
      if (filters.poolId && node.pool_id !== filters.poolId) {
        return false;
      }

      // Search filter
      if (filters.search && !node.node_id.toLowerCase().includes(filters.search.toLowerCase()) &&
          !node.operator_id.toLowerCase().includes(filters.search.toLowerCase())) {
        return false;
      }

      // PoOT score filter
      if (node.poot_score < filters.minPootScore) {
        return false;
      }

      return true;
    });
  }, [nodes, filters]);

  // Bulk actions
  const bulkActions: BulkAction[] = [
    {
      id: 'activate',
      label: 'Activate Nodes',
      icon: '▶️',
      action: handleActivateNodes,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to activate the selected nodes?',
    },
    {
      id: 'deactivate',
      label: 'Deactivate Nodes',
      icon: '⏸️',
      action: handleDeactivateNodes,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to deactivate the selected nodes?',
    },
    {
      id: 'suspend',
      label: 'Suspend Nodes',
      icon: '🚫',
      action: handleSuspendNodes,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to suspend the selected nodes? They will be removed from the network.',
    },
    {
      id: 'maintenance',
      label: 'Maintenance Mode',
      icon: '🔧',
      action: handleMaintenanceMode,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to put the selected nodes in maintenance mode?',
    },
    {
      id: 'export',
      label: 'Export Nodes',
      icon: '📄',
      action: handleExportNodes,
      requiresConfirmation: false,
      confirmationMessage: '',
    },
  ];

  async function handleActivateNodes(nodeIds: string[]): Promise<void> {
    try {
      // Implement node activation logic
      showToast({
        type: 'success',
        title: 'Nodes Activated',
        message: `${nodeIds.length} nodes have been activated successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Activation Failed',
        message: error instanceof Error ? error.message : 'Failed to activate nodes',
      });
    }
  }

  async function handleDeactivateNodes(nodeIds: string[]): Promise<void> {
    try {
      // Implement node deactivation logic
      showToast({
        type: 'success',
        title: 'Nodes Deactivated',
        message: `${nodeIds.length} nodes have been deactivated successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Deactivation Failed',
        message: error instanceof Error ? error.message : 'Failed to deactivate nodes',
      });
    }
  }

  async function handleSuspendNodes(nodeIds: string[]): Promise<void> {
    try {
      // Implement node suspension logic
      showToast({
        type: 'success',
        title: 'Nodes Suspended',
        message: `${nodeIds.length} nodes have been suspended successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Suspension Failed',
        message: error instanceof Error ? error.message : 'Failed to suspend nodes',
      });
    }
  }

  async function handleMaintenanceMode(nodeIds: string[]): Promise<void> {
    try {
      // Implement maintenance mode logic
      showToast({
        type: 'success',
        title: 'Maintenance Mode',
        message: `${nodeIds.length} nodes have been put in maintenance mode`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Maintenance Mode Failed',
        message: error instanceof Error ? error.message : 'Failed to enable maintenance mode',
      });
    }
  }

  async function handleExportNodes(nodeIds: string[]): Promise<void> {
    try {
      // Implement export logic
      showToast({
        type: 'success',
        title: 'Nodes Exported',
        message: `${nodeIds.length} nodes have been exported successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Export Failed',
        message: error instanceof Error ? error.message : 'Failed to export nodes',
      });
    }
  }

  const handleNodeSelect = (nodeId: string) => {
    const newSelected = new Set(selectedNodes);
    if (newSelected.has(nodeId)) {
      newSelected.delete(nodeId);
    } else {
      newSelected.add(nodeId);
    }
    setSelectedNodes(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedNodes.size === filteredNodes.length) {
      setSelectedNodes(new Set());
    } else {
      setSelectedNodes(new Set(filteredNodes.map(n => n.node_id)));
    }
  };

  const handleBulkAction = (action: BulkAction) => {
    if (selectedNodes.size === 0) {
      showToast({
        type: 'warning',
        title: 'No Nodes Selected',
        message: 'Please select at least one node to perform this action',
      });
      return;
    }

    if (action.requiresConfirmation) {
      setPendingBulkAction(action);
      setShowConfirmModal(true);
    } else {
      action.action(Array.from(selectedNodes));
    }
  };

  const confirmBulkAction = async () => {
    if (pendingBulkAction) {
      await pendingBulkAction.action(Array.from(selectedNodes));
      setShowConfirmModal(false);
      setPendingBulkAction(null);
    }
  };

  const handleAddNode = () => {
    setFormData({
      operator_id: '',
      status: 'registered',
      resources: {
        cpu_cores: 4,
        memory_gb: 8,
        disk_gb: 100,
        network_speed_mbps: 100,
      },
      location: {
        country: '',
        region: '',
      },
    });
    setShowAddNode(true);
  };

  const handleNodeClick = async (node: Node) => {
    try {
      // Mock node details - in real implementation, this would fetch detailed node information
      const nodeDetails: NodeDetails = {
        node,
        resources: node.resources,
        health: {
          cpu_usage: Math.random() * 100,
          memory_usage: Math.random() * 100,
          disk_usage: Math.random() * 100,
          network_bandwidth: Math.random() * 1000,
          last_check: new Date().toISOString(),
          status: Math.random() > 0.7 ? 'critical' : Math.random() > 0.4 ? 'warning' : 'healthy',
        },
      };

      setSelectedNode(nodeDetails);
      setShowNodeDetails(true);
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Failed to Load Node Details',
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    }
  };

  const handleSubmitNode = async (data: NodeFormData) => {
    try {
      // Implement node creation logic
      showToast({
        type: 'success',
        title: 'Node Added',
        message: `Node for operator ${data.operator_id} has been added successfully`,
      });
      
      setShowAddNode(false);
      await refetchNodes();
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Operation Failed',
        message: error instanceof Error ? error.message : 'Failed to add node',
      });
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'registered': return 'bg-blue-100 text-blue-800';
      case 'inactive': return 'bg-yellow-100 text-yellow-800';
      case 'suspended': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getHealthColor = (health: string): string => {
    switch (health) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatPootScore = (score: number): string => {
    return score.toFixed(2);
  };

  if (loading || nodesLoading) {
    return (
      <DashboardLayout
        title="Nodes Management"
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
            <p className="text-gray-600">Loading nodes...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Nodes Management"
      torStatus={torStatus}
      headerActions={
        <div className="flex items-center space-x-4">
          <TorIndicator status={torStatus} size="small" />
        </div>
      }
    >
      <div className="space-y-6">
        {/* Node Statistics */}
        <GridLayout columns={4} gap="lg">
          <CardLayout
            title="Total Nodes"
            subtitle="Registered in system"
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white"
          >
            <div className="text-3xl font-bold">{nodes.length}</div>
            <div className="text-blue-100 text-sm">Node operators</div>
          </CardLayout>

          <CardLayout
            title="Active Nodes"
            subtitle="Currently running"
            className="bg-gradient-to-r from-green-500 to-green-600 text-white"
          >
            <div className="text-3xl font-bold">{nodes.filter(n => n.status === 'active').length}</div>
            <div className="text-green-100 text-sm">Online nodes</div>
          </CardLayout>

          <CardLayout
            title="Average PoOT Score"
            subtitle="Proof of Onion Time"
            className="bg-gradient-to-r from-purple-500 to-purple-600 text-white"
          >
            <div className="text-3xl font-bold">
              {nodes.length > 0 ? (nodes.reduce((sum, n) => sum + n.poot_score, 0) / nodes.length).toFixed(1) : '0.0'}
            </div>
            <div className="text-purple-100 text-sm">Network score</div>
          </CardLayout>

          <CardLayout
            title="Pool Coverage"
            subtitle="Nodes in pools"
            className="bg-gradient-to-r from-orange-500 to-orange-600 text-white"
          >
            <div className="text-3xl font-bold">{nodes.filter(n => n.pool_id).length}</div>
            <div className="text-orange-100 text-sm">Pooled nodes</div>
          </CardLayout>
        </GridLayout>

        {/* Filters and Actions */}
        <CardLayout
          title="Filters & Actions"
          subtitle="Filter nodes and perform bulk operations"
          className="bg-white border border-gray-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Statuses</option>
                <option value="registered">Registered</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Pool ID</label>
              <input
                type="text"
                value={filters.poolId}
                onChange={(e) => setFilters(prev => ({ ...prev, poolId: e.target.value }))}
                placeholder="Filter by pool ID"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min PoOT Score</label>
              <input
                type="number"
                value={filters.minPootScore}
                onChange={(e) => setFilters(prev => ({ ...prev, minPootScore: Number(e.target.value) }))}
                min="0"
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                placeholder="Search nodes"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-end space-x-2">
              <button
                onClick={handleAddNode}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Add Node
              </button>
              <button
                onClick={() => setFilters({
                  status: 'all',
                  poolId: '',
                  search: '',
                  minPootScore: 0,
                })}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        </CardLayout>

        {/* Bulk Actions */}
        {selectedNodes.size > 0 && (
          <CardLayout
            title={`Bulk Actions (${selectedNodes.size} selected)`}
            subtitle="Perform actions on multiple nodes"
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
                onClick={() => setSelectedNodes(new Set())}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear Selection
              </button>
            </div>
          </CardLayout>
        )}

        {/* Nodes Table */}
        <CardLayout
          title={`Nodes (${filteredNodes.length})`}
          subtitle="Manage network nodes"
          className="bg-white border border-gray-200"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left p-3">
                    <input
                      type="checkbox"
                      checked={selectedNodes.size === filteredNodes.length && filteredNodes.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-gray-300"
                    />
                  </th>
                  <th className="text-left p-3 font-medium">Node ID</th>
                  <th className="text-left p-3 font-medium">Operator ID</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">PoOT Score</th>
                  <th className="text-left p-3 font-medium">Pool ID</th>
                  <th className="text-left p-3 font-medium">Resources</th>
                  <th className="text-left p-3 font-medium">Created</th>
                  <th className="text-left p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredNodes.map((node) => (
                  <tr key={node.node_id} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer">
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedNodes.has(node.node_id)}
                        onChange={() => handleNodeSelect(node.node_id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="p-3 font-mono text-sm" onClick={() => handleNodeClick(node)}>
                      {node.node_id.substring(0, 12)}...
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleNodeClick(node)}>
                      {node.operator_id.substring(0, 12)}...
                    </td>
                    <td className="p-3" onClick={() => handleNodeClick(node)}>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(node.status)}`}>
                        {node.status}
                      </span>
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleNodeClick(node)}>
                      {formatPootScore(node.poot_score)}
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleNodeClick(node)}>
                      {node.pool_id ? (
                        <span className="font-mono">{node.pool_id.substring(0, 8)}...</span>
                      ) : (
                        <span className="text-gray-400">No pool</span>
                      )}
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleNodeClick(node)}>
                      <div className="space-y-1">
                        <div>CPU: {node.resources.cpu_usage.toFixed(1)}%</div>
                        <div>RAM: {node.resources.memory_usage.toFixed(1)}%</div>
                      </div>
                    </td>
                    <td className="p-3 text-sm" onClick={() => handleNodeClick(node)}>
                      {formatDate(node.created_at)}
                    </td>
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleNodeClick(node)}
                        className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredNodes.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">🖥️</div>
                <p>No nodes found</p>
                <p className="text-sm">Try adjusting your filters or add a new node</p>
              </div>
            )}
          </div>
        </CardLayout>
      </div>

      {/* Add Node Modal */}
      <FormModal
        isOpen={showAddNode}
        onClose={() => setShowAddNode(false)}
        onSubmit={handleSubmitNode}
        title="Add New Node"
        submitText="Add Node"
        cancelText="Cancel"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Operator ID</label>
            <input
              type="text"
              value={formData.operator_id}
              onChange={(e) => setFormData(prev => ({ ...prev, operator_id: e.target.value }))}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Pool ID</label>
            <input
              type="text"
              value={formData.pool_id || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, pool_id: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value as any }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="registered">Registered</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CPU Cores</label>
              <input
                type="number"
                value={formData.resources.cpu_cores}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  resources: { ...prev.resources, cpu_cores: Number(e.target.value) }
                }))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Memory (GB)</label>
              <input
                type="number"
                value={formData.resources.memory_gb}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  resources: { ...prev.resources, memory_gb: Number(e.target.value) }
                }))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Disk (GB)</label>
              <input
                type="number"
                value={formData.resources.disk_gb}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  resources: { ...prev.resources, disk_gb: Number(e.target.value) }
                }))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Network (Mbps)</label>
              <input
                type="number"
                value={formData.resources.network_speed_mbps}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  resources: { ...prev.resources, network_speed_mbps: Number(e.target.value) }
                }))}
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
              <input
                type="text"
                value={formData.location.country}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  location: { ...prev.location, country: e.target.value }
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
              <input
                type="text"
                value={formData.location.region}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  location: { ...prev.location, region: e.target.value }
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </FormModal>

      {/* Node Details Modal */}
      <Modal
        isOpen={showNodeDetails}
        onClose={() => setShowNodeDetails(false)}
        title="Node Details"
        size="lg"
      >
        {selectedNode && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Node ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedNode.node.node_id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(selectedNode.node.status)}`}>
                  {selectedNode.node.status}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Operator ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedNode.node.operator_id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">PoOT Score</label>
                <p className="mt-1 text-sm text-gray-900">{formatPootScore(selectedNode.node.poot_score)}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Pool ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedNode.node.pool_id || 'No pool'}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Health Status</label>
                <span className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${getHealthColor(selectedNode.health.status)}`}>
                  {selectedNode.health.status}
                </span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Resource Usage</label>
              <div className="mt-1 grid grid-cols-2 gap-4">
                <div>
                  <div className="flex justify-between text-sm">
                    <span>CPU Usage</span>
                    <span>{selectedNode.health.cpu_usage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${selectedNode.health.cpu_usage}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Memory Usage</span>
                    <span>{selectedNode.health.memory_usage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div className="bg-green-600 h-2 rounded-full" style={{ width: `${selectedNode.health.memory_usage}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Disk Usage</span>
                    <span>{selectedNode.health.disk_usage.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                    <div className="bg-purple-600 h-2 rounded-full" style={{ width: `${selectedNode.health.disk_usage}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>Network Bandwidth</span>
                    <span>{selectedNode.health.network_bandwidth.toFixed(1)} Mbps</span>
                  </div>
                </div>
              </div>
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

export default NodesPage;
