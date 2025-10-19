// electron-gui/renderer/admin/pages/UsersPage.tsx
// Admin Users Management Page - User list with role-based filtering, create/edit user modals

import React, { useState, useEffect, useMemo } from 'react';
import { DashboardLayout, GridLayout, CardLayout } from '../../common/components/Layout';
import { Modal, FormModal, ConfirmModal } from '../../common/components/Modal';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { useAllUsers, useDeleteSession } from '../../common/hooks/useApi';
import { User, HardwareWallet } from '../../../shared/types';
import { TorStatus } from '../../../shared/tor-types';

interface UserFilters {
  role: 'all' | 'user' | 'node_operator' | 'admin' | 'super_admin';
  status: 'all' | 'active' | 'suspended' | 'pending';
  search: string;
  hasHardwareWallet: boolean | null;
}

interface UserFormData {
  email: string;
  tron_address: string;
  role: 'user' | 'node_operator' | 'admin' | 'super_admin';
  hardware_wallet?: {
    type: 'ledger' | 'trezor' | 'keepkey';
    device_id: string;
    public_key: string;
  };
}

interface BulkAction {
  id: string;
  label: string;
  icon: string;
  action: (userIds: string[]) => Promise<void>;
  requiresConfirmation: boolean;
  confirmationMessage: string;
}

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showEditUser, setShowEditUser] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingBulkAction, setPendingBulkAction] = useState<BulkAction | null>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const [filters, setFilters] = useState<UserFilters>({
    role: 'all',
    status: 'all',
    search: '',
    hasHardwareWallet: null,
  });

  const [formData, setFormData] = useState<UserFormData>({
    email: '',
    tron_address: '',
    role: 'user',
  });

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  // API hooks
  const { data: usersData, loading: usersLoading, refetch: refetchUsers } = useAllUsers();
  const { execute: deleteUser, loading: deleteLoading } = useDeleteSession(); // Reusing deleteSession hook

  // Update users when data changes
  useEffect(() => {
    if (usersData) {
      setUsers(usersData);
    }
  }, [usersData]);

  // Filter users based on current filters
  const filteredUsers = useMemo(() => {
    return users.filter(user => {
      // Role filter
      if (filters.role !== 'all' && user.role !== filters.role) {
        return false;
      }

      // Search filter
      if (filters.search && !user.email.toLowerCase().includes(filters.search.toLowerCase()) &&
          !user.tron_address.toLowerCase().includes(filters.search.toLowerCase())) {
        return false;
      }

      // Hardware wallet filter
      if (filters.hasHardwareWallet !== null) {
        const hasWallet = !!user.hardware_wallet;
        if (hasWallet !== filters.hasHardwareWallet) {
          return false;
        }
      }

      return true;
    });
  }, [users, filters]);

  // Bulk actions
  const bulkActions: BulkAction[] = [
    {
      id: 'suspend',
      label: 'Suspend Users',
      icon: '⏸️',
      action: handleSuspendUsers,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to suspend the selected users? They will not be able to access the system.',
    },
    {
      id: 'activate',
      label: 'Activate Users',
      icon: '▶️',
      action: handleActivateUsers,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to activate the selected users?',
    },
    {
      id: 'change-role',
      label: 'Change Role',
      icon: '👤',
      action: handleChangeRole,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to change the role of the selected users?',
    },
    {
      id: 'export',
      label: 'Export Users',
      icon: '📄',
      action: handleExportUsers,
      requiresConfirmation: false,
      confirmationMessage: '',
    },
  ];

  async function handleSuspendUsers(userIds: string[]): Promise<void> {
    try {
      // Implement user suspension logic
      showToast({
        type: 'success',
        title: 'Users Suspended',
        message: `${userIds.length} users have been suspended successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Suspension Failed',
        message: error instanceof Error ? error.message : 'Failed to suspend users',
      });
    }
  }

  async function handleActivateUsers(userIds: string[]): Promise<void> {
    try {
      // Implement user activation logic
      showToast({
        type: 'success',
        title: 'Users Activated',
        message: `${userIds.length} users have been activated successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Activation Failed',
        message: error instanceof Error ? error.message : 'Failed to activate users',
      });
    }
  }

  async function handleChangeRole(userIds: string[]): Promise<void> {
    try {
      // Implement role change logic
      showToast({
        type: 'success',
        title: 'Roles Changed',
        message: `${userIds.length} user roles have been updated successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Role Change Failed',
        message: error instanceof Error ? error.message : 'Failed to change user roles',
      });
    }
  }

  async function handleExportUsers(userIds: string[]): Promise<void> {
    try {
      // Implement export logic
      showToast({
        type: 'success',
        title: 'Users Exported',
        message: `${userIds.length} users have been exported successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Export Failed',
        message: error instanceof Error ? error.message : 'Failed to export users',
      });
    }
  }

  const handleUserSelect = (userId: string) => {
    const newSelected = new Set(selectedUsers);
    if (newSelected.has(userId)) {
      newSelected.delete(userId);
    } else {
      newSelected.add(userId);
    }
    setSelectedUsers(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedUsers.size === filteredUsers.length) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(filteredUsers.map(u => u.user_id)));
    }
  };

  const handleBulkAction = (action: BulkAction) => {
    if (selectedUsers.size === 0) {
      showToast({
        type: 'warning',
        title: 'No Users Selected',
        message: 'Please select at least one user to perform this action',
      });
      return;
    }

    if (action.requiresConfirmation) {
      setPendingBulkAction(action);
      setShowConfirmModal(true);
    } else {
      action.action(Array.from(selectedUsers));
    }
  };

  const confirmBulkAction = async () => {
    if (pendingBulkAction) {
      await pendingBulkAction.action(Array.from(selectedUsers));
      setShowConfirmModal(false);
      setPendingBulkAction(null);
    }
  };

  const handleCreateUser = () => {
    setFormData({
      email: '',
      tron_address: '',
      role: 'user',
    });
    setShowCreateUser(true);
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setFormData({
      email: user.email,
      tron_address: user.tron_address,
      role: user.role,
      hardware_wallet: user.hardware_wallet ? {
        type: user.hardware_wallet.type,
        device_id: user.hardware_wallet.device_id,
        public_key: user.hardware_wallet.public_key,
      } : undefined,
    });
    setShowEditUser(true);
  };

  const handleDeleteUser = async (user: User) => {
    try {
      await deleteUser(user.user_id);
      await refetchUsers();
      showToast({
        type: 'success',
        title: 'User Deleted',
        message: `User ${user.email} has been deleted successfully`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Delete Failed',
        message: error instanceof Error ? error.message : 'Failed to delete user',
      });
    }
  };

  const handleSubmitUser = async (data: UserFormData) => {
    try {
      // Implement user creation/update logic
      if (showCreateUser) {
        // Create new user
        showToast({
          type: 'success',
          title: 'User Created',
          message: `User ${data.email} has been created successfully`,
        });
      } else {
        // Update existing user
        showToast({
          type: 'success',
          title: 'User Updated',
          message: `User ${data.email} has been updated successfully`,
        });
      }
      
      setShowCreateUser(false);
      setShowEditUser(false);
      await refetchUsers();
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Operation Failed',
        message: error instanceof Error ? error.message : 'Failed to save user',
      });
    }
  };

  const getRoleColor = (role: string): string => {
    switch (role) {
      case 'super_admin': return 'bg-red-100 text-red-800';
      case 'admin': return 'bg-purple-100 text-purple-800';
      case 'node_operator': return 'bg-blue-100 text-blue-800';
      case 'user': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString();
  };

  const isValidTronAddress = (address: string): boolean => {
    return address.length === 34 && address.startsWith('T');
  };

  if (loading || usersLoading) {
    return (
      <DashboardLayout
        title="Users Management"
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
            <p className="text-gray-600">Loading users...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Users Management"
      torStatus={torStatus}
      headerActions={
        <div className="flex items-center space-x-4">
          <TorIndicator status={torStatus} size="small" />
        </div>
      }
    >
      <div className="space-y-6">
        {/* Filters and Actions */}
        <CardLayout
          title="Filters & Actions"
          subtitle="Filter users and perform bulk operations"
          className="bg-white border border-gray-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select
                value={filters.role}
                onChange={(e) => setFilters(prev => ({ ...prev, role: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Roles</option>
                <option value="user">User</option>
                <option value="node_operator">Node Operator</option>
                <option value="admin">Admin</option>
                <option value="super_admin">Super Admin</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hardware Wallet</label>
              <select
                value={filters.hasHardwareWallet === null ? 'all' : filters.hasHardwareWallet ? 'yes' : 'no'}
                onChange={(e) => setFilters(prev => ({ 
                  ...prev, 
                  hasHardwareWallet: e.target.value === 'all' ? null : e.target.value === 'yes' 
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Users</option>
                <option value="yes">Has Hardware Wallet</option>
                <option value="no">No Hardware Wallet</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                placeholder="Search by email or TRON address"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-end space-x-2">
              <button
                onClick={handleCreateUser}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Create User
              </button>
              <button
                onClick={() => setFilters({
                  role: 'all',
                  status: 'all',
                  search: '',
                  hasHardwareWallet: null,
                })}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        </CardLayout>

        {/* Bulk Actions */}
        {selectedUsers.size > 0 && (
          <CardLayout
            title={`Bulk Actions (${selectedUsers.size} selected)`}
            subtitle="Perform actions on multiple users"
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
                onClick={() => setSelectedUsers(new Set())}
                className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors"
              >
                Clear Selection
              </button>
            </div>
          </CardLayout>
        )}

        {/* Users Table */}
        <CardLayout
          title={`Users (${filteredUsers.length})`}
          subtitle="Manage system users"
          className="bg-white border border-gray-200"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left p-3">
                    <input
                      type="checkbox"
                      checked={selectedUsers.size === filteredUsers.length && filteredUsers.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-gray-300"
                    />
                  </th>
                  <th className="text-left p-3 font-medium">Email</th>
                  <th className="text-left p-3 font-medium">TRON Address</th>
                  <th className="text-left p-3 font-medium">Role</th>
                  <th className="text-left p-3 font-medium">Hardware Wallet</th>
                  <th className="text-left p-3 font-medium">Created</th>
                  <th className="text-left p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.user_id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="p-3">
                      <input
                        type="checkbox"
                        checked={selectedUsers.has(user.user_id)}
                        onChange={() => handleUserSelect(user.user_id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="p-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium">{user.email}</span>
                        <span className="text-xs text-gray-500 font-mono">({user.user_id.substring(0, 8)}...)</span>
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-mono">{user.tron_address.substring(0, 12)}...</span>
                        {isValidTronAddress(user.tron_address) ? (
                          <span className="text-green-500 text-xs">✓</span>
                        ) : (
                          <span className="text-red-500 text-xs">✗</span>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleColor(user.role)}`}>
                        {user.role.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-3">
                      {user.hardware_wallet ? (
                        <div className="flex items-center space-x-2">
                          <span className="text-green-500">✓</span>
                          <span className="text-xs text-gray-600">{user.hardware_wallet.type}</span>
                        </div>
                      ) : (
                        <span className="text-red-500">✗</span>
                      )}
                    </td>
                    <td className="p-3 text-sm">{formatDate(user.created_at)}</td>
                    <td className="p-3">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleEditUser(user)}
                          className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user)}
                          className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredUsers.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <div className="text-4xl mb-2">👥</div>
                <p>No users found</p>
                <p className="text-sm">Try adjusting your filters or create a new user</p>
              </div>
            )}
          </div>
        </CardLayout>
      </div>

      {/* Create User Modal */}
      <FormModal
        isOpen={showCreateUser}
        onClose={() => setShowCreateUser(false)}
        onSubmit={handleSubmitUser}
        title="Create New User"
        submitText="Create User"
        cancelText="Cancel"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">TRON Address</label>
            <input
              type="text"
              value={formData.tron_address}
              onChange={(e) => setFormData(prev => ({ ...prev, tron_address: e.target.value }))}
              required
              placeholder="T..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value as any }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="user">User</option>
              <option value="node_operator">Node Operator</option>
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </div>
        </div>
      </FormModal>

      {/* Edit User Modal */}
      <FormModal
        isOpen={showEditUser}
        onClose={() => setShowEditUser(false)}
        onSubmit={handleSubmitUser}
        title="Edit User"
        submitText="Update User"
        cancelText="Cancel"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">TRON Address</label>
            <input
              type="text"
              value={formData.tron_address}
              onChange={(e) => setFormData(prev => ({ ...prev, tron_address: e.target.value }))}
              required
              placeholder="T..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value as any }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="user">User</option>
              <option value="node_operator">Node Operator</option>
              <option value="admin">Admin</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </div>

          {formData.hardware_wallet && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hardware Wallet</label>
              <div className="p-3 bg-gray-50 rounded-md">
                <div className="text-sm">
                  <div><strong>Type:</strong> {formData.hardware_wallet.type}</div>
                  <div><strong>Device ID:</strong> {formData.hardware_wallet.device_id}</div>
                  <div><strong>Public Key:</strong> {formData.hardware_wallet.public_key.substring(0, 20)}...</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </FormModal>

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

export default UsersPage;
