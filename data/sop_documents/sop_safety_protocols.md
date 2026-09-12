# SOP-SAF-001: Warehouse General Safety & Emergency Protocols

## 1. Purpose & Scope
This Standard Operating Procedure (SOP) defines emergency stop triggers, human-robot separation minimums, and zone lockdown conditions for autonomous mobile robots (AMRs).

## 2. Emergency Stop (E-Stop) Conditions
- Immediate emergency stop must be triggered upon any detected personnel within 1.0 meter of an active AMR route.
- All AMRs within the affected sector must transition to `STALLED` state within 200 milliseconds.
- Resumption of operations requires supervisor authorization through the supervisory dashboard.

## 3. Personnel Zones
- Pedestrian crosswalks (marked yellow on floor grids) enforce an AMR maximum speed of 0.5 m/s.
- Robots must yield right-of-way to human operators at all grid intersections.
