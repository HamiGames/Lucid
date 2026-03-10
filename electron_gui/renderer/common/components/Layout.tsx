// Layout.tsx - Shared layout wrapper
// Based on the electron-multi-gui-development.plan.md specifications

import React, { ReactNode } from 'react';
import { TorStatus } from '../../../shared/tor-types';
import TorIndicator from './TorIndicator';

interface LayoutProps {
  children: ReactNode;
  title?: string;
  torStatus?: TorStatus;
  showTorIndicator?: boolean;
  showHeader?: boolean;
  showFooter?: boolean;
  className?: string;
  headerContent?: ReactNode;
  footerContent?: ReactNode;
  sidebar?: ReactNode;
  sidebarCollapsed?: boolean;
  onTorIndicatorClick?: () => void;
}

const Layout: React.FC<LayoutProps> = ({
  children,
  title,
  torStatus,
  showTorIndicator = true,
  showHeader = true,
  showFooter = false,
  className = '',
  headerContent,
  footerContent,
  sidebar,
  sidebarCollapsed = false,
  onTorIndicatorClick,
}) => {
  return (
    <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col ${className}`}>
      {/* Header */}
      {showHeader && (
        <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between h-16 px-4">
            <div className="flex items-center space-x-4">
              {title && (
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {title}
                </h1>
              )}
              {headerContent}
            </div>
            
            <div className="flex items-center space-x-4">
              {showTorIndicator && torStatus && (
                <TorIndicator
                  status={torStatus}
                  size="medium"
                  showText={true}
                  onClick={onTorIndicatorClick}
                />
              )}
            </div>
          </div>
        </header>
      )}

      {/* Main content area */}
      <div className="flex flex-1">
        {/* Sidebar */}
        {sidebar && (
          <aside
            className={`bg-white dark:bg-gray-800 shadow-sm border-r border-gray-200 dark:border-gray-700 transition-all duration-300 ${
              sidebarCollapsed ? 'w-16' : 'w-64'
            }`}
          >
            {sidebar}
          </aside>
        )}

        {/* Main content */}
        <main className="flex-1 flex flex-col">
          <div className="flex-1 p-6">
            {children}
          </div>
        </main>
      </div>

      {/* Footer */}
      {showFooter && (
        <footer className="bg-white dark:bg-gray-800 shadow-sm border-t border-gray-200 dark:border-gray-700">
          <div className="px-4 py-3">
            {footerContent || (
              <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
                <div className="flex items-center space-x-4">
                  <span>Lucid Desktop</span>
                  <span>v1.0.0</span>
                </div>
                <div className="flex items-center space-x-4">
                  {showTorIndicator && torStatus && (
                    <TorIndicator
                      status={torStatus}
                      size="small"
                      showText={false}
                      onClick={onTorIndicatorClick}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </footer>
      )}
    </div>
  );
};

// Full-screen layout variant
export const FullScreenLayout: React.FC<{
  children: ReactNode;
  torStatus?: TorStatus;
  showTorIndicator?: boolean;
  className?: string;
  onTorIndicatorClick?: () => void;
}> = ({
  children,
  torStatus,
  showTorIndicator = true,
  className = '',
  onTorIndicatorClick,
}) => {
  return (
    <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 ${className}`}>
      {/* Floating Tor indicator */}
      {showTorIndicator && torStatus && (
        <div className="fixed top-4 right-4 z-50">
          <TorIndicator
            status={torStatus}
            size="medium"
            showText={true}
            onClick={onTorIndicatorClick}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-2 border border-gray-200 dark:border-gray-700"
          />
        </div>
      )}
      
      {children}
    </div>
  );
};

// Centered layout variant
export const CenteredLayout: React.FC<{
  children: ReactNode;
  title?: string;
  subtitle?: string;
  torStatus?: TorStatus;
  showTorIndicator?: boolean;
  className?: string;
  onTorIndicatorClick?: () => void;
}> = ({
  children,
  title,
  subtitle,
  torStatus,
  showTorIndicator = true,
  className = '',
  onTorIndicatorClick,
}) => {
  return (
    <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center ${className}`}>
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          {title && (
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              {title}
            </h1>
          )}
          {subtitle && (
            <p className="text-gray-600 dark:text-gray-400">
              {subtitle}
            </p>
          )}
        </div>

        {/* Content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
          {children}
        </div>

        {/* Footer with Tor indicator */}
        {showTorIndicator && torStatus && (
          <div className="mt-6 text-center">
            <TorIndicator
              status={torStatus}
              size="small"
              showText={true}
              onClick={onTorIndicatorClick}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// Dashboard layout variant
export const DashboardLayout: React.FC<{
  children: ReactNode;
  title?: string;
  torStatus?: TorStatus;
  showTorIndicator?: boolean;
  className?: string;
  headerActions?: ReactNode;
  onTorIndicatorClick?: () => void;
}> = ({
  children,
  title,
  torStatus,
  showTorIndicator = true,
  className = '',
  headerActions,
  onTorIndicatorClick,
}) => {
  return (
    <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 ${className}`}>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {title && (
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {title}
                </h1>
              )}
            </div>
            
            <div className="flex items-center space-x-4">
              {headerActions}
              {showTorIndicator && torStatus && (
                <TorIndicator
                  status={torStatus}
                  size="medium"
                  showText={true}
                  onClick={onTorIndicatorClick}
                />
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="p-6">
        {children}
      </main>
    </div>
  );
};

// Grid layout variant
export const GridLayout: React.FC<{
  children: ReactNode;
  columns?: 1 | 2 | 3 | 4;
  gap?: 'sm' | 'md' | 'lg';
  className?: string;
}> = ({
  children,
  columns = 2,
  gap = 'md',
  className = '',
}) => {
  const columnClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
  };

  const gapClasses = {
    sm: 'gap-4',
    md: 'gap-6',
    lg: 'gap-8',
  };

  return (
    <div className={`grid ${columnClasses[columns]} ${gapClasses[gap]} ${className}`}>
      {children}
    </div>
  );
};

// Card layout variant
export const CardLayout: React.FC<{
  children: ReactNode;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  className?: string;
}> = ({
  children,
  title,
  subtitle,
  actions,
  className = '',
}) => {
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      {(title || subtitle || actions) && (
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {subtitle}
                </p>
              )}
            </div>
            {actions && (
              <div className="flex items-center space-x-2">
                {actions}
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="p-6">
        {children}
      </div>
    </div>
  );
};

export default Layout;
