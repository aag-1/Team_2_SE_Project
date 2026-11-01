# Traffic Management System (Simulation) — MVP

A simple, local, Python + Pygame traffic-intersection simulation for the Team 2
Software Engineering mini-project.

## What works in this starter application

- One four-way intersection with two non-conflicting straight-through traffic flows.
- Vehicles spawn from all four approaches at a configurable rate.
- Vehicles obey red, amber (stop before entering), and green signal states.
- Vehicles queue behind one another and leave the screen after crossing.
- Automatic fixed-time signal cycle.
- Start/pause, reset, and manual single-step controls.
- Live vehicle count, queue length, throughput, and average waiting time.
- Timestamped event log.
- Scenario settings loaded from `data/scenarios.json`.

This is a working **MVP foundation**, not a claim that all 20 functional, 8
non-functional, and 6 security requirements in the submitted SRS are complete.
Adaptive control, emergency preemption, incident management, authentication,
role permissions, experiment comparison, and report export are not implemented
in this first version.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux with a graphical desktop

## Setup (Windows PowerShell)

```powershell
cd Traffic_Management_System_MVP
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

If PowerShell blocks activation, use:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

## Setup (Linux/macOS)

```bash
cd Traffic_Management_System_MVP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Controls

- **Space** — pause / resume
- **N** — advance one simulation step while paused
- **R** — reset the simulation (vehicles, KPIs, signal phase; spawn rate kept)
- **Up / Down** — increase / decrease vehicle spawn rate (TMS-F-003, clamped 0.25–5.0 s)
- **I** — trigger / clear traffic incident, blocked N/S demo (TMS-F-014, admin only)
- **L** — export event log to `event_log.jsonl` (TMS-F-020)
- **O** — demo admin login / logout (TMS-SR-001)
- **1 / 2** — switch role operator / analyst (TMS-SR-002; admin needs login)
- **Esc** — quit

Congestion banner shows CONGESTED when queue/wait/active thresholds in
`data/scenarios.json` are exceeded (TMS-F-010). Dashboard KPIs refresh live
(TMS-F-016, TMS-NF-005).

## Project structure

```text
Traffic_Management_System_MVP/
├── main.py
├── requirements.txt
├── README.md
├── data/
│   └── scenarios.json
├── simulation/
│   ├── __init__.py
│   ├── signals.py
│   ├── traffic.py
│   └── metrics.py
├── interface/
│   ├── __init__.py
│   └── dashboard.py
└── tests/
    ├── test_signals.py
    └── test_metrics.py
```

## Notes for the team

1. Keep the submitted SRS, SAD, and Software Test Plan unchanged.
2. Agree on shared interfaces before splitting implementation among members.
3. Use SRS IDs as the source of truth. The submitted STP's feature-to-ID mapping
   differs from the SRS mapping; document this in a new note rather than editing
   submitted documents.
4. Create a feature branch per member and raise PRs for repository-owner review.
5. Run `pytest -q` after installing requirements.

## Current MVP boundaries

The visual model uses a single straight-through lane per approach. It is an
educational abstraction, not a calibrated road-traffic model. The simulation
does not represent turning movements, pedestrians, real sensors, or real
traffic infrastructure.
