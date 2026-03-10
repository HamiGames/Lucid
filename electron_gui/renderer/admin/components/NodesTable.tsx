import React, { useState, useMemo } from 'react';

interface Node {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'maintenance';
  ip: string;
  location: string;
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkLatency: number;
  lastSeen: string;
  sessionCount: number;
  totalSessions: number;
  uptime: string;
  version: string;
}

interface NodesTableProps {
  nodes: Node[];
  loading?: boolean;
  onNodeSelect?: (node: Node) => void;
  onNodeMaintenance?: (nodeId: string) => void;
  onNodeRestart?: (nodeId: string) => void;
  onBulkAction?: (action: string, nodeIds: string[]) => void;
  onRefresh?: () => void;
  className?: string;
}

export const NodesTable: React.FC<NodesTableProps> = ({
  nodes,
  loading = false,
  onNodeSelect,
  onNodeMaintenance,
  onNodeRestart,
  onBulkAction,
  onRefresh,
  className = ''
}) => {
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [sortField, setSortField] = useState<keyof Node>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterLocation, setFilterLocation] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedNodes(nodes.map(node => node.id));
    } else {
      setSelectedNodes([]);
    }
  };

  const handleSelectNode = (nodeId: string, checked: boolean) => {
    if (checked) {
      setSelectedNodes(prev => [...prev, nodeId]);
    } else {
      setSelectedNodes(prev => prev.filter(id => id !== nodeId));
    }
  };

  const handleSort = (field: keyof Node) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedNodes = useMemo(() => {
    let filtered = nodes.filter(node => {
      if (filterStatus && node.status !== filterStatus) return false;
      if (filterLocation && !node.location.toLowerCase().includes(filterLocation.toLowerCase())) return false;
      if (searchTerm && !node.name.toLowerCase().includes(searchTerm.toLowerCase()) && 
          !node.ip.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });

    return filtered.sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return sortDirection === 'asc' 
        ? (aValue < bValue ? -1 : 1)
        : (aValue > bValue ? -1 : 1);
    });
  }, [nodes, filterStatus, filterLocation, searchTerm, sortField, sortDirection]);

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'online':
        return 'status-online';
      case 'offline':
        return 'status-offline';
      case 'maintenance':
        return 'status-maintenance';
      default:
        return '';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online':
        return '🟢';
      case 'offline':
        return '🔴';
      case 'maintenance':
        return '🟡';
      default:
        return '⚪';
    }
  };

  const getUsageClass = (usage: number) => {
    if (usage >= 90) return 'usage-critical';
    if (usage >= 70) return 'usage-warning';
    return 'usage-normal';
  };

  const handleBulkAction = (action: string) => {
    if (onBulkAction && selectedNodes.length > 0) {
      onBulkAction(action, selectedNodes);
      setSelectedNodes([]);
    }
  };

  if (loading) {
    return (
      <div className={`nodes-table loading ${className}`}>
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading nodes...</div>
      </div>
    );
  }

  return (
    <div className={`nodes-table ${className}`}>
      <div className="table-header">
        <div className="table-title">
          <h3>Node Management</h3>
          <span className="node-count">{filteredAndSortedNodes.length} nodes</span>
        </div>
        <div className="table-actions">
          {selectedNodes.length > 0 && (
            <div className="bulk-actions">
              <button 
                className="btn warning"
                onClick={() => handleBulkAction('maintenance')}
              >
                Maintenance Mode ({selectedNodes.length})
              </button>
              <button 
                className="btn secondary"
                onClick={() => handleBulkAction('restart')}
              >
                Restart Selected
              </button>
            </div>
          )}
          <button className="btn primary">
            ➕ Add Node
          </button>
          <button className="btn secondary" onClick={onRefresh}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="table-filters">
        <div className="filter-group">
          <label>Status:</label>
          <select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="maintenance">Maintenance</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Location:</label>
          <input 
            type="text"
            placeholder="Filter by location..."
            value={filterLocation}
            onChange={(e) => setFilterLocation(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>Search:</label>
          <input 
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="table-container">
        <table className="nodes-table-content">
          <thead>
            <tr>
              <th className="checkbox-col">
                <input 
                  type="checkbox"
                  checked={selectedNodes.length === nodes.length && nodes.length > 0}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('name')}
              >
                Node Name {sortField === 'name' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('status')}
              >
                Status {sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('ip')}
              >
                IP Address {sortField === 'ip' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('location')}
              >
                Location {sortField === 'location' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('cpuUsage')}
              >
                CPU {sortField === 'cpuUsage' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('memoryUsage')}
              >
                Memory {sortField === 'memoryUsage' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('sessionCount')}
              >
                Active Sessions {sortField === 'sessionCount' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('lastSeen')}
              >
                Last Seen {sortField === 'lastSeen' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedNodes.map((node) => (
              <tr key={node.id} className="node-row">
                <td className="checkbox-col">
                  <input 
                    type="checkbox"
                    checked={selectedNodes.includes(node.id)}
                    onChange={(e) => handleSelectNode(node.id, e.target.checked)}
                  />
                </td>
                <td className="node-name">
                  <button 
                    className="node-link"
                    onClick={() => onNodeSelect?.(node)}
                  >
                    {node.name}
                  </button>
                  <div className="node-version">v{node.version}</div>
                </td>
                <td className="status-cell">
                  <span className={`status-badge ${getStatusClass(node.status)}`}>
                    {getStatusIcon(node.status)} {node.status}
                  </span>
                </td>
                <td className="ip-cell">{node.ip}</td>
                <td className="location-cell">{node.location}</td>
                <td className="cpu-cell">
                  <div className="usage-bar">
                    <div 
                      className={`usage-fill ${getUsageClass(node.cpuUsage)}`}
                      style={{ width: `${node.cpuUsage}%` }}
                    ></div>
                    <span className="usage-text">{node.cpuUsage}%</span>
                  </div>
                </td>
                <td className="memory-cell">
                  <div className="usage-bar">
                    <div 
                      className={`usage-fill ${getUsageClass(node.memoryUsage)}`}
                      style={{ width: `${node.memoryUsage}%` }}
                    ></div>
                    <span className="usage-text">{node.memoryUsage}%</span>
                  </div>
                </td>
                <td className="session-count">{node.sessionCount}</td>
                <td className="last-seen">{node.lastSeen}</td>
                <td className="actions-cell">
                  <div className="action-buttons">
                    <button 
                      className="btn-icon"
                      onClick={() => onNodeSelect?.(node)}
                      title="View Details"
                    >
                      👁️
                    </button>
                    {node.status === 'online' ? (
                      <button 
                        className="btn-icon warning"
                        onClick={() => onNodeMaintenance?.(node.id)}
                        title="Maintenance Mode"
                      >
                        🔧
                      </button>
                    ) : (
                      <button 
                        className="btn-icon success"
                        onClick={() => onNodeRestart?.(node.id)}
                        title="Restart Node"
                      >
                        🔄
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredAndSortedNodes.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">🖥️</div>
          <div className="empty-text">No nodes found</div>
          <div className="empty-subtext">
            {nodes.length === 0 
              ? 'No nodes are registered'
              : 'Try adjusting your filters'
            }
          </div>
        </div>
      )}
    </div>
  );
};

export default NodesTable;
