import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import '../common/styles/global.css';
import './styles/developer.css';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
