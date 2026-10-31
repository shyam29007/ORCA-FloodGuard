import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMode } from '../context/ModeContext';
import { useAuth } from '../context/AuthContext';
import { REFERENCE_VILLAGES, CWC_GAUGE_STATIONS, BBMB_DAMS } from '../utils/punjabData';
import riverService from '../services/riverService';
import damService from '../services/damService';
import alertService from '../services/alertService';
import providerService from '../services/providerService';
import StatusBadge from '../components/common/StatusBadge';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { formatWaterLevel, formatCusecs } from '../utils/formatters';

export function Dashboard() {
  const navigate = useNavigate();
  const { isDemoMode, selectedDistrict } = useMode();
  const { isOfficial } = useAuth();

  const [loading, setLoading] = useState(true);
  const [providerStatus, setProviderStatus] = useState(null);
  const [pendingAlerts, setPendingAlerts] = useState([]);
  const [riverReadings, setRiverReadings] = useState([]);
  const [damReadings, setDamReadings] = useState([]);

  // Assistant Input State
  const [selectedVillageId, setSelectedVillageId] = useState(REFERENCE_VILLAGES[2].id);
  const [assistantQuery, setAssistantQuery] = useState('');

  const loadData = async () => {
    try {
      const [provRes, alertRes, riverRes, damRes] = await Promise.allSettled([
        providerService.getStatus(),
        alertService.getPendingAlerts(),
        riverService.getAllRiverReadings(null, isDemoMode),
        damService.getDamInformation(null, isDemoMode),
      ]);

      if (provRes.status === 'fulfilled') setProviderStatus(provRes.value);
      if (alertRes.status === 'fulfilled') setPendingAlerts(alertRes.value || []);
      if (riverRes.status === 'fulfilled') setRiverReadings(riverRes.value || []);
      if (damRes.status === 'fulfilled') setDamReadings(damRes.value || []);
    } catch (err) {
      console.warn('Dashboard data fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [isDemoMode]);

  // Handle assistant query / navigation
  const handleAssistantSubmit = (e) => {
    if (e) e.preventDefault();
    const targetVillage = REFERENCE_VILLAGES.find((v) => v.id === selectedVillageId) || REFERENCE_VILLAGES[2];
    const qLower = assistantQuery.toLowerCase();

    if (qLower.includes('rainfall') || qLower.includes('weather') || qLower.includes('forecast')) {
      navigate(`/weather?district=${encodeURIComponent(targetVillage.district)}`);
    } else if (qLower.includes('river') || qLower.includes('gauge') || qLower.includes('level') || qLower.includes('stage')) {
      navigate(`/river?district=${encodeURIComponent(targetVillage.district)}`);
    } else if (qLower.includes('evacuat') || qLower.includes('shelter') || qLower.includes('camp')) {
      navigate(`/evacuation?village=${encodeURIComponent(targetVillage.name)}`);
    } else {
      // Default to AI flood assessment for the selected village
      navigate(`/assessment?village=${encodeURIComponent(targetVillage.name)}&district=${encodeURIComponent(targetVillage.district)}&lat=${targetVillage.coordinates[0]}&lng=${targetVillage.coordinates[1]}`);
    }
  };

  const handleChipClick = (queryText, villageId) => {
    setAssistantQuery(queryText);
    if (villageId) setSelectedVillageId(villageId);
    const targetVillage = REFERENCE_VILLAGES.find((v) => v.id === villageId) || REFERENCE_VILLAGES[2];

    if (queryText.includes('Rainfall')) {
      navigate(`/weather?district=${encodeURIComponent(targetVillage.district)}`);
    } else if (queryText.includes('River')) {
      navigate(`/river?district=${encodeURIComponent(targetVillage.district)}`);
    } else if (queryText.includes('Evacuation')) {
      navigate(`/evacuation?village=${encodeURIComponent(targetVillage.name)}`);
    } else {
      navigate(`/assessment?village=${encodeURIComponent(targetVillage.name)}&district=${encodeURIComponent(targetVillage.district)}&lat=${targetVillage.coordinates[0]}&lng=${targetVillage.coordinates[1]}`);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Synchronizing Sutlej-Beas telemetry & early-warning status..." />;
  }

  return (
    <div className="container-fluid px-0">
      {/* 1. HERO SECTION */}
      <div className="hero-card p-4 p-md-5 mb-4">
        <i className="bi bi-shield-fill-check hero-pattern d-none d-lg-block"></i>

        <div className="position-relative z-1" style={{ maxWidth: '820px' }}>
          <div className="d-flex align-items-center gap-2 mb-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{
                width: '42px',
                height: '42px',
                background: 'linear-gradient(135deg, #16865F 0%, #24B6A0 100%)',
                boxShadow: '0 2px 10px rgba(22, 134, 95, 0.35)',
              }}
            >
              <i className="bi bi-shield-fill-check fs-4"></i>
            </div>
            <div>
              <h2 className="fw-bold mb-0" style={{ color: '#092F2B', letterSpacing: '-0.5px' }}>
                ORCA-FloodGuard
              </h2>
              <span className="fw-semibold text-uppercase" style={{ fontSize: '0.75rem', color: '#16865F', letterSpacing: '0.8px' }}>
                Punjab Flood Early-Warning Advisor
              </span>
            </div>
          </div>

          <p className="mt-3 mb-4 fs-6" style={{ color: '#4B635E', lineHeight: '1.6' }}>
            AI-powered multi-agent flood risk assessment for Sutlej, Beas and Ravi river basins. Get flood-risk insights, analyze vulnerable locations and support informed emergency decisions.
          </p>

          <div className="d-flex flex-wrap align-items-center gap-3">
            <button
              type="button"
              className="btn btn-primary px-4 py-2 d-flex align-items-center gap-2"
              onClick={() => navigate('/assessment')}
            >
              <i className="bi bi-cpu fs-5"></i>
              <span>Assess Flood Risk</span>
              <i className="bi bi-arrow-right ms-1"></i>
            </button>
            <button
              type="button"
              className="btn btn-outline-teal px-4 py-2 d-flex align-items-center gap-2"
              onClick={() => navigate('/map')}
            >
              <i className="bi bi-map"></i>
              <span>Explore Interactive Map</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. FIVE PROMINENT FEATURE CARDS */}
      <div className="row g-3 mb-4">
        {/* CARD 1 — Assess Flood Risk */}
        <div className="col-12 col-md-6 col-lg-4 col-xl">
          <div
            className="feature-card"
            onClick={() => navigate('/assessment')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div className="feature-icon-wrapper">
                  <i className="bi bi-shield-check"></i>
                </div>
                <i className="bi bi-arrow-right feature-arrow fs-5"></i>
              </div>
              <h6 className="fw-bold mb-2" style={{ color: '#152E2B' }}>
                Assess Flood Risk
              </h6>
              <p className="small mb-0" style={{ color: '#687B78', lineHeight: '1.5' }}>
                Run AI-powered multi-agent flood-risk assessment for any village or location in Punjab.
              </p>
            </div>
            <div className="mt-3 pt-2 border-top" style={{ borderColor: '#DFEAE6', fontSize: '0.75rem', color: '#16865F', fontWeight: 600 }}>
              Launch Orchestrator &rarr;
            </div>
          </div>
        </div>

        {/* CARD 2 — Explore Flood Map */}
        <div className="col-12 col-md-6 col-lg-4 col-xl">
          <div
            className="feature-card"
            onClick={() => navigate('/map')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div className="feature-icon-wrapper">
                  <i className="bi bi-map"></i>
                </div>
                <i className="bi bi-arrow-right feature-arrow fs-5"></i>
              </div>
              <h6 className="fw-bold mb-2" style={{ color: '#152E2B' }}>
                Explore Flood Map
              </h6>
              <p className="small mb-0" style={{ color: '#687B78', lineHeight: '1.5' }}>
                View river gauges, dams, villages and geographical information.
              </p>
            </div>
            <div className="mt-3 pt-2 border-top" style={{ borderColor: '#DFEAE6', fontSize: '0.75rem', color: '#16865F', fontWeight: 600 }}>
              Open Spatial Viewer &rarr;
            </div>
          </div>
        </div>

        {/* CARD 3 — Check Weather & Rainfall */}
        <div className="col-12 col-md-6 col-lg-4 col-xl">
          <div
            className="feature-card"
            onClick={() => navigate('/weather')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div className="feature-icon-wrapper">
                  <i className="bi bi-cloud-rain"></i>
                </div>
                <i className="bi bi-arrow-right feature-arrow fs-5"></i>
              </div>
              <h6 className="fw-bold mb-2" style={{ color: '#152E2B' }}>
                Check Weather & Rainfall
              </h6>
              <p className="small mb-0" style={{ color: '#687B78', lineHeight: '1.5' }}>
                Inspect rainfall forecasts and weather evidence for your district.
              </p>
            </div>
            <div className="mt-3 pt-2 border-top" style={{ borderColor: '#DFEAE6', fontSize: '0.75rem', color: '#16865F', fontWeight: 600 }}>
              Inspect Meteorology &rarr;
            </div>
          </div>
        </div>

        {/* CARD 4 — Monitor River Gauges */}
        <div className="col-12 col-md-6 col-lg-4 col-xl">
          <div
            className="feature-card"
            onClick={() => navigate('/river')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div className="feature-icon-wrapper">
                  <i className="bi bi-water"></i>
                </div>
                <i className="bi bi-arrow-right feature-arrow fs-5"></i>
              </div>
              <h6 className="fw-bold mb-2" style={{ color: '#152E2B' }}>
                Monitor River Gauges
              </h6>
              <p className="small mb-0" style={{ color: '#687B78', lineHeight: '1.5' }}>
                Inspect river gauge levels, discharge and warning thresholds.
              </p>
            </div>
            <div className="mt-3 pt-2 border-top" style={{ borderColor: '#DFEAE6', fontSize: '0.75rem', color: '#16865F', fontWeight: 600 }}>
              View River Stages &rarr;
            </div>
          </div>
        </div>

        {/* CARD 5 — View & Authorize Alerts */}
        <div className="col-12 col-md-6 col-lg-4 col-xl">
          <div
            className="feature-card"
            onClick={() => navigate('/alerts')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div
                  className="feature-icon-wrapper"
                  style={{
                    backgroundColor: pendingAlerts.length > 0 ? '#FEF7ED' : '#E7F6EF',
                    color: pendingAlerts.length > 0 ? '#E99A36' : '#16865F',
                  }}
                >
                  <i className="bi bi-broadcast-pin"></i>
                </div>
                <i className="bi bi-arrow-right feature-arrow fs-5"></i>
              </div>
              <div className="d-flex align-items-center gap-2 mb-2">
                <h6 className="fw-bold mb-0" style={{ color: '#152E2B' }}>
                  View & Authorize Alerts
                </h6>
                {pendingAlerts.length > 0 && (
                  <span className="badge rounded-pill" style={{ backgroundColor: '#E99A36', color: '#FFFFFF', fontSize: '0.65rem' }}>
                    {pendingAlerts.length} Pending
                  </span>
                )}
              </div>
              <p className="small mb-0" style={{ color: '#687B78', lineHeight: '1.5' }}>
                Review AI-generated advisory drafts and authorize official warnings.
              </p>
            </div>
            <div className="mt-3 pt-2 border-top" style={{ borderColor: '#DFEAE6', fontSize: '0.75rem', color: '#E99A36', fontWeight: 600 }}>
              Official Authorization Gate &rarr;
            </div>
          </div>
        </div>
      </div>

      {/* 3. ORCA ASSISTANT INPUT AREA */}
      <div className="orca-card p-4 mb-4">
        <div className="d-flex align-items-center gap-2 mb-3">
          <i className="bi bi-chat-square-text text-success fs-5"></i>
          <div>
            <h6 className="fw-bold mb-0" style={{ color: '#152E2B' }}>
              ORCA Flood-Risk Intelligence Assistant
            </h6>
            <span className="small" style={{ color: '#687B78' }}>
              Guided assessment entry point connected directly to the 6-agent hydrological orchestrator.
            </span>
          </div>
        </div>

        <form onSubmit={handleAssistantSubmit} className="mb-3">
          <div className="assistant-search-box d-flex flex-column flex-md-row align-items-stretch align-items-md-center gap-2">
            {/* Location selector dropdown */}
            <div className="d-flex align-items-center flex-shrink-0 pe-2 border-end border-opacity-25" style={{ borderColor: '#DFEAE6' }}>
              <i className="bi bi-geo-alt me-2" style={{ color: '#16865F' }}></i>
              <select
                className="form-select form-select-sm border-0 bg-transparent fw-semibold shadow-none"
                style={{ color: '#152E2B', fontSize: '0.85rem', minWidth: '170px', cursor: 'pointer' }}
                value={selectedVillageId}
                onChange={(e) => setSelectedVillageId(e.target.value)}
              >
                {REFERENCE_VILLAGES.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.district})
                  </option>
                ))}
              </select>
            </div>

            {/* Input query field */}
            <div className="flex-grow-1 d-flex align-items-center px-2">
              <i className="bi bi-search text-muted me-2"></i>
              <input
                type="text"
                className="form-control border-0 bg-transparent shadow-none px-0"
                placeholder="Ask ORCA-FloodGuard about flood conditions, rainfall forecasts, river levels..."
                style={{ fontSize: '0.9rem', color: '#152E2B' }}
                value={assistantQuery}
                onChange={(e) => setAssistantQuery(e.target.value)}
              />
            </div>

            {/* Submit button */}
            <button
              type="submit"
              className="btn btn-primary d-flex align-items-center justify-content-center gap-2 px-4 py-2"
              style={{ borderRadius: '10px' }}
            >
              <span>Analyze</span>
              <i className="bi bi-arrow-right"></i>
            </button>
          </div>
        </form>

        {/* Suggested Question Chips */}
        <div className="d-flex flex-wrap align-items-center gap-2">
          <span className="small fw-semibold" style={{ color: '#687B78', fontSize: '0.78rem' }}>
            Suggested Inquiries:
          </span>
          <button
            type="button"
            className="question-chip btn btn-sm"
            onClick={() => handleChipClick('Flood risk for Gidderpindi', 'vil-gidderpindi-01')}
          >
            <i className="bi bi-shield-exclamation me-1" style={{ color: '#E99A36' }}></i>
            Flood risk for Gidderpindi
          </button>
          <button
            type="button"
            className="question-chip btn btn-sm"
            onClick={() => handleChipClick('Rainfall forecast for Jalandhar', 'vil-phillaur-03')}
          >
            <i className="bi bi-cloud-rain me-1" style={{ color: '#2789B6' }}></i>
            Rainfall forecast for Jalandhar
          </button>
          <button
            type="button"
            className="question-chip btn btn-sm"
            onClick={() => handleChipClick('River level at Phillaur', 'vil-phillaur-03')}
          >
            <i className="bi bi-water me-1" style={{ color: '#16865F' }}></i>
            River level at Phillaur
          </button>
          <button
            type="button"
            className="question-chip btn btn-sm"
            onClick={() => handleChipClick('Evacuation information near a selected village', 'vil-shahkot-02')}
          >
            <i className="bi bi-signpost-2 me-1" style={{ color: '#10483F' }}></i>
            Evacuation information for Shahkot
          </button>
        </div>
      </div>

      {/* 4. REAL HYDROLOGICAL STATUS SNAPSHOT */}
      <div className="row g-4 mb-4">
        {/* River Stages */}
        <div className="col-12 col-lg-7">
          <div className="orca-card h-100 p-3">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div className="d-flex align-items-center gap-2">
                <i className="bi bi-water text-success fs-5"></i>
                <h6 className="fw-bold mb-0" style={{ color: '#152E2B' }}>
                  Critical CWC River Gauge Stages (Sutlej & Beas)
                </h6>
                <StatusBadge
                  status={isDemoMode ? 'SIMULATED SCENARIO' : (providerStatus?.providers?.CWC?.has_live_data ? 'LIVE' : 'NO LIVE DATA')}
                  size="sm"
                />
              </div>
              <button
                type="button"
                className="btn btn-link btn-sm text-decoration-none p-0 fw-semibold"
                style={{ color: '#16865F', fontSize: '0.8rem' }}
                onClick={() => navigate('/river')}
              >
                All Gauges &rarr;
              </button>
            </div>

            <div className="table-responsive">
              <table className="table orca-table table-sm align-middle">
                <thead>
                  <tr>
                    <th>Station Name</th>
                    <th>River</th>
                    <th>Current Stage</th>
                    <th>Warning Level</th>
                    <th>Danger Level</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {CWC_GAUGE_STATIONS.slice(0, 4).map((st) => {
                    const match = Array.isArray(riverReadings)
                      ? riverReadings.find((r) => r.station_id === st.station_id || r.name === st.name || r.station_name === st.name)
                      : null;
                    const currentStage = match?.current_water_level_m ?? match?.reading?.water_level_meters;
                    const isAboveDanger = match?.is_above_danger || (currentStage != null && currentStage >= st.danger_level_m);
                    const isAboveWarning = match?.is_above_warning || (currentStage != null && currentStage >= st.warning_level_m);

                    return (
                      <tr key={st.id}>
                        <td className="fw-semibold" style={{ color: '#152E2B' }}>
                          {st.name} ({st.district})
                        </td>
                        <td style={{ color: '#687B78' }}>{st.river}</td>
                        <td className="font-monospace fw-bold" style={{ color: isAboveDanger ? '#D94A4A' : (isAboveWarning ? '#E99A36' : '#10483F') }}>
                          {currentStage != null ? formatWaterLevel(currentStage) : '—'}
                        </td>
                        <td className="font-monospace" style={{ color: '#687B78' }}>
                          {formatWaterLevel(st.warning_level_m)}
                        </td>
                        <td className="font-monospace" style={{ color: '#D94A4A' }}>
                          {formatWaterLevel(st.danger_level_m)}
                        </td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              backgroundColor: isAboveDanger ? '#FDF2F2' : (isAboveWarning ? '#FEF7ED' : '#E7F6EF'),
                              color: isAboveDanger ? '#D94A4A' : (isAboveWarning ? '#E99A36' : '#16865F'),
                              fontSize: '0.68rem',
                            }}
                          >
                            {isAboveDanger ? 'DANGER' : (isAboveWarning ? 'WARNING' : 'NORMAL')}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* BBMB Dam Dispatches */}
        <div className="col-12 col-lg-5">
          <div className="orca-card h-100 p-3">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <div className="d-flex align-items-center gap-2">
                <i className="bi bi-bounding-box-circles text-success fs-5"></i>
                <h6 className="fw-bold mb-0" style={{ color: '#152E2B' }}>
                  BBMB Major Reservoirs
                </h6>
                <StatusBadge
                  status={isDemoMode ? 'SIMULATED SCENARIO' : (providerStatus?.providers?.BBMB?.has_live_data ? 'LIVE' : 'NO LIVE DATA')}
                  size="sm"
                />
              </div>
              <button
                type="button"
                className="btn btn-link btn-sm text-decoration-none p-0 fw-semibold"
                style={{ color: '#16865F', fontSize: '0.8rem' }}
                onClick={() => navigate('/dams')}
              >
                Dam Bulletins &rarr;
              </button>
            </div>

            <div className="d-flex flex-column gap-3">
              {BBMB_DAMS.map((dam) => {
                const match = Array.isArray(damReadings)
                  ? damReadings.find((d) => d.dam_id === dam.id || d.name?.toLowerCase().includes(dam.name.toLowerCase().split(' ')[0]))
                  : null;
                const currentLevel = match?.current_water_level_m;
                const spillwayDischarge = match?.outflow_discharge_cusecs;
                const isSpilling = spillwayDischarge != null && spillwayDischarge > 0;

                return (
                  <div
                    key={dam.id}
                    className="p-3 rounded-3"
                    style={{
                      backgroundColor: '#F8FAF9',
                      border: '1px solid #DFEAE6',
                    }}
                  >
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className="fw-bold" style={{ color: '#152E2B' }}>
                        {dam.name} ({dam.river})
                      </span>
                      <span
                        className="badge font-monospace"
                        style={{
                          backgroundColor: isSpilling ? '#FEF7ED' : '#E7F6EF',
                          color: isSpilling ? '#E99A36' : '#16865F',
                        }}
                      >
                        {isSpilling ? `Discharging ${formatCusecs(spillwayDischarge)}` : 'Normal Storage'}
                      </span>
                    </div>
                    <div className="row g-2 small">
                      <div className="col-6">
                        <span className="text-muted d-block" style={{ fontSize: '0.72rem' }}>Current Reservoir Stage:</span>
                        <strong className="font-monospace" style={{ color: '#152E2B' }}>
                          {currentLevel != null ? formatWaterLevel(currentLevel) : formatWaterLevel(dam.full_reservoir_level_m - 3.2)}
                        </strong>
                      </div>
                      <div className="col-6">
                        <span className="text-muted d-block" style={{ fontSize: '0.72rem' }}>Spillway Outflow:</span>
                        <strong className="font-monospace" style={{ color: isSpilling ? '#E99A36' : '#10483F' }}>
                          {spillwayDischarge != null ? `${formatCusecs(spillwayDischarge)}` : '0 cusecs (Gates closed)'}
                        </strong>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-top d-flex justify-content-between align-items-center" style={{ borderColor: '#DFEAE6', fontSize: '0.7rem' }}>
                      <span className="text-muted">Full Reservoir Level: {formatWaterLevel(dam.full_reservoir_level_m)}</span>
                      <StatusBadge status={isDemoMode ? 'SIMULATED SCENARIO' : 'STATIC_REFERENCE'} size="sm" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 5. DEMO MODE INFORMATION BANNER */}
      <div
        className="p-3 p-md-4 rounded-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3"
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #DFEAE6',
          boxShadow: '0 1px 3px rgba(9, 47, 43, 0.05)',
        }}
      >
        <div className="d-flex align-items-start gap-3">
          <div
            className="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
            style={{ width: '36px', height: '36px', backgroundColor: '#E7F6EF', color: '#16865F' }}
          >
            <i className="bi bi-info-circle fs-5"></i>
          </div>
          <div>
            <h6 className="fw-bold mb-1" style={{ color: '#092F2B' }}>
              Operating in DEMO Mode
            </h6>
            <p className="small mb-0" style={{ color: '#687B78', maxWidth: '720px', lineHeight: '1.5' }}>
              Operating with simulated scenario datasets (SIMULATED SCENARIO / STATIC_REFERENCE). Official government telemetry from IMD, CWC and BBMB requires institutional credentials for live access.
            </p>
          </div>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary btn-sm flex-shrink-0 d-flex align-items-center gap-1"
          onClick={() => navigate('/system')}
        >
          <i className="bi bi-hdd-network"></i>
          <span>View System Status</span>
        </button>
      </div>
    </div>
  );
}

export default Dashboard;
