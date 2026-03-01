import React from 'react';

interface NavItem {
  id: string;
  label: string;
  icon: string;
  path: string;
  badge?: number;
}

interface AdminSidebarProps {
  activeItem?: string;
  onNavigate?: (path: string) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

const navItems: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: '📊',
    path: '/admin/dashboard'
  },
  {
    id: 'sessions',
    label: 'Sessions',
    icon: '🖥️',
    path: '/admin/sessions'
  },
  {
    id: 'users',
    label: 'Users',
    icon: '👥',
    path: '/admin/users'
  },
  {
    id: 'nodes',
    label: 'Nodes',
    icon: '🖥️',
    path: '/admin/nodes'
  },
  {
    id: 'blockchain',
    label: 'Blockchain',
    icon: '⛓️',
    path: '/admin/blockchain'
  },
  {
    id: 'audit',
    label: 'Audit Logs',
    icon: '📋',
    path: '/admin/audit'
  },
  {
    id: 'config',
    label: 'Configuration',
    icon: '⚙️',
    path: '/admin/config'
  }
];

export const AdminSidebar: React.FC<AdminSidebarProps> = ({
  activeItem = 'dashboard',
  onNavigate,
  collapsed = false,
  onToggleCollapse
}) => {
  const handleNavClick = (item: NavItem) => {
    if (onNavigate) {
      onNavigate(item.path);
    }
  };

  return (
    <nav className={`admin-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-content">
        <div className="sidebar-header">
          <button 
            className="toggle-btn"
            onClick={onToggleCollapse}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? '▶' : '◀'}
          </button>
        </div>
        
        <ul className="nav-menu">
          {navItems.map((item) => (
            <li 
              key={item.id}
              className={`nav-item ${activeItem === item.id ? 'active' : ''}`}
            >
              <button
                className="nav-link"
                onClick={() => handleNavClick(item)}
                title={item.label}
              >
                <span className="nav-icon">{item.icon}</span>
                {!collapsed && (
                  <>
                    <span className="nav-text">{item.label}</span>
                    {item.badge && item.badge > 0 && (
                      <span className="nav-badge">{item.badge}</span>
                    )}
                  </>
                )}
              </button>
            </li>
          ))}
        </ul>
        
        {!collapsed && (
          <div className="sidebar-footer">
            <div className="system-info">
              <div className="info-item">
                <span className="info-label">System Status</span>
                <span className="info-value status-online">Online</span>
              </div>
              <div className="info-item">
                <span className="info-label">Last Update</span>
                <span className="info-value">{new Date().toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default AdminSidebar;
