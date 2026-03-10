/**
 * Error Boundary Component - React error handling
 * SPEC-1B Implementation for admin interface
 */

import React, { ReactNode, ReactElement } from 'react';

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactElement;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorCount: number;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('Error caught by boundary:', error, errorInfo);
    
    this.setState((prevState) => ({
      errorCount: prevState.errorCount + 1,
    }));

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Component stack:', errorInfo.componentStack);
    }
  }

  resetError = (): void => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render(): ReactElement {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.resetError);
      }

      return (
        <div
          style={{
            padding: '20px',
            margin: '20px',
            border: '1px solid #f5222d',
            borderRadius: '4px',
            backgroundColor: '#fff2e8',
          }}
        >
          <h2 style={{ color: '#f5222d', marginTop: 0 }}>Something went wrong</h2>
          <p style={{ color: '#d4380d' }}>
            {this.state.error.message || 'An unexpected error occurred'}
          </p>
          {process.env.NODE_ENV === 'development' && (
            <pre
              style={{
                backgroundColor: '#f6f6f6',
                padding: '10px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
              }}
            >
              {this.state.error.stack}
            </pre>
          )}
          <button
            onClick={this.resetError}
            style={{
              padding: '8px 16px',
              backgroundColor: '#f5222d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              marginTop: '10px',
            }}
          >
            Try Again
          </button>
        </div>
      );
    }

    return <>{this.props.children}</>;
  }
}

export default ErrorBoundary;
