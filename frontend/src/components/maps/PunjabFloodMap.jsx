import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import {
  PUNJAB_MAP_CENTER,
  PUNJAB_DEFAULT_ZOOM,
  REFERENCE_VILLAGES,
  CWC_GAUGE_STATIONS,
  BBMB_DAMS,
  SEEDED_RELIEF_CENTRES,
} from '../../utils/punjabData';
import { getRiskColor, formatWaterLevel } from '../../utils/formatters';

// Fix Leaflet's default marker icons in Vite/bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom colored SVG pin generator for high visual clarity
function createCustomIcon(color, label = '') {
  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="
        background-color: ${color};
        width: 28px;
        height: 28px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(9, 47, 43, 0.25);
        border: 2px solid #ffffff;
      ">
        <span style="transform: rotate(45deg); color: #fff; font-size: 11px; font-weight: bold;">
          ${label}
        </span>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
  });
}

export function PunjabFloodMap({
  height = '500px',
  villages = REFERENCE_VILLAGES,
  riverStations = CWC_GAUGE_STATIONS,
  dams = BBMB_DAMS,
  reliefCentres = SEEDED_RELIEF_CENTRES,
  showRoutes = true,
}) {
  const [layers, setLayers] = useState({
    villages: true,
    riverStations: true,
    dams: true,
    reliefCentres: true,
    routes: showRoutes,
  });

  const toggleLayer = (layerKey) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  // Build candidate evacuation lines connecting villages to nearest relief centres
  const evacuationLines = [
    {
      from: [31.1465, 75.1872], // Gidderpindi
      to: [31.0850, 75.3400],   // Shahkot School
      name: 'Gidderpindi -> Shahkot Shelter Corridor',
      status: 'CANDIDATE',
    },
    {
      from: [31.0267, 75.7871], // Phillaur
      to: [31.0300, 75.7900],   // Phillaur Community Hall
      name: 'Phillaur -> Police Academy Hall',
      status: 'CANDIDATE',
    },
    {
      from: [31.1683, 74.9600], // Harike
      to: [31.1700, 74.9650],   // Harike High Ground
      name: 'Harike Village -> Sanctuary High Ground',
      status: 'CANDIDATE',
    },
    {
      from: [31.2359, 76.4989], // Anandpur Sahib
      to: [30.9750, 76.5250],   // Ropar Camp
      name: 'Anandpur Sahib -> Ropar Civil Shelter',
      status: 'UNVERIFIED',
    },
    {
      from: [30.9237, 74.6065], // Firozpur Rural
      to: [30.9300, 74.6100],   // Firozpur Cantt
      name: 'Firozpur Rural -> Cantonment Centre',
      status: 'CANDIDATE',
    },
  ];

  return (
    <div className="position-relative w-100" style={{ height }}>
      {/* Floating Filter Toggles & Legend Bar */}
      <div
        className="position-absolute top-0 end-0 m-3 z-3 p-3 rounded-3 shadow-md"
        style={{
          fontSize: '0.78rem',
          backgroundColor: '#FFFFFF',
          border: '1px solid #DFEAE6',
          boxShadow: '0 4px 16px rgba(9, 47, 43, 0.1)',
        }}
      >
        <div className="fw-bold mb-2 pb-1 border-bottom" style={{ color: '#092F2B' }}>
          Geospatial Map Layers
        </div>
        <div className="d-flex flex-column gap-1">
          <label className="d-flex align-items-center gap-2 cursor-pointer" style={{ color: '#152E2B' }}>
            <input
              type="checkbox"
              className="form-check-input mt-0"
              checked={layers.villages}
              onChange={() => toggleLayer('villages')}
            />
            <span style={{ color: '#D94A4A' }}>●</span> Monitored Villages ({villages.length})
          </label>
          <label className="d-flex align-items-center gap-2 cursor-pointer" style={{ color: '#152E2B' }}>
            <input
              type="checkbox"
              className="form-check-input mt-0"
              checked={layers.riverStations}
              onChange={() => toggleLayer('riverStations')}
            />
            <span style={{ color: '#16865F' }}>▲</span> CWC River Gauges ({riverStations.length})
          </label>
          <label className="d-flex align-items-center gap-2 cursor-pointer" style={{ color: '#152E2B' }}>
            <input
              type="checkbox"
              className="form-check-input mt-0"
              checked={layers.dams}
              onChange={() => toggleLayer('dams')}
            />
            <span style={{ color: '#24B6A0' }}>■</span> BBMB Reservoirs ({dams.length})
          </label>
          <label className="d-flex align-items-center gap-2 cursor-pointer" style={{ color: '#152E2B' }}>
            <input
              type="checkbox"
              className="form-check-input mt-0"
              checked={layers.reliefCentres}
              onChange={() => toggleLayer('reliefCentres')}
            />
            <span style={{ color: '#E99A36' }}>★</span> Relief Centres ({reliefCentres.length})
          </label>
          <label className="d-flex align-items-center gap-2 cursor-pointer" style={{ color: '#152E2B' }}>
            <input
              type="checkbox"
              className="form-check-input mt-0"
              checked={layers.routes}
              onChange={() => toggleLayer('routes')}
            />
            <span style={{ color: '#E99A36' }}>—</span> Evacuation Corridors (Candidate)
          </label>
        </div>
      </div>

      {/* React Leaflet Map */}
      <MapContainer
        center={PUNJAB_MAP_CENTER}
        zoom={PUNJAB_DEFAULT_ZOOM}
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* 1. Monitored Villages */}
        {layers.villages &&
          villages.map((v) => {
            const riskColor = getRiskColor(v.risk_profile || 'HIGH');
            return (
              <Marker
                key={v.id}
                position={v.coordinates}
                icon={createCustomIcon(riskColor, 'V')}
              >
                <Popup>
                  <div className="p-1">
                    <h6 className="fw-bold mb-1" style={{ color: '#092F2B' }}>{v.name} ({v.name_pa || ''})</h6>
                    <div className="small text-muted mb-2">District: {v.district}</div>
                    <div className="d-flex justify-content-between mb-1 small">
                      <span className="text-muted">Assessed Risk:</span>
                      <strong style={{ color: riskColor }}>{v.risk_profile || 'HIGH'}</strong>
                    </div>
                    <div className="d-flex justify-content-between mb-1 small">
                      <span className="text-muted">Elevation AMSL:</span>
                      <span className="font-monospace">{v.elevation_m} m</span>
                    </div>
                    <div className="d-flex justify-content-between small">
                      <span className="text-muted">Nearest River:</span>
                      <span>{v.river || 'Sutlej River'}</span>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

        {/* 2. CWC River Gauge Stations */}
        {layers.riverStations &&
          riverStations.map((st) => (
            <Marker
              key={st.station_id || st.id}
              position={st.coordinates}
              icon={createCustomIcon('#16865F', 'G')}
            >
              <Popup>
                <div className="p-1">
                  <h6 className="fw-bold mb-1" style={{ color: '#092F2B' }}>{st.name || st.station_name}</h6>
                  <div className="small text-muted mb-2">CWC Gauge Site • {st.river} River</div>
                  <div className="d-flex justify-content-between mb-1 small">
                    <span className="text-muted">Warning Level:</span>
                    <strong style={{ color: '#E99A36' }}>{formatWaterLevel(st.warning_level_meters || st.warning_level_m)}</strong>
                  </div>
                  <div className="d-flex justify-content-between small">
                    <span className="text-muted">Danger Limit:</span>
                    <strong style={{ color: '#D94A4A' }}>{formatWaterLevel(st.danger_level_meters || st.danger_level_m)}</strong>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* 3. BBMB Major Dams */}
        {layers.dams &&
          dams.map((dam) => (
            <Marker
              key={dam.dam_id || dam.id}
              position={dam.coordinates}
              icon={createCustomIcon('#24B6A0', 'D')}
            >
              <Popup>
                <div className="p-1">
                  <h6 className="fw-bold mb-1" style={{ color: '#092F2B' }}>{dam.name}</h6>
                  <div className="small text-muted mb-2">BBMB Reservoir • {dam.river || dam.basin}</div>
                  <div className="d-flex justify-content-between small">
                    <span className="text-muted">Full Reservoir Level:</span>
                    <strong className="font-monospace">{formatWaterLevel(dam.full_reservoir_level_m || dam.frl_m)}</strong>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* 4. Seeded Relief Centres */}
        {layers.reliefCentres &&
          reliefCentres.map((rc) => (
            <Marker
              key={rc.centre_id || rc.id}
              position={rc.coordinates}
              icon={createCustomIcon('#E99A36', 'S')}
            >
              <Popup>
                <div className="p-1">
                  <h6 className="fw-bold mb-1" style={{ color: '#092F2B' }}>{rc.name}</h6>
                  <div className="small text-muted mb-2">Relief Centre • {rc.district}</div>
                  <div className="d-flex justify-content-between mb-1 small">
                    <span className="text-muted">Shelter Capacity:</span>
                    <strong style={{ color: '#16865F' }}>{rc.capacity_persons || rc.capacity} persons</strong>
                  </div>
                  <div className="d-flex justify-content-between small">
                    <span className="text-muted">Verification Status:</span>
                    <span className="badge" style={{ backgroundColor: '#F0FAF5', color: '#16865F' }}>REFERENCE_STATIC</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* 5. Candidate Evacuation Lines */}
        {layers.routes &&
          evacuationLines.map((line, idx) => (
            <Polyline
              key={idx}
              positions={[line.from, line.to]}
              pathOptions={{
                color: '#E99A36',
                weight: 3,
                dashArray: '6, 6',
                opacity: 0.85,
              }}
            >
              <Popup>
                <div className="small p-1">
                  <strong style={{ color: '#78350F' }}>{line.name}</strong>
                  <div className="text-muted mt-1">Status: {line.status} (Uninspected Candidate)</div>
                </div>
              </Popup>
            </Polyline>
          ))}
      </MapContainer>
    </div>
  );
}

export default PunjabFloodMap;
