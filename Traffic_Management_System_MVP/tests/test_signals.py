from simulation.signals import SignalController


def test_initial_signal_states():
    controller = SignalController()
    assert controller.state_for("N") == "GREEN"
    assert controller.state_for("S") == "GREEN"
    assert controller.state_for("E") == "RED"
    assert controller.state_for("W") == "RED"


def test_signal_changes_to_amber_after_green_duration():
    controller = SignalController(green_seconds=10, amber_seconds=3, red_clearance_seconds=1)
    assert controller.update(10) == "NS_AMBER"
    assert controller.state_for("N") == "AMBER"
    assert controller.state_for("E") == "RED"


def test_signal_cycle_returns_to_north_south_green():
    controller = SignalController(green_seconds=1, amber_seconds=1, red_clearance_seconds=0.5)
    transitions = []
    for _ in range(6):
        transitions.append(controller.update(1))
    assert controller.phase == "NS_GREEN"

def test_signal_uses_configured_phase_sequence():
    controller = SignalController(
        green_seconds=2,
        amber_seconds=1,
        red_clearance_seconds=0.5
    )

    expected_phases = [
        "NS_AMBER",
        "ALL_RED_TO_EW",
        "EW_GREEN",
        "EW_AMBER",
        "ALL_RED_TO_NS",
        "NS_GREEN"
    ]

    for expected_phase in expected_phases:
        controller.elapsed = controller._phase_duration()
        assert controller.update(0) == expected_phase
        assert controller.phase == expected_phase
