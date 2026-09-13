const API_BASE = 'http://localhost:8000';

export async function fetchFleetStatus() {
  const response = await fetch(`${API_BASE}/api/v1/fleet/status`);
  if (!response.ok) {
    throw new Error('Failed to fetch fleet status');
  }
  return response.json();
}

export async function dispatchOrder(payload) {
  const response = await fetch(`${API_BASE}/api/v1/orders/dispatch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error('Failed to dispatch order');
  }

  return response.json();
}

export async function triggerEmergencyStop(resume = false) {
  const response = await fetch(`${API_BASE}/api/v1/simulation/e-stop?resume=${resume}`, {
    method: 'POST'
  });

  if (!response.ok) {
    throw new Error('Failed to update emergency stop');
  }

  return response.json();
}

export async function checkCompliance(payload) {
  const params = new URLSearchParams({
    payload_weight: String(payload.payload_weight),
    speed: String(payload.speed),
    is_hazmat: String(Boolean(payload.is_hazmat)),
    target_zone: payload.target_zone
  });

  const response = await fetch(`${API_BASE}/api/v1/compliance/verify?${params.toString()}`);

  if (!response.ok) {
    throw new Error('Failed to check compliance');
  }

  return response.json();
}
