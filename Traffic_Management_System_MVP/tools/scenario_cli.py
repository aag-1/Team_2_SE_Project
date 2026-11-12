"""Operator tool to create, validate and compare scenarios.

Requirements covered: TMS-F-001 (create), TMS-F-019 / TMS-SR-003 (validate),
TMS-NF-007 (compare a saved experiment's configuration with another file).

Examples (run from the Traffic_Management_System_MVP folder):
    python -m tools.scenario_cli create --name "Rush hour" --approaches N,S,E \
        --spawn-interval 0.6 --green 15 --out data/scenarios/rush_hour.json
    python -m tools.scenario_cli validate data/scenarios/rush_hour.json
    python -m tools.scenario_cli compare data/scenarios/rush_hour.json \
        data/experiments/experiment_20261112_101500.json
    python main.py --scenario data/scenarios/rush_hour.json
"""
import argparse
import sys

from simulation.experiment_store import compare_scenarios
from simulation.scenario import ScenarioError, create_scenario, load_scenario, save_scenario

OPTION_TO_KEY = {
    "spawn_interval": "spawn_interval_seconds", "speed": "vehicle_speed",
    "green": "green_seconds", "amber": "amber_seconds",
    "red_clearance": "red_clearance_seconds", "seed": "seed",
}


def _summary(scenario) -> str:
    roads = ", ".join(f"{r.id}({r.approach})" for r in scenario.roads)
    sim = scenario.simulation
    return (f"Scenario '{scenario.name}': intersection {scenario.intersections[0].id}, "
            f"roads {roads}; spawn every {sim['spawn_interval_seconds']}s, "
            f"green/amber/red {sim['green_seconds']}/{sim['amber_seconds']}/"
            f"{sim['red_clearance_seconds']}s")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="scenario_cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="create a new scenario file")
    create.add_argument("--name", required=True)
    create.add_argument("--approaches", default="N,S,E,W",
                        help="comma-separated approach roads, e.g. N,S,E")
    create.add_argument("--intersection-id", default="INT-1")
    create.add_argument("--spawn-interval", type=float)
    create.add_argument("--speed", type=float)
    create.add_argument("--green", type=float)
    create.add_argument("--amber", type=float)
    create.add_argument("--red-clearance", type=float)
    create.add_argument("--seed", type=int)
    create.add_argument("--out", required=True)
    create.add_argument("--force", action="store_true", help="overwrite an existing file")
    check = sub.add_parser("validate", help="validate a scenario or saved experiment file")
    check.add_argument("path")
    diff = sub.add_parser("compare", help="compare the configurations in two files")
    diff.add_argument("first")
    diff.add_argument("second")
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            overrides = {key: getattr(args, opt) for opt, key in OPTION_TO_KEY.items()
                         if getattr(args, opt) is not None}
            approaches = [a.strip().upper() for a in args.approaches.split(",") if a.strip()]
            scenario = create_scenario(args.name, approaches, args.intersection_id, **overrides)
            path = save_scenario(args.out, scenario, overwrite=args.force)
            print(f"Created {path}\n{_summary(scenario)}")
        elif args.command == "validate":
            print(f"VALID: {_summary(load_scenario(args.path))}")
        else:
            diffs = compare_scenarios(load_scenario(args.first), load_scenario(args.second))
            print("\n".join(diffs) if diffs else "IDENTICAL: no configuration differences")
            return 1 if diffs else 0
        return 0
    except ScenarioError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"Not written: {exc} (use --force to overwrite)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
