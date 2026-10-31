import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import RiskBadge from '../common/RiskBadge';

export function AlertApprovalModal({ alert, onClose, onApprove, onReject }) {
  const { user, isOfficial } = useAuth();
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [authError, setAuthError] = useState(null);

  if (!alert) return null;

  const handleAction = async (action) => {
    setIsSubmitting(true);
    setAuthError(null);
    try {
      const payload = {
        alert_id: alert.id || alert.alert_id,
        approved_by: user?.full_name || 'Authorized Emergency Official',
        action,
        approval_reason: notes || `Reviewed and ${action.toLowerCase()}ed via Command Center`,
        modification_notes: notes || `Reviewed and ${action.toLowerCase()}ed via Command Center`,
      };
      if (action === 'APPROVE') {
        await onApprove(payload);
      } else {
        await onReject(payload);
      }
      onClose();
    } catch (err) {
      setAuthError(err.response?.data?.detail || err.message || 'Authorization rejected by server-side RBAC.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="modal fade show d-block"
      tabIndex="-1"
      style={{ backgroundColor: 'rgba(9, 47, 43, 0.6)', backdropFilter: 'blur(4px)' }}
    >
      <div className="modal-dialog modal-lg modal-dialog-centered">
        <div className="modal-content shadow-lg" style={{ borderRadius: '14px', border: '1px solid #DFEAE6', backgroundColor: '#FFFFFF' }}>
          {/* Header */}
          <div className="modal-header border-bottom py-3" style={{ backgroundColor: '#F8FAF9' }}>
            <div className="d-flex align-items-center gap-2">
              <div
                className="rounded-circle d-flex align-items-center justify-content-center text-white"
                style={{ width: '32px', height: '32px', backgroundColor: '#E99A36' }}
              >
                <i className="bi bi-shield-check"></i>
              </div>
              <h6 className="modal-title fw-bold mb-0" style={{ color: '#092F2B' }}>
                Human Approval Gate: Flood Warning Draft
              </h6>
            </div>
            <button type="button" className="btn-close" onClick={onClose} disabled={isSubmitting} />
          </div>

          {/* Body */}
          <div className="modal-body p-4">
            {authError && (
              <div
                className="alert py-2 px-3 small mb-3 d-flex align-items-center gap-2"
                style={{ backgroundColor: '#FDF2F2', border: '1px solid #F8CBCB', color: '#D94A4A' }}
              >
                <i className="bi bi-shield-slash fs-5"></i>
                <div>
                  <strong>Server-Side RBAC Authorization Denied:</strong> {authError}
                </div>
              </div>
            )}

            {!isOfficial && (
              <div
                className="alert py-2 px-3 small mb-3 d-flex align-items-center gap-2"
                style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3', color: '#92400E' }}
              >
                <i className="bi bi-shield-lock-fill fs-5" style={{ color: '#E99A36' }}></i>
                <div>
                  <strong>DEMO / Observer Session:</strong> Live broadcast authorization requires verified <code>OFFICIAL</code> or <code>ADMIN</code> clearance. Current role is <code>{user?.role || 'UNAUTHENTICATED'}</code>.
                </div>
              </div>
            )}

            <div className="d-flex justify-content-between align-items-center mb-3">
              <div>
                <span className="small text-muted">Target Village Location:</span>
                <h5 className="mb-0 fw-bold" style={{ color: '#092F2B' }}>{alert.village_name}</h5>
              </div>
              <div className="text-end">
                <span className="small text-muted d-block">Evaluated Risk:</span>
                <RiskBadge risk={alert.risk_level} size="lg" />
              </div>
            </div>

            {/* Headline */}
            <div className="p-3 mb-3 rounded-3" style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3' }}>
              <span className="small text-uppercase fw-semibold" style={{ color: '#92400E' }}>Headline</span>
              <div className="fw-bold mt-1" style={{ color: '#78350F' }}>{alert.headline}</div>
            </div>

            {/* Bilingual Text */}
            <div className="row g-3 mb-3">
              <div className="col-md-6">
                <div className="p-3 rounded-3 h-100" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                  <div className="small text-uppercase fw-semibold mb-2" style={{ color: '#16865F' }}>English Advisory</div>
                  <p className="small mb-0" style={{ lineHeight: '1.6', color: '#152E2B' }}>
                    {alert.body_en || alert.english_text}
                  </p>
                </div>
              </div>
              <div className="col-md-6">
                <div className="p-3 rounded-3 h-100" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                  <div className="small text-uppercase fw-semibold mb-2" style={{ color: '#16865F' }}>Gurmukhi (ਪੰਜਾਬੀ) Advisory</div>
                  <p className="small mb-0" style={{ lineHeight: '1.7', color: '#10483F' }}>
                    {alert.body_pa || alert.punjabi_text}
                  </p>
                </div>
              </div>
            </div>

            {/* Officer review notes input */}
            <div className="mb-2">
              <label className="form-label small fw-semibold" style={{ color: '#152E2B' }}>
                Official Review Notes & Verification Remarks: <span className="text-danger">*</span>
              </label>
              <textarea
                className="form-control form-control-sm"
                rows="2"
                placeholder="Enter verification notes (e.g. Siphon discharge confirmed via Sutlej field patrol)..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Footer actions */}
          <div className="modal-footer border-top d-flex justify-content-between p-3" style={{ backgroundColor: '#F8FAF9' }}>
            <span className="small text-muted">
              Reviewing Officer: <strong>{user?.full_name || 'Emergency Official'}</strong> ({user?.role || 'OFFICIAL'})
            </span>
            <div className="d-flex gap-2">
              <button
                type="button"
                className="btn btn-outline-danger btn-sm px-3"
                onClick={() => handleAction('REJECT')}
                disabled={isSubmitting}
              >
                Reject Warning
              </button>
              <button
                type="button"
                className="btn btn-success btn-sm px-4 fw-bold"
                style={{ backgroundColor: '#16865F', borderColor: '#16865F' }}
                onClick={() => handleAction('APPROVE')}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Authorizing...' : 'Authorize & Broadcast Alert'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AlertApprovalModal;
