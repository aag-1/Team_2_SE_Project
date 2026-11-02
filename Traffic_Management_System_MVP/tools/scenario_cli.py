"""Operator tool to create a traffic scenario file (TMS-F-001).

Example (run from the Traffic_Management_System_MVP folder):
    python -m tools.scenario_cli create --name "Rush hour" --approaches N,S,E \
        --spawn-interval 0.6 --green 15 --out data/scenarios/rush_hour.json
    python main.py --scenario data/scenarios/rush_hour.json
"""
import argparse
import sys

from simulation.scenario import ScenarioError, create_scenario, save_scenario

OPTION_TO_KEY = {
    "spawn_interval": "spawn_interval_seconds", "speed": "vehicle_speed",
    "green": "green_seconds", "amber": "amber_seconds",
    "red_clearance": "red_clearance_seconds", "seed": "seed",
}


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
    args = parser.parse_args(argv)

    overrides = {key: getattr(args, opt) for opt, key in OPTION_TO_KEY.items()
                 if getattr(args, opt) is not None}
    approaches = [a.strip().upper() for a in args.approaches.split(",") if a.strip()]
    try:
        scenario = create_scenario(args.name, approaches, args.intersection_id, **overrides)
        path = save_scenario(args.out, scenario, overwrite=args.force)
    except ScenarioError as exc:
        print(f"Not created: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"Not written: {exc} (use --force to overwrite)", file=sys.stderr)
        return 1
    roads = ", ".join(f"{r.id}({r.approach})" for r in scenario.roads)
    print(f"Created {path}\nScenario '{scenario.name}': intersection "
          f"{scenario.intersections[0].id}, roads {roads}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
