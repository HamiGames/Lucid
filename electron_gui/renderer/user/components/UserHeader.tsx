import React, { useState } from 'react';
import { TorIndicator } from '../../common/components/TorIndicator';

interface User {
  id: string;
  email: string;
  tron_address: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string;
  session_count: number;
}

interface UserRoute {
  id: string;
  path: string;
  component: React.ComponentType<any>;
  title: string;
  requiresAuth: boolean;
  icon?: string;
}

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
}

interface UserHeaderProps {
  user: User | null;
  currentRoute: string;
  routes: UserRoute[];
  onRouteChange: (routeId: string) => void;
  onLogout: () => void;
  notifications: Notification[];
  onNotificationDismiss: (id: string) => void;
}

export const UserHeader: React.FC<UserHeaderProps> = ({
  user,
  currentRoute,
  routes,
  onRouteChange,
  onLogout,
  notifications,
  onNotificationDismiss
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleNotificationClick = () => {
    setShowNotifications(!showNotifications);
    setShowUserMenu(false);
  };

  const handleUserMenuClick = () => {
    setShowUserMenu(!showUserMenu);
    setShowNotifications(false);
  };

  const handleOutsideClick = (event: React.MouseEvent) => {
    if ((event.target as HTMLElement).closest('.user-header-dropdown')) {
      return;
    }
    setShowNotifications(false);
    setShowUserMenu(false);
  };

  const getNotificationCount = () => {
    return notifications.length;
  };

  const getNotificationIcon = () => {
    const count = getNotificationCount();
    if (count === 0) {
      return '🔔';
    } else if (count < 5) {
      return '🔔';
    } else {
      return '🔔';
    }
  };

  return (
    <header className="user-header" onClick={handleOutsideClick}>
      <div className="user-header-left">
        {/* Logo */}
        <div className="user-logo">
          <span style={{ fontSize: '1.5rem', marginRight: '0.5rem' }}>🔐</span>
          Lucid User
        </div>

        {/* Navigation */}
        <nav className="user-nav">
          {routes.map(route => (
            <button
              key={route.id}
              className={`user-nav-item ${currentRoute === route.id ? 'active' : ''}`}
              onClick={() => onRouteChange(route.id)}
              title={route.title}
            >
              {route.icon && <span style={{ marginRight: '0.25rem' }}>{route.icon}</span>}
              {route.title}
            </button>
          ))}
        </nav>
      </div>

      <div className="user-header-right">
        {/* Tor Status Indicator */}
        <TorIndicator />

        {/* Notifications */}
        <div className="user-notifications user-header-dropdown" style={{ position: 'relative' }}>
          <button
            className="user-notification-bell"
            onClick={handleNotificationClick}
            title="Notifications"
          >
            <span style={{ fontSize: '1.25rem' }}>{getNotificationIcon()}</span>
            {getNotificationCount() > 0 && (
              <span className="user-notification-badge">
                {getNotificationCount() > 99 ? '99+' : getNotificationCount()}
              </span>
            )}
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: '0',
              marginTop: '0.5rem',
              width: '320px',
              maxHeight: '400px',
              backgroundColor: 'var(--user-bg-primary)',
              border: '1px solid var(--user-border-primary)',
              borderRadius: 'var(--user-radius-lg)',
              boxShadow: 'var(--user-shadow-lg)',
              zIndex: 1000,
              overflow: 'hidden'
            }}>
              <div style={{
                padding: '1rem',
                borderBottom: '1px solid var(--user-border-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>Notifications</h3>
                <button
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--user-text-secondary)',
                    cursor: 'pointer',
                    fontSize: '1.25rem',
                    padding: '0.25rem'
                  }}
                  onClick={() => setShowNotifications(false)}
                >
                  ×
                </button>
              </div>

              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {notifications.length === 0 ? (
                  <div style={{
                    padding: '2rem',
                    textAlign: 'center',
                    color: 'var(--user-text-secondary)'
                  }}>
                    <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔔</div>
                    <p style={{ margin: 0 }}>No notifications</p>
                  </div>
                ) : (
                  notifications.map(notification => (
                    <div
                      key={notification.id}
                      style={{
                        padding: '1rem',
                        borderBottom: '1px solid var(--user-border-primary)',
                        cursor: 'pointer',
                        transition: 'background-color var(--user-transition-fast)'
                      }}
                      onMouseEnter={(e) => {
                        (e.target as HTMLElement).style.backgroundColor = 'var(--user-bg-secondary)';
                      }}
                      onMouseLeave={(e) => {
                        (e.target as HTMLElement).style.backgroundColor = 'transparent';
                      }}
                      onClick={() => onNotificationDismiss(notification.id)}
                    >
                      <div style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.75rem'
                      }}>
                        <div style={{
                          fontSize: '1.25rem',
                          marginTop: '0.125rem'
                        }}>
                          {notification.type === 'success' && '✅'}
                          {notification.type === 'error' && '❌'}
                          {notification.type === 'warning' && '⚠️'}
                          {notification.type === 'info' && 'ℹ️'}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{
                            fontWeight: '500',
                            fontSize: '0.875rem',
                            marginBottom: '0.25rem',
                            color: 'var(--user-text-primary)'
                          }}>
                            {notification.title}
                          </div>
                          <div style={{
                            fontSize: '0.75rem',
                            color: 'var(--user-text-secondary)',
                            marginBottom: '0.25rem'
                          }}>
                            {notification.message}
                          </div>
                          <div style={{
                            fontSize: '0.75rem',
                            color: 'var(--user-text-tertiary)'
                          }}>
                            {new Date(notification.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {notifications.length > 0 && (
                <div style={{
                  padding: '0.75rem',
                  borderTop: '1px solid var(--user-border-primary)',
                  textAlign: 'center'
                }}>
                  <button
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--user-primary)',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      fontWeight: '500'
                    }}
                    onClick={() => {
                      notifications.forEach(n => onNotificationDismiss(n.id));
                      setShowNotifications(false);
                    }}
                  >
                    Clear All
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="user-header-dropdown" style={{ position: 'relative' }}>
          <button
            className="user-btn user-btn-secondary"
            onClick={handleUserMenuClick}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.75rem'
            }}
          >
            <div style={{
              width: '2rem',
              height: '2rem',
              borderRadius: '50%',
              backgroundColor: 'var(--user-primary)',
              color: 'var(--user-text-inverse)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.875rem',
              fontWeight: '600'
            }}>
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <span style={{ fontSize: '0.875rem' }}>
              {user?.email || 'User'}
            </span>
            <span style={{ fontSize: '0.75rem' }}>▼</span>
          </button>

          {/* User Menu Dropdown */}
          {showUserMenu && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: '0',
              marginTop: '0.5rem',
              width: '200px',
              backgroundColor: 'var(--user-bg-primary)',
              border: '1px solid var(--user-border-primary)',
              borderRadius: 'var(--user-radius-lg)',
              boxShadow: 'var(--user-shadow-lg)',
              zIndex: 1000,
              overflow: 'hidden'
            }}>
              <div style={{ padding: '0.5rem 0' }}>
                <button
                  className="user-nav-item"
                  onClick={() => {
                    onRouteChange('profile');
                    setShowUserMenu(false);
                  }}
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    border: 'none',
                    background: 'none',
                    borderRadius: '0'
                  }}
                >
                  👤 Profile
                </button>
                <button
                  className="user-nav-item"
                  onClick={() => {
                    onRouteChange('settings');
                    setShowUserMenu(false);
                  }}
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    border: 'none',
                    background: 'none',
                    borderRadius: '0'
                  }}
                >
                  ⚙️ Settings
                </button>
                <div style={{
                  height: '1px',
                  backgroundColor: 'var(--user-border-primary)',
                  margin: '0.5rem 0'
                }} />
                <button
                  className="user-nav-item"
                  onClick={() => {
                    onLogout();
                    setShowUserMenu(false);
                  }}
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    border: 'none',
                    background: 'none',
                    borderRadius: '0',
                    color: 'var(--user-error)'
                  }}
                >
                  🚪 Logout
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
