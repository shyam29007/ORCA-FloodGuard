import React from 'react';
import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div className="d-flex flex-column align-items-center justify-content-center p-5 text-center my-auto">
      <div
        className="rounded-circle d-flex align-items-center justify-content-center mb-3"
        style={{ width: '64px', height: '64px', backgroundColor: '#FEF7ED', color: '#E99A36' }}
      >
        <i className="bi bi-exclamation-triangle fs-1"></i>
      </div>
      <h3 className="fw-bold mb-2" style={{ color: '#092F2B' }}>
        404 — Tactical View Not Found
      </h3>
      <p className="small mb-4 text-muted" style={{ maxWidth: '420px' }}>
        The requested tactical monitoring corridor or dashboard view is not mapped in the command center.
      </p>
      <Link to="/" className="btn btn-primary btn-sm px-4 py-2 fw-semibold d-inline-flex align-items-center gap-2">
        <i className="bi bi-arrow-left"></i>
        <span>Return to Command Centre</span>
      </Link>
    </div>
  );
}

export default NotFound;
