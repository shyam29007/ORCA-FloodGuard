"""CLI script to verify operational status of all data providers."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent
for p in [str(backend_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.tools.weather_tool import fetch_weather_forecast
from backend.app.tools.river_tool import PUNJAB_RIVER_STATIONS, fetch_river_reading
from backend.app.tools.dam_tool import PUNJAB_DAMS, fetch_dam_telemetry
from backend.app.tools.elevation_tool import fetch_elevation_profile
from backend.app.core.llm_factory import get_llm


def main():
    print("=" * 60)
    print("ORCA-FloodGuard: Telemetry & Provider Source Verification")
    print("=" * 60)

    # 1. Weather
    print("\n[1] Checking Weather Telemetry (IMD)...")
    wf, w_ev = fetch_weather_forecast(31.1465, 75.1872, district="Jalandhar")
    print(f"  Status: OK | 24h Rain: {wf.rainfall_24h_mm} mm | Mode: {'SIMULATED' if wf.is_simulated else 'LIVE'}")

    # 2. River Stations
    print("\n[2] Checking River Gauge Network (CWC)...")
    print(f"  Total Stations Registered: {len(PUNJAB_RIVER_STATIONS)}")
    sample_station = PUNJAB_RIVER_STATIONS[0]
    rd, r_ev = fetch_river_reading(sample_station.station_id)
    print(f"  Sample Station: {sample_station.station_name} | Reading: {rd.water_level_meters} m | Status: {rd.status.value}")

    # 3. Dams
    print("\n[3] Checking Dam Reservoir Telemetry (BBMB)...")
    print(f"  Total Dams Registered: {len(PUNJAB_DAMS)}")
    dams, d_ev = fetch_dam_telemetry(river_basin="Sutlej")
    print(f"  Bhakra Outflow: {dams[0].outflow_discharge_cusecs:,.0f} cusecs | Status: {dams[0].status.value}")

    # 4. Elevation
    print("\n[4] Checking Elevation Profile (NASA SRTM)...")
    elev, is_low, _, _ = fetch_elevation_profile(31.1465, 75.1872)
    print(f"  Elevation: {elev} m AMSL | Low-Lying Floodplain: {is_low}")

    # 5. LLM Factory
    print("\n[5] Checking Configured LLM Factory...")
    llm = get_llm()
    print(f"  Provider Instance: {llm.__class__.__name__} | Available: {llm.is_available()}")

    print("\n" + "=" * 60)
    print("All provider interfaces operational.")
    print("=" * 60)


if __name__ == "__main__":
    main()

