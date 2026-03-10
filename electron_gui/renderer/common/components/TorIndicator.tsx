// TorIndicator.tsx - Green light connection indicator
// Based on the electron-multi-gui-development.plan.md specifications

import React from 'react';
import { TorStatus } from '../../../shared/tor-types';
import { getTorStatusColor, getTorStatusText, getTorBootstrapProgress } from '../../../shared/utils';

interface TorIndicatorProps {
  status: TorStatus;
  size?: 'small' | 'medium' | 'large';
  showText?: boolean;
  showProgress?: boolean;
  className?: string;
  onClick?: () => void;
}

const TorIndicator: React.FC<TorIndicatorProps> = ({
  status,
  size = 'medium',
  showText = true,
  showProgress = true,
  className = '',
  onClick,
}) => {
  const color = getTorStatusColor(status);
  const text = getTorStatusText(status);
  const progress = getTorBootstrapProgress(status);

  const sizeClasses = {
    small: 'w-3 h-3',
    medium: 'w-4 h-4',
    large: 'w-6 h-6',
  };

  const textSizeClasses = {
    small: 'text-xs',
    medium: 'text-sm',
    large: 'text-base',
  };

  const indicatorClasses = `
    relative inline-flex items-center justify-center
    ${sizeClasses[size]}
    ${className}
  `.trim();

  const textClasses = `
    ml-2 font-medium
    ${textSizeClasses[size]}
  `.trim();

  const progressClasses = `
    absolute inset-0 rounded-full
    ${status.status === 'connecting' ? 'animate-pulse' : ''}
  `.trim();

  return (
    <div
      className={`flex items-center cursor-pointer ${onClick ? 'hover:opacity-80' : ''}`}
      onClick={onClick}
      title={`Tor Status: ${text}${status.status === 'connecting' ? ` (${progress}%)` : ''}`}
    >
      <div className={indicatorClasses}>
        {/* Background circle */}
        <div
          className="w-full h-full rounded-full border-2 border-gray-300 dark:border-gray-600"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.1)' }}
        />
        
        {/* Status indicator */}
        <div
          className={`w-full h-full rounded-full ${progressClasses}`}
          style={{ backgroundColor: color }}
        />
        
        {/* Bootstrap progress ring */}
        {status.status === 'connecting' && showProgress && (
          <svg
            className="absolute inset-0 w-full h-full transform -rotate-90"
            viewBox="0 0 24 24"
          >
            <circle
              cx="12"
              cy="12"
              r="10"
              stroke="rgba(255, 255, 255, 0.3)"
              strokeWidth="2"
              fill="none"
            />
            <circle
              cx="12"
              cy="12"
              r="10"
              stroke="rgba(255, 255, 255, 0.8)"
              strokeWidth="2"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 10}`}
              strokeDashoffset={`${2 * Math.PI * 10 * (1 - progress / 100)}`}
              strokeLinecap="round"
            />
          </svg>
        )}
        
        {/* Pulse animation for connecting state */}
        {status.status === 'connecting' && (
          <div
            className="absolute inset-0 rounded-full animate-ping"
            style={{ backgroundColor: color, opacity: 0.3 }}
          />
        )}
      </div>
      
      {showText && (
        <span className={textClasses} style={{ color }}>
          {text}
        </span>
      )}
      
      {/* Progress percentage for connecting state */}
      {status.status === 'connecting' && showProgress && (
        <span className={`ml-1 ${textSizeClasses[size]} text-gray-500`}>
          ({progress}%)
        </span>
      )}
    </div>
  );
};

// Alternative compact version for headers
export const TorIndicatorCompact: React.FC<{
  status: TorStatus;
  className?: string;
  onClick?: () => void;
}> = ({ status, className = '', onClick }) => {
  const color = getTorStatusColor(status);
  const text = getTorStatusText(status);

  return (
    <div
      className={`flex items-center space-x-1 ${className}`}
      onClick={onClick}
      title={`Tor: ${text}`}
    >
      <div
        className="w-2 h-2 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span className="text-xs text-gray-600 dark:text-gray-400">
        {text}
      </span>
    </div>
  );
};

// Detailed status component
export const TorStatusDetailed: React.FC<{
  status: TorStatus;
  className?: string;
}> = ({ status, className = '' }) => {
  const color = getTorStatusColor(status);
  const text = getTorStatusText(status);
  const progress = getTorBootstrapProgress(status);

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Tor Connection
        </h3>
        <TorIndicator status={status} size="large" showText={false} />
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">Status:</span>
          <span className="text-sm font-medium" style={{ color }}>
            {text}
          </span>
        </div>
        
        {status.status === 'connecting' && (
          <div className="flex justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">Progress:</span>
            <span className="text-sm font-medium">{progress}%</span>
          </div>
        )}
        
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">Circuits:</span>
          <span className="text-sm font-medium">{status.circuits.length}</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">Proxy Port:</span>
          <span className="text-sm font-medium">{status.proxy_port}</span>
        </div>
        
        {status.last_connected && (
          <div className="flex justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">Last Connected:</span>
            <span className="text-sm font-medium">
              {new Date(status.last_connected).toLocaleString()}
            </span>
          </div>
        )}
        
        {status.error && (
          <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
            <p className="text-sm text-red-600 dark:text-red-400">
              {status.error}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// Circuit list component
export const TorCircuitsList: React.FC<{
  circuits: TorStatus['circuits'];
  className?: string;
}> = ({ circuits, className = '' }) => {
  if (circuits.length === 0) {
    return (
      <div className={`text-center py-4 text-gray-500 dark:text-gray-400 ${className}`}>
        No circuits available
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <h4 className="text-sm font-medium text-gray-900 dark:text-white">
        Active Circuits ({circuits.length})
      </h4>
      <div className="space-y-1">
        {circuits.map((circuit) => (
          <div
            key={circuit.id}
            className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm"
          >
            <div className="flex items-center space-x-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  circuit.status === 'built' ? 'bg-green-500' : 'bg-yellow-500'
                }`}
              />
              <span className="font-mono text-xs">{circuit.id.slice(0, 8)}...</span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {circuit.path.length} hops
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TorIndicator;
