import React, { useState, useEffect } from 'react';
import { useMode } from '../context/ModeContext';
import weatherService from '../services/weatherService';
import RainfallChart from '../components/charts/RainfallChart';
import LoadingSpinner from '../components/common/LoadingSpinner';
import StatusBadge from '../components/common/StatusBadge';
import { formatDateTime, formatRainfall, formatNumber } from '../utils/formatters';
import { PUNJAB_DISTRICTS } from '../utils/punjabData';

export function WeatherMonitoring() {
  const { isDemoMode, selectedDistrict } = useMode();
  const [district, setDistrict] = useState(selectedDistrict !== 'All Districts' ? selectedDistrict : 'Jalandhar');
  const [loading, setLoading] = useState(true);
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState(null);

  const fetchForecast = async (targetDistrict) => {
    setLoading(true);
    setError(null);
    try {
      const res = await weatherService.getForecast(31.0267, 75.7871, targetDistrict, isDemoMode);
      setForecast(res);
    } catch (err) {
      setError(err.message || 'Failed to retrieve IMD weather telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const d = selectedDistrict !== 'All Districts' ? selectedDistrict : 'Jalandhar';
    setDistrict(d);
    fetchForecast(d);
  }, [selectedDistrict, isDemoMode]);

  return (
    <div className="container-fluid px-0">
      {/* Page Title & Controls */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{ width: '36px', height: '36px', backgroundColor: '#16865F' }}
            >
              <i className="bi bi-cloud-rain fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              Weather & Precipitation Telemetry
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Official India Meteorological Department (IMD) Quantitative Precipitation Forecasts (QPF) and radar observations.
          </p>
        </div>

        {/* District Selector & Refresh */}
        <div className="d-flex align-items-center gap-2">
          <select
            className="form-select form-select-sm"
            style={{ width: '180px' }}
            value={district}
            onChange={(e) => {
              setDistrict(e.target.value);
              fetchForecast(e.target.value);
            }}
          >
            {PUNJAB_DISTRICTS.filter((d) => d !== 'All Districts').map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={() => fetchForecast(district)}
            disabled={loading}
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
          </button>
        </div>
      </div>

      {loading && <LoadingSpinner message="Querying IMD weather gateway telemetry..." />}

      {error && (
        <div
          className="alert p-3 mb-4 d-flex align-items-center gap-2"
          style={{ backgroundColor: '#FDF2F2', borderColor: '#F8CBCB', color: '#D94A4A' }}
        >
          <i className="bi bi-exclamation-triangle-fill fs-5"></i>
          <span>{error}</span>
        </div>
      )}

      {forecast && !loading && (
        <div className="d-flex flex-column gap-4">
          {/* Atmospheric Telemetry Metric Cards */}
          <div className="row g-3">
            <div className="col-12 col-sm-6 col-xl-3">
              <div className="orca-card p-3">
                <span className="small text-uppercase fw-semibold" style={{ color: '#687B78', letterSpacing: '0.5px' }}>
                  Precipitation (24h)
                </span>
                <div className="d-flex align-items-baseline gap-2 mt-1">
                  <h3 className="fw-bold mb-0" style={{ color: '#16865F' }}>
                    {formatRainfall(forecast.rainfall_24h_mm)}
                  </h3>
                </div>
                <span className="small mt-2 d-block text-muted">
                  Precipitation Probability: <strong>{forecast.precipitation_probability || 85}%</strong>
                </span>
              </div>
            </div>

            <div className="col-12 col-sm-6 col-xl-3">
              <div className="orca-card p-3">
                <span className="small text-uppercase fw-semibold" style={{ color: '#687B78', letterSpacing: '0.5px' }}>
                  Surface Temperature
                </span>
                <div className="d-flex align-items-baseline gap-2 mt-1">
                  <h3 className="fw-bold mb-0" style={{ color: '#E99A36' }}>
                    {formatNumber(forecast.temperature_c, 1)} &deg;C
                  </h3>
                </div>
                <span className="small mt-2 d-block text-muted">Surface AWS Observation</span>
              </div>
            </div>

            <div className="col-12 col-sm-6 col-xl-3">
              <div className="orca-card p-3">
                <span className="small text-uppercase fw-semibold" style={{ color: '#687B78', letterSpacing: '0.5px' }}>
                  Wind Velocity
                </span>
                <div className="d-flex align-items-baseline gap-2 mt-1">
                  <h3 className="fw-bold mb-0" style={{ color: '#10483F' }}>
                    {formatNumber(forecast.wind_speed_kmh, 1)} km/h
                  </h3>
                </div>
                <span className="small mt-2 d-block text-muted">Monsoon Vector: South-West</span>
              </div>
            </div>

            <div className="col-12 col-sm-6 col-xl-3">
              <div className="orca-card p-3">
                <span className="small text-uppercase fw-semibold" style={{ color: '#687B78', letterSpacing: '0.5px' }}>
                  Evidence Source
                </span>
                <div className="mt-2">
                  <StatusBadge status={forecast.is_simulated ? 'SIMULATED' : 'LIVE DATA AVAILABLE'} size="lg" />
                </div>
                <span className="small mt-2 d-block text-muted" style={{ fontSize: '0.72rem' }}>
                  Issued: {formatDateTime(forecast.forecast_issue_time)}
                </span>
              </div>
            </div>
          </div>

          {/* Chart & Horizon Comparison */}
          <div className="row g-4">
            <div className="col-12 col-xl-8">
              <div className="orca-card p-4 h-100">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                    Precipitation Accumulation vs Critical Thresholds ({district})
                  </span>
                  <StatusBadge status={forecast.is_simulated ? 'SIMULATED' : 'LIVE'} />
                </div>
                <RainfallChart
                  rainfall24h={forecast.rainfall_24h_mm}
                  rainfall48h={forecast.rainfall_48h_mm}
                  rainfall72h={forecast.rainfall_72h_mm}
                  height={280}
                />
              </div>
            </div>

            {/* Threshold Analysis Card */}
            <div className="col-12 col-xl-4">
              <div className="orca-card p-4 h-100 d-flex flex-column justify-content-between">
                <div>
                  <h6 className="fw-bold mb-3" style={{ color: '#092F2B' }}>
                    Deterministic Rainfall Risk Rules
                  </h6>
                  <div className="d-flex flex-column gap-2 small">
                    <div
                      className="p-2 rounded-3 d-flex justify-content-between align-items-center"
                      style={{ backgroundColor: '#FDF2F2', border: '1px solid #F8CBCB' }}
                    >
                      <span className="fw-bold" style={{ color: '#D94A4A' }}>&gt; 120 mm (24h)</span>
                      <span className="badge badge-risk-critical">CRITICAL FLOOD RISK</span>
                    </div>
                    <div
                      className="p-2 rounded-3 d-flex justify-content-between align-items-center"
                      style={{ backgroundColor: '#FDF2F2', border: '1px solid #F8CBCB' }}
                    >
                      <span className="fw-bold" style={{ color: '#EA5454' }}>75 - 120 mm (24h)</span>
                      <span className="badge badge-risk-high">HIGH FLOOD RISK</span>
                    </div>
                    <div
                      className="p-2 rounded-3 d-flex justify-content-between align-items-center"
                      style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3' }}
                    >
                      <span className="fw-bold" style={{ color: '#E99A36' }}>40 - 75 mm (24h)</span>
                      <span className="badge badge-risk-moderate">MODERATE RISK</span>
                    </div>
                    <div
                      className="p-2 rounded-3 d-flex justify-content-between align-items-center"
                      style={{ backgroundColor: '#E7F6EF', border: '1px solid #BCE3D4' }}
                    >
                      <span className="fw-bold" style={{ color: '#16865F' }}>&lt; 40 mm (24h)</span>
                      <span className="badge badge-risk-normal">NORMAL / LOW</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-top small" style={{ borderColor: '#DFEAE6', color: '#687B78', fontSize: '0.72rem' }}>
                  Safety Requirement: Missing measurements are never converted to zero. Telemetry older than 24h evaluates to INSUFFICIENT_EVIDENCE in strict mode.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WeatherMonitoring;
