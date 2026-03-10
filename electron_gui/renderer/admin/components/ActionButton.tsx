import React from 'react';

interface ActionButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  icon?: string;
  iconPosition?: 'left' | 'right';
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  title?: string;
  fullWidth?: boolean;
}

export const ActionButton: React.FC<ActionButtonProps> = ({
  children,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  icon,
  iconPosition = 'left',
  onClick,
  type = 'button',
  className = '',
  title,
  fullWidth = false
}) => {
  const getVariantClass = () => {
    switch (variant) {
      case 'primary':
        return 'btn-primary';
      case 'secondary':
        return 'btn-secondary';
      case 'success':
        return 'btn-success';
      case 'warning':
        return 'btn-warning';
      case 'danger':
        return 'btn-danger';
      case 'info':
        return 'btn-info';
      default:
        return 'btn-primary';
    }
  };

  const getSizeClass = () => {
    switch (size) {
      case 'small':
        return 'btn-small';
      case 'medium':
        return 'btn-medium';
      case 'large':
        return 'btn-large';
      default:
        return 'btn-medium';
    }
  };

  const getLoadingClass = () => {
    return loading ? 'btn-loading' : '';
  };

  const getDisabledClass = () => {
    return disabled ? 'btn-disabled' : '';
  };

  const getFullWidthClass = () => {
    return fullWidth ? 'btn-full-width' : '';
  };

  const handleClick = () => {
    if (!disabled && !loading && onClick) {
      onClick();
    }
  };

  const renderIcon = () => {
    if (!icon) return null;
    
    return (
      <span className={`btn-icon ${iconPosition === 'right' ? 'icon-right' : 'icon-left'}`}>
        {loading ? '⏳' : icon}
      </span>
    );
  };

  const renderContent = () => {
    if (loading) {
      return (
        <>
          <span className="loading-spinner"></span>
          <span className="btn-text">Loading...</span>
        </>
      );
    }

    return (
      <>
        {icon && iconPosition === 'left' && renderIcon()}
        <span className="btn-text">{children}</span>
        {icon && iconPosition === 'right' && renderIcon()}
      </>
    );
  };

  return (
    <button
      type={type}
      className={`
        action-btn 
        ${getVariantClass()} 
        ${getSizeClass()} 
        ${getLoadingClass()} 
        ${getDisabledClass()} 
        ${getFullWidthClass()} 
        ${className}
      `.trim()}
      onClick={handleClick}
      disabled={disabled || loading}
      title={title}
    >
      {renderContent()}
    </button>
  );
};

export default ActionButton;
