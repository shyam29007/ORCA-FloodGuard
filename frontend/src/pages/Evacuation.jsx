import React, { useState, useEffect } from 'react';
import evacuationService from '../services/evacuationService';
import LoadingSpinner from '../components/common/LoadingSpinner';
import StatusBadge from '../components/common/StatusBadge';
import { SEEDED_RELIEF_CENTRES, REFERENCE_VILLAGES, PUNJAB_DISTRICTS } from '../utils/punjabData';

export function Evacuation() {
  const [reliefCentres, setReliefCentres] = useState(SEEDED_RELIEF_CENTRES);
  const [routes, setRoutes] = useState([]);
  const [selectedVillage, setSelectedVillage] = useState(REFERENCE_VILLAGES[0]);
  const [filterDistrict, setFilterDistrict] = useState('All Districts');
  const [loading, setLoading] = useState(true);

  const loadEvacuationData = async () => {
    setLoading(true);
    try {
      const [centresRes, routesRes] = await Promise.allSettled([
        evacuationService.getReliefCentres(filterDistrict !== 'All Districts' ? filterDistrict : null),
        evacuationService.getRoutes({
          village_name: selectedVillage.name,
          latitude: selectedVillage.coordinates[0],
          longitude: selectedVillage.coordinates[1],
        }),
      ]);

      if (centresRes.status === 'fulfilled' && centresRes.value?.length) {
        setReliefCentres(centresRes.value);
      }
      if (routesRes.status === 'fulfilled' && routesRes.value?.length) {
        setRoutes(routesRes.value);
      } else {
        setRoutes([
          {
            route_id: 'rt-gidd-shahkot-01',
            origin_village: selectedVillage.name,
            destination_relief_centre: 'Shahkot Government Senior Secondary School',
            distance_km: 16.5,
            estimated_travel_time_minutes: 35,
            verification_status: 'CANDIDATE',
            elevation_min_m: 211.5,
            elevation_max_m: 222.0,
            has_low_lying_segments: true,
            inundation_hazard_segments: ['NH-703 Culvert #4 (Potential Overflow Risk)'],
            recommended_vehicle_types: ['Heavy Transport', 'Buses', 'High-Clearance 4x4'],
          },
          {
            route_id: 'rt-gidd-nakodar-02',
            origin_village: selectedVillage.name,
            destination_relief_centre: 'Nakodar Civil Community Hall',
            distance_km: 24.2,
            estimated_travel_time_minutes: 50,
            verification_status: 'UNVERIFIED',
            elevation_min_m: 216.0,
            elevation_max_m: 228.0,
            has_low_lying_segments: false,
            inundation_hazard_segments: [],
            recommended_vehicle_types: ['All Vehicles', 'Tractors'],
          },
        ]);
      }
    } catch (err) {
      console.warn('Evacuation data error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvacuationData();
  }, [selectedVillage, filterDistrict]);

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
              <i className="bi bi-signpost-2 fs-5"></i>
            </div>
            <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
              Evacuation Corridors & Shelter Directory
            </h4>
          </div>
          <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
            Topographic elevation corridor analysis, inundation pinch points, and designated emergency high-ground shelters.
          </p>
        </div>

        {/* Filters */}
        <div className="d-flex align-items-center gap-2">
          <select
            className="form-select form-select-sm"
            style={{ width: '160px' }}
            value={filterDistrict}
            onChange={(e) => setFilterDistrict(e.target.value)}
          >
            {PUNJAB_DISTRICTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>

          <select
            className="form-select form-select-sm"
            style={{ width: '180px' }}
            value={selectedVillage.id}
            onChange={(e) => {
              const v = REFERENCE_VILLAGES.find((vil) => vil.id === e.target.value);
              if (v) setSelectedVillage(v);
            }}
          >
            {REFERENCE_VILLAGES.map((v) => (
              <option key={v.id} value={v.id}>
                From: {v.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Mandatory Safety Alert */}
      <div
        className="p-3 mb-4 rounded-3 d-flex align-items-start gap-3"
        style={{ backgroundColor: '#FEF7ED', border: '1px solid #FCE4C3' }}
      >
        <i className="bi bi-shield-exclamation fs-4 flex-shrink-0" style={{ color: '#E99A36' }}></i>
        <div className="small" style={{ lineHeight: '1.5' }}>
          <strong className="d-block mb-1" style={{ color: '#78350F' }}>
            Safety Mandate: Algorithmic Routes Remain Strictly Candidate
          </strong>
          <span style={{ color: '#92400E' }}>
            ORCA-FloodGuard enforces a core safety invariant: routes synthesized from digital elevation models are classified as{' '}
            <strong>CANDIDATE / UNVERIFIED</strong>. They must never be announced as safe without verified on-ground physical inspection by local civil engineers.
          </span>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Calculating digital elevation corridors and shelter proximity..." />
      ) : (
        <div className="row g-4">
          {/* Candidate Corridors Column */}
          <div className="col-12 col-lg-6">
            <div className="orca-card p-4 h-100">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                  Candidate Evacuation Corridors for {selectedVillage.name}
                </span>
                <span className="badge font-monospace" style={{ backgroundColor: '#FEF7ED', color: '#E99A36' }}>
                  UNVERIFIED CANDIDATE
                </span>
              </div>

              <div className="d-flex flex-column gap-3">
                {routes.map((rt) => (
                  <div
                    key={rt.route_id}
                    className="p-3 rounded-3"
                    style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}
                  >
                    <div className="d-flex justify-content-between align-items-start mb-2">
                      <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                        {rt.destination_relief_centre}
                      </h6>
                      <span className="badge font-monospace" style={{ backgroundColor: '#FEF7ED', color: '#E99A36' }}>
                        {rt.verification_status}
                      </span>
                    </div>

                    <div className="row g-2 small mb-2 text-muted">
                      <div className="col-6">
                        Distance: <strong style={{ color: '#152E2B' }}>{rt.distance_km} km</strong>
                      </div>
                      <div className="col-6">
                        Est. Transit Time: <strong style={{ color: '#152E2B' }}>{rt.estimated_travel_time_minutes} mins</strong>
                      </div>
                      <div className="col-6">
                        Elevation Profile: <span className="font-monospace text-dark">{rt.elevation_min_m}m - {rt.elevation_max_m}m</span>
                      </div>
                      <div className="col-6">
                        Low Depression: <span className="text-warning fw-bold">{rt.has_low_lying_segments ? 'Hazard Present' : 'Clear'}</span>
                      </div>
                    </div>

                    {rt.inundation_hazard_segments?.length > 0 && (
                      <div className="p-2 rounded mb-2 small" style={{ backgroundColor: '#FDF2F2', border: '1px solid #F8CBCB', color: '#D94A4A' }}>
                        <i className="bi bi-exclamation-triangle me-1"></i>
                        Pinch Points: {rt.inundation_hazard_segments.join(', ')}
                      </div>
                    )}

                    <div className="d-flex flex-wrap gap-1 mt-2">
                      {rt.recommended_vehicle_types?.map((vtype, i) => (
                        <span key={i} className="badge" style={{ backgroundColor: '#E7F6EF', color: '#16865F', fontSize: '0.68rem' }}>
                          {vtype}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Seeded Relief Shelters Column */}
          <div className="col-12 col-lg-6">
            <div className="orca-card p-4 h-100">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <span className="fw-bold small text-uppercase" style={{ color: '#092F2B', letterSpacing: '0.5px' }}>
                  Designated Emergency Relief Shelters ({reliefCentres.length})
                </span>
                <span className="badge font-monospace" style={{ backgroundColor: '#E7F6EF', color: '#16865F' }}>
                  SDMA Registered
                </span>
              </div>

              <div className="d-flex flex-column gap-3">
                {reliefCentres.map((centre) => (
                  <div
                    key={centre.centre_id}
                    className="p-3 rounded-3"
                    style={{ backgroundColor: '#F8FAF9', border: '1px solid #DFEAE6' }}
                  >
                    <div className="d-flex justify-content-between align-items-start mb-1">
                      <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                        {centre.name}
                      </h6>
                      <span className="badge" style={{ backgroundColor: '#E7F6EF', color: '#16865F' }}>
                        Capacity: {centre.capacity_persons}
                      </span>
                    </div>

                    <div className="small text-muted mb-2">
                      {centre.district} • High Ground AMSL: <strong>{centre.elevation_m}m</strong>
                    </div>

                    <div className="d-flex flex-wrap gap-1">
                      <span className="badge" style={{ backgroundColor: '#FFFFFF', color: '#152E2B', border: '1px solid #DFEAE6', fontSize: '0.68rem' }}>
                        Potable Water: {centre.has_potable_water ? 'Yes' : 'No'}
                      </span>
                      <span className="badge" style={{ backgroundColor: '#FFFFFF', color: '#152E2B', border: '1px solid #DFEAE6', fontSize: '0.68rem' }}>
                        Medical Aid: {centre.has_medical_station ? 'Staffed' : 'Pending'}
                      </span>
                      <span className="badge" style={{ backgroundColor: '#FFFFFF', color: '#152E2B', border: '1px solid #DFEAE6', fontSize: '0.68rem' }}>
                        Helipad: {centre.has_helipad ? 'Available' : 'None'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Evacuation;
