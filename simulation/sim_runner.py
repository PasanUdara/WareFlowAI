"""
Simulation Runner [Member 2]
Entry point to run the discrete simulation loop via CLI or optional Pygame window.
"""

import time
import sys
from .environment import WarehouseEnvironment


def run_cli_simulation(ticks: int = 10, interval_sec: float = 0.5):
    """Run discrete simulation ticks and print telemetry to stdout."""
    env = WarehouseEnvironment(width=20, height=15, num_robots=4)
    print("=" * 60)
    print("[WareFlow AI] Warehouse Simulation Initialized")
    print(f"Grid: {env.grid.width}x{env.grid.height} | Robots: {len(env.robots)}")
    print("=" * 60)
    
    for tick_idx in range(1, ticks + 1):
        anomalies = env.tick(delta_time=interval_sec)
        telemetry = env.get_fleet_telemetry()
        print(f"[Tick {tick_idx:02d}] Fleet status: {[r['robot_id'] + ':' + r['state'] + '(' + str(r['battery']) + '%)' for r in telemetry]}")
        if anomalies:
            print(f"  --> Anomalies detected: {anomalies}")
        time.sleep(0.05)


def run_pygame_simulation():
    """
    Launch Pygame graphical visualizer.
    
    # TODO: [Member 2] Implement Pygame window rendering AMR grid sprites and paths.
    """
    try:
        import pygame
        print("[WareFlow AI] Initializing Pygame warehouse visualizer...")
        pygame.init()
        # Placeholder Pygame window initialization
        # screen = pygame.display.set_mode((800, 600))
        # pygame.display.set_caption("WareFlow AI - Warehouse Floor")
        print("[WareFlow AI] Pygame visualizer placeholder ready.")
        pygame.quit()
    except ImportError:
        print("[WareFlow AI] Pygame not installed. Falling back to CLI mode.")
        run_cli_simulation()


if __name__ == "__main__":
    if "--gui" in sys.argv:
        run_pygame_simulation()
    else:
        run_cli_simulation()
