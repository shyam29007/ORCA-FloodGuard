import React, { useState, useEffect } from 'react';
import { useMode } from '../context/ModeContext';
import damService from '../services/damService';
import DamCapacityChart from '../components/charts/DamCapacityChart';
import LoadingSpinner from '../components/common/LoadingSpinner';
import StatusBadge from '../components/common/StatusBadge';
import { formatWaterLevel, formatCusecs, formatDateTime } from '../utils/formatters';

export function DamInformation() {
  const { isDemoMode } = useMode();
  const [dams, setDams] = useState([]);
  const [selectedBasin, setSelectedBasin] = useState('ALL');
  const [loading, setLoading] = useState(true);

  const loadDams = async () => {
    setLoading(true);
    try {
      const basinFilter = selectedBasin === 'ALL' ? null : selectedBasin;
      const res = await damService.getDamInformation(basinFilter, isDemoMode);
      setDams(res || []);
    } catch (err) {
      console.warn('Dam telemetry fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDams();
  }, [selectedBasin, isDemoMode]);

  return (
    <div className="container-fluid px-0">
      {/* Page Title */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{ width: '36px', height: '36px', backgroundColor: '#16865F' }}
            >
              <i className="bi bi-bounding-box-circles fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              Dams & Reservoirs Telemetry
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Automated telemetry from Bhakra Beas Management Board (BBMB) and PSPCL for Sutlej, Beas, and Ravi reservoirs.
          </p>
        </div>

        {/* Basin filter & Refresh */}
        <div className="d-flex align-items-center gap-2">
          <select
            className="form-select form-select-sm"
            style={{ width: '160px' }}
            value={selectedBasin}
            onChange={(e) => setSelectedBasin(e.target.value)}
          >
            <option value="ALL">All Basins</option>
            <option value="Sutlej">Sutlej Basin</option>
            <option value="Beas">Beas Basin</option>
            <option value="Ravi">Ravi Basin</option>
          </select>
          <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={loadDams}
            disabled={loading}
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Querying BBMB SCADA reservoir dispatch network..." />
      ) : (
        <div className="d-flex flex-column gap-4">
          {/* Capacity Overview Chart */}
          <div className="orca-card p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                Reservoir Live Storage Fill Percentages (%)
              </span>
              <StatusBadge status={dams[0]?.status || "SIMULATED"} />
            </div>
            <DamCapacityChart dams={dams} height={240} />
          </div>

          {/* Dam Detail Cards Grid */}
          <div className="row g-4">
            {dams.map((dam) => {
              const fillPct = dam.fill_percentage != null ? dam.fill_percentage : 72;
              return (
                <div key={dam.dam_id} className="col-12 col-md-6 col-xl-4">
                  <div className="orca-card p-4 h-100 d-flex flex-column justify-content-between">
                    <div>
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <div>
                          <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                            {dam.name}
                          </h6>
                          <span className="small text-muted">{dam.river} Basin</span>
                        </div>
                        <StatusBadge status={dam.status || 'OPERATIONAL'} size="sm" />
                      </div>

                      {/* Fill Progress Bar */}
                      <div className="my-3">
                        <div className="d-flex justify-content-between small mb-1">
                          <span className="text-muted">Storage Capacity:</span>
                          <strong className="font-monospace" style={{ color: fillPct > 85 ? '#D94A4A' : '#16865F' }}>
                            {fillPct}%
                          </strong>
                        </div>
                        <div className="progress" style={{ height: '8px', backgroundColor: '#E8F0EC' }}>
                          <div
                            className="progress-bar"
                            role="progressbar"
                            style={{
                              width: `${Math.min(fillPct, 100)}%`,
                              backgroundColor: fillPct > 85 ? '#D94A4A' : fillPct > 70 ? '#E99A36' : '#16865F',
                            }}
                          />
                        </div>
                      </div>

                      {/* Stats Table */}
                      <div className="p-3 rounded-3 small mb-3" style={{ backgroundColor: '#F8FAF9' }}>
                        <div className="d-flex justify-content-between mb-2">
                          <span className="text-muted">Current Water Level:</span>
                          <strong className="font-monospace" style={{ color: '#152E2B' }}>
                            {formatWaterLevel(dam.current_water_level_m)}
                          </strong>
                        </div>
                        <div className="d-flex justify-content-between mb-2">
                          <span className="text-muted">Full Reservoir Level (FRL):</span>
                          <span className="font-monospace text-muted">
                            {formatWaterLevel(dam.full_reservoir_level_m)}
                          </span>
                        </div>
                        <div className="d-flex justify-content-between mb-2">
                          <span className="text-muted">Inflow Discharge:</span>
                          <span className="font-monospace text-dark">
                            {formatCusecs(dam.inflow_cusecs)}
                          </span>
                        </div>
                        <div className="d-flex justify-content-between">
                          <span className="text-muted">Spillway Outflow:</span>
                          <strong className="font-monospace" style={{ color: dam.spillway_outflow_cusecs > 0 ? '#D94A4A' : '#16865F' }}>
                            {formatCusecs(dam.spillway_outflow_cusecs)}
                          </strong>
                        </div>
                      </div>
                    </div>

                    <div className="pt-2 border-top d-flex justify-content-between align-items-center small text-muted" style={{ borderColor: '#DFEAE6', fontSize: '0.72rem' }}>
                      <span>Observed: {formatDateTime(dam.observed_at)}</span>
                      <div className="d-flex align-items-center gap-2">
                        {(dam.is_simulated || dam.status === 'SIMULATED') && (
                          <span className="badge font-monospace" style={{ backgroundColor: '#FEF3C7', color: '#92400E', fontSize: '0.65rem' }}>
                            SIMULATED
                          </span>
                        )}
                        <span className="font-monospace">ID: {dam.dam_id}</span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default DamInformation;
