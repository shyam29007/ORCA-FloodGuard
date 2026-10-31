import React from 'react';

export function LoadingSpinner({ message = 'Loading live telemetry...' }) {
  return (
    <div className="d-flex flex-column align-items-center justify-content-center p-5 text-center">
      <div
        className="spinner-border mb-3"
        style={{
          width: '2.5rem',
          height: '2.5rem',
          color: '#16865F',
          borderWidth: '3px',
        }}
        role="status"
      >
        <span className="visually-hidden">Loading...</span>
      </div>
      <p className="small mb-0 font-monospace" style={{ color: '#687B78' }}>
        {message}
      </p>
    </div>
  );
}

export default LoadingSpinner;
