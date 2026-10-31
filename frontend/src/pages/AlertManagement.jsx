import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import alertService from '../services/alertService';
import floodService from '../services/floodService';
import AlertApprovalModal from '../components/alerts/AlertApprovalModal';
import RiskBadge from '../components/common/RiskBadge';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { formatDateTime } from '../utils/formatters';
import { REFERENCE_VILLAGES } from '../utils/punjabData';

export function AlertManagement() {
  const { user, isOfficial, isAdmin } = useAuth();
  const [pendingAlerts, setPendingAlerts] = useState([]);
  const [selectedAlertForModal, setSelectedAlertForModal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDrafting, setIsDrafting] = useState(false);
  const [draftVillage, setDraftVillage] = useState('Phillaur');
  const [draftRisk, setDraftRisk] = useState('HIGH');
  const [draftRain, setDraftRain] = useState(78.5);
  const [approvalResult, setApprovalResult] = useState(null);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const res = await alertService.getPendingAlerts();
      setPendingAlerts(res || []);
    } catch (err) {
      console.warn('Error loading alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleCreateDraft = async (e) => {
    e.preventDefault();
    setIsDrafting(true);
    try {
      // Find village coordinates to run linked scenario assessment
      const vObj = REFERENCE_VILLAGES.find((v) => v.name === draftVillage) || REFERENCE_VILLAGES[0];
      const assessRes = await floodService.assessFloodRisk({
        village_name: draftVillage,
        coordinates: { latitude: vObj.coordinates[0], longitude: vObj.coordinates[1] },
        district: vObj.district,
        forecast_horizon_hours: 24,
        include_simulated_fallback: true,
        operational_mode: false,
      });
      const assessmentId = assessRes?.id || assessRes?.assessment_id;
      if (!assessmentId) {
        throw new Error('Could not establish verified assessment reference for draft linkage.');
      }
      await alertService.draftAlert(draftVillage, draftRisk, parseFloat(draftRain), assessmentId);
      await loadAlerts();
    } catch (err) {
      alert(`Draft creation error: ${err.message}`);
    } finally {
      setIsDrafting(false);
    }
  };

  const handleApprove = async (alertId, payload) => {
    const res = await alertService.approveAlert(alertId, payload);
    setApprovalResult({
      alertId,
      approvedBy: res?.approved_by || user?.full_name || 'Emergency Official',
      status: res?.status || 'APPROVED',
      dispatchResults: res?.dispatch_results || [],
    });
    await loadAlerts();
  };

  const handleReject = async (alertId, payload) => {
    const res = await alertService.approveAlert(alertId, { ...payload, action: 'REJECT' });
    setApprovalResult({
      alertId,
      approvedBy: res?.approved_by || user?.full_name || 'Emergency Official',
      status: 'REJECTED',
      dispatchResults: [],
    });
    await loadAlerts();
  };

  return (
    <div className="container-fluid px-0">
      {/* Title */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{ width: '36px', height: '36px', backgroundColor: '#E99A36' }}
            >
              <i className="bi bi-broadcast-pin fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              Official Warning Authorization Gate
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            MANDATORY SAFETY PROTOCOL: AI agents formulate bilingual warning drafts; only authorized emergency officials may authorize citizen broadcast.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary btn-sm d-flex align-items-center gap-2 px-3 py-2"
          onClick={loadAlerts}
          disabled={loading}
          style={{ borderRadius: '8px' }}
        >
          <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Approval Confirmation Banner */}
      {approvalResult && (
        <div
          className="alert p-3 mb-4 rounded-3 d-flex align-items-center justify-content-between"
          style={{
            backgroundColor: approvalResult.status === 'APPROVED' ? '#E8F5E9' : '#FFEBEE',
            border: `1px solid ${approvalResult.status === 'APPROVED' ? '#C8E6C9' : '#FFCDD2'}`,
            color: approvalResult.status === 'APPROVED' ? '#1B5E20' : '#B71C1C',
          }}
          role="alert"
        >
          <div>
            <div className="fw-bold d-flex align-items-center gap-2">
              <i className={`bi ${approvalResult.status === 'APPROVED' ? 'bi-shield-check' : 'bi-x-circle-fill'} fs-5`}></i>
              <span>
                {approvalResult.status === 'APPROVED'
                  ? 'Official Advisory Broadcast Authorization Confirmed'
                  : 'Official Advisory Rejected'}
              </span>
            </div>
            <div className="small mt-1">
              Authorized Officer: <strong>{approvalResult.approvedBy}</strong> • Alert ID: <span className="font-monospace">{approvalResult.alertId}</span>
            </div>
            {approvalResult.status === 'APPROVED' && (
              <div className="small text-muted mt-1" style={{ fontSize: '0.8rem' }}>
                Dispatch Safety Protocol: Status is <strong>MOCKED</strong>. External network transmissions bypassed in sandbox mode (0 live cellular recipients).
              </div>
            )}
          </div>
          <button
            type="button"
            className="btn-close"
            onClick={() => setApprovalResult(null)}
            aria-label="Close"
          ></button>
        </div>
      )}

      {/* Role Notice */}
      {!isOfficial && (
        <div
          className="p-3 mb-4 rounded-3 d-flex align-items-center gap-3"
          style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3', color: '#92400E' }}
        >
          <i className="bi bi-shield-lock-fill fs-4 flex-shrink-0" style={{ color: '#E99A36' }}></i>
          <div className="small">
            <strong>{user?.role === 'DEMO' ? 'DEMO SESSION: Broadcast Locked —' : 'Read-Only Observer Mode:'}</strong>{' '}
            {user?.role === 'DEMO'
              ? 'You are currently logged into an evaluation sandbox session. Official advisory broadcast authorization is locked to verified Emergency Officials (SDMA/DDMA) and Administrators. Evaluators may review drafts, but approval submissions will be rejected by server-side RBAC (HTTP 403 Forbidden).'
              : 'You are currently signed in as a Citizen/Guest. To approve or reject official flood warnings, authenticate as an authorized Emergency Official or Administrator account via the top-right profile switcher.'}
          </div>
        </div>
      )}

      {loading ? (
        <LoadingSpinner message="Querying pending advisory queue..." />
      ) : (
        <div className="row g-4">
          {/* Pending Alerts Queue Column */}
          <div className="col-12 col-xl-8">
            <div className="orca-card p-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                  Pending Early-Warning Advisories ({pendingAlerts.length})
                </span>
                <span className="badge font-monospace" style={{ backgroundColor: '#FEF7ED', color: '#E99A36' }}>
                  AWAITING OFFICIAL SIGN-OFF
                </span>
              </div>

              {pendingAlerts.length === 0 ? (
                <div className="p-5 text-center text-muted">
                  <i className="bi bi-check-circle-fill text-success fs-1 mb-2 d-block"></i>
                  <h6 className="fw-bold" style={{ color: '#152E2B' }}>No Pending Alerts in Queue</h6>
                  <p className="small mb-0">All AI-generated advisories have been reviewed and authorized.</p>
                </div>
              ) : (
                <div className="d-flex flex-column gap-3">
                  {pendingAlerts.map((alert) => {
                    const alertId = alert.alert_id || alert.id;
                    return (
                      <div
                        key={alertId}
                        className="p-3 rounded-3"
                        style={{
                          backgroundColor: '#FFFFFF',
                          border: '1px solid #DFEAE6',
                          borderLeft: `4px solid ${
                            alert.risk_level === 'CRITICAL' || alert.risk_level === 'HIGH' ? '#D94A4A' : '#E99A36'
                          }`,
                        }}
                      >
                        <div className="d-flex flex-column flex-sm-row justify-content-between align-items-sm-start gap-2 mb-2">
                          <div>
                            <div className="d-flex align-items-center gap-2">
                              <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                                {alert.headline || `Flood Advisory: ${alert.village_name}`}
                              </h6>
                              <RiskBadge risk={alert.risk_level} size="sm" />
                            </div>
                            <span className="small text-muted mt-1 d-block">
                              Target: {alert.village_name} ({alert.district || 'Punjab'}) • Created: {formatDateTime(alert.created_at)}
                            </span>
                          </div>

                          <button
                            type="button"
                            className="btn btn-primary btn-sm flex-shrink-0"
                            onClick={() => setSelectedAlertForModal(alert)}
                          >
                            Review & Authorize &rarr;
                          </button>
                        </div>

                        {/* Bilingual Body Preview */}
                        <div className="p-3 rounded-3 my-2 small" style={{ backgroundColor: '#F8FAF9' }}>
                          <div className="mb-2">
                            <strong className="d-block text-dark mb-1">English:</strong>
                            <span style={{ color: '#152E2B' }}>{alert.english_text || alert.body_en}</span>
                          </div>
                          {(alert.punjabi_text || alert.body_pa) && (
                            <div className="pt-2 border-top" style={{ borderColor: '#DFEAE6' }}>
                              <strong className="d-block text-dark mb-1">Gurmukhi (ਪੰਜਾਬੀ):</strong>
                              <span style={{ color: '#10483F' }}>{alert.punjabi_text || alert.body_pa}</span>
                            </div>
                          )}
                        </div>

                        <div className="d-flex justify-content-between align-items-center small text-muted" style={{ fontSize: '0.72rem' }}>
                          <span>Target Channels: <strong>{(alert.target_channels || []).join(', ') || alert.target_group || 'SMS, VOICE_CALL'}</strong></span>
                          <span className="font-monospace">Draft ID: {alertId?.slice(0, 16)}...</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Test / Manual Advisory Drafter Column */}
          <div className="col-12 col-xl-4">
            <div className="orca-card p-4">
              <h6 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
                <i className="bi bi-pencil-square text-success"></i>
                Simulate Scenario Advisory Draft
              </h6>
              <p className="small text-muted mb-3">
                Trigger Alert Agent to synthesize a new bilingual advisory draft for testing the human approval gate.
              </p>

              <form onSubmit={handleCreateDraft}>
                <div className="mb-3">
                  <label className="form-label small fw-semibold">Village Location</label>
                  <select
                    className="form-select form-select-sm"
                    value={draftVillage}
                    onChange={(e) => setDraftVillage(e.target.value)}
                  >
                    {REFERENCE_VILLAGES.map((v) => (
                      <option key={v.id} value={v.name}>
                        {v.name} ({v.district})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label small fw-semibold">Scenario Risk Level</label>
                  <select
                    className="form-select form-select-sm"
                    value={draftRisk}
                    onChange={(e) => setDraftRisk(e.target.value)}
                  >
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="HIGH">HIGH</option>
                    <option value="MODERATE">MODERATE</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label small fw-semibold">Precipitation (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    className="form-control form-control-sm font-monospace"
                    value={draftRain}
                    onChange={(e) => setDraftRain(e.target.value)}
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-outline-primary w-100 py-2 fw-semibold"
                  disabled={isDrafting}
                >
                  {isDrafting ? 'Synthesizing Advisory...' : 'Queue Test Advisory Draft'}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Review & Approval Modal */}
      {selectedAlertForModal && (
        <AlertApprovalModal
          alert={selectedAlertForModal}
          onClose={() => setSelectedAlertForModal(null)}
          onApprove={(payload) =>
            handleApprove(selectedAlertForModal.alert_id || selectedAlertForModal.id, payload)
          }
          onReject={(payload) =>
            handleReject(selectedAlertForModal.alert_id || selectedAlertForModal.id, payload)
          }
        />
      )}
    </div>
  );
}

export default AlertManagement;
