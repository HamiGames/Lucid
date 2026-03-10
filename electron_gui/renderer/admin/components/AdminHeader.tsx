import React from 'react';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { TorIndicator } from '../../common/components/TorIndicator';

interface AdminHeaderProps {
  userName?: string;
  onLogout?: () => void;
  onRefresh?: () => void;
}

export const AdminHeader: React.FC<AdminHeaderProps> = ({
  userName = 'Admin User',
  onLogout,
  onRefresh
}) => {
  const { isConnected, status } = useTorStatus();

  return (
    <header className="admin-header">
      <div className="header-left">
        <h1 className="admin-title">Lucid Admin Dashboard</h1>
        <span className="admin-version">v1.0.0</span>
      </div>
      <div className="header-right">
        <div className="system-status">
          <TorIndicator 
            isConnected={isConnected}
            status={status}
            showText={true}
          />
        </div>
        <div className="admin-user">
          <span className="user-name">{userName}</span>
          <button 
            className="logout-btn" 
            onClick={onLogout}
            title="Logout from admin panel"
          >
            Logout
          </button>
        </div>
        <button 
          className="refresh-btn" 
          onClick={onRefresh}
          title="Refresh system status"
        >
          🔄
        </button>
      </div>
    </header>
  );
};

export default AdminHeader;
