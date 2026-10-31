import React from 'react';
import { useMode } from '../../context/ModeContext';

export function ModeSwitch() {
  const { mode, isDemoMode, toggleMode } = useMode();

  return (
    <div className="d-flex align-items-center">
      <button
        type="button"
        onClick={toggleMode}
        className="btn btn-sm d-flex align-items-center gap-2 px-3 py-1 rounded-pill transition-all"
        style={{
          backgroundColor: isDemoMode ? '#E7F6EF' : '#E0F2FE',
          color: isDemoMode ? '#10483F' : '#0369A1',
          border: `1px solid ${isDemoMode ? '#BCE3D4' : '#BAE6FD'}`,
          fontSize: '0.78rem',
          fontWeight: 600,
        }}
        title="Toggle between Scenario Simulation (Demo) and Operational Telemetry"
      >
        <span
          className="rounded-circle d-inline-block"
          style={{
            width: '8px',
            height: '8px',
            backgroundColor: isDemoMode ? '#16865F' : '#0284C7',
          }}
        />
        <span>{isDemoMode ? 'MODE: DEMO / SCENARIO' : 'MODE: OPERATIONAL LIVE'}</span>
      </button>
    </div>
  );
}

export default ModeSwitch;
