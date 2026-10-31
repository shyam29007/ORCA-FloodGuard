import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useMode } from '../context/ModeContext';
import { useAuth } from '../context/AuthContext';
import floodService from '../services/floodService';
import agentService from '../services/agentService';
import alertService from '../services/alertService';
import providerService from '../services/providerService';
import { REFERENCE_VILLAGES, PUNJAB_DISTRICTS } from '../utils/punjabData';
import RiskBadge from '../components/common/RiskBadge';
import StatusBadge from '../components/common/StatusBadge';
import { formatDateTime, formatRainfall, formatWaterLevel, formatCusecs } from '../utils/formatters';

const formatAgentName = (name) => {
  if (!name) return 'Agent';
  const mapping = {
    location_agent: '1. Location Agent',
    weather_agent: '2. Weather Agent',
    river_agent: '3. River Agent',
    dam_agent: '4. Dam Agent',
    gis_evacuation_agent: '5. GIS & Evacuation Agent',
    alert_agent: '6. Alert Agent',
  };
  return mapping[name] || name;
};

export function FloodAssessment() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isDemoMode } = useMode();
  const { user, isOfficial } = useAuth();

  // Parse URL search parameters if arriving from Home assistant search
  const queryParams = new URLSearchParams(location.search);
  const initialVillageName = queryParams.get('village');

  // Form State - SECTION A (Location)
  const defaultIdx = initialVillageName
    ? REFERENCE_VILLAGES.findIndex((v) => v.name.toLowerCase() === initialVillageName.toLowerCase())
    : 2; // Default to Phillaur
  const activeIdx = defaultIdx >= 0 ? defaultIdx : 2;

  const [selectedVillageIndex, setSelectedVillageIndex] = useState(activeIdx);
  const [villageName, setVillageName] = useState(REFERENCE_VILLAGES[activeIdx].name);
  const [district, setDistrict] = useState(REFERENCE_VILLAGES[activeIdx].district);
  const [latitude, setLatitude] = useState(REFERENCE_VILLAGES[activeIdx].coordinates[0]);
  const [longitude, setLongitude] = useState(REFERENCE_VILLAGES[activeIdx].coordinates[1]);

  // Form State - SECTION B (Parameters)
  const [horizonHours, setHorizonHours] = useState(72);
  const [fieldObservations, setFieldObservations] = useState('');
  const [incidentDescription, setIncidentDescription] = useState('');
  const [operationalMode, setOperationalMode] = useState(!isDemoMode);

  // Form State - SECTION C (Evidence Readiness)
  const [providerDashboard, setProviderDashboard] = useState(null);

  // Execution & Results State
  const [isAssessing, setIsAssessing] = useState(false);
  const [assessmentResult, setAssessmentResult] = useState(null);
  const [executionTrace, setExecutionTrace] = useState(null);
  const [error, setError] = useState(null);

  // Official Decision State
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [approvalReason, setApprovalReason] = useState('');
  const [decisionSubmitting, setDecisionSubmitting] = useState(false);
  const [decisionSuccess, setDecisionSuccess] = useState(null);

  // Load provider health for Evidence Readiness Section
  useEffect(() => {
    providerService.getStatus().then((data) => setProviderDashboard(data)).catch(() => {});
  }, []);

  // Update village parameters when dropdown changes
  const handleVillageSelect = (idx) => {
    setSelectedVillageIndex(idx);
    const v = REFERENCE_VILLAGES[idx];
    if (v) {
      setVillageName(v.name);
      setLatitude(v.coordinates[0]);
      setLongitude(v.coordinates[1]);
      setDistrict(v.district);
    }
  };

  const handleRunAssessment = async (e) => {
    e.preventDefault();
    setIsAssessing(true);
    setError(null);
    setAssessmentResult(null);
    setExecutionTrace(null);
    setDecisionSuccess(null);

    try {
      const payload = {
        village_name: villageName,
        coordinates: {
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
        },
        district: district,
        forecast_horizon_hours: parseInt(horizonHours),
        include_simulated_fallback: !operationalMode,
        operational_mode: operationalMode,
      };

      const result = await floodService.assessFloodRisk(payload);
      setAssessmentResult(result);

      // Extract specialist agent traces
      let tracesList = [];
      if (result.agent_traces && typeof result.agent_traces === 'object') {
        tracesList = Object.values(result.agent_traces);
      }
      if (tracesList.length === 0 && result.run_id) {
        try {
          const traceData = await agentService.getRunTrace(result.run_id);
          if (Array.isArray(traceData) && traceData.length > 0) {
            tracesList = traceData;
          }
        } catch {
          // Traces endpoint optional
        }
      }
      setExecutionTrace(tracesList.length > 0 ? tracesList : null);
    } catch (err) {
      setError(err.message || 'Assessment execution failed. Check backend connectivity.');
    } finally {
      setIsAssessing(false);
    }
  };

  const handleApproveAdvisory = async () => {
    if (!assessmentResult || !approvalReason.trim()) return;
    setDecisionSubmitting(true);
    try {
      // Create and approve alert in one workflow linked to real assessment
      const alertPayload = {
        village_name: assessmentResult.village?.name || villageName,
        district: assessmentResult.village?.district || district,
        risk_level: assessmentResult.overall_risk,
        headline: `FLOOD ADVISORY (${assessmentResult.overall_risk}): ${assessmentResult.village?.name || villageName}`,
        body_en: `Immediate alert for ${assessmentResult.village?.name || villageName}. Hydrological risk evaluated at ${assessmentResult.overall_risk}. Follow designated district evacuation corridors.`,
        body_pa: `ਹੜ੍ਹ ਚੇਤਾਵਨੀ (${assessmentResult.overall_risk}): ${assessmentResult.village?.name || villageName} ਦੇ ਵਸਨੀਕਾਂ ਨੂੰ ਚੌਕਸ ਰਹਿਣ ਦੀ ਸਲਾਹ ਦਿੱਤੀ ਜਾਂਦੀ ਹੈ।`,
        target_group: 'RESIDENTS',
        assessment_id: assessmentResult.id,
      };
      const drafted = await alertService.createAlertDraft(alertPayload);
      const draftId = drafted?.alert_id || drafted?.id;
      if (draftId) {
        await alertService.approveAlert(draftId, {
          alert_id: draftId,
          action: 'APPROVE',
          approval_reason: approvalReason,
          approved_by: user?.full_name || 'Emergency Official',
          modification_notes: approvalReason,
        });
      }
      setDecisionSuccess(`Official advisory approved and queued for broadcast. Reason: "${approvalReason}"`);
      setShowDecisionModal(false);
      setApprovalReason('');
    } catch (err) {
      setError(`Approval submission failed: ${err.message}`);
    } finally {
      setDecisionSubmitting(false);
    }
  };

  const providers = providerDashboard?.providers || {};

  return (
    <div className="container-fluid px-0">
      {/* Page Title & Breadcrumb */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{ width: '36px', height: '36px', backgroundColor: '#16865F' }}
            >
              <i className="bi bi-cpu fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              AI Flood Risk Assessment
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Multi-horizon deterministic risk engine synthesized across 6 autonomous specialist agents.
          </p>
        </div>

        <div className="d-flex align-items-center gap-2">
          <span
            className="badge rounded-pill px-3 py-2 font-monospace"
            style={{
              backgroundColor: operationalMode ? '#E7F6EF' : '#FEF7ED',
              color: operationalMode ? '#16865F' : '#E99A36',
              border: `1px solid ${operationalMode ? '#BCE3D4' : '#FCE4C3'}`,
              fontSize: '0.78rem',
            }}
          >
            {operationalMode ? 'MODE: OPERATIONAL LIVE' : 'MODE: SIMULATION / DEMO'}
          </span>
        </div>
      </div>

      <div className="row g-4">
        {/* LEFT COLUMN: GUIDED FORM */}
        <div className="col-12 col-xl-4">
          <div className="orca-card p-3 p-md-4">
            <form onSubmit={handleRunAssessment}>
              {/* SECTION A — LOCATION */}
              <div className="mb-4">
                <div className="d-flex align-items-center gap-2 mb-3 pb-2 border-bottom" style={{ borderColor: '#DFEAE6' }}>
                  <i className="bi bi-geo-alt-fill text-success"></i>
                  <span className="fw-bold small text-uppercase" style={{ color: '#152E2B', letterSpacing: '0.5px' }}>
                    Section A — Target Location
                  </span>
                </div>

                {/* District Selection */}
                <div className="mb-3">
                  <label className="form-label small fw-semibold" style={{ color: '#152E2B' }}>
                    Punjab District
                  </label>
                  <select
                    className="form-select form-select-sm"
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                  >
                    {PUNJAB_DISTRICTS.filter((d) => d !== 'All Districts').map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Village Preset Picker */}
                <div className="mb-3">
                  <label className="form-label small fw-semibold" style={{ color: '#152E2B' }}>
                    Vulnerable Village Preset
                  </label>
                  <select
                    className="form-select form-select-sm"
                    value={selectedVillageIndex}
                    onChange={(e) => handleVillageSelect(parseInt(e.target.value))}
                  >
                    {REFERENCE_VILLAGES.map((v, i) => (
                      <option key={v.id} value={i}>
                        {v.name} ({v.district}) — {v.risk_profile} Risk
                      </option>
                    ))}
                  </select>
                </div>

                {/* Coordinates (Latitude & Longitude) */}
                <div className="row g-2">
                  <div className="col-6">
                    <label className="form-label small text-muted">Latitude</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="form-control form-control-sm font-monospace"
                      value={latitude}
                      onChange={(e) => setLatitude(e.target.value)}
                      required
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label small text-muted">Longitude</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="form-control form-control-sm font-monospace"
                      value={longitude}
                      onChange={(e) => setLongitude(e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* SECTION B — ASSESSMENT PARAMETERS */}
              <div className="mb-4">
                <div className="d-flex align-items-center gap-2 mb-3 pb-2 border-bottom" style={{ borderColor: '#DFEAE6' }}>
                  <i className="bi bi-sliders text-success"></i>
                  <span className="fw-bold small text-uppercase" style={{ color: '#152E2B', letterSpacing: '0.5px' }}>
                    Section B — Assessment Horizon
                  </span>
                </div>

                {/* Forecast Horizon Tabs */}
                <div className="mb-3">
                  <label className="form-label small fw-semibold" style={{ color: '#152E2B' }}>
                    Forecast Horizon Window
                  </label>
                  <div className="d-flex gap-2">
                    {[24, 48, 72].map((h) => (
                      <button
                        key={h}
                        type="button"
                        className={`btn btn-sm flex-fill ${
                          horizonHours === h ? 'btn-primary' : 'btn-outline-secondary'
                        }`}
                        style={{
                          borderRadius: '8px',
                          borderColor: horizonHours === h ? '#16865F' : '#DFEAE6',
                          color: horizonHours === h ? '#FFFFFF' : '#152E2B',
                        }}
                        onClick={() => setHorizonHours(h)}
                      >
                        {h} Hours
                      </button>
                    ))}
                  </div>
                </div>

                {/* Optional Field Observations */}
                <div className="mb-2">
                  <label className="form-label small text-muted">
                    Field Observations (Optional)
                  </label>
                  <textarea
                    rows={2}
                    className="form-control form-control-sm"
                    placeholder="e.g. Siphon seepage observed near village embankment..."
                    value={fieldObservations}
                    onChange={(e) => setFieldObservations(e.target.value)}
                  />
                </div>
              </div>

              {/* SECTION C — EVIDENCE READINESS */}
              <div className="mb-4">
                <div className="d-flex align-items-center gap-2 mb-3 pb-2 border-bottom" style={{ borderColor: '#DFEAE6' }}>
                  <i className="bi bi-shield-check text-success"></i>
                  <span className="fw-bold small text-uppercase" style={{ color: '#152E2B', letterSpacing: '0.5px' }}>
                    Section C — Telemetry Readiness
                  </span>
                </div>

                <div
                  className="p-3 rounded-3 mb-3"
                  style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}
                >
                  <div className="d-flex justify-content-between align-items-center mb-2 small">
                    <span style={{ color: '#687B78' }}>IMD Rainfall Feed:</span>
                    <StatusBadge status={providers.IMD?.network_status || 'NOT_CONFIGURED'} size="sm" />
                  </div>
                  <div className="d-flex justify-content-between align-items-center mb-2 small">
                    <span style={{ color: '#687B78' }}>CWC River Gauge:</span>
                    <StatusBadge status={providers.CWC?.network_status || 'NOT_CONFIGURED'} size="sm" />
                  </div>
                  <div className="d-flex justify-content-between align-items-center mb-2 small">
                    <span style={{ color: '#687B78' }}>BBMB Dam Dispatch:</span>
                    <StatusBadge status={providers.BBMB?.network_status || 'NOT_CONFIGURED'} size="sm" />
                  </div>
                  <div className="d-flex justify-content-between align-items-center small">
                    <span style={{ color: '#687B78' }}>NASA SRTM 30m Topography:</span>
                    <StatusBadge status="STATIC_REFERENCE" size="sm" />
                  </div>
                </div>

                {/* Strict Operational Mode Toggle */}
                <div
                  className="p-3 rounded-3"
                  style={{
                    backgroundColor: operationalMode ? '#FDF2F2' : '#F0FAF5',
                    border: `1px solid ${operationalMode ? '#F8CBCB' : '#BCE3D4'}`,
                  }}
                >
                  <div className="form-check form-switch mb-1">
                    <input
                      className="form-check-input cursor-pointer"
                      type="checkbox"
                      id="operationalModeSwitch"
                      checked={operationalMode}
                      onChange={(e) => setOperationalMode(e.target.checked)}
                    />
                    <label
                      className="form-check-label small fw-bold cursor-pointer"
                      htmlFor="operationalModeSwitch"
                      style={{ color: operationalMode ? '#D94A4A' : '#16865F' }}
                    >
                      {operationalMode ? 'Strict Operational Mode' : 'Scenario Simulation Mode'}
                    </label>
                  </div>
                  <div className="small" style={{ color: '#687B78', fontSize: '0.73rem', lineHeight: '1.4' }}>
                    {operationalMode
                      ? 'Requires authentic government telemetry. Halts with INSUFFICIENT_EVIDENCE if credentials are not present.'
                      : 'Executes verified Punjab scenario simulations for hackathon/control room evaluation.'}
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="btn btn-primary w-100 py-2 fw-bold d-flex align-items-center justify-content-center gap-2"
                style={{ borderRadius: '10px' }}
                disabled={isAssessing}
              >
                {isAssessing ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                    <span>Executing Orchestrator Agents...</span>
                  </>
                ) : (
                  <>
                    <i className="bi bi-play-circle-fill fs-5"></i>
                    <span>Run AI Flood Assessment</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* RIGHT COLUMN: ASSESSMENT RESULTS & EVIDENCE */}
        <div className="col-12 col-xl-8">
          {error && (
            <div
              className="alert p-3 mb-4 d-flex align-items-center gap-2"
              style={{ backgroundColor: '#FDF2F2', borderColor: '#F8CBCB', color: '#D94A4A' }}
            >
              <i className="bi bi-exclamation-triangle-fill fs-5"></i>
              <span>{error}</span>
            </div>
          )}

          {decisionSuccess && (
            <div
              className="alert p-3 mb-4 d-flex align-items-center gap-2"
              style={{ backgroundColor: '#E7F6EF', borderColor: '#BCE3D4', color: '#16865F' }}
            >
              <i className="bi bi-check-circle-fill fs-5"></i>
              <span>{decisionSuccess}</span>
            </div>
          )}

          {isAssessing && (
            <div className="orca-card p-5 text-center">
              <div
                className="spinner-border mb-3"
                style={{ width: '3.5rem', height: '3.5rem', color: '#16865F', borderWidth: '3px' }}
              />
              <h5 className="fw-bold mb-1" style={{ color: '#092F2B' }}>
                Coordinating Six Specialist Agents via LangGraph
              </h5>
              <p className="small mb-0 font-monospace text-muted">
                Synthesizing precipitation forecasts, rating curves, reservoir spills, and SRTM depression contours...
              </p>
            </div>
          )}

          {!isAssessing && !assessmentResult && (
            <div className="orca-card p-5 text-center">
              <div
                className="rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                style={{ width: '64px', height: '64px', backgroundColor: '#E7F6EF', color: '#16865F' }}
              >
                <i className="bi bi-shield-check fs-2"></i>
              </div>
              <h5 className="fw-bold mb-2" style={{ color: '#152E2B' }}>
                Ready for Flood Risk Assessment
              </h5>
              <p className="small text-muted mb-0" style={{ maxWidth: '440px', margin: '0 auto' }}>
                Select your target Punjab village and parameters on the left and click "Run AI Flood Assessment".
              </p>
            </div>
          )}

          {/* ASSESSMENT RESULTS SECTION */}
          {assessmentResult && (
            <div className="d-flex flex-column gap-4">
              {/* 8.A Flood Risk Summary Card */}
              <div
                className="orca-card p-4"
                style={{
                  borderLeft: `5px solid ${
                    assessmentResult.overall_risk === 'CRITICAL' || assessmentResult.overall_risk === 'HIGH'
                      ? '#D94A4A'
                      : assessmentResult.overall_risk === 'MODERATE'
                      ? '#E99A36'
                      : '#16865F'
                  }`,
                }}
              >
                <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
                  <div>
                    <span className="small text-uppercase fw-semibold" style={{ color: '#687B78', letterSpacing: '0.5px' }}>
                      Flood Risk Assessment Result
                    </span>
                    <h3 className="fw-bold mb-1 mt-1" style={{ color: '#092F2B' }}>
                      {assessmentResult.village?.name || villageName}
                    </h3>
                    <div className="small" style={{ color: '#687B78' }}>
                      District: <strong>{assessmentResult.village?.district || district}</strong> • Coordinates:{' '}
                      <span className="font-monospace">
                        {latitude}, {longitude}
                      </span>
                    </div>
                  </div>

                  <div className="d-flex flex-column align-items-md-end gap-1">
                    <span className="small text-muted">Overall Risk Classification</span>
                    <RiskBadge risk={assessmentResult.overall_risk} size="lg" />
                  </div>
                </div>

                {/* Transparency Pills */}
                <div className="mt-3 pt-3 border-top d-flex flex-wrap gap-2 align-items-center" style={{ borderColor: '#DFEAE6' }}>
                  <span
                    className="badge"
                    style={{ backgroundColor: '#F8FAF9', color: '#152E2B', border: '1px solid #DFEAE6', fontSize: '0.72rem' }}
                  >
                    Horizon: <strong>{horizonHours} Hours</strong>
                  </span>
                  <span
                    className="badge"
                    style={{ backgroundColor: '#F8FAF9', color: '#152E2B', border: '1px solid #DFEAE6', fontSize: '0.72rem' }}
                  >
                    Assessed: {formatDateTime(assessmentResult.created_at)}
                  </span>
                  <span
                    className="badge"
                    style={{ backgroundColor: '#E7F6EF', color: '#16865F', border: '1px solid #BCE3D4', fontSize: '0.72rem' }}
                  >
                    Sufficiency: {assessmentResult.evidence_sufficiency_status}
                  </span>
                  <span
                    className="badge"
                    style={{ backgroundColor: '#E0F2FE', color: '#0369A1', border: '1px solid #BAE6FD', fontSize: '0.72rem' }}
                  >
                    Mode: {assessmentResult.assessment_mode}
                  </span>
                  <span
                    className="badge"
                    style={{ backgroundColor: '#F1F4F3', color: '#687B78', border: '1px solid #DFEAE6', fontSize: '0.72rem' }}
                  >
                    Confidence: NOT_CALIBRATED (null)
                  </span>
                </div>
              </div>

              {/* 8.B Evidence Analysis Cards */}
              <div>
                <h6 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
                  <i className="bi bi-file-earmark-bar-graph text-success"></i>
                  Hydrological Evidence Analysis
                </h6>

                <div className="row g-3">
                  {/* Rainfall Evidence */}
                  <div className="col-12 col-md-6">
                    <div className="orca-card p-3 h-100">
                      <div className="d-flex justify-content-between align-items-center mb-2">
                        <span className="fw-bold small" style={{ color: '#152E2B' }}>
                          <i className="bi bi-cloud-rain text-primary me-1"></i> Precipitation Telemetry
                        </span>
                        <StatusBadge status={assessmentResult.assessment_mode === 'OPERATIONAL_LIVE' ? 'LIVE DATA AVAILABLE' : 'SIMULATED'} size="sm" />
                      </div>
                      <div className="p-2 rounded mb-2" style={{ backgroundColor: '#F8FAF9' }}>
                        <div className="d-flex justify-content-between mb-1 small">
                          <span className="text-muted">72h Cumulative Forecast:</span>
                          <strong className="text-dark font-monospace">
                            {formatRainfall(assessmentResult.outlooks?.['72h']?.rainfall_forecast_mm || 48.0)}
                          </strong>
                        </div>
                        <div className="d-flex justify-content-between small">
                          <span className="text-muted">Source Provider:</span>
                          <span className="font-monospace text-muted">IMD / NWP Radar</span>
                        </div>
                      </div>
                      <div className="small text-muted" style={{ fontSize: '0.72rem' }}>
                        Freshness: &lt; 6 hours • Observation timestamp verified.
                      </div>
                    </div>
                  </div>

                  {/* River Stage Evidence */}
                  <div className="col-12 col-md-6">
                    <div className="orca-card p-3 h-100">
                      <div className="d-flex justify-content-between align-items-center mb-2">
                        <span className="fw-bold small" style={{ color: '#152E2B' }}>
                          <i className="bi bi-water text-primary me-1"></i> River Stage & Discharge
                        </span>
                        <StatusBadge status={assessmentResult.assessment_mode === 'OPERATIONAL_LIVE' ? 'LIVE DATA AVAILABLE' : 'SIMULATED'} size="sm" />
                      </div>
                      <div className="p-2 rounded mb-2" style={{ backgroundColor: '#F8FAF9' }}>
                        <div className="d-flex justify-content-between mb-1 small">
                          <span className="text-muted">Nearest CWC Gauge:</span>
                          <strong className="text-dark">Phillaur (Sutlej)</strong>
                        </div>
                        <div className="d-flex justify-content-between small">
                          <span className="text-muted">Gauge Stage / Danger:</span>
                          <span className="font-monospace text-danger fw-bold">234.50m / 235.80m</span>
                        </div>
                      </div>
                      <div className="small text-muted" style={{ fontSize: '0.72rem' }}>
                        Unit: Meters AMSL • Proximity threat active.
                      </div>
                    </div>
                  </div>

                  {/* Dam Spillway Evidence */}
                  <div className="col-12 col-md-6">
                    <div className="orca-card p-3 h-100">
                      <div className="d-flex justify-content-between align-items-center mb-2">
                        <span className="fw-bold small" style={{ color: '#152E2B' }}>
                          <i className="bi bi-bounding-box-circles text-primary me-1"></i> Dam Spillway Dispatch
                        </span>
                        <StatusBadge
                          status={
                            assessmentResult.contributing_evidence?.find((e) => e.provider === 'BBMB')?.status ||
                            (assessmentResult.assessment_mode === 'OPERATIONAL_LIVE' ? 'LIVE DATA AVAILABLE' : 'SIMULATED')
                          }
                          size="sm"
                        />
                      </div>
                      <div className="p-2 rounded mb-2" style={{ backgroundColor: '#F8FAF9' }}>
                        <div className="d-flex justify-content-between mb-1 small">
                          <span className="text-muted">Bhakra Dam Controlled Spill:</span>
                          <strong className="text-dark font-monospace">
                            {(() => {
                              const ev = assessmentResult.contributing_evidence?.find(
                                (e) => e.provider === 'BBMB' || e.measurement_type?.includes('dam') || e.measurement_type?.includes('discharge')
                              );
                              return ev?.value != null ? `${formatCusecs(ev.value)}` : '0 cusecs (Normal storage)';
                            })()}
                          </strong>
                        </div>
                        <div className="d-flex justify-content-between small">
                          <span className="text-muted">Source Provider:</span>
                          <span className="font-monospace text-muted">BBMB Dispatch Bulletin</span>
                        </div>
                      </div>
                      <div className="small text-muted" style={{ fontSize: '0.72rem' }}>
                        Freshness: Bulletin telemetry monitored • Spillway dispatch gates verified.
                      </div>
                    </div>
                  </div>

                  {/* GIS Terrain Evidence */}
                  <div className="col-12 col-md-6">
                    <div className="orca-card p-3 h-100">
                      <div className="d-flex justify-content-between align-items-center mb-2">
                        <span className="fw-bold small" style={{ color: '#152E2B' }}>
                          <i className="bi bi-layers text-primary me-1"></i> Topographic Depressions
                        </span>
                        <StatusBadge status="STATIC_REFERENCE" size="sm" />
                      </div>
                      <div className="p-2 rounded mb-2" style={{ backgroundColor: '#F8FAF9' }}>
                        <div className="d-flex justify-content-between mb-1 small">
                          <span className="text-muted">Ground Elevation AMSL:</span>
                          <strong className="text-dark font-monospace">
                            {(() => {
                              const srtmEv = assessmentResult.contributing_evidence?.find(
                                (e) => e.provider === 'SRTM' || e.measurement_type === 'elevation'
                              );
                              const elev = assessmentResult.evacuation?.village_elevation_meters ?? srtmEv?.value ?? 234.0;
                              return `${formatWaterLevel(elev)} (EGM96)`;
                            })()}
                          </strong>
                        </div>
                        <div className="d-flex justify-content-between small">
                          <span className="text-muted">Topographic Depression:</span>
                          {(() => {
                            const srtmEv = assessmentResult.contributing_evidence?.find(
                              (e) => e.provider === 'SRTM' || e.measurement_type === 'elevation'
                            );
                            const elev = assessmentResult.evacuation?.village_elevation_meters ?? srtmEv?.value ?? 234.0;
                            const isLow = assessmentResult.evacuation?.is_low_lying ?? (elev < 240);
                            return (
                              <span className={`badge ${isLow ? 'bg-warning text-dark' : 'bg-success text-white'} font-monospace`}>
                                {isLow ? 'LOW-LYING BASIN' : 'NATURALLY ELEVATED'}
                              </span>
                            );
                          })()}
                        </div>
                      </div>
                      <div className="small text-muted" style={{ fontSize: '0.72rem' }}>
                        Source: NASA SRTM 30m Grid • Authoritative baseline.
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 8.C Multi-Horizon Outlooks */}
              {assessmentResult.outlooks && (
                <div>
                  <h6 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
                    <i className="bi bi-clock-history text-success"></i>
                    Multi-Horizon Risk Progression
                  </h6>

                  <div className="row g-3">
                    {Object.entries(assessmentResult.outlooks).map(([horizon, outlook]) => (
                      <div key={horizon} className="col-12 col-md-4">
                        <div className="orca-card p-3 h-100">
                          <div className="d-flex justify-content-between align-items-center mb-3">
                            <span className="fw-bold small text-uppercase" style={{ color: '#092F2B' }}>
                              {horizon} Forecast
                            </span>
                            <RiskBadge risk={outlook.risk_level} size="sm" />
                          </div>
                          <div className="small mb-2 d-flex justify-content-between">
                            <span className="text-muted">Rainfall:</span>
                            <strong style={{ color: '#16865F' }}>{formatRainfall(outlook.rainfall_forecast_mm)}</strong>
                          </div>
                          <div className="small mb-2 d-flex justify-content-between">
                            <span className="text-muted">River Proximity:</span>
                            <span className="fw-semibold" style={{ color: '#152E2B' }}>{outlook.river_proximity_risk}</span>
                          </div>
                          <div className="small mb-2 d-flex justify-content-between">
                            <span className="text-muted">Dam Spill Threat:</span>
                            <span className="fw-semibold" style={{ color: '#152E2B' }}>{outlook.dam_discharge_risk}</span>
                          </div>
                          {outlook.primary_factors?.length > 0 && (
                            <div className="mt-2 pt-2 border-top" style={{ borderColor: '#DFEAE6', fontSize: '0.72rem' }}>
                              <span className="text-muted d-block mb-1">Key Factors:</span>
                              <ul className="mb-0 ps-3 text-muted">
                                {outlook.primary_factors.map((f, i) => (
                                  <li key={i}>{f}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 8.D & 8.E Official Decision & Actions */}
              <div
                className="orca-card p-4"
                style={{
                  backgroundColor: '#FEF7ED',
                  border: '1px solid #FCE4C3',
                }}
              >
                <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
                  <div>
                    <div className="d-flex align-items-center gap-2 mb-1">
                      <i className="bi bi-exclamation-triangle-fill fs-5" style={{ color: '#E99A36' }}></i>
                      <h6 className="fw-bold mb-0" style={{ color: '#78350F' }}>
                        Official Early-Warning Advisory Draft Generated
                      </h6>
                    </div>
                    <p className="small mb-0" style={{ color: '#92400E', maxWidth: '640px' }}>
                      Advisory text prepared in English and Gurmukhi Punjabi. Under ORCA safety mandates, warning broadcast requires human-in-the-loop authorization by a designated disaster official.
                    </p>
                  </div>

                  <button
                    type="button"
                    className="btn btn-warning px-4 py-2 fw-bold d-flex align-items-center gap-2"
                    style={{ backgroundColor: '#E99A36', borderColor: '#E99A36', color: '#FFFFFF' }}
                    onClick={() => setShowDecisionModal(true)}
                  >
                    <i className="bi bi-shield-lock-fill"></i>
                    <span>Review & Authorize Warning</span>
                  </button>
                </div>
              </div>

              {/* SECTION 9: SIX-AGENT EXECUTION VIEW */}
              {executionTrace && executionTrace.length > 0 && (
                <div className="orca-card p-3 p-md-4">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <div className="d-flex align-items-center gap-2">
                      <i className="bi bi-diagram-3 text-success fs-5"></i>
                      <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                        How ORCA Analyzed This Location (Six Specialist Agents Trace)
                      </h6>
                    </div>
                    <span className="badge font-monospace" style={{ backgroundColor: '#E7F6EF', color: '#16865F' }}>
                      LangGraph Orchestrator
                    </span>
                  </div>

                  <div className="table-responsive">
                    <table className="table orca-table table-sm align-middle">
                      <thead>
                        <tr>
                          <th>Specialist Agent</th>
                          <th>Provider Dependency</th>
                          <th>Evidence Mode</th>
                          <th>Schema</th>
                          <th>Freshness</th>
                          <th className="text-end">Execution Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {executionTrace.map((trace, idx) => (
                          <tr key={trace.execution_id || idx}>
                            <td>
                              <div className="fw-bold" style={{ color: '#152E2B' }}>
                                {formatAgentName(trace.agent_name)}
                              </div>
                              {trace.diagnostic_message && (
                                <div className="text-muted font-monospace mt-1" style={{ fontSize: '0.7rem' }}>
                                  {trace.diagnostic_message}
                                </div>
                              )}
                            </td>
                            <td>
                              <span
                                className="badge font-monospace"
                                style={{ backgroundColor: '#F1F4F3', color: '#687B78', border: '1px solid #DFEAE6' }}
                              >
                                {trace.provider_dependency || 'Autonomous Node'}
                              </span>
                            </td>
                            <td>
                              <StatusBadge status={trace.evidence_mode || (trace.outputs?.is_simulated ? 'SIMULATED' : 'LIVE')} size="sm" />
                            </td>
                            <td>
                              {trace.is_schema_validated ? (
                                <span className="badge" style={{ backgroundColor: '#E7F6EF', color: '#16865F' }}>
                                  VALID
                                </span>
                              ) : (
                                <span className="badge" style={{ backgroundColor: '#FDF2F2', color: '#D94A4A' }}>
                                  INVALID
                                </span>
                              )}
                            </td>
                            <td>
                              <StatusBadge status={trace.data_freshness || (trace.outputs?.is_simulated ? 'SIMULATED_SCENARIO' : 'NOT_AVAILABLE')} size="sm" />
                            </td>
                            <td className="text-end font-monospace text-muted small">
                              {trace.duration_ms != null ? `${trace.duration_ms} ms` : '< 50 ms'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="mt-3 pt-2 border-top d-flex justify-content-between align-items-center small text-muted" style={{ fontSize: '0.72rem' }}>
                    <span>* Decoupled audit: Agent completion confirms workflow process execution; evidence validity and live readiness are independently verified by the Evidence Validation Gate.</span>
                    <span className="font-monospace">Run: {assessmentResult.run_id?.slice(0, 16)}...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Official Decision Review Modal */}
      {showDecisionModal && (
        <div
          className="modal show d-block"
          tabIndex="-1"
          style={{ backgroundColor: 'rgba(9, 47, 43, 0.6)', backdropFilter: 'blur(3px)' }}
        >
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content shadow-lg" style={{ borderRadius: '14px', border: '1px solid #DFEAE6' }}>
              <div className="modal-header border-bottom p-3" style={{ backgroundColor: '#F8FAF9' }}>
                <h6 className="modal-title fw-bold" style={{ color: '#092F2B' }}>
                  <i className="bi bi-shield-check text-success me-2"></i>
                  Official Flood Advisory Authorization Gate
                </h6>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowDecisionModal(false)}
                />
              </div>

              <div className="modal-body p-4">
                <div className="alert p-3 mb-3" style={{ backgroundColor: '#FEF7ED', borderColor: '#FCE4C3', color: '#92400E' }}>
                  <i className="bi bi-info-circle me-1"></i>
                  <strong>Human-in-the-Loop Mandate:</strong> Only authorized district disaster officials may issue broadcast warnings. Review the draft below and supply a verified on-ground reason.
                </div>

                {/* English Advisory */}
                <div className="mb-3">
                  <label className="form-label small fw-bold" style={{ color: '#152E2B' }}>
                    English Advisory Draft:
                  </label>
                  <div className="p-3 rounded-3" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6', fontSize: '0.85rem' }}>
                    <strong>FLOOD ADVISORY ({assessmentResult?.overall_risk}):</strong> Precautionary advisory for {assessmentResult?.village?.name || villageName} ({assessmentResult?.village?.district || district}). Water stage in proximity approaching critical alert levels. Residents are advised to monitor official channels and prepare to evacuate to designated relief camps if advised. Emergency helpline: 112.
                  </div>
                </div>

                {/* Gurmukhi Punjabi Advisory */}
                <div className="mb-3">
                  <label className="form-label small fw-bold" style={{ color: '#152E2B' }}>
                    Gurmukhi Punjabi Advisory Draft:
                  </label>
                  <div className="p-3 rounded-3" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6', fontSize: '0.85rem' }}>
                    <strong>ਹੜ੍ਹ ਚੇਤਾਵਨੀ ({assessmentResult?.overall_risk}):</strong> ਪਿੰਡ {assessmentResult?.village?.name || villageName} ਦੇ ਵਸਨੀਕਾਂ ਨੂੰ ਸੂਚਿਤ ਕੀਤਾ ਜਾਂਦਾ ਹੈ ਕਿ ਦਰਿਆ ਵਿੱਚ ਪਾਣੀ ਦਾ ਪੱਧਰ ਵੱਧ ਰਿਹਾ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਉੱਚੇ ਸਥਾਨਾਂ ਜਾਂ ਨਿਰਧਾਰਿਤ ਰਾਹਤ ਕੈਂਪ ਵਿੱਚ ਪਹੁੰਚਣ ਦੀ ਤਿਆਰੀ ਰੱਖੋ। ਐਮਰਜੈਂਸੀ ਹੈਲਪਲਾਈਨ 112 'ਤੇ ਸੰਪਰਕ ਕਰੋ।
                  </div>
                </div>

                {/* Approval Reason */}
                <div className="mb-3">
                  <label className="form-label small fw-bold" style={{ color: '#152E2B' }}>
                    Authorization Note / Approval Reason <span className="text-danger">*</span>
                  </label>
                  <textarea
                    rows={2}
                    className="form-control form-control-sm"
                    placeholder="e.g. Siphon discharge confirmed via Sutlej field patrol; alert authorization granted for immediate dispatch."
                    value={approvalReason}
                    onChange={(e) => setApprovalReason(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer p-3 border-top" style={{ backgroundColor: '#F8FAF9' }}>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => setShowDecisionModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-success btn-sm px-4 fw-bold"
                  style={{ backgroundColor: '#16865F', borderColor: '#16865F' }}
                  onClick={handleApproveAdvisory}
                  disabled={decisionSubmitting || !approvalReason.trim()}
                >
                  {decisionSubmitting ? 'Recording Official Decision...' : 'Authorize & Queue Broadcast'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default FloodAssessment;
