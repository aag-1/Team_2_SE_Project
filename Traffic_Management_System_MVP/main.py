"""Entry point for the Traffic Management System (Simulation) MVP.

Usage:
    python main.py                                      # default data/scenarios.json
    python main.py --scenario data/scenarios/x.json     # a scenario file
    python main.py --scenario data/experiments/y.json   # re-run a saved experiment's config
"""
import argparse
import sys

from simulation.scenario import ScenarioError, load_scenario


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Traffic Management System simulation")
    parser.add_argument("--scenario", help="scenario or saved experiment JSON file "
                                           "(default: data/scenarios.json)")
    args = parser.parse_args(argv)

    from interface.dashboard import CONFIG_PATH, run_app
    try:
        scenario = load_scenario(args.scenario or CONFIG_PATH)
    except ScenarioError as exc:
        # TMS-F-019: invalid configuration prevents execution and shows a useful error.
        print(f"Simulation not started. {exc}", file=sys.stderr)
        return 2

    run_app(scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
