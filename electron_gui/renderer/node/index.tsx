import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

// Import global styles
import '../common/styles/global.css';
import './styles/node.css';

// Initialize the Node GUI application
const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found');
}

const root = createRoot(container);
root.render(<App />);

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
});

// Handle global errors
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);
});
