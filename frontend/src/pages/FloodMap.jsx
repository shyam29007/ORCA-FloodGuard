import React, { useState } from 'react';
import PunjabFloodMap from '../components/maps/PunjabFloodMap';
import {
  REFERENCE_VILLAGES,
  CWC_GAUGE_STATIONS,
  BBMB_DAMS,
  SEEDED_RELIEF_CENTRES,
  PUNJAB_DISTRICTS,
} from '../utils/punjabData';
import { useMode } from '../context/ModeContext';

export function FloodMap() {
  const { selectedDistrict, setSelectedDistrict } = useMode();
  const [filterDistrict, setFilterDistrict] = useState(selectedDistrict || 'All Districts');

  const filteredVillages =
    filterDistrict === 'All Districts'
      ? REFERENCE_VILLAGES
      : REFERENCE_VILLAGES.filter((v) => v.district.toLowerCase() === filterDistrict.toLowerCase());

  return (
    <div className="container-fluid px-0 h-100 d-flex flex-column">
      {/* Top Header & Filter Bar */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
        <div>
          <div className="d-flex align-items-center gap-2">
            <div
              className="rounded-3 d-flex align-items-center justify-content-center text-white"
              style={{ width: '36px', height: '36px', backgroundColor: '#16865F' }}
            >
              <i className="bi bi-map fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              Interactive Flood & Evacuation Geospatial Map
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Authoritative visualization of monitored villages, CWC gauge sites, BBMB dams, and candidate evacuation corridors.
          </p>
        </div>

        {/* District selection */}
        <div className="d-flex align-items-center gap-2">
          <i className="bi bi-funnel text-muted"></i>
          <select
            className="form-select form-select-sm"
            style={{ width: '180px' }}
            value={filterDistrict}
            onChange={(e) => {
              setFilterDistrict(e.target.value);
              setSelectedDistrict(e.target.value);
            }}
          >
            {PUNJAB_DISTRICTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Quick Stat Counter Pills */}
      <div className="d-flex flex-wrap gap-2 mb-3">
        <span
          className="badge py-2 px-3 small d-flex align-items-center gap-2"
          style={{ backgroundColor: '#FFFFFF', color: '#152E2B', border: '1px solid #DFEAE6', borderRadius: '8px' }}
        >
          <span style={{ color: '#D94A4A' }}>●</span> Monitored Villages: <strong>{filteredVillages.length}</strong>
        </span>
        <span
          className="badge py-2 px-3 small d-flex align-items-center gap-2"
          style={{ backgroundColor: '#FFFFFF', color: '#152E2B', border: '1px solid #DFEAE6', borderRadius: '8px' }}
        >
          <span style={{ color: '#16865F' }}>▲</span> CWC Gauge Sites: <strong>{CWC_GAUGE_STATIONS.length}</strong>
        </span>
        <span
          className="badge py-2 px-3 small d-flex align-items-center gap-2"
          style={{ backgroundColor: '#FFFFFF', color: '#152E2B', border: '1px solid #DFEAE6', borderRadius: '8px' }}
        >
          <span style={{ color: '#24B6A0' }}>■</span> BBMB Major Reservoirs: <strong>{BBMB_DAMS.length}</strong>
        </span>
        <span
          className="badge py-2 px-3 small d-flex align-items-center gap-2"
          style={{ backgroundColor: '#FFFFFF', color: '#152E2B', border: '1px solid #DFEAE6', borderRadius: '8px' }}
        >
          <span style={{ color: '#E99A36' }}>★</span> Designated Shelters: <strong>{SEEDED_RELIEF_CENTRES.length}</strong>
        </span>
      </div>

      {/* Map Card */}
      <div className="orca-card flex-grow-1 overflow-hidden" style={{ minHeight: '620px' }}>
        <PunjabFloodMap
          height="620px"
          villages={filteredVillages}
          riverStations={CWC_GAUGE_STATIONS}
          dams={BBMB_DAMS}
          reliefCentres={SEEDED_RELIEF_CENTRES}
          showRoutes={true}
        />
      </div>

      {/* Verification Notice Footer */}
      <div
        className="mt-3 p-3 rounded-3 small d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2"
        style={{ backgroundColor: '#FFFFFF', border: '1px solid #DFEAE6', color: '#687B78' }}
      >
        <span>
          <strong>Safety Invariant Note:</strong> Evacuation lines shown are classified as <em>CANDIDATE</em> uninspected routes until field validation by authorized civil engineers.
        </span>
        <span className="font-monospace text-muted" style={{ fontSize: '0.72rem' }}>
          Basemap: OpenStreetMap | SRTM 30m Digital Elevation Model
        </span>
      </div>
    </div>
  );
}

export default FloodMap;
