/**
 * Formatting helpers for hydrological, meteorological, and temporal data.
 */

export function formatDateTime(isoString) {
  if (!isoString) return 'N/A';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString);
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }) + ' IST';
  } catch {
    return String(isoString);
  }
}

export function formatNumber(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(Number(val))) return '—';
  return Number(val).toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatRainfall(val) {
  if (val === null || val === undefined || isNaN(Number(val))) return 'No Data';
  return `${formatNumber(val, 1)} mm`;
}

export function formatWaterLevel(val) {
  if (val === null || val === undefined || isNaN(Number(val))) return 'No Data';
  return `${formatNumber(val, 2)} m`;
}

export const formatMeters = formatWaterLevel;

export function formatCusecs(val) {
  if (val === null || val === undefined || isNaN(Number(val))) return 'No Data';
  return `${formatNumber(val, 0)} cusecs`;
}

export function getRiskBadgeClass(risk) {
  if (!risk) return 'badge bg-secondary';
  const r = String(risk).toUpperCase();
  switch (r) {
    case 'CRITICAL':
      return 'badge badge-risk-critical';
    case 'HIGH':
      return 'badge badge-risk-high';
    case 'MODERATE':
      return 'badge badge-risk-moderate';
    case 'LOW':
      return 'badge badge-risk-low';
    case 'NORMAL':
      return 'badge badge-risk-normal';
    case 'INSUFFICIENT_EVIDENCE':
      return 'badge bg-secondary text-light';
    default:
      return 'badge bg-secondary';
  }
}

export function getRiskColor(risk) {
  if (!risk) return '#6b7280';
  const r = String(risk).toUpperCase();
  switch (r) {
    case 'CRITICAL':
      return '#dc2626';
    case 'HIGH':
      return '#ef4444';
    case 'MODERATE':
      return '#f97316';
    case 'LOW':
      return '#eab308';
    case 'NORMAL':
      return '#10b981';
    default:
      return '#6b7280';
  }
}
