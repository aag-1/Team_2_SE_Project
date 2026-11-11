
"""Pygame dashboard and application loop."""
from pathlib import Path
from datetime import datetime
import pygame

from simulation.engine import SimulationEngine
from simulation.scenario import Scenario, load_scenario
from simulation.report import save_summary_report

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "data" / "scenarios.json"
REPORT_DIR = BASE_DIR / "reports"

COLORS = {
    "background": (238, 241, 244),
    "road": (58, 62, 68),
    "road_line": (225, 205, 110),
    "white": (250, 250, 250),
    "text": (30, 35, 42),
    "green": (45, 190, 95),
    "amber": (245, 175, 35),
    "red": (220, 65, 65),
    "panel": (252, 253, 254),
    "muted": (105, 112, 120),
}


def load_config():
    return load_scenario(CONFIG_PATH)


def run_app(scenario: Scenario | None = None):
    scenario = scenario or load_config()
    pygame.init()
    width = scenario.window["width"]
    height = scenario.window["height"]
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(scenario.window["title"])
    clock = pygame.time.Clock()
    fps = 0.0
    font = pygame.font.SysFont("arial", 19)
    small = pygame.font.SysFont("arial", 15)

    engine = SimulationEngine(scenario)
    sim, signals, metrics = engine.traffic, engine.signals, engine.metrics
    events = [f"Scenario loaded: {scenario.name}"]

    def log(message):
        stamp = datetime.now().strftime("%H:%M:%S")
        events.insert(0, f"{stamp}  {message}")
        del events[8:]

    engine.add_listener(lambda _type, message, _ctx: log(message))

    def draw_text(text, x, y, color=None, selected_font=None):
        screen.blit(
            (selected_font or font).render(
                str(text),
                True,
                color or COLORS["text"]
            ),
            (x, y)
        )

    def draw_road():
        cx, cy, half = sim.cx, sim.cy, sim.road_half
        screen.fill(COLORS["background"])

        pygame.draw.rect(
            screen, COLORS["road"], (cx-half, 0, half*2, height)
        )
        pygame.draw.rect(
            screen, COLORS["road"], (0, cy-half, width, half*2)
        )

        for y in range(0, int(cy-half), 34):
            pygame.draw.line(
                screen, COLORS["road_line"],
                (cx, y), (cx, min(y+18, cy-half)), 2
            )

        for y in range(int(cy+half), height, 34):
            pygame.draw.line(
                screen, COLORS["road_line"],
                (cx, y), (cx, min(y+18, height)), 2
            )

        for x in range(0, int(cx-half), 34):
            pygame.draw.line(
                screen, COLORS["road_line"],
                (x, cy), (min(x+18, cx-half), cy), 2
            )

        for x in range(int(cx+half), width, 34):
            pygame.draw.line(
                screen, COLORS["road_line"],
                (x, cy), (min(x+18, width), cy), 2
            )

        pygame.draw.line(
            screen, COLORS["white"],
            (cx-half, cy-half-8), (cx+half, cy-half-8), 4
        )
        pygame.draw.line(
            screen, COLORS["white"],
            (cx-half, cy+half+8), (cx+half, cy+half+8), 4
        )
        pygame.draw.line(
            screen, COLORS["white"],
            (cx-half-8, cy-half), (cx-half-8, cy+half), 4
        )
        pygame.draw.line(
            screen, COLORS["white"],
            (cx+half+8, cy-half), (cx+half+8, cy+half), 4
        )

    def draw_signals():
        positions = {
            "N": (sim.cx+88, sim.cy-sim.road_half-30),
            "S": (sim.cx-112, sim.cy+sim.road_half+10),
            "W": (sim.cx-sim.road_half-32, sim.cy-95),
            "E": (sim.cx+sim.road_half+10, sim.cy+75)
        }

        for direction, (x, y) in positions.items():
            state = signals.state_for(direction)
            color = COLORS[state.lower()]
            pygame.draw.rect(
                screen, (25, 27, 30), (x, y, 26, 26),
                border_radius=5
            )
            pygame.draw.circle(screen, color, (x+13, y+13), 8)
            draw_text(direction, x+5, y-20, COLORS["white"], small)

    def draw_vehicles():
        for car in sim.vehicles:
            if car.direction in ("N", "S"):
                rect = pygame.Rect(
                    int(car.x-car.width/2),
                    int(car.y-car.length/2),
                    int(car.width),
                    int(car.length)
                )
            else:
                rect = pygame.Rect(
                    int(car.x-car.length/2),
                    int(car.y-car.width/2),
                    int(car.length),
                    int(car.width)
                )

            pygame.draw.rect(
                screen, car.color, rect, border_radius=5
            )
            pygame.draw.rect(
                screen, (25, 30, 35), rect, 1, border_radius=5
            )

    def draw_panel():
        panel_x = 18
        pygame.draw.rect(
            screen, COLORS["panel"], (panel_x, 16, 370, 280),
            border_radius=10
        )

        draw_text(
            "TRAFFIC MANAGEMENT SIMULATOR",
            32, 28, selected_font=small
        )
        draw_text(f"Vehicles active: {len(sim.vehicles)}", 32, 55)
        draw_text(f"Vehicles generated: {metrics.spawned}", 32, 82)
        draw_text(
            f"Throughput: {metrics.throughput_per_minute:.2f} vehicles/min",
            32, 109
        )
        draw_text(f"Queue length: {sim.queue_length()}", 32, 136)
        draw_text(
            f"Average wait: {metrics.average_wait_seconds:.1f} s",
            32, 163
        )

        density = sim.traffic_density()
        draw_text("TRAFFIC DENSITY (vehicles/km)", 32, 190, selected_font=small)
        draw_text(
            f"N: {density['N']:.1f}   S: {density['S']:.1f}",
            32, 211, selected_font=small
        )
        draw_text(
            f"E: {density['E']:.1f}   W: {density['W']:.1f}",
            32, 233, selected_font=small
        )
        draw_text(
            f"Visual update rate: {fps:.1f} FPS",
            32, 260, selected_font=small
        )

        draw_text("EVENT LOG", width-312, 28, selected_font=small)

        for i, entry in enumerate(events[:6]):
            draw_text(
                entry, width-312, 53+i*21,
                COLORS["muted"], small
            )

        phase = signals.phase.replace("_", " ")
        pygame.draw.rect(
            screen, COLORS["panel"],
            (18, height-72, 550, 54), border_radius=9
        )
        draw_text(f"Signal phase: {phase}", 32, height-62)
        draw_text(
            f"{engine.state}   |   Spawn interval: {sim.spawn_interval:.2f}s"
            f"   |   t = {engine.clock:.1f}s",
            32, height-35, COLORS["muted"], small
        )
        draw_text(
            "SPACE: pause   N: step   R: reset   P: report   UP/DOWN: traffic rate   ESC: quit",
            width-700, height-48, COLORS["text"], small
        )

    running = True

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        fps = clock.get_fps()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_SPACE:
                    engine.toggle_pause()

                elif event.key == pygame.K_n:
                    engine.step()

                elif event.key == pygame.K_r:
                    engine.reset()

                elif event.key == pygame.K_p:
                    try:
                        report_path = save_summary_report(engine, REPORT_DIR)
                        log(f"Summary report saved: {report_path.name}")
                    except (OSError, ValueError) as exc:
                        log(f"Report generation failed: {exc}")

                elif event.key == pygame.K_UP:
                    value = engine.set_spawn_interval(sim.spawn_interval - 0.15)
                    log(f"Traffic rate increased ({value:.2f}s interval)")

                elif event.key == pygame.K_DOWN:
                    value = engine.set_spawn_interval(sim.spawn_interval + 0.15)
                    log(f"Traffic rate decreased ({value:.2f}s interval)")

        engine.tick(dt)
        draw_road()
        draw_vehicles()
        draw_signals()
        draw_panel()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run_app()
