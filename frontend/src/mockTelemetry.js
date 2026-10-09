export const MOCK_FLEET = [
  { robot_id: 'R1', name: 'Atlas', x: 2, y: 10, state: 'MOVING', battery: 82, current_task: 'ORD-1042 · Pick A2', waypoints: [[3, 10], [3, 9], [3, 8], [3, 7]], destination: [3, 7], payload: 'Item-A' },
  { robot_id: 'R2', name: 'Nova', x: 7, y: 12, state: 'PICKING', battery: 64, current_task: 'ORD-1047 · Pick B1', waypoints: [[7, 11], [7, 10]], destination: [7, 10], payload: 'Carton' },
  {
    robot_id: 'R3',
    name: 'Orion',
    x: 11,
    y: 5,
    state: 'STUCK',
    battery: 38,
    current_task: 'ORD-1050 · Delivery',
    is_rerouted: true,
    original_path: [[11, 5], [11, 6], [11, 7], [11, 8]],
    detour_path: [[10, 5], [10, 6], [10, 7], [10, 8]],
    waypoints: [[10, 5], [10, 6], [10, 7], [10, 8]],
    destination: [10, 8]
  },
  { robot_id: 'R4', name: 'Lyra', x: 2, y: 14, state: 'CHARGING', battery: 23, current_task: null, waypoints: [], destination: [2, 14] }
];

export const MOCK_BLOCKED_CELLS = [[11, 6]];

