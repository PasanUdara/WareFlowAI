# SOP-BAT-004: Battery Management & Charging Station Protocols

## 1. Operating Thresholds
- **Optimal Range**: 40% - 100% state-of-charge.
- **Low Battery Advisory**: Below 30% — robot should complete current task and queue for charging.
- **Critical Battery Threshold**: Below 15% — robot must reject new tasks, pause non-critical workloads, and autonomously return to the nearest available charging dock.
- **Emergency Depletion**: Below 5% — robot initiates immediate safe stop to preserve battery chemistry.

## 2. Charging Dock Queue Management
- Dock occupancy must be tracked dynamically.
- When all charging bays are occupied, robots below 20% battery must be prioritized over scheduled routine top-ups.
