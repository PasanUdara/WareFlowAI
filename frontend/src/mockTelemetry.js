export const MOCK_FLEET = [
  {
    robot_id: 'R1',
    name: 'Atlas',
    x: 3,
    y: 10,
    state: 'MOVING',
    battery: 82,
    current_task: 'ORD-1042 · Pick A2',
    waypoints: [[3, 9], [3, 8], [3, 7], [3, 6], [3, 5], [3, 4]],
    destination: [3, 4],
    payload: 'Item-A'
  },
  {
    robot_id: 'R2',
    name: 'Nova',
    x: 8,
    y: 6,
    state: 'PICKING',
    battery: 64,
    current_task: 'ORD-1047 · Pick B1',
    waypoints: [[8, 5], [8, 4], [8, 3]],
    destination: [8, 3],
    payload: 'Carton'
  },
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
    detour_path: [
      [11, 4], [11, 3], [11, 2],
      [10, 2], [9, 2], [8, 2],
      [8, 3], [8, 4], [8, 5], [8, 6], [8, 7], [8, 8], [8, 9], [8, 10],
      [9, 10], [10, 10], [11, 10],
      [11, 9], [11, 8]
    ],
    waypoints: [
      [11, 4], [11, 3], [11, 2],
      [10, 2], [9, 2], [8, 2],
      [8, 3], [8, 4], [8, 5], [8, 6], [8, 7], [8, 8], [8, 9], [8, 10],
      [9, 10], [10, 10], [11, 10],
      [11, 9], [11, 8]
    ],
    destination: [11, 8]
  },
  {
    robot_id: 'R4',
    name: 'Lyra',
    x: 2,
    y: 13,
    state: 'CHARGING',
    battery: 23,
    current_task: null,
    waypoints: [],
    destination: [2, 13]
  }
];

export const MOCK_BLOCKED_CELLS = [[11, 6]];

