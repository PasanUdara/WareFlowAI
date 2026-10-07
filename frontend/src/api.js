const API_BASE = 'http://localhost:8000';

export function getAuthToken() {
  return localStorage.getItem('wareflow_token') || '';
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('wareflow_token', token);
  } else {
    localStorage.removeItem('wareflow_token');
  }
}

export function clearAuthToken() {
  localStorage.removeItem('wareflow_token');
}

function getHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse(response) {
  if (response.status === 401) {
    clearAuthToken();
    window.dispatchEvent(new Event('wareflow_unauthorized'));
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Authentication token expired. Please log in again.');
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP Error ${response.status}`);
  }

  return response.json();
}

export async function loginUser(username, password) {
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });

  const data = await handleResponse(response);
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

export async function fetchFleetStatus() {
  const response = await fetch(`${API_BASE}/api/v1/fleet/status`, {
    headers: getHeaders()
  });
  return handleResponse(response);
}

export async function fetchFleetRobots() {
  const response = await fetch(`${API_BASE}/api/v1/fleet/robots`, {
    headers: getHeaders()
  });
  return handleResponse(response);
}

export async function createRobot(robotData) {
  const response = await fetch(`${API_BASE}/api/v1/fleet/robots`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(robotData)
  });
  return handleResponse(response);
}

export async function disableRobot(robotId) {
  const response = await fetch(`${API_BASE}/api/v1/fleet/robots/${robotId}/disable`, {
    method: 'POST',
    headers: getHeaders()
  });
  return handleResponse(response);
}

export async function enableRobot(robotId) {
  const response = await fetch(`${API_BASE}/api/v1/fleet/robots/${robotId}/enable`, {
    method: 'POST',
    headers: getHeaders()
  });
  return handleResponse(response);
}

export async function dispatchOrder(payload) {
  const response = await fetch(`${API_BASE}/api/v1/orders/dispatch`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload)
  });
  return handleResponse(response);
}

export async function triggerEmergencyStop(resume = false) {
  const endpoint = resume ? '/api/v1/simulation/resume' : '/api/v1/simulation/e-stop?resume=false';
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: getHeaders()
  });
  return handleResponse(response);
}

export async function checkCompliance(payload) {
  const params = new URLSearchParams({
    payload_weight: String(payload.payload_weight),
    speed: String(payload.speed),
    is_hazmat: String(Boolean(payload.is_hazmat)),
    target_zone: payload.target_zone || 'General'
  });
  const response = await fetch(`${API_BASE}/api/v1/compliance/verify?${params.toString()}`, {
    headers: getHeaders()
  });
  return handleResponse(response);
}

export async function fetchEventHistory(limit = 30) {
  const response = await fetch(`${API_BASE}/api/v1/events/history?limit=${limit}`, {
    headers: getHeaders()
  });
  return handleResponse(response);
}
