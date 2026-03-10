// renderer/admin/index.tsx - Admin GUI entry point
// Based on the electron-multi-gui-development.plan.md specifications

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import '../common/styles/global.css';

// Initialize the admin GUI
const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found');
}

const root = createRoot(container);

// Render the admin application
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Handle hot module replacement in development
if (process.env.NODE_ENV === 'development' && module.hot) {
  module.hot.accept('./App', () => {
    const NextApp = require('./App').default;
    root.render(
      <React.StrictMode>
        <NextApp />
      </React.StrictMode>
    );
  });
}

// Global error handler
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
});

// Initialize admin-specific services
console.log('Admin GUI initialized');
