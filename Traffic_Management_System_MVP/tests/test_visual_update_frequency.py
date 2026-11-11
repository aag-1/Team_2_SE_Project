
"""Visual update frequency tests for the Traffic Management System."""
import os
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def test_visual_updates_at_least_10_times_per_second():
    performance_script = """
import time
import pygame
from interface.dashboard import run_app

frame_times = []

original_flip = pygame.display.flip

def counted_flip():
    frame_times.append(time.perf_counter())
    original_flip()

pygame.display.flip = counted_flip

def controlled_events():
    if frame_times and time.perf_counter() - frame_times[0] >= 1.5:
        return [pygame.event.Event(pygame.QUIT)]
    return []

pygame.event.get = controlled_events

run_app()

if len(frame_times) < 2:
    raise RuntimeError("Not enough frames were rendered to measure FPS.")

elapsed = frame_times[-1] - frame_times[0]
fps = (len(frame_times) - 1) / elapsed

print(f"VISUAL_FPS={fps:.2f}")
"""

    environment = os.environ.copy()
    environment["SDL_VIDEODRIVER"] = "dummy"
    environment["SDL_AUDIODRIVER"] = "dummy"

    result = subprocess.run(
        [sys.executable, "-c", performance_script],
        cwd=PROJECT_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, (
        f"Visual performance test failed:\n{result.stderr}"
    )

    fps_line = next(
        (
            line for line in result.stdout.splitlines()
            if line.startswith("VISUAL_FPS=")
        ),
        None,
    )

    assert fps_line is not None, "FPS measurement was not reported."

    measured_fps = float(fps_line.split("=", 1)[1])

    assert measured_fps >= 10.0, (
        f"Visual update rate was {measured_fps:.2f} FPS; "
        "the requirement is at least 10 FPS."
    )
