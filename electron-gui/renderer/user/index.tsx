import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './styles/user.css';

// Initialize the User GUI
const initializeUserGUI = () => {
  const rootElement = document.getElementById('user-root');
  if (!rootElement) {
    throw new Error('User GUI root element not found');
  }

  const root = ReactDOM.createRoot(rootElement);
  root.render(<App />);

  console.log('User GUI initialized successfully');
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeUserGUI);
} else {
  initializeUserGUI();
}

// Handle window events
window.addEventListener('beforeunload', () => {
  console.log('User GUI shutting down');
});

// Export for potential external use
export { App };
