"""TMS-NF-003 reliability run: N consecutive headless runs of M simulated minutes.

    python -m tools.reliability_run --runs 5 --minutes 30
Exit code 0 only if every run completes with valid state.
"""
import argparse
import sys
import time
import traceback
from pathlib import Path

from simulation.engine import SimulationEngine
from simulation.scenario import ScenarioError, load_scenario

DT = 1 / 30
DEFAULT_SCENARIO = Path(__file__).resolve().parents[1] / "data" / "scenarios.json"


def check_invariants(engine) -> list[str]:
    m, t = engine.metrics, engine.traffic
    problems = []
    if m.spawned < m.completed:
        problems.append("completed > spawned")
    if len(t.vehicles) != m.spawned - m.completed:
        problems.append("active vehicle count does not match metrics")
    if m.total_wait_seconds < 0:
        problems.append("negative wait time")
    for car in t.vehicles:
        if not (-100 <= car.x <= t.width + 100 and -100 <= car.y <= t.height + 100):
            problems.append(f"vehicle outside world at ({car.x:.0f}, {car.y:.0f})")
            break
    return problems


def run_once(scenario, minutes: float, run_no: int) -> dict:
    engine = SimulationEngine(scenario)
    engine.traffic.seed = scenario.simulation["seed"] + run_no  # vary traffic between runs
    engine.reset()
    target, problems = minutes * 60, []
    start = time.perf_counter()
    while engine.clock < target - 1e-9:
        engine.tick(DT)
        if engine.tick_count % 1800 == 0:  # every simulated minute
            problems += check_invariants(engine)
            if problems:
                break
    problems += check_invariants(engine)
    return {"run": run_no, "sim_seconds": round(engine.clock, 2), "ok": not problems,
            "problems": problems, "wall_seconds": round(time.perf_counter() - start, 2),
            "spawned": engine.metrics.spawned, "completed": engine.metrics.completed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--minutes", type=float, default=30)
    parser.add_argument("--scenario", default=str(DEFAULT_SCENARIO))
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
    except ScenarioError as exc:
        print(f"Run not started. {exc}", file=sys.stderr)
        return 2
    passed = 0
    for run_no in range(1, args.runs + 1):
        try:
            result = run_once(scenario, args.minutes, run_no)
        except Exception:  # an unhandled failure is exactly what this test detects
            result = {"run": run_no, "ok": False, "problems": [traceback.format_exc()]}
        passed += result["ok"]
        print(result)
    print(f"{passed}/{args.runs} runs completed {args.minutes:g} simulated minutes "
          f"without failure ({100 * passed / args.runs:.0f}%)")
    return 0 if passed == args.runs else 1


if __name__ == "__main__":
    sys.exit(main())
