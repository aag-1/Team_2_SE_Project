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
- Scenario settings loaded from `data/scenarios.json`, including the road network
  (one four-way intersection, configurable N/S/E/W approach roads).
- Create new scenarios from the command line and run them with `--scenario`.

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
- **R** — reset the simulation (same scenario, same arrival sequence)
- **S** — save the configuration + current results to `data/experiments/`
- **Up / Down** — increase / decrease vehicle spawn rate
- **Esc** — quit

## Scenarios

```bash
python -m tools.scenario_cli create --name "Rush hour" --approaches N,S,E \
    --spawn-interval 0.6 --green 15 --out data/scenarios/rush_hour.json
python -m tools.scenario_cli validate data/scenarios/rush_hour.json
python main.py --scenario data/scenarios/rush_hour.json
```

Scenario files are validated before the window opens. An invalid file stops
`main.py` with exit code 2 and lists every problem found (missing fields,
out-of-range values, unknown fields, NaN/Infinity, duplicate keys, oversized or
non-UTF-8 files). The current model supports one four-way intersection;
scenarios with more than one intersection are rejected with an explicit message.

## Experiments and reliability

```bash
python main.py --scenario data/experiments/experiment_20261112_101500.json
python -m tools.scenario_cli compare data/scenarios.json data/experiments/experiment_20261112_101500.json
python -m tools.reliability_run --runs 5 --minutes 30
```

A saved experiment (key **S**) holds the full configuration and the results at
the time of saving. It can be run again with `--scenario`, and `compare` shows
any configuration differences. The reliability run checks 5 consecutive
30-minute simulated runs without the window (TMS-NF-003).

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
│   ├── engine.py      # master clock + pause/resume/step/reset
│   ├── scenario.py    # scenario model + validation layer
│   ├── experiment_store.py  # save / reload / compare experiments
│   ├── signals.py
│   ├── traffic.py
│   └── metrics.py
├── interface/
│   ├── __init__.py
│   └── dashboard.py
├── tools/
│   ├── scenario_cli.py     # create / validate / compare scenario files
│   └── reliability_run.py  # 5 x 30-minute headless reliability run
└── tests/                # python -m pytest -q
```

## Notes for the team

1. Keep the submitted SRS, SAD, and Software Test Plan unchanged.
2. Agree on shared interfaces before splitting implementation among members.
3. Use SRS IDs as the source of truth. The submitted STP's feature-to-ID mapping
   differs from the SRS mapping; document this in a new note rather than editing
   submitted documents.
4. Create a feature branch per member and raise PRs for repository-owner review.
5. Run `python -m pytest -q` from the `Traffic_Management_System_MVP` folder after
   installing requirements. On macOS, pygame 2.6.1 fonts fail on Python 3.14; use a
   Python 3.12 virtual environment to run the window.



## Secure external API communication

The optional `SecureAPIClient` supports secure communication with external
traffic sensor/API services.

- Remote API URLs must use HTTPS.
- Server certificates are verified using Python's default SSL context.
- Requests use Bearer-token authentication.
- API tokens should be stored in the `TRAFFIC_API_TOKEN` environment variable.
- Requests use a configurable timeout and handle connection and response errors.

### Configure the API token (Windows PowerShell)

```powershell
$env:TRAFFIC_API_TOKEN = "your-api-token"
```

### Example usage

```python
from simulation.secure_api import SecureAPIClient

client = SecureAPIClient("https://example.com/api")
data = client.get("sensors/data")

print(data)
```

The client is optional. The simulator does not require a live external API
or physical sensors to run.


## Current MVP boundaries

The visual model uses a single straight-through lane per approach. It is an
educational abstraction, not a calibrated road-traffic model. The simulation
does not represent turning movements, pedestrians, real sensors, or real
traffic infrastructure.
