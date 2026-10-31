import React, { useState, useEffect } from 'react';
import providerService from '../services/providerService';
import apiClient from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { formatDateTime } from '../utils/formatters';

export function SystemStatus() {
  const [providerData, setProviderData] = useState(null);
  const [backendHealth, setBackendHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [probing, setProbing] = useState({});

  const loadStatus = async () => {
    try {
      const [provRes, healthRes] = await Promise.allSettled([
        providerService.getStatus(),
        apiClient.get('/health'),
      ]);

      if (provRes.status === 'fulfilled') setProviderData(provRes.value);
      if (healthRes.status === 'fulfilled') setBackendHealth(healthRes.value);
    } catch (err) {
      console.warn('System status fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleProbeAll = async () => {
    setRefreshing(true);
    try {
      const [probeRes, healthRes] = await Promise.allSettled([
        providerService.probeAll(),
        apiClient.get('/health'),
      ]);

      if (probeRes.status === 'fulfilled') setProviderData(probeRes.value);
      if (healthRes.status === 'fulfilled') setBackendHealth(healthRes.value);
    } catch (err) {
      console.warn('Probe gateways error:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const probeSingleProvider = async (name) => {
    const key = name.toUpperCase();
    const lower = name.toLowerCase();
    setProbing((prev) => ({ ...prev, [lower]: true }));
    try {
      const res = await providerService.probeProvider(lower);
      setProviderData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          providers: {
            ...prev.providers,
            [key]: res,
          },
        };
      });
    } catch (err) {
      console.warn(`Probe provider ${name} error:`, err);
    } finally {
      setProbing((prev) => ({ ...prev, [lower]: false }));
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Diagnosing telemetry gateways and database connectivity..." />;
  }

  const providers = providerData?.providers || {};
  const summary = providerData?.summary || {};
  const isAllLive = summary?.live_data_available_count === summary?.total_providers && summary?.total_providers > 0;

  return (
    <div className="container-fluid px-0">
      {/* Title & Probe Action */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{ width: '36px', height: '36px', backgroundColor: '#16865F' }}
            >
              <i className="bi bi-hdd-network fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              System & Telemetry Providers Gateway
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Real-time diagnostics of external government telemetry feeds (IMD, CWC, BBMB) and backend service integrity.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary btn-sm d-flex align-items-center gap-2 px-3 py-2"
          onClick={handleProbeAll}
          disabled={refreshing}
          style={{ borderRadius: '8px' }}
        >
          <i className={`bi bi-arrow-clockwise ${refreshing ? 'spin' : ''}`}></i>
          <span>{refreshing ? 'Probing All Gateways...' : 'Probe Gateways'}</span>
        </button>
      </div>

      {/* Decoupling Invariant Banner */}
      <div
        className="p-3 mb-4 rounded-3 d-flex align-items-start gap-3"
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DFEAE6',
          boxShadow: '0 1px 3px rgba(9, 47, 43, 0.04)',
        }}
      >
        <div
          className="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
          style={{ width: '32px', height: '32px', backgroundColor: '#E7F6EF', color: '#16865F' }}
        >
          <i className="bi bi-info-circle-fill"></i>
        </div>
        <div className="small" style={{ lineHeight: '1.5' }}>
          <strong className="d-block mb-1" style={{ color: '#092F2B' }}>
            Architecture Decoupling: Application State vs. Live Government Telemetry
          </strong>
          <span style={{ color: '#687B78' }}>
            A running FastAPI server indicates <span className="fw-bold" style={{ color: '#16865F' }}>APPLICATION ONLINE</span> and database connectivity.
            It does <strong>NOT</strong> imply live telemetry. Real-time hydrological feeds from IMD, CWC, and BBMB require authentic institutional gateway credentials, validated payload schemas, and fresh observation timestamps (&lt; 24h).
            When credentials are unconfigured, ORCA-FloodGuard operates in <strong>DEMO MODE</strong> with simulated scenario datasets (SIMULATED SCENARIO / STATIC_REFERENCE), or halts strictly with <strong>INSUFFICIENT_EVIDENCE</strong> in <strong>OPERATIONAL MODE</strong>.
          </span>
        </div>
      </div>

      {/* 1. SECTIONS A, B & C: APPLICATION, DATABASE & LLM HEALTH */}
      {backendHealth && (
        <div className="orca-card p-4 mb-4">
          <div className="d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2 mb-3 pb-2 border-bottom" style={{ borderColor: '#DFEAE6' }}>
            <div className="d-flex align-items-center gap-2">
              <i className="bi bi-server text-success fs-5"></i>
              <h6 className="fw-bold mb-0 text-uppercase small" style={{ color: '#092F2B' }}>
                Application Service & Core Infrastructure
              </h6>
            </div>
            <div className="d-flex align-items-center gap-2">
              <StatusBadge status={backendHealth.app_status || 'APPLICATION ONLINE'} />
              <StatusBadge status={backendHealth.database_health || 'DATABASE CONNECTED'} />
            </div>
          </div>

          <div className="row g-3">
            {/* Section A: Application */}
            <div className="col-12 col-sm-6 col-md-3">
              <div className="p-3 rounded-3" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                <span className="small text-muted d-block mb-1">Application Branding</span>
                <div className="fw-bold small" style={{ color: '#152E2B' }}>
                  {backendHealth.app_name || 'ORCA-FloodGuard'}
                </div>
                <div className="small text-muted mt-1 font-monospace" style={{ fontSize: '0.7rem' }}>
                  Environment: {backendHealth.environment || 'production'}
                </div>
              </div>
            </div>

            {/* Section B: Database */}
            <div className="col-12 col-sm-6 col-md-3">
              <div className="p-3 rounded-3" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                <span className="small text-muted d-block mb-1">Database Connectivity</span>
                <div className="fw-bold small" style={{ color: '#152E2B' }}>
                  {backendHealth.database_mode} ({backendHealth.database_status || 'connected'})
                </div>
                <div className="small text-muted mt-1 font-monospace" style={{ fontSize: '0.7rem' }}>
                  Engine: SQLite / PostgreSQL
                </div>
              </div>
            </div>

            {/* Section C: LLM Configuration */}
            <div className="col-12 col-sm-6 col-md-3">
              <div className="p-3 rounded-3" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                <div className="d-flex justify-content-between align-items-center mb-1">
                  <span className="small text-muted">LLM Reasoning Refiner</span>
                  <StatusBadge
                    status={
                      backendHealth.llm_configuration_status === 'CONFIGURED'
                        ? 'CONFIGURED'
                        : 'MOCK / DETERMINISTIC'
                    }
                  />
                </div>
                <div className="fw-bold small font-monospace" style={{ color: '#152E2B' }}>
                  {backendHealth.llm_provider || 'gemini'} ({backendHealth.llm_model_id || 'gemini-1.5-flash'})
                </div>
                <div className="small mt-1 text-muted" style={{ fontSize: '0.7rem' }}>
                  {backendHealth.llm_configuration_status === 'CONFIGURED'
                    ? 'Active cloud API provider'
                    : 'Deterministic bilingual fallback active'}
                </div>
              </div>
            </div>

            {/* Overall Telemetry State */}
            <div className="col-12 col-sm-6 col-md-3">
              <div className="p-3 rounded-3" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                <span className="small text-muted d-block mb-1">Telemetry Fallback Policy</span>
                <div className="fw-bold small" style={{ color: '#152E2B' }}>
                  Scenario Simulation Allowed
                </div>
                <div className="small text-muted mt-1" style={{ fontSize: '0.7rem' }}>
                  Status: Simulation Fallback Enabled
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. SECTIONS D, E & F: EXTERNAL GOVERNMENT TELEMETRY PROVIDERS */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h6 className="fw-bold small text-uppercase mb-0 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
          <i className="bi bi-activity text-success"></i> Government Telemetry Providers Gateway Status
        </h6>
        <div className="d-flex align-items-center gap-2">
          <span className="text-muted small">Aggregated Readiness:</span>
          <StatusBadge status={isAllLive ? 'LIVE DATA AVAILABLE' : 'SIMULATION ACTIVE'} />
        </div>
      </div>

      <div className="row g-4 mb-4">
        {/* SECTION D — IMD Provider Card */}
        {providers.IMD && (
          <div className="col-12 col-lg-4">
            <div className="orca-card p-3 h-100 d-flex flex-column justify-content-between">
              <div>
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <div>
                    <h5 className="fw-bold mb-0" style={{ color: '#092F2B' }}>IMD Connector</h5>
                    <span className="small text-muted">{providers.IMD.service_type}</span>
                  </div>
                  <StatusBadge status={providers.IMD.status} />
                </div>

                {/* Dependent Agent Info */}
                <div
                  className="p-2 rounded-3 mb-3 small"
                  style={{ backgroundColor: '#E7F6EF', border: '1px solid #BCE3D4' }}
                >
                  <div className="d-flex justify-content-between mb-1">
                    <span className="fw-bold" style={{ color: '#10483F' }}>Dependent Agent:</span>
                    <strong style={{ color: '#152E2B' }}>{providers.IMD.dependent_agent_name || 'Weather Agent'}</strong>
                  </div>
                  <div style={{ fontSize: '0.73rem', color: '#687B78' }}>
                    <strong>Impact:</strong> {providers.IMD.impact_description || 'Live rainfall evidence unavailable.'}
                  </div>
                </div>

                {/* Checklist */}
                <div className="d-flex flex-column gap-2 mb-3 small">
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Gateway Base URL:</span>
                    <span className={`font-monospace ${providers.IMD.is_configured ? 'text-success fw-bold' : 'text-muted'}`}>
                      {providers.IMD.is_configured ? 'CONFIGURED' : 'NOT_CONFIGURED'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Authentication:</span>
                    <span className={`font-monospace ${providers.IMD.is_authenticated ? 'text-success fw-bold' : 'text-danger'}`}>
                      {providers.IMD.is_authenticated ? 'AUTHENTICATED' : 'BLOCKED / MISSING'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="text-muted">Network Connection:</span>
                    <StatusBadge status={providers.IMD.network_status || 'NOT_CONFIGURED'} size="sm" />
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Last Active Probe:</span>
                    <span className="font-monospace text-dark" style={{ fontSize: '0.72rem' }}>
                      {providers.IMD.last_probe_timestamp ? formatDateTime(providers.IMD.last_probe_timestamp) : 'Not Yet Tested'}
                    </span>
                  </div>
                  {providers.IMD.latency_ms != null && (
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">Probe Latency:</span>
                      <span className="font-monospace fw-bold" style={{ color: '#16865F', fontSize: '0.72rem' }}>
                        {providers.IMD.latency_ms} ms
                      </span>
                    </div>
                  )}
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Payload Validation:</span>
                    <span className="font-monospace text-muted">
                      {providers.IMD.payload_schema_validation || providers.IMD.data_validation_status || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Measurements:</span>
                    <span className="font-monospace text-muted">
                      {providers.IMD.measurement_validation || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Timestamp:</span>
                    <span className="font-monospace text-muted">
                      {providers.IMD.timestamp_validation || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Data Freshness:</span>
                    <span className="font-monospace text-muted">
                      {providers.IMD.data_freshness || providers.IMD.data_freshness_status || 'NOT_AVAILABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="text-muted">Operational Live Data:</span>
                    <span
                      className="badge font-monospace"
                      style={{
                        backgroundColor: providers.IMD.operational_data_available ? '#E7F6EF' : '#F8FAF9',
                        color: providers.IMD.operational_data_available ? '#16865F' : '#687B78',
                        border: '1px solid #DFEAE6',
                        fontSize: '0.68rem',
                      }}
                    >
                      {providers.IMD.operational_data_available ? 'AVAILABLE' : 'UNAVAILABLE'}
                    </span>
                  </div>
                </div>

                {/* Verified Government Endpoint */}
                <div className="p-2 rounded-3 mb-2" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                  <span className="text-muted d-block" style={{ fontSize: '0.68rem' }}>Verified Government Portal:</span>
                  <div className="small font-monospace text-truncate" style={{ color: '#16865F' }}>
                    {providers.IMD.verified_official_endpoint}
                  </div>
                </div>

                {/* Institutional Access Restriction */}
                <div className="p-2 rounded-3 mb-2" style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3' }}>
                  <span className="fw-semibold d-block mb-1" style={{ fontSize: '0.68rem', color: '#92400E' }}>
                    Institutional Access Restriction:
                  </span>
                  <p className="mb-0" style={{ fontSize: '0.72rem', color: '#78350F', lineHeight: '1.4' }}>
                    {providers.IMD.access_restriction}
                  </p>
                </div>
              </div>

              <div className="mt-3 pt-2 border-top d-flex justify-content-between align-items-center" style={{ borderColor: '#DFEAE6' }}>
                <div className="text-muted text-truncate me-2" style={{ fontSize: '0.7rem' }}>
                  Diagnostic: {providers.IMD.error_message || 'Connector configured according to safety specification.'}
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm flex-shrink-0"
                  style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                  onClick={() => probeSingleProvider('imd')}
                  disabled={probing['imd']}
                >
                  <i className={`bi bi-arrow-clockwise me-1 ${probing['imd'] ? 'spin' : ''}`}></i>
                  {probing['imd'] ? 'Probing...' : 'Probe'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SECTION E — CWC River Provider Card */}
        {providers.CWC && (
          <div className="col-12 col-lg-4">
            <div className="orca-card p-3 h-100 d-flex flex-column justify-content-between">
              <div>
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <div>
                    <h5 className="fw-bold mb-0" style={{ color: '#092F2B' }}>CWC Connector</h5>
                    <span className="small text-muted">{providers.CWC.service_type}</span>
                  </div>
                  <StatusBadge status={providers.CWC.status} />
                </div>

                {/* Dependent Agent Info */}
                <div
                  className="p-2 rounded-3 mb-3 small"
                  style={{ backgroundColor: '#E7F6EF', border: '1px solid #BCE3D4' }}
                >
                  <div className="d-flex justify-content-between mb-1">
                    <span className="fw-bold" style={{ color: '#10483F' }}>Dependent Agent:</span>
                    <strong style={{ color: '#152E2B' }}>{providers.CWC.dependent_agent_name || 'River Agent'}</strong>
                  </div>
                  <div style={{ fontSize: '0.73rem', color: '#687B78' }}>
                    <strong>Impact:</strong> {providers.CWC.impact_description || 'Live river gauge evidence unavailable.'}
                  </div>
                </div>

                {/* Checklist */}
                <div className="d-flex flex-column gap-2 mb-3 small">
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Gateway Base URL:</span>
                    <span className={`font-monospace ${providers.CWC.is_configured ? 'text-success fw-bold' : 'text-muted'}`}>
                      {providers.CWC.is_configured ? 'CONFIGURED' : 'NOT_CONFIGURED'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Authentication:</span>
                    <span className={`font-monospace ${providers.CWC.is_authenticated ? 'text-success fw-bold' : 'text-danger'}`}>
                      {providers.CWC.is_authenticated ? 'AUTHENTICATED' : 'BLOCKED / MISSING'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="text-muted">Network Connection:</span>
                    <StatusBadge status={providers.CWC.network_status || 'NOT_CONFIGURED'} size="sm" />
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Last Active Probe:</span>
                    <span className="font-monospace text-dark" style={{ fontSize: '0.72rem' }}>
                      {providers.CWC.last_probe_timestamp ? formatDateTime(providers.CWC.last_probe_timestamp) : 'Not Yet Tested'}
                    </span>
                  </div>
                  {providers.CWC.latency_ms != null && (
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">Probe Latency:</span>
                      <span className="font-monospace fw-bold" style={{ color: '#16865F', fontSize: '0.72rem' }}>
                        {providers.CWC.latency_ms} ms
                      </span>
                    </div>
                  )}
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Payload Validation:</span>
                    <span className="font-monospace text-muted">
                      {providers.CWC.payload_schema_validation || providers.CWC.data_validation_status || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Measurements:</span>
                    <span className="font-monospace text-muted">
                      {providers.CWC.measurement_validation || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Timestamp:</span>
                    <span className="font-monospace text-muted">
                      {providers.CWC.timestamp_validation || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Data Freshness:</span>
                    <span className="font-monospace text-muted">
                      {providers.CWC.data_freshness || providers.CWC.data_freshness_status || 'NOT_AVAILABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="text-muted">Operational Live Data:</span>
                    <span
                      className="badge font-monospace"
                      style={{
                        backgroundColor: providers.CWC.operational_data_available ? '#E7F6EF' : '#F8FAF9',
                        color: providers.CWC.operational_data_available ? '#16865F' : '#687B78',
                        border: '1px solid #DFEAE6',
                        fontSize: '0.68rem',
                      }}
                    >
                      {providers.CWC.operational_data_available ? 'AVAILABLE' : 'UNAVAILABLE'}
                    </span>
                  </div>
                </div>

                {/* Verified Government Endpoint */}
                <div className="p-2 rounded-3 mb-2" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                  <span className="text-muted d-block" style={{ fontSize: '0.68rem' }}>Verified Government Portal:</span>
                  <div className="small font-monospace text-truncate" style={{ color: '#16865F' }}>
                    {providers.CWC.verified_official_endpoint}
                  </div>
                </div>

                {/* Institutional Access Restriction */}
                <div className="p-2 rounded-3 mb-2" style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3' }}>
                  <span className="fw-semibold d-block mb-1" style={{ fontSize: '0.68rem', color: '#92400E' }}>
                    Institutional Access Restriction:
                  </span>
                  <p className="mb-0" style={{ fontSize: '0.72rem', color: '#78350F', lineHeight: '1.4' }}>
                    {providers.CWC.access_restriction}
                  </p>
                </div>
              </div>

              <div className="mt-3 pt-2 border-top d-flex justify-content-between align-items-center" style={{ borderColor: '#DFEAE6' }}>
                <div className="text-muted text-truncate me-2" style={{ fontSize: '0.7rem' }}>
                  Diagnostic: {providers.CWC.error_message || 'Connector configured according to safety specification.'}
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm flex-shrink-0"
                  style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                  onClick={() => probeSingleProvider('cwc')}
                  disabled={probing['cwc']}
                >
                  <i className={`bi bi-arrow-clockwise me-1 ${probing['cwc'] ? 'spin' : ''}`}></i>
                  {probing['cwc'] ? 'Probing...' : 'Probe'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SECTION F — BBMB Dam Provider Card */}
        {providers.BBMB && (
          <div className="col-12 col-lg-4">
            <div className="orca-card p-3 h-100 d-flex flex-column justify-content-between">
              <div>
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <div>
                    <h5 className="fw-bold mb-0" style={{ color: '#092F2B' }}>BBMB Connector</h5>
                    <span className="small text-muted">{providers.BBMB.service_type}</span>
                  </div>
                  <StatusBadge status={providers.BBMB.status} />
                </div>

                {/* Dependent Agent Info */}
                <div
                  className="p-2 rounded-3 mb-3 small"
                  style={{ backgroundColor: '#E7F6EF', border: '1px solid #BCE3D4' }}
                >
                  <div className="d-flex justify-content-between mb-1">
                    <span className="fw-bold" style={{ color: '#10483F' }}>Dependent Agent:</span>
                    <strong style={{ color: '#152E2B' }}>{providers.BBMB.dependent_agent_name || 'Dam Agent'}</strong>
                  </div>
                  <div style={{ fontSize: '0.73rem', color: '#687B78' }}>
                    <strong>Impact:</strong> {providers.BBMB.impact_description || 'Live reservoir storage evidence unavailable.'}
                  </div>
                </div>

                {/* Checklist */}
                <div className="d-flex flex-column gap-2 mb-3 small">
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Gateway Base URL:</span>
                    <span className={`font-monospace ${providers.BBMB.is_configured ? 'text-success fw-bold' : 'text-muted'}`}>
                      {providers.BBMB.is_configured ? 'CONFIGURED' : 'NOT_CONFIGURED'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Authentication:</span>
                    <span className={`font-monospace ${providers.BBMB.is_authenticated ? 'text-success fw-bold' : 'text-danger'}`}>
                      {providers.BBMB.is_authenticated ? 'AUTHENTICATED' : 'BLOCKED / MISSING'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="text-muted">Network Connection:</span>
                    <StatusBadge status={providers.BBMB.network_status || 'NOT_CONFIGURED'} size="sm" />
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Last Active Probe:</span>
                    <span className="font-monospace text-dark" style={{ fontSize: '0.72rem' }}>
                      {providers.BBMB.last_probe_timestamp ? formatDateTime(providers.BBMB.last_probe_timestamp) : 'Not Yet Tested'}
                    </span>
                  </div>
                  {providers.BBMB.latency_ms != null && (
                    <div className="d-flex justify-content-between">
                      <span className="text-muted">Probe Latency:</span>
                      <span className="font-monospace fw-bold" style={{ color: '#16865F', fontSize: '0.72rem' }}>
                        {providers.BBMB.latency_ms} ms
                      </span>
                    </div>
                  )}
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Payload Validation:</span>
                    <span className="font-monospace text-muted">
                      {providers.BBMB.payload_schema_validation || providers.BBMB.data_validation_status || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Measurements:</span>
                    <span className="font-monospace text-muted">
                      {providers.BBMB.measurement_validation || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Timestamp:</span>
                    <span className="font-monospace text-muted">
                      {providers.BBMB.timestamp_validation || 'NOT_APPLICABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted">Data Freshness:</span>
                    <span className="font-monospace text-muted">
                      {providers.BBMB.data_freshness || providers.BBMB.data_freshness_status || 'NOT_AVAILABLE'}
                    </span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="text-muted">Operational Live Data:</span>
                    <span
                      className="badge font-monospace"
                      style={{
                        backgroundColor: providers.BBMB.operational_data_available ? '#E7F6EF' : '#F8FAF9',
                        color: providers.BBMB.operational_data_available ? '#16865F' : '#687B78',
                        border: '1px solid #DFEAE6',
                        fontSize: '0.68rem',
                      }}
                    >
                      {providers.BBMB.operational_data_available ? 'AVAILABLE' : 'UNAVAILABLE'}
                    </span>
                  </div>
                </div>

                {/* Verified Government Endpoint */}
                <div className="p-2 rounded-3 mb-2" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                  <span className="text-muted d-block" style={{ fontSize: '0.68rem' }}>Verified Government Portal:</span>
                  <div className="small font-monospace text-truncate" style={{ color: '#16865F' }}>
                    {providers.BBMB.verified_official_endpoint}
                  </div>
                </div>

                {/* Institutional Access Restriction */}
                <div className="p-2 rounded-3 mb-2" style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3' }}>
                  <span className="fw-semibold d-block mb-1" style={{ fontSize: '0.68rem', color: '#92400E' }}>
                    Institutional Access Restriction:
                  </span>
                  <p className="mb-0" style={{ fontSize: '0.72rem', color: '#78350F', lineHeight: '1.4' }}>
                    {providers.BBMB.access_restriction}
                  </p>
                </div>
              </div>

              <div className="mt-3 pt-2 border-top d-flex justify-content-between align-items-center" style={{ borderColor: '#DFEAE6' }}>
                <div className="text-muted text-truncate me-2" style={{ fontSize: '0.7rem' }}>
                  Diagnostic: {providers.BBMB.error_message || 'Connector configured according to safety specification.'}
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm flex-shrink-0"
                  style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                  onClick={() => probeSingleProvider('bbmb')}
                  disabled={probing['bbmb']}
                >
                  <i className={`bi bi-arrow-clockwise me-1 ${probing['bbmb'] ? 'spin' : ''}`}></i>
                  {probing['bbmb'] ? 'Probing...' : 'Probe'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. SECTION G: STATIC TOPOGRAPHICAL & GIS REFERENCE ARCHITECTURE */}
      <h6 className="fw-bold small text-uppercase mb-3 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
        <i className="bi bi-layers text-success"></i> Static Geographic Reference Architecture (Non-Live Baseline)
      </h6>

      <div className="row g-4 mb-4">
        <div className="col-12 col-md-6">
          <div className="orca-card p-3 h-100">
            <div className="d-flex justify-content-between align-items-start mb-2">
              <div>
                <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                  NASA SRTM Elevation Grid (30m)
                </h6>
                <span className="small text-muted">Digital Elevation Model (DEM) Topography</span>
              </div>
              <StatusBadge status="STATIC_REFERENCE" />
            </div>

            <p className="small mb-3" style={{ color: '#687B78', lineHeight: '1.5' }}>
              Baseline ground elevation AMSL (EGM96 geoid datum) acquired during the Shuttle Radar Topography Mission.
              This represents authoritative static terrain contours to identify low-lying depressions (&lt; 216m AMSL).
            </p>

            <div className="p-3 rounded-3 small" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
              <div className="d-flex justify-content-between mb-1">
                <span className="text-muted">Dependent Agent:</span>
                <strong style={{ color: '#152E2B' }}>GIS & Evacuation Agent</strong>
              </div>
              <div className="d-flex justify-content-between mb-1">
                <span className="text-muted">Evidence Classification:</span>
                <span className="badge font-monospace" style={{ backgroundColor: '#F4FAF7', color: '#16865F', border: '1px solid #DFEAE6' }}>
                  STATIC_REFERENCE
                </span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted">Telemetry Status:</span>
                <span style={{ color: '#E99A36', fontWeight: 600 }}>Non-Live Topographical Reference</span>
              </div>
            </div>
          </div>
        </div>

        <div className="col-12 col-md-6">
          <div className="orca-card p-3 h-100">
            <div className="d-flex justify-content-between align-items-start mb-2">
              <div>
                <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                  OpenStreetMap & Punjab Relief Infrastructure
                </h6>
                <span className="small text-muted">Evacuation Corridors & Seeded Shelter Capacities</span>
              </div>
              <StatusBadge status="STATIC_REFERENCE" />
            </div>

            <p className="small mb-3" style={{ color: '#687B78', lineHeight: '1.5' }}>
              Designated relief centres (schools, colleges, community centres) and road network vectors.
              Under ORCA safety rules, all generated evacuation routes remain labeled <code>CANDIDATE / UNVERIFIED</code> until authorized on-ground field inspection.
            </p>

            <div className="p-3 rounded-3 small" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
              <div className="d-flex justify-content-between mb-1">
                <span className="text-muted">Dependent Agent:</span>
                <strong style={{ color: '#152E2B' }}>GIS & Evacuation Agent</strong>
              </div>
              <div className="d-flex justify-content-between mb-1">
                <span className="text-muted">Route Verification:</span>
                <span className="badge font-monospace" style={{ backgroundColor: '#FEF7ED', color: '#E99A36', border: '1px solid #FCE4C3' }}>
                  UNVERIFIED CANDIDATE
                </span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted">Relief Centre Stored:</span>
                <span style={{ color: '#16865F', fontWeight: 600 }}>Verified Seeded Capacities</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SystemStatus;
