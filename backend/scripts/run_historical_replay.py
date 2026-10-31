"""CLI script to run historical flood replay simulation."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent
for p in [str(backend_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.schemas.replay import HistoricalReplayStartRequest, HistoricalReplayStepRequest
from backend.app.services.replay_service import ReplayService


def main():
    print("=" * 60)
    print("ORCA-FloodGuard: 2023 Punjab Monsoon Floods Replay Simulation")
    print("=" * 60)

    start_req = HistoricalReplayStartRequest(
        event_name="2023_punjab_monsoon_floods",
        target_villages=["Gidderpindi", "Phillaur", "Harike"],
    )
    status = ReplayService.start_replay(start_req)
    print(f"Session: {status.replay_id}")
    print(f"Initial Step {status.current_step}/{status.total_steps} at {status.simulated_timestamp}")
    print(f"Summary: {status.summary}")
    print(f"Village Risks: {status.village_risks}")
    print("-" * 60)

    while not status.is_completed:
        input("\nPress [ENTER] to advance replay to next time step...")
        step_req = HistoricalReplayStepRequest(steps_to_advance=1)
        status = ReplayService.step_replay(status.replay_id, step_req)
        print(f"Advanced to Step {status.current_step}/{status.total_steps} at {status.simulated_timestamp}")
        print(f"Summary: {status.summary}")
        print(f"Village Risks: {status.village_risks}")

    print("\nReplay simulation finished.")


if __name__ == "__main__":
    main()

