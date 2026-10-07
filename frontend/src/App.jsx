import { useEffect, useMemo, useState, useRef } from 'react';
import {
  checkCompliance,
  clearAuthToken,
  createRobot,
  disableRobot,
  dispatchOrder,
  enableRobot,
  fetchEventHistory,
  fetchFleetStatus,
  getAuthToken,
  loginUser,
  triggerEmergencyStop
} from './api';

const defaultOrder = 'Move 5 pallets from Shelf A2 to Packing Station 3.';

const PRESET_ORDERS = [
  { label: '📦 Standard Delivery', text: 'Move 5 pallets from Shelf A2 to Packing Station 3.' },
  { label: '⚠️ Hazmat Transfer', text: 'Transport 1 drum of solvent from Hazmat Aisle 4 to Station 2' },
  { label: '🏗️ Heavy Equipment', text: 'Move 2 heavy motor assemblies (24kg) from Receiving to Shelf B1' },
  { label: '❓ Ambiguous Order', text: 'Bring the blue box from somewhere over there' }
];

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(localStorage.getItem('wareflow_user') || 'admin');
  const [activeTab, setActiveTab] = useState('overview');

  // Login Form State
  const [loginUsername, setLoginUsername] = useState('admin');
  const [loginPassword, setLoginPassword] = useState('admin123');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Dashboard Data State
  const [fleet, setFleet] = useState([]);
  const [emergencyStop, setEmergencyStop] = useState(false);
  const [selectedRobotId, setSelectedRobotId] = useState('R1');
  const [globalError, setGlobalError] = useState('');
  const [wsStatus, setWsStatus] = useState('Disconnected');

  // Task Planner State
  const [orderText, setOrderText] = useState(defaultOrder);
  const [plan, setPlan] = useState(null);
  const [planning, setPlanning] = useState(false);

  // Add Robot Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRobot, setNewRobot] = useState({
    robot_id: '',
    name: '',
    model: 'AMR',
    capabilities: 'transport, pallet',
    x: 0,
    y: 0
  });

  // Compliance Form State
  const [complianceForm, setComplianceForm] = useState({
    payload_weight: 15.0,
    speed: 1.2,
    is_hazmat: false,
    target_zone: 'Zone-A'
  });
  const [complianceResult, setComplianceResult] = useState(null);

  // Agent Event Log Stream
  const [activityLogs, setActivityLogs] = useState([]);
  const wsRef = useRef(null);

  // ---------------------------------------------------------------------------
  // Authentication & Unauthorized Event Listener
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const handleUnauthorized = () => {
      setIsAuthenticated(false);
      clearAuthToken();
      setLoginError('Session expired. Please log in with demo credentials.');
    };
    window.addEventListener('wareflow_unauthorized', handleUnauthorized);
    return () => window.removeEventListener('wareflow_unauthorized', handleUnauthorized);
  }, []);

  // ---------------------------------------------------------------------------
  // Real-Time WebSocket Telemetry Subscription
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!isAuthenticated) return;

    let socket;
    let isSubscribed = true;

    const connectWebSocket = () => {
      try {
        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/telemetry';
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (isSubscribed) setWsStatus('Connected');
        };

        socket.onmessage = (event) => {
          if (!isSubscribed) return;
          try {
            const data = JSON.parse(event.data);
            if (data.robots) {
              setFleet(data.robots);
              if (data.emergency_stopped !== undefined) {
                setEmergencyStop(Boolean(data.emergency_stopped));
              }
            }
          } catch (err) {
            console.error('WebSocket parse error:', err);
          }
        };

        socket.onerror = () => {
          if (isSubscribed) setWsStatus('Connecting...');
        };

        socket.onclose = () => {
          if (isSubscribed) {
            setWsStatus('Reconnecting...');
            setTimeout(connectWebSocket, 3000);
          }
        };
      } catch (err) {
        if (isSubscribed) setWsStatus('Connection Failed');
      }
    };

    connectWebSocket();

    // Initial HTTP fetch
    loadFleetData();
    loadEventHistory();

    return () => {
      isSubscribed = false;
      if (socket) socket.close();
    };
  }, [isAuthenticated]);

  const loadFleetData = async () => {
    try {
      const data = await fetchFleetStatus();
      setFleet(data.robots || []);
      setEmergencyStop(Boolean(data.emergency_stop));
    } catch (err) {
      // Handled by 401 interceptor or error display
    }
  };

  const loadEventHistory = async () => {
    try {
      const data = await fetchEventHistory(25);
      if (data.events) {
        const formatted = data.events.map((e) => ({
          time: new Date(e.timestamp).toLocaleTimeString(),
          source: e.source,
          type: e.event_type,
          summary: `${e.source} ➔ ${e.destination}: ${JSON.stringify(e.payload).substring(0, 40)}`
        }));
        setActivityLogs(formatted);
      }
    } catch (err) {
      // Silent catch for initial log load
    }
  };

  // ---------------------------------------------------------------------------
  // Computed Summaries
  // ---------------------------------------------------------------------------
  const fleetSummary = useMemo(() => {
    const total = fleet.length || 4;
    const moving = fleet.filter((r) => String(r.state).toUpperCase() === 'MOVING').length;
    const charging = fleet.filter((r) => String(r.state).toUpperCase() === 'CHARGING').length;
    const attention = fleet.filter(
      (r) => Number(r.battery) < 25 || ['ERROR', 'STUCK'].includes(String(r.state).toUpperCase()) || r.enabled === false
    ).length;
    const avgBattery = total ? Math.round(fleet.reduce((sum, r) => sum + Number(r.battery || 0), 0) / total) : 100;
    return { total, moving, charging, attention, avgBattery };
  }, [fleet]);

  const selectedRobot = useMemo(() => {
    return fleet.find((r) => r.robot_id === selectedRobotId) || fleet[0] || null;
  }, [fleet, selectedRobotId]);

  // ---------------------------------------------------------------------------
  // Event Handlers
  // ---------------------------------------------------------------------------
  const handleLogin = async (e, customUser, customPass) => {
    if (e) e.preventDefault();
    const userToLogin = customUser || loginUsername;
    const passToLogin = customPass || loginPassword;

    if (!userToLogin.trim() || !passToLogin.trim()) {
      setLoginError('Please provide both username and password.');
      return;
    }
    setLoginLoading(true);
    setLoginError('');

    try {
      const data = await loginUser(userToLogin.trim(), passToLogin.trim());
      setIsAuthenticated(true);
      setCurrentUser(data.username);
      localStorage.setItem('wareflow_user', data.username);
      setGlobalError('');
    } catch (err) {
      setLoginError(err.message || 'Invalid username or password.');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    clearAuthToken();
    localStorage.removeItem('wareflow_user');
    setIsAuthenticated(false);
  };

  const handleDispatchOrder = async (e) => {
    if (e) e.preventDefault();
    if (!orderText.trim()) return;

    setPlanning(true);
    setGlobalError('');
    setPlan(null);

    try {
      const result = await dispatchOrder({ order_text: orderText.trim() });
      setPlan(result);
      if (result.assigned_robot_id) {
        setSelectedRobotId(result.assigned_robot_id);
      }
      addActivityLog('Gateway', 'ORDER_DISPATCH', `Dispatched: "${orderText.substring(0, 30)}..."`);
      await loadEventHistory();
    } catch (err) {
      setGlobalError(err.message || 'Task Planning agent could not execute request.');
    } finally {
      setPlanning(false);
    }
  };

  const handleToggleEmergencyStop = async (resume = false) => {
    const actionName = resume ? 'Resume Fleet Movement' : 'Global Emergency Stop';
    if (!window.confirm(`Are you sure you want to trigger: ${actionName}?`)) {
      return;
    }

    try {
      const result = await triggerEmergencyStop(resume);
      setEmergencyStop(Boolean(result.emergency_stop));
      addActivityLog('Gateway', resume ? 'SYSTEM_RESUMED' : 'EMERGENCY_STOP', result.message);
      await loadFleetData();
    } catch (err) {
      setGlobalError(err.message || 'Emergency control request failed.');
    }
  };

  const handleCreateRobot = async (e) => {
    e.preventDefault();
    if (!newRobot.robot_id.trim()) {
      alert('Robot ID is required.');
      return;
    }

    try {
      const capabilities = newRobot.capabilities.split(',').map((c) => c.trim()).filter(Boolean);
      await createRobot({
        robot_id: newRobot.robot_id.trim().toUpperCase(),
        name: newRobot.name.trim() || `Warehouse Robot ${newRobot.robot_id}`,
        model: newRobot.model,
        capabilities,
        initial_position: [Number(newRobot.x), Number(newRobot.y)]
      });

      setShowAddModal(false);
      setNewRobot({ robot_id: '', name: '', model: 'AMR', capabilities: 'transport, pallet', x: 0, y: 0 });
      addActivityLog('FleetManager', 'ROBOT_CREATED', `Registered new unit ${newRobot.robot_id}`);
      await loadFleetData();
    } catch (err) {
      alert(err.message || 'Failed to create robot.');
    }
  };

  const handleToggleRobotState = async (robotId, currentlyEnabled) => {
    try {
      if (currentlyEnabled) {
        await disableRobot(robotId);
        addActivityLog('FleetManager', 'ROBOT_DISABLED', `Disabled unit ${robotId}`);
      } else {
        await enableRobot(robotId);
        addActivityLog('FleetManager', 'ROBOT_ENABLED', `Enabled unit ${robotId}`);
      }
      await loadFleetData();
    } catch (err) {
      setGlobalError(err.message || 'Failed to toggle robot status.');
    }
  };

  const handleCheckCompliance = async (e) => {
    e.preventDefault();
    setGlobalError('');
    try {
      const res = await checkCompliance(complianceForm);
      setComplianceResult(res);
      addActivityLog('ComplianceAgent', res.is_compliant ? 'COMPLIANCE_APPROVED' : 'COMPLIANCE_REJECTED', `Zone: ${complianceForm.target_zone}`);
    } catch (err) {
      setGlobalError(err.message || 'Compliance verification unavailable.');
    }
  };

  const addActivityLog = (source, type, summary) => {
    const newEntry = {
      time: new Date().toLocaleTimeString(),
      source,
      type,
      summary
    };
    setActivityLogs((prev) => [newEntry, ...prev.slice(0, 24)]);
  };

  // ---------------------------------------------------------------------------
  // 1. LOGIN SCREEN (Unauthenticated View)
  // ---------------------------------------------------------------------------
  if (!isAuthenticated) {
    return (
      <div className="login-screen">
        <div className="login-card card">
          <div className="login-brand">
            <div className="brand-mark">WF</div>
            <h2>WareFlow AI</h2>
            <p>Autonomous Warehouse AMR Control Center</p>
          </div>

          {loginError && (
            <div className="notice error">
              {loginError}
            </div>
          )}

          <form onSubmit={handleLogin} className="login-form">
            <label>
              Username
              <input
                type="text"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                placeholder="admin or operator"
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="admin123 or operator123"
                required
              />
            </label>

            <button type="submit" className="glow-button full-width" disabled={loginLoading}>
              {loginLoading ? 'Authenticating...' : 'Sign In to Command Center →'}
            </button>
          </form>

          <div className="demo-credentials-box">
            <small>💡 Quick Demo Credentials:</small>
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button
                type="button"
                className="secondary-button"
                style={{ flex: 1, fontSize: '11px', padding: '6px' }}
                onClick={() => handleLogin(null, 'admin', 'admin123')}
              >
                Login as Admin (admin / admin123)
              </button>
              <button
                type="button"
                className="secondary-button"
                style={{ flex: 1, fontSize: '11px', padding: '6px' }}
                onClick={() => handleLogin(null, 'operator', 'operator123')}
              >
                Login as Operator (operator / operator123)
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 2. DASHBOARD VIEW (Authenticated Shell)
  // ---------------------------------------------------------------------------
  return (
    <div className="app-shell">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">WF</div>
          <div>
            <strong>WareFlow AI</strong>
            <span>AMR ORCHESTRATOR</span>
          </div>
        </div>

        <nav className="nav-list">
          <button className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
            <i>⌂</i> Overview
          </button>
          <button className={`nav-item ${activeTab === 'planning' ? 'active' : ''}`} onClick={() => setActiveTab('planning')}>
            <i>✦</i> Task Planner <small className="badge-member">M1</small>
          </button>
          <button className={`nav-item ${activeTab === 'fleet' ? 'active' : ''}`} onClick={() => setActiveTab('fleet')}>
            <i>◉</i> Fleet Command <small className="badge-member">M2/M4</small>
          </button>
          <button className={`nav-item ${activeTab === 'compliance' ? 'active' : ''}`} onClick={() => setActiveTab('compliance')}>
            <i>✓</i> Compliance RAG <small className="badge-member">M3</small>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile">
            <span>👤 User: <strong>{currentUser}</strong></span>
            <button className="text-button" onClick={handleLogout}>Sign Out</button>
          </div>
          <div className="system-status-indicator">
            <span className={`pulse-dot ${emergencyStop ? 'critical' : 'healthy'}`} />
            WS: {wsStatus}
          </div>
        </div>
      </aside>

      {/* WORKSPACE */}
      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="overline">Operations / <span className="tab-highlight">{activeTab.toUpperCase()}</span></p>
            <h1>Warehouse Command Center</h1>
          </div>

          <div className="header-actions">
            <button className="icon-button" onClick={loadFleetData} title="Refresh Telemetry">↻</button>
            <button className="icon-button" onClick={handleLogout} title="Sign Out / Switch User">🔒</button>
            <span className={`system-badge ${emergencyStop ? 'critical' : 'online'}`}>
              <b /> {emergencyStop ? 'EMERGENCY STOPPED' : 'FLEET ONLINE'}
            </span>
            {emergencyStop ? (
              <button onClick={() => handleToggleEmergencyStop(true)} className="stop-button resume">
                ▶ Resume Fleet
              </button>
            ) : (
              <button onClick={() => handleToggleEmergencyStop(false)} className="stop-button stop">
                🛑 EMERGENCY STOP
              </button>
            )}
          </div>
        </header>

        {globalError && (
          <div className="notice warning-notice">
            <span>⚠️ {globalError}</span>
            <button onClick={() => setGlobalError('')}>×</button>
          </div>
        )}

        {/* METRICS STRIP */}
        <section className="metric-grid">
          <div className="metric cyan">
            <div className="metric-icon">🤖</div>
            <div>
              <span>Fleet Online</span>
              <strong>{fleetSummary.total} AMRs</strong>
              <small>Connected to Grid</small>
            </div>
          </div>
          <div className="metric violet">
            <div className="metric-icon">↗</div>
            <div>
              <span>Active Tasks</span>
              <strong>{fleetSummary.moving} Moving</strong>
              <small>{fleetSummary.charging} Charging</small>
            </div>
          </div>
          <div className="metric lime">
            <div className="metric-icon">⚡</div>
            <div>
              <span>Average Battery</span>
              <strong>{fleetSummary.avgBattery}%</strong>
              <small>Fleet Charge Level</small>
            </div>
          </div>
          <div className="metric orange">
            <div className="metric-icon">⚠️</div>
            <div>
              <span>Alerts / Disabled</span>
              <strong>{fleetSummary.attention} Units</strong>
              <small>Needs Attention</small>
            </div>
          </div>
        </section>

        {/* TAB 1: OVERVIEW & MAP */}
        {activeTab === 'overview' && (
          <div className="tab-view fade-in">
            <div className="dashboard-grid">
              {/* 2D Grid Map */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <p className="overline">LIVE TELEMETRY MAP (20x15)</p>
                    <h3>2D Warehouse Grid Telemetry</h3>
                  </div>
                  <div className="map-legend">
                    <span><b className="dot cyan" /> IDLE</span>
                    <span><b className="dot violet" /> MOVING</span>
                    <span><b className="dot orange" /> ATTENTION</span>
                  </div>
                </div>

                <div className="warehouse-grid-large">
                  {Array.from({ length: 300 }, (_, index) => {
                    const x = index % 20;
                    const y = Math.floor(index / 20);
                    const robot = fleet.find((r) => {
                      const rx = r.x ?? r.position?.[0];
                      const ry = r.y ?? r.position?.[1];
                      return Number(rx) === x && Number(ry) === y;
                    });
                    const isSelected = robot && robot.robot_id === selectedRobotId;

                    return (
                      <div className={`grid-square ${isSelected ? 'selected-square' : ''}`} key={index}>
                        {robot && (
                          <button
                            className={`robot-pin ${String(robot.state).toLowerCase()} ${robot.enabled === false ? 'disabled' : ''}`}
                            onClick={() => setSelectedRobotId(robot.robot_id)}
                            title={`${robot.robot_id} (${robot.name}) - ${robot.state}`}
                          >
                            {robot.robot_id}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Selected AMR Detail */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <p className="overline">SELECTED AMR INSPECTOR</p>
                    <h3>{selectedRobot?.robot_id || 'Select a Robot'}</h3>
                  </div>
                </div>

                {selectedRobot ? (
                  <div className="robot-inspector-card">
                    <div className="inspector-head">
                      <div className="amr-icon">🤖</div>
                      <div>
                        <h4>{selectedRobot.name || selectedRobot.robot_id}</h4>
                        <span className={`state-tag ${String(selectedRobot.state).toLowerCase()}`}>
                          {selectedRobot.state}
                        </span>
                      </div>
                    </div>

                    <div className="telemetry-rows">
                      <div className="t-row"><span>Robot ID</span><strong>{selectedRobot.robot_id}</strong></div>
                      <div className="t-row"><span>Position</span><strong>X: {selectedRobot.x ?? selectedRobot.position?.[0]}, Y: {selectedRobot.y ?? selectedRobot.position?.[1]}</strong></div>
                      <div className="t-row"><span>Battery Level</span><strong>{selectedRobot.battery}%</strong></div>
                      <div className="t-row"><span>Current Task</span><strong>{selectedRobot.current_task || 'None (Idle)'}</strong></div>
                      <div className="t-row"><span>Operational Status</span><strong>{selectedRobot.enabled !== false ? 'Enabled' : 'Disabled'}</strong></div>
                    </div>

                    <button
                      className={`secondary-button full-width ${selectedRobot.enabled !== false ? 'stop' : 'resume'}`}
                      onClick={() => handleToggleRobotState(selectedRobot.robot_id, selectedRobot.enabled !== false)}
                    >
                      {selectedRobot.enabled !== false ? 'Disable Robot' : 'Enable Robot'}
                    </button>
                  </div>
                ) : (
                  <p className="overline">Click a robot on the grid to inspect details.</p>
                )}
              </div>
            </div>

            {/* Agent Activity / Event Log Stream */}
            <div className="card margin-top">
              <div className="card-header">
                <div>
                  <p className="overline">INTER-AGENT PROTOCOL BUS</p>
                  <h3>Real-time Agent Activity Stream</h3>
                </div>
                <button className="text-button" onClick={loadEventHistory}>Refresh Logs</button>
              </div>

              <div className="event-log-container">
                {activityLogs.map((log, idx) => (
                  <div key={idx} className="log-row">
                    <span className="log-time">{log.time}</span>
                    <span className="log-route">{log.source}</span>
                    <span className="log-event">{log.type}</span>
                    <span className="log-payload">{log.summary}</span>
                  </div>
                ))}
                {!activityLogs.length && <div className="overline">Listening to EventBus events...</div>}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: TASK PLANNER */}
        {activeTab === 'planning' && (
          <div className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Member 1 Agent</span>
              <h2>Task Planning Agent — LangGraph Ingestion</h2>
              <p>Parses natural language commands, splits subtasks, and assigns available AMRs.</p>
            </div>

            <div className="planner-workspace">
              <div className="card">
                <p className="overline">NATURAL LANGUAGE OPERATION DISPATCH</p>
                <div className="preset-chips">
                  {PRESET_ORDERS.map((p, i) => (
                    <button key={i} className="chip" onClick={() => setOrderText(p.text)}>
                      {p.label}
                    </button>
                  ))}
                </div>

                <form onSubmit={handleDispatchOrder}>
                  <textarea
                    rows={4}
                    value={orderText}
                    onChange={(e) => setOrderText(e.target.value)}
                    placeholder="e.g. Move 5 pallets from Shelf A2 to Packing Station 3."
                    className="order-input"
                  />
                  <div className="planner-submit-bar">
                    <span className="char-count">{orderText.length}/500 chars</span>
                    <button type="submit" className="glow-button" disabled={planning}>
                      {planning ? 'Running LangGraph Planner...' : '⚡ Dispatch Task'}
                    </button>
                  </div>
                </form>
              </div>

              {plan && (
                <div className={`card plan-result-card ${plan.status === 'assigned' ? 'success-border' : 'warning-border'}`}>
                  <div className="plan-header">
                    <span className="status-pill-lg">{plan.status?.toUpperCase()}</span>
                    <h3>{plan.status === 'assigned' ? 'Task Dispatched & Assigned' : 'Requires Review'}</h3>
                  </div>

                  {plan.parsed_order && (
                    <div className="parsed-entities">
                      <div className="entity"><span>Item:</span> <strong>{plan.parsed_order.item || 'Cartons'}</strong></div>
                      <div className="entity"><span>Qty:</span> <strong>{plan.parsed_order.quantity || 1}</strong></div>
                      <div className="entity"><span>Route:</span> <strong>{plan.parsed_order.source} ➔ {plan.parsed_order.destination}</strong></div>
                      <div className="entity"><span>Assigned AMR:</span> <strong className="highlight-amr">{plan.assigned_robot_id || 'None'}</strong></div>
                    </div>
                  )}

                  {plan.subtasks && (
                    <div className="subtask-timeline">
                      <p className="overline">DECOMPOSED SUBTASKS</p>
                      {plan.subtasks.map((st, i) => (
                        <div key={i} className="subtask-row">
                          <span className="step-num">{i + 1}</span>
                          <span className="action-tag">{st.action}</span>
                          <div className="task-desc">
                            <strong>{st.target || st.item || 'Step'}</strong>
                            <small>{st.description}</small>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: FLEET MANAGEMENT */}
        {activeTab === 'fleet' && (
          <div className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Member 4 Integration</span>
              <h2>Robot & Fleet Management Console</h2>
              <p>Add new AMRs, manage capabilities, and enable/disable fleet units safely.</p>
            </div>

            <div className="card">
              <div className="card-header">
                <div>
                  <p className="overline">REGISTERED AMRs</p>
                  <h3>Fleet Control Table</h3>
                </div>
                <button className="glow-button" onClick={() => setShowAddModal(true)}>+ Add Robot</button>
              </div>

              <div className="table-wrap">
                <table className="fleet-table">
                  <thead>
                    <tr>
                      <th>ROBOT ID</th>
                      <th>NAME</th>
                      <th>STATUS</th>
                      <th>BATTERY</th>
                      <th>POSITION</th>
                      <th>CURRENT TASK</th>
                      <th>CAPABILITIES</th>
                      <th>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fleet.map((r) => (
                      <tr key={r.robot_id} className={selectedRobotId === r.robot_id ? 'active-row' : ''}>
                        <td><strong>{r.robot_id}</strong></td>
                        <td>{r.name || `Robot ${r.robot_id}`}</td>
                        <td><span className={`state-badge ${String(r.state).toLowerCase()}`}>{r.state}</span></td>
                        <td>
                          <div className="battery-cell">
                            <div className="battery-mini"><i style={{ width: `${r.battery}%` }} /></div>
                            {r.battery}%
                          </div>
                        </td>
                        <td>[{r.x ?? r.position?.[0]}, {r.y ?? r.position?.[1]}]</td>
                        <td>{r.current_task || 'None'}</td>
                        <td><small>{r.capabilities ? r.capabilities.join(', ') : 'transport, pallet'}</small></td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => handleToggleRobotState(r.robot_id, r.enabled !== false)}
                          >
                            {r.enabled !== false ? 'Disable' : 'Enable'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: COMPLIANCE */}
        {activeTab === 'compliance' && (
          <div className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Member 3 RAG Agent</span>
              <h2>Knowledge & SOP Compliance Gate</h2>
              <p>Validates mission metrics against ingested Qdrant vector database rules.</p>
            </div>

            <div className="dashboard-grid">
              <div className="card">
                <form onSubmit={handleCheckCompliance} className="compliance-form">
                  <div className="form-row">
                    <label>
                      Payload Weight (kg)
                      <input
                        type="number"
                        value={complianceForm.payload_weight}
                        onChange={(e) => setComplianceForm({ ...complianceForm, payload_weight: Number(e.target.value) })}
                      />
                    </label>
                    <label>
                      Speed (m/s)
                      <input
                        type="number"
                        step="0.1"
                        value={complianceForm.speed}
                        onChange={(e) => setComplianceForm({ ...complianceForm, speed: Number(e.target.value) })}
                      />
                    </label>
                  </div>

                  <label className="input-label">
                    Target Zone
                    <input
                      type="text"
                      value={complianceForm.target_zone}
                      onChange={(e) => setComplianceForm({ ...complianceForm, target_zone: e.target.value })}
                    />
                  </label>

                  <label className="checkbox-line">
                    <input
                      type="checkbox"
                      checked={complianceForm.is_hazmat}
                      onChange={(e) => setComplianceForm({ ...complianceForm, is_hazmat: e.target.checked })}
                    />
                    Hazardous Material Payload
                  </label>

                  <button type="submit" className="glow-button full-width">Verify Operation</button>
                </form>

                {complianceResult && (
                  <div className={`compliance-result-box ${complianceResult.is_compliant ? 'pass' : 'fail'}`}>
                    <h4>{complianceResult.is_compliant ? '✅ Approved' : '❌ Violations Detected'}</h4>
                    {complianceResult.violations?.map((v, i) => (
                      <div key={i}>• {v}</div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ADD ROBOT MODAL */}
        {showAddModal && (
          <div className="modal-overlay">
            <div className="modal-card card">
              <h3>Register New AMR Unit</h3>
              <form onSubmit={handleCreateRobot} className="modal-form">
                <label>
                  Robot ID *
                  <input
                    type="text"
                    placeholder="e.g. R5"
                    value={newRobot.robot_id}
                    onChange={(e) => setNewRobot({ ...newRobot, robot_id: e.target.value })}
                    required
                  />
                </label>
                <label>
                  Robot Name
                  <input
                    type="text"
                    placeholder="e.g. Warehouse Heavy Robot 5"
                    value={newRobot.name}
                    onChange={(e) => setNewRobot({ ...newRobot, name: e.target.value })}
                  />
                </label>
                <div className="form-row">
                  <label>
                    X Coordinate
                    <input
                      type="number"
                      value={newRobot.x}
                      onChange={(e) => setNewRobot({ ...newRobot, x: e.target.value })}
                    />
                  </label>
                  <label>
                    Y Coordinate
                    <input
                      type="number"
                      value={newRobot.y}
                      onChange={(e) => setNewRobot({ ...newRobot, y: e.target.value })}
                    />
                  </label>
                </div>
                <label>
                  Capabilities (comma-separated)
                  <input
                    type="text"
                    value={newRobot.capabilities}
                    onChange={(e) => setNewRobot({ ...newRobot, capabilities: e.target.value })}
                  />
                </label>
                <div className="modal-actions">
                  <button type="submit" className="glow-button">Register Unit</button>
                  <button type="button" className="secondary-button" onClick={() => setShowAddModal(false)}>Cancel</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
