import React, { useState } from 'react';
import replayService from '../services/replayService';
import RiskBadge from '../components/common/RiskBadge';
import { formatDateTime } from '../utils/formatters';

export function HistoricalReplay() {
  const [eventName, setEventName] = useState('2023_punjab_monsoon_floods');
  const [replayState, setReplayState] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStepping, setIsStepping] = useState(false);

  const handleStartReplay = async () => {
    setIsStarting(true);
    try {
      const res = await replayService.startReplay(
        eventName,
        ['Gidderpindi', 'Shahkot', 'Phillaur', 'Harike'],
        6
      );
      setReplayState(res);
    } catch (err) {
      alert(`Failed to start replay: ${err.message}`);
    } finally {
      setIsStarting(false);
    }
  };

  const handleStep = async () => {
    if (!replayState?.replay_id) return;
    setIsStepping(true);
    try {
      const res = await replayService.advanceStep(replayState.replay_id, 1);
      setReplayState(res);
    } catch (err) {
      alert(`Step advance failed: ${err.message}`);
    } finally {
      setIsStepping(false);
    }
  };

  const currentStep = replayState?.current_step ?? 0;
  const totalSteps = replayState?.total_steps ?? 12;
  const progressPct = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;

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
              <i className="bi bi-clock-history fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              Historical Flood Disaster Replay Simulator
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Time-stepped chronologic replay of historical flood surges in Punjab to evaluate agentic early-warning response.
          </p>
        </div>
      </div>

      <div className="row g-4">
        {/* Left Column: Replay Controls */}
        <div className="col-12 col-xl-4">
          <div className="orca-card p-4 mb-4">
            <h6 className="fw-bold mb-3" style={{ color: '#092F2B' }}>
              Simulation Scenario Parameters
            </h6>

            <div className="mb-3">
              <label className="form-label small fw-semibold">Historical Disaster Event</label>
              <select
                className="form-select form-select-sm"
                value={eventName}
                onChange={(e) => setEventName(e.target.value)}
              >
                <option value="2023_punjab_monsoon_floods">July 2023 Sutlej-Beas Monsoon Inundation</option>
                <option value="2019_sutlej_breach_surge">August 2019 Ropar-Harike Embankment Breach</option>
              </select>
            </div>

            <div className="p-3 mb-3 rounded-3 small" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6', color: '#687B78' }}>
              <div className="fw-semibold mb-1" style={{ color: '#152E2B' }}>Scenario Parameters:</div>
              <div>• Time Horizon: July 09 - July 12, 2023</div>
              <div>• Step Increment: +6 Hours per step</div>
              <div>• Monitored Basin: Sutlej Basin (Jalandhar & Tarn Taran)</div>
            </div>

            {!replayState ? (
              <button
                type="button"
                className="btn btn-primary w-100 fw-bold d-flex align-items-center justify-content-center gap-2 py-2"
                onClick={handleStartReplay}
                disabled={isStarting}
              >
                {isStarting ? (
                  <span>Initializing Replay Stream...</span>
                ) : (
                  <>
                    <i className="bi bi-play-circle-fill fs-5"></i>
                    <span>Initialize Historical Replay</span>
                  </>
                )}
              </button>
            ) : (
              <div className="d-flex flex-column gap-2">
                <button
                  type="button"
                  className="btn btn-teal w-100 py-2 d-flex align-items-center justify-content-center gap-2 fw-semibold"
                  onClick={handleStep}
                  disabled={isStepping || currentStep >= totalSteps}
                >
                  <i className="bi bi-skip-forward-fill"></i>
                  <span>Advance Timeline (+6h)</span>
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary w-100 py-1"
                  onClick={() => setReplayState(null)}
                >
                  Reset Replay Simulation
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Replay State & Progress */}
        <div className="col-12 col-xl-8">
          <div className="orca-card p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                Timeline Execution Progress
              </span>
              <span className="badge font-monospace" style={{ backgroundColor: '#E7F6EF', color: '#16865F' }}>
                Step {currentStep} of {totalSteps}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="progress mb-4" style={{ height: '10px', backgroundColor: '#E8F0EC' }}>
              <div
                className="progress-bar"
                role="progressbar"
                style={{ width: `${progressPct}%`, backgroundColor: '#16865F' }}
              />
            </div>

            {!replayState ? (
              <div className="p-5 text-center text-muted">
                <i className="bi bi-clock-history fs-1 mb-2 d-block text-muted"></i>
                <h6 className="fw-bold" style={{ color: '#152E2B' }}>Simulation Stream Standby</h6>
                <p className="small mb-0">Select historical monsoon event on the left and click "Initialize".</p>
              </div>
            ) : (
              <div>
                <div className="p-3 rounded-3 mb-3 d-flex justify-content-between align-items-center" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                  <div>
                    <span className="text-muted small">Simulation Timestamp:</span>
                    <h5 className="mb-0 fw-bold font-monospace" style={{ color: '#10483F' }}>
                      {formatDateTime(replayState.simulated_timestamp)}
                    </h5>
                  </div>
                  <span className="badge font-monospace" style={{ backgroundColor: '#FEF7ED', color: '#E99A36' }}>
                    REPLAY STEP ACTIVE
                  </span>
                </div>

                {/* Village Status Grid */}
                <h6 className="fw-bold mb-3" style={{ color: '#092F2B' }}>
                  Village Risk Evaluations at This Timeline Step
                </h6>

                <div className="row g-3">
                  {Object.entries(replayState.village_evaluations || {}).map(([vName, vData]) => (
                    <div key={vName} className="col-12 col-md-6">
                      <div className="p-3 rounded-3" style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}>
                        <div className="d-flex justify-content-between align-items-center mb-2">
                          <h6 className="fw-bold mb-0" style={{ color: '#152E2B' }}>{vName}</h6>
                          <RiskBadge risk={vData.risk_level || 'HIGH'} size="sm" />
                        </div>
                        <div className="small text-muted mb-1">
                          Water Stage: <strong className="text-dark font-monospace">{vData.water_level_m || 234.2}m</strong>
                        </div>
                        <div className="small text-muted">
                          Recommended Action: <em>{vData.recommendation || 'Continuous Embankment Monitoring'}</em>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default HistoricalReplay;
