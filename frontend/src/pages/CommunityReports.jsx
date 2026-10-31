import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import reportService from '../services/reportService';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { formatDateTime } from '../utils/formatters';
import { REFERENCE_VILLAGES } from '../utils/punjabData';

export function CommunityReports() {
  const { user, isOfficial } = useAuth();
  const [reports, setReports] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  // Form state
  const [villageName, setVillageName] = useState('Phillaur');
  const [latitude, setLatitude] = useState(31.0267);
  const [longitude, setLongitude] = useState(75.7871);
  const [waterInches, setWaterInches] = useState(14);
  const [observations, setObservations] = useState('');
  const [reporterName, setReporterName] = useState(user?.full_name || 'Anonymous Citizen');
  const [mediaUrl, setMediaUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const loadReports = async () => {
    setLoading(true);
    try {
      const res = await reportService.getReports(statusFilter !== 'ALL' ? statusFilter : null);
      setReports(res || []);
    } catch (err) {
      console.warn('Reports load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [statusFilter]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitSuccess(false);

    try {
      const payload = {
        village_name: villageName,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        water_level_inches: parseFloat(waterInches),
        observations: observations || 'Observed rising canal seepage and minor overflow on residential road.',
        reporter_name: reporterName,
        media_url: mediaUrl || 'https://images.unsplash.com/photo-1547683905-f686c993aae5?auto=format&fit=crop&w=400&q=80',
      };

      await reportService.uploadReport(payload);
      setSubmitSuccess(true);
      setObservations('');
      await loadReports();
    } catch (err) {
      alert(`Submission error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReviewAction = async (reportId, action) => {
    try {
      await reportService.reviewReport(reportId, {
        status: action,
        reviewer_name: user?.full_name || 'Emergency Official',
        review_notes: `Ground incident ${action.toLowerCase()}ed via Command Center`,
        confidence_weight: action === 'VERIFIED' ? 0.95 : 0.2,
      });
      await loadReports();
    } catch (err) {
      alert(`Review action failed: ${err.message}`);
    }
  };

  return (
    <div className="container-fluid px-0">
      {/* Title */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{ width: '36px', height: '36px', backgroundColor: '#16865F' }}
            >
              <i className="bi bi-chat-left-text fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              Citizen & Field Ground Reports
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Crowdsourced on-ground flood observations, inundation depths, and visual evidence review queue.
          </p>
        </div>

        {/* Filter & Refresh */}
        <div className="d-flex align-items-center gap-2">
          <select
            className="form-select form-select-sm"
            style={{ width: '160px' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING">Pending Review</option>
            <option value="VERIFIED">Verified</option>
            <option value="REJECTED">Rejected</option>
          </select>
          <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={loadReports}
            disabled={loading}
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
          </button>
        </div>
      </div>

      <div className="row g-4">
        {/* Reports Feed Column */}
        <div className="col-12 col-xl-8">
          <div className="orca-card p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                Field Submissions Queue ({reports.length})
              </span>
              <span className="badge font-monospace" style={{ backgroundColor: '#E7F6EF', color: '#16865F' }}>
                Crowdsourced Observations
              </span>
            </div>

            {loading ? (
              <LoadingSpinner message="Querying citizen report queue..." />
            ) : reports.length === 0 ? (
              <div className="p-5 text-center text-muted">
                <i className="bi bi-inbox fs-1 mb-2 d-block"></i>
                <h6 className="fw-bold" style={{ color: '#152E2B' }}>No Reports Found</h6>
                <p className="small mb-0">No citizen ground observations under this filter criteria.</p>
              </div>
            ) : (
              <div className="d-flex flex-column gap-3">
                {reports.map((rep) => (
                  <div
                    key={rep.id || rep.report_id}
                    className="p-3 rounded-3"
                    style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}
                  >
                    <div className="d-flex flex-column flex-sm-row justify-content-between align-items-sm-start gap-2 mb-2">
                      <div>
                        <div className="d-flex align-items-center gap-2">
                          <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                            {rep.village_name}
                          </h6>
                          <StatusBadge status={rep.status} size="sm" />
                        </div>
                        <span className="small text-muted" style={{ fontSize: '0.75rem' }}>
                          Reported by: <strong>{rep.reporter_name || 'Citizen'}</strong> • {formatDateTime(rep.created_at)}
                        </span>
                      </div>

                      {/* Official Verification Controls */}
                      {isOfficial && rep.status === 'PENDING' && (
                        <div className="d-flex gap-2">
                          <button
                            type="button"
                            className="btn btn-outline-danger btn-sm py-1 px-2"
                            style={{ fontSize: '0.75rem' }}
                            onClick={() => handleReviewAction(rep.id || rep.report_id, 'REJECTED')}
                          >
                            Reject
                          </button>
                          <button
                            type="button"
                            className="btn btn-success btn-sm py-1 px-2 fw-semibold"
                            style={{ backgroundColor: '#16865F', borderColor: '#16865F', fontSize: '0.75rem' }}
                            onClick={() => handleReviewAction(rep.id || rep.report_id, 'VERIFIED')}
                          >
                            Verify & Ingest
                          </button>
                        </div>
                      )}
                    </div>

                    <div className="p-2 rounded mb-2 small" style={{ backgroundColor: '#FFFFFF', border: '1px solid #DFEAE6' }}>
                      <div className="mb-1">
                        <span className="text-muted">Reported Water Depth: </span>
                        <strong className="font-monospace text-danger">{rep.water_level_inches} inches</strong>
                      </div>
                      <p className="mb-0 text-dark" style={{ lineHeight: '1.4' }}>
                        {rep.observations}
                      </p>
                    </div>

                    {rep.review_notes && (
                      <div className="small text-muted" style={{ fontSize: '0.72rem' }}>
                        Reviewer Note: <em>"{rep.review_notes}"</em>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* New Report Form Column */}
        <div className="col-12 col-xl-4">
          <div className="orca-card p-4">
            <h6 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
              <i className="bi bi-send-fill text-success"></i>
              Submit Ground Inundation Report
            </h6>

            {submitSuccess && (
              <div
                className="alert p-3 mb-3 small d-flex align-items-center gap-2"
                style={{ backgroundColor: '#E7F6EF', borderColor: '#BCE3D4', color: '#16865F' }}
              >
                <i className="bi bi-check-circle-fill"></i>
                <span>Report submitted successfully and entered verification queue.</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label small fw-semibold">Village</label>
                <select
                  className="form-select form-select-sm"
                  value={villageName}
                  onChange={(e) => {
                    setVillageName(e.target.value);
                    const v = REFERENCE_VILLAGES.find((vil) => vil.name === e.target.value);
                    if (v) {
                      setLatitude(v.coordinates[0]);
                      setLongitude(v.coordinates[1]);
                    }
                  }}
                >
                  {REFERENCE_VILLAGES.map((v) => (
                    <option key={v.id} value={v.name}>
                      {v.name} ({v.district})
                    </option>
                  ))}
                </select>
              </div>

              <div className="row g-2 mb-3">
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

              <div className="mb-3">
                <label className="form-label small fw-semibold">Estimated Water Inundation (Inches)</label>
                <input
                  type="number"
                  step="1"
                  className="form-control form-control-sm font-monospace"
                  value={waterInches}
                  onChange={(e) => setWaterInches(e.target.value)}
                  required
                />
              </div>

              <div className="mb-3">
                <label className="form-label small fw-semibold">Field Observations</label>
                <textarea
                  rows={3}
                  className="form-control form-control-sm"
                  placeholder="Describe road blockage, breach status, residential inundation..."
                  value={observations}
                  onChange={(e) => setObservations(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary w-100 py-2 fw-semibold"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Uploading Report...' : 'Submit Ground Report'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CommunityReports;
