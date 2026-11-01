
"""Startup performance tests for the Traffic Management System."""
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def test_application_starts_within_five_seconds():
    startup_script = """
import time
import pygame
from interface.dashboard import run_app

start_time = time.perf_counter()

# Close the application after its first rendered frame.
pygame.event.get = lambda: [pygame.event.Event(pygame.QUIT)]

run_app()

startup_time = time.perf_counter() - start_time
print(f"STARTUP_TIME={startup_time:.4f}")
"""

    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"

    result = subprocess.run(
        [sys.executable, "-c", startup_script],
        cwd=PROJECT_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, (
        f"Application startup failed:\n{result.stderr}"
    )

    startup_line = next(
        (
            line for line in result.stdout.splitlines()
            if line.startswith("STARTUP_TIME=")
        ),
        None
    )

    assert startup_line is not None, (
        "Application did not report its startup time."
    )

    startup_seconds = float(
        startup_line.split("=", 1)[1]
    )

    assert startup_seconds < 5.0, (
        f"Startup took {startup_seconds:.2f} seconds; "
        "the requirement is under 5 seconds."
    )
