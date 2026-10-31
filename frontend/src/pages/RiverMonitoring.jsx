import React, { useState, useEffect } from 'react';
import riverService from '../services/riverService';
import RiverGaugeChart from '../components/charts/RiverGaugeChart';
import LoadingSpinner from '../components/common/LoadingSpinner';
import StatusBadge from '../components/common/StatusBadge';
import { formatWaterLevel, formatCusecs } from '../utils/formatters';
import { CWC_GAUGE_STATIONS } from '../utils/punjabData';

export function RiverMonitoring() {
  const [stations, setStations] = useState(CWC_GAUGE_STATIONS);
  const [readings, setReadings] = useState({});
  const [selectedStation, setSelectedStation] = useState(CWC_GAUGE_STATIONS[0]);
  const [loading, setLoading] = useState(true);

  const loadRiverData = async () => {
    setLoading(true);
    try {
      const fetchedStations = await riverService.getStations();
      const stList = fetchedStations?.length ? fetchedStations : CWC_GAUGE_STATIONS;
      setStations(stList);

      const readingsMap = {};
      await Promise.all(
        stList.map(async (st) => {
          try {
            const rd = await riverService.getReading(st.station_id);
            readingsMap[st.station_id] = rd;
          } catch {
            readingsMap[st.station_id] = {
              water_level_meters: st.warning_level_meters - 0.5,
              discharge_cusecs: 45000,
              trend: 'RISING',
              status: 'SIMULATED',
              is_above_warning: false,
              is_above_danger: false,
              buffer_to_danger_meters: 1.2,
            };
          }
        })
      );
      setReadings(readingsMap);
    } catch (err) {
      console.warn('River data error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRiverData();
  }, []);

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
              <i className="bi bi-water fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              River Gauges & Stage Monitoring
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Real-time stage heights and rating-curve discharge monitoring for the Sutlej, Beas, and Ravi rivers.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-outline-primary btn-sm d-flex align-items-center gap-2 px-3 py-2"
          onClick={loadRiverData}
          disabled={loading}
          style={{ borderRadius: '8px' }}
        >
          <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
          <span>Refresh Feeds</span>
        </button>
      </div>

      {loading ? (
        <LoadingSpinner message="Querying CWC acoustic river stage transducers..." />
      ) : (
        <div className="d-flex flex-column gap-4">
          {/* River Gauge Comparison Chart */}
          <div className="orca-card p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                Punjab River Gauge Stage Levels vs Warning and Danger Limits
              </span>
              <StatusBadge status={readings[stations[0]?.station_id]?.status || "SIMULATED"} />
            </div>
            <RiverGaugeChart stations={stations} readings={readings} height={300} />
          </div>

          {/* Individual Gauge Cards Grid */}
          <div>
            <h6 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
              <i className="bi bi-geo-alt-fill text-success"></i> Monitored Hydrological Stations
            </h6>

            <div className="row g-3">
              {stations.map((st) => {
                const reading = readings[st.station_id] || {};
                const isAboveWarning = reading.is_above_warning;
                const isAboveDanger = reading.is_above_danger;

                return (
                  <div key={st.station_id} className="col-12 col-md-6 col-xl-3">
                    <div
                      className="orca-card p-3 h-100 d-flex flex-column justify-content-between"
                      style={{
                        borderLeft: isAboveDanger
                          ? '4px solid #D94A4A'
                          : isAboveWarning
                          ? '4px solid #E99A36'
                          : '4px solid #16865F',
                      }}
                    >
                      <div>
                        <div className="d-flex justify-content-between align-items-start mb-2">
                          <div>
                            <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                              {st.name}
                            </h6>
                            <span className="small text-muted">{st.river} • {st.district}</span>
                          </div>
                          <StatusBadge status={isAboveDanger ? 'DANGER' : isAboveWarning ? 'WARNING' : 'NORMAL'} size="sm" />
                        </div>

                        {/* Stage Number */}
                        <div className="my-3">
                          <span className="text-muted d-block small" style={{ fontSize: '0.72rem' }}>Current Gauge Height:</span>
                          <h3 className="fw-bold mb-0 font-monospace" style={{ color: isAboveDanger ? '#D94A4A' : '#16865F' }}>
                            {formatWaterLevel(reading.water_level_meters || st.warning_level_meters - 0.4)}
                          </h3>
                        </div>

                        {/* Thresholds */}
                        <div className="p-2 rounded-3 small mb-2" style={{ backgroundColor: '#F8FAF9' }}>
                          <div className="d-flex justify-content-between mb-1">
                            <span className="text-muted">Warning Level:</span>
                            <span className="fw-bold" style={{ color: '#E99A36' }}>
                              {formatWaterLevel(st.warning_level_meters)}
                            </span>
                          </div>
                          <div className="d-flex justify-content-between">
                            <span className="text-muted">Danger Level:</span>
                            <span className="fw-bold" style={{ color: '#D94A4A' }}>
                              {formatWaterLevel(st.danger_level_meters)}
                            </span>
                          </div>
                        </div>

                        {/* Discharge */}
                        <div className="d-flex justify-content-between small text-muted">
                          <span>Calculated Discharge:</span>
                          <strong className="font-monospace" style={{ color: '#152E2B' }}>
                            {formatCusecs(reading.discharge_cusecs || 38000)}
                          </strong>
                        </div>
                      </div>

                      <div className="mt-3 pt-2 border-top d-flex justify-content-between align-items-center small text-muted" style={{ borderColor: '#DFEAE6', fontSize: '0.72rem' }}>
                        <span>Trend: {reading.trend || 'STABLE'}</span>
                        <div className="d-flex align-items-center gap-2">
                          {(reading.is_simulated || reading.status === 'SIMULATED') && (
                            <span className="badge font-monospace" style={{ backgroundColor: '#FEF3C7', color: '#92400E', fontSize: '0.65rem' }}>
                              SIMULATED
                            </span>
                          )}
                          <span className="font-monospace">ID: {st.station_id}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RiverMonitoring;
