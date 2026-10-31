import React from 'react';

export function StatusBadge({ status, size = 'sm' }) {
  if (!status) return null;
  const s = String(status).trim().toUpperCase();

  let bg = '#F1F4F3';
  let color = '#687B78';
  let border = '#DFEAE6';
  let label = s.replace(/_/g, ' ');

  switch (s) {
    case 'APPLICATION ONLINE':
    case 'APPLICATION_ONLINE':
    case 'DATABASE CONNECTED':
    case 'DATABASE_CONNECTED':
    case 'LIVE DATA AVAILABLE':
    case 'LIVE_DATA_AVAILABLE':
    case 'CONNECTED':
    case 'APPROVED':
    case 'VERIFIED':
    case 'COMPLETED':
    case 'OPERATIONAL':
      bg = '#E7F6EF';
      color = '#16865F';
      border = '#BCE3D4';
      if (s.includes('APPLICATION')) label = 'APPLICATION ONLINE';
      if (s.includes('DATABASE')) label = 'DATABASE CONNECTED';
      if (s.includes('LIVE')) label = 'LIVE DATA AVAILABLE';
      if (s === 'CONNECTED') label = 'CONNECTED';
      break;

    case 'SIMULATION ACTIVE':
    case 'SIMULATION_ACTIVE':
    case 'SIMULATED':
    case 'SIMULATED_DEMO':
      bg = '#EBF6F4';
      color = '#10483F';
      border = '#BCE3D4';
      label = 'SIMULATION ACTIVE';
      break;

    case 'STATIC REFERENCE':
    case 'STATIC_REFERENCE':
    case 'STATIC_REF':
      bg = '#F4FAF7';
      color = '#16865F';
      border = '#DFEAE6';
      label = 'STATIC REFERENCE';
      break;

    case 'CONFIGURED':
      bg = '#EBF6F4';
      color = '#24B6A0';
      border = '#BCE3D4';
      label = 'CONFIGURED';
      break;

    case 'PROVIDER NOT_CONFIGURED':
    case 'PROVIDER_NOT_CONFIGURED':
      bg = '#F4F7F6';
      color = '#687B78';
      border = '#DFEAE6';
      label = 'PROVIDER NOT_CONFIGURED';
      break;

    case 'NOT_CONFIGURED':
      bg = '#F4F7F6';
      color = '#687B78';
      border = '#DFEAE6';
      label = 'NOT CONFIGURED';
      break;

    case 'NOT_TESTED':
      bg = '#F4F7F6';
      color = '#8FA9A3';
      border = '#DFEAE6';
      label = 'NOT TESTED';
      break;

    case 'PROVIDER AUTHENTICATION_FAILED':
    case 'AUTHENTICATION_FAILED':
    case 'ACCESS_DENIED':
    case 'BLOCKED_BY_ACCESS':
    case 'CONNECTION_FAILED':
    case 'FAILED':
    case 'REJECTED':
    case 'TIMEOUT':
      bg = '#FDF2F2';
      color = '#D94A4A';
      border = '#F8CBCB';
      if (s === 'TIMEOUT') label = 'TIMEOUT';
      else if (s === 'BLOCKED_BY_ACCESS') label = 'BLOCKED BY ACCESS';
      else if (s.includes('AUTH') || s === 'ACCESS_DENIED') label = 'ACCESS DENIED';
      else if (s === 'CONNECTION_FAILED') label = 'CONNECTION FAILED';
      break;

    case 'PROVIDER DATA_INVALID':
    case 'DATA_INVALID':
    case 'PROVIDER DATA_STALE':
    case 'DATA_STALE':
    case 'STALE':
    case 'PENDING':
    case 'PENDING_APPROVAL':
    case 'RUNNING':
      bg = '#FEF7ED';
      color = '#E99A36';
      border = '#FCE4C3';
      if (s.includes('INVALID')) label = 'DATA INVALID';
      else if (s.includes('STALE')) label = 'DATA STALE';
      else if (s.includes('PENDING')) label = 'PENDING APPROVAL';
      break;

    case 'VALID_RESPONSE':
      bg = '#F0FAF5';
      color = '#16865F';
      border = '#BCE3D4';
      label = 'VALID RESPONSE';
      break;

    case 'UNAVAILABLE':
    case 'INSUFFICIENT_EVIDENCE':
      bg = '#F1F4F3';
      color = '#687B78';
      border = '#DFEAE6';
      label = s.replace(/_/g, ' ');
      break;

    default:
      bg = '#F1F4F3';
      color = '#687B78';
      border = '#DFEAE6';
      label = s.replace(/_/g, ' ');
  }

  const padding = size === 'lg' ? '6px 14px' : '3px 8px';
  const fontSize = size === 'lg' ? '0.85rem' : '0.72rem';

  return (
    <span
      className="badge-status"
      style={{
        backgroundColor: bg,
        color: color,
        border: `1px solid ${border}`,
        padding: padding,
        fontSize: fontSize,
      }}
    >
      {label}
    </span>
  );
}

export default StatusBadge;
