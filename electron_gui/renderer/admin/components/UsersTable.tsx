import React, { useState, useMemo } from 'react';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user' | 'node_operator';
  status: 'active' | 'suspended' | 'pending';
  lastLogin: string;
  sessionCount: number;
  totalSessions: number;
  createdAt: string;
  permissions: string[];
}

interface UsersTableProps {
  users: User[];
  loading?: boolean;
  onUserSelect?: (user: User) => void;
  onUserEdit?: (user: User) => void;
  onUserSuspend?: (userId: string) => void;
  onUserActivate?: (userId: string) => void;
  onBulkAction?: (action: string, userIds: string[]) => void;
  onRefresh?: () => void;
  className?: string;
}

export const UsersTable: React.FC<UsersTableProps> = ({
  users,
  loading = false,
  onUserSelect,
  onUserEdit,
  onUserSuspend,
  onUserActivate,
  onBulkAction,
  onRefresh,
  className = ''
}) => {
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [sortField, setSortField] = useState<keyof User>('username');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filterRole, setFilterRole] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedUsers(users.map(user => user.id));
    } else {
      setSelectedUsers([]);
    }
  };

  const handleSelectUser = (userId: string, checked: boolean) => {
    if (checked) {
      setSelectedUsers(prev => [...prev, userId]);
    } else {
      setSelectedUsers(prev => prev.filter(id => id !== userId));
    }
  };

  const handleSort = (field: keyof User) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedUsers = useMemo(() => {
    let filtered = users.filter(user => {
      if (filterRole && user.role !== filterRole) return false;
      if (filterStatus && user.status !== filterStatus) return false;
      if (searchTerm && !user.username.toLowerCase().includes(searchTerm.toLowerCase()) && 
          !user.email.toLowerCase().includes(searchTerm.toLowerCase())) return false;
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
  }, [users, filterRole, filterStatus, searchTerm, sortField, sortDirection]);

  const getRoleClass = (role: string) => {
    switch (role) {
      case 'admin':
        return 'role-admin';
      case 'user':
        return 'role-user';
      case 'node_operator':
        return 'role-node-operator';
      default:
        return '';
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'admin':
        return '👑';
      case 'user':
        return '👤';
      case 'node_operator':
        return '🖥️';
      default:
        return '👤';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'active':
        return 'status-active';
      case 'suspended':
        return 'status-suspended';
      case 'pending':
        return 'status-pending';
      default:
        return '';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return '🟢';
      case 'suspended':
        return '🔴';
      case 'pending':
        return '🟡';
      default:
        return '⚪';
    }
  };

  const handleBulkAction = (action: string) => {
    if (onBulkAction && selectedUsers.length > 0) {
      onBulkAction(action, selectedUsers);
      setSelectedUsers([]);
    }
  };

  if (loading) {
    return (
      <div className={`users-table loading ${className}`}>
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading users...</div>
      </div>
    );
  }

  return (
    <div className={`users-table ${className}`}>
      <div className="table-header">
        <div className="table-title">
          <h3>User Management</h3>
          <span className="user-count">{filteredAndSortedUsers.length} users</span>
        </div>
        <div className="table-actions">
          {selectedUsers.length > 0 && (
            <div className="bulk-actions">
              <button 
                className="btn danger"
                onClick={() => handleBulkAction('suspend')}
              >
                Suspend Selected ({selectedUsers.length})
              </button>
              <button 
                className="btn secondary"
                onClick={() => handleBulkAction('activate')}
              >
                Activate Selected
              </button>
            </div>
          )}
          <button className="btn primary">
            ➕ Add User
          </button>
          <button className="btn secondary" onClick={onRefresh}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="table-filters">
        <div className="filter-group">
          <label>Role:</label>
          <select 
            value={filterRole} 
            onChange={(e) => setFilterRole(e.target.value)}
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="user">User</option>
            <option value="node_operator">Node Operator</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Status:</label>
          <select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="pending">Pending</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Search:</label>
          <input 
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="table-container">
        <table className="users-table-content">
          <thead>
            <tr>
              <th className="checkbox-col">
                <input 
                  type="checkbox"
                  checked={selectedUsers.length === users.length && users.length > 0}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('username')}
              >
                Username {sortField === 'username' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('email')}
              >
                Email {sortField === 'email' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('role')}
              >
                Role {sortField === 'role' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('status')}
              >
                Status {sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('lastLogin')}
              >
                Last Login {sortField === 'lastLogin' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('sessionCount')}
              >
                Active Sessions {sortField === 'sessionCount' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('totalSessions')}
              >
                Total Sessions {sortField === 'totalSessions' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedUsers.map((user) => (
              <tr key={user.id} className="user-row">
                <td className="checkbox-col">
                  <input 
                    type="checkbox"
                    checked={selectedUsers.includes(user.id)}
                    onChange={(e) => handleSelectUser(user.id, e.target.checked)}
                  />
                </td>
                <td className="username-cell">
                  <button 
                    className="user-link"
                    onClick={() => onUserSelect?.(user)}
                  >
                    {user.username}
                  </button>
                </td>
                <td className="email-cell">{user.email}</td>
                <td className="role-cell">
                  <span className={`role-badge ${getRoleClass(user.role)}`}>
                    {getRoleIcon(user.role)} {user.role.replace('_', ' ')}
                  </span>
                </td>
                <td className="status-cell">
                  <span className={`status-badge ${getStatusClass(user.status)}`}>
                    {getStatusIcon(user.status)} {user.status}
                  </span>
                </td>
                <td className="last-login">{user.lastLogin}</td>
                <td className="session-count">{user.sessionCount}</td>
                <td className="total-sessions">{user.totalSessions}</td>
                <td className="actions-cell">
                  <div className="action-buttons">
                    <button 
                      className="btn-icon"
                      onClick={() => onUserSelect?.(user)}
                      title="View Details"
                    >
                      👁️
                    </button>
                    <button 
                      className="btn-icon"
                      onClick={() => onUserEdit?.(user)}
                      title="Edit User"
                    >
                      ✏️
                    </button>
                    {user.status === 'active' ? (
                      <button 
                        className="btn-icon danger"
                        onClick={() => onUserSuspend?.(user.id)}
                        title="Suspend User"
                      >
                        🚫
                      </button>
                    ) : (
                      <button 
                        className="btn-icon success"
                        onClick={() => onUserActivate?.(user.id)}
                        title="Activate User"
                      >
                        ✅
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredAndSortedUsers.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">👥</div>
          <div className="empty-text">No users found</div>
          <div className="empty-subtext">
            {users.length === 0 
              ? 'No users are registered'
              : 'Try adjusting your filters'
            }
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersTable;
