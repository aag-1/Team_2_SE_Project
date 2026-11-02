"""Entry point for the Traffic Management System (Simulation) MVP.

Usage:
    python main.py                                   # default data/scenarios.json
    python main.py --scenario data/scenarios/x.json  # a scenario file
"""
import argparse

from simulation.scenario import load_scenario


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Traffic Management System simulation")
    parser.add_argument("--scenario", help="scenario JSON file (default: data/scenarios.json)")
    args = parser.parse_args(argv)
    scenario = load_scenario(args.scenario) if args.scenario else None

    from interface.dashboard import run_app
    run_app(scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
