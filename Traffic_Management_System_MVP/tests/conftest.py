import copy
from pathlib import Path

import pytest

from simulation.scenario import DEFAULT_SCENARIO, load_scenario

DATA = Path(__file__).resolve().parents[1] / "data" / "scenarios.json"


@pytest.fixture
def default_scenario():
    return load_scenario(DATA)


@pytest.fixture
def raw_default():
    return copy.deepcopy(DEFAULT_SCENARIO)
