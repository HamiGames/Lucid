import React from 'react';

interface LoadingOverlayProps {
  visible: boolean;
  message?: string;
  progress?: number;
  showProgress?: boolean;
  size?: 'small' | 'medium' | 'large';
  variant?: 'spinner' | 'dots' | 'pulse' | 'bars';
  className?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  visible,
  message = 'Loading...',
  progress,
  showProgress = false,
  size = 'medium',
  variant = 'spinner',
  className = ''
}) => {
  if (!visible) return null;

  const getSizeClass = () => {
    switch (size) {
      case 'small':
        return 'loading-small';
      case 'medium':
        return 'loading-medium';
      case 'large':
        return 'loading-large';
      default:
        return 'loading-medium';
    }
  };

  const getVariantClass = () => {
    switch (variant) {
      case 'spinner':
        return 'loading-spinner';
      case 'dots':
        return 'loading-dots';
      case 'pulse':
        return 'loading-pulse';
      case 'bars':
        return 'loading-bars';
      default:
        return 'loading-spinner';
    }
  };

  const renderSpinner = () => (
    <div className={`spinner ${getSizeClass()}`}>
      <div className="spinner-ring"></div>
    </div>
  );

  const renderDots = () => (
    <div className={`dots ${getSizeClass()}`}>
      <div className="dot"></div>
      <div className="dot"></div>
      <div className="dot"></div>
    </div>
  );

  const renderPulse = () => (
    <div className={`pulse ${getSizeClass()}`}>
      <div className="pulse-circle"></div>
    </div>
  );

  const renderBars = () => (
    <div className={`bars ${getSizeClass()}`}>
      <div className="bar"></div>
      <div className="bar"></div>
      <div className="bar"></div>
      <div className="bar"></div>
    </div>
  );

  const renderLoader = () => {
    switch (variant) {
      case 'dots':
        return renderDots();
      case 'pulse':
        return renderPulse();
      case 'bars':
        return renderBars();
      default:
        return renderSpinner();
    }
  };

  return (
    <div className={`loading-overlay ${className}`}>
      <div className="loading-content">
        <div className={`loading-animation ${getVariantClass()}`}>
          {renderLoader()}
        </div>
        
        <div className="loading-text">
          {message}
        </div>
        
        {showProgress && progress !== undefined && (
          <div className="loading-progress">
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
              ></div>
            </div>
            <div className="progress-text">
              {Math.round(progress)}%
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LoadingOverlay;
