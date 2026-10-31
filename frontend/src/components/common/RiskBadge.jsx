import React from 'react';

export function RiskBadge({ risk, size = 'md' }) {
  const r = String(risk || 'UNKNOWN').toUpperCase();

  let bg = '#687B78';
  let color = '#FFFFFF';
  let border = 'transparent';

  switch (r) {
    case 'CRITICAL':
      bg = '#D94A4A';
      color = '#FFFFFF';
      break;
    case 'HIGH':
      bg = '#EA5454';
      color = '#FFFFFF';
      break;
    case 'MODERATE':
      bg = '#E99A36';
      color = '#FFFFFF';
      break;
    case 'LOW':
      bg = '#24B6A0';
      color = '#FFFFFF';
      break;
    case 'NORMAL':
    case 'SAFE':
      bg = '#16865F';
      color = '#FFFFFF';
      break;
    case 'INSUFFICIENT_EVIDENCE':
      bg = '#F1F4F3';
      color = '#687B78';
      border = '#DFEAE6';
      break;
    default:
      bg = '#687B78';
      color = '#FFFFFF';
  }

  const padding = size === 'lg' ? '6px 14px' : size === 'sm' ? '3px 8px' : '4px 10px';
  const fontSize = size === 'lg' ? '0.85rem' : size === 'sm' ? '0.7rem' : '0.75rem';

  return (
    <span
      className="badge font-monospace text-uppercase"
      style={{
        backgroundColor: bg,
        color: color,
        border: border !== 'transparent' ? `1px solid ${border}` : 'none',
        padding: padding,
        fontSize: fontSize,
        fontWeight: 700,
        letterSpacing: '0.5px',
        borderRadius: '6px',
      }}
    >
      {r.replace(/_/g, ' ')}
    </span>
  );
}

export default RiskBadge;
