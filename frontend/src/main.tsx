import React from 'react';
import ReactDOM from 'react-dom/client';
import { App as AntApp } from 'antd';
import App from './App';
import './styles/tableLayout.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <AntApp>
      <App />
    </AntApp>
  </React.StrictMode>,
);