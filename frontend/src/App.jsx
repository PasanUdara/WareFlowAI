import { useEffect, useMemo, useState, useRef } from 'react';
import { checkCompliance, dispatchOrder, fetchFleetStatus, getTelemetryWsUrl, triggerEmergencyStop } from './api';

const defaultOrder = 'Move 5 cartons of surgical gloves from Shelf-B2 to Packing-Station-3';

const ORDER_PRESETS = [
  {
    label: '📦 Medical Gloves (Standard)',
    text: 'Move 5 cartons of surgical gloves from Shelf-B2 to Packing-Station-3'
  },
  {
    label: '❄️ Cold-Chain Insulin (Urgent)',
    text: 'Transfer 12 vials of insulin from Cold-Storage-A to Dispatch-Bay-1'
  },
  {
    label: '⚠️ Biohazard Hazmat (Safety Gate)',
    text: 'Relocate 2 hazardous chemical containers from Chemical-Vault to Waste-Depot-4'
  },
  {
    label: '❓ Vague Order (Clarify Path)',
    text: 'Take the items from back there to somewhere near the front'
  }
];

// LangGraph node definitions — mirrors graph.py exactly
const GRAPH_NODES = [
  { id: 'start',           label: 'START',          type: 'terminal', icon: '▶', desc: 'Entry point of the Task Planning workflow.' },
  { id: 'parse_order',     label: 'Parse Order',    type: 'node',     icon: '⬡', desc: 'LLM extracts item, quantity, source & destination from free-text order.' },
  { id: 'decompose_tasks', label: 'Decompose Tasks', type: 'node',    icon: '⬡', desc: 'Splits the parsed order into atomic subtasks (navigate, pick, drop) for AMR.' },
  { id: 'assign_robot',    label: 'Assign Robot',   type: 'node',     icon: '⬡', desc: 'Picks best available AMR from live fleet based on battery & status.' },
  { id: 'clarify_order',   label: 'Clarify Order',  type: 'alt',      icon: '⬡', desc: 'Triggered when parsing fails — asks for a clearer order description.' },
  { id: 'escalate_to_human', label: 'Escalate',     type: 'alt',      icon: '⬡', desc: 'No available robot found — escalates mission to a human supervisor.' },
  { id: 'end',             label: 'END',            type: 'terminal', icon: '■', desc: 'Workflow completion.' },
];

const HAPPY_PATH   = ['start', 'parse_order', 'decompose_tasks', 'assign_robot', 'end'];
const PARSE_FAIL   = ['start', 'parse_order', 'clarify_order', 'end'];
const ASSIGN_FAIL  = ['start', 'parse_order', 'decompose_tasks', 'assign_robot', 'escalate_to_human', 'end'];

const NODE_STEP_MAP = {
  start:           'Initializing task planning state…',
  parse_order:     'LLM parsing natural-language order…',
  decompose_tasks: 'Decomposing mission into atomic AMR subtasks…',
  assign_robot:    'Selecting highest-battery available AMR…',
  clarify_order:   'Ambiguous order — generating clarification prompt…',
  escalate_to_human: 'No eligible AMR online — escalating to supervisor…',
  end:             'Planning sequence complete.'
};

const STEP_DELAY_MS = 650;

function getPath(plan) {
  if (!plan) return [];
  if (plan.requires_escalation) return ASSIGN_FAIL;
  if (plan.status === 'clarification_needed' || plan.status === 'parse_failed') return PARSE_FAIL;
  return HAPPY_PATH;
}

// Layout coordinate helpers for Warehouse 20x15 Digital Twin
const CHARGING_DOCKS = new Set(['1,0', '2,0', '3,0', '4,0']);
const DROPOFF_BAYS   = new Set(['1,14', '2,14', '3,14', '4,14']);
const SHELF_COORDS   = new Set();
for (let y = 3; y <= 11; y++) {
  [4, 5, 8, 9, 12, 13, 16, 17].forEach(x => SHELF_COORDS.add(`${x},${y}`));
}

function App() {
  const [activeView, setActiveView]         = useState('agent');
  const [fleet, setFleet]                   = useState([]);
  const [emergencyStop, setEmergencyStop]   = useState(false);
  const [orderText, setOrderText]           = useState(defaultOrder);
  const [plan, setPlan]                     = useState(null);
  const [planning, setPlanning]             = useState(false);
  const [activeNodes, setActiveNodes]       = useState([]);
  const [currentStep, setCurrentStep]       = useState(null);
  const [error, setError]                   = useState('');
  const [selectedRobot, setSelectedRobot]   = useState(null);
  const [complianceForm, setComplianceForm] = useState({ payload_weight: 15, speed: 1.2, is_hazmat: false, target_zone: 'Zone-A' });
  const [complianceResult, setComplianceResult] = useState(null);
  const [isVerifying, setIsVerifying]       = useState(false);
  const [isStreaming, setIsStreaming]       = useState(false);
  const [tickCount, setTickCount]           = useState(0);

  const animTimer = useRef(null);
  const wsRef     = useRef(null);

  // 1. Initial Load & Live Telemetry WebSocket
  const loadFleet = async () => {
    try {
      const data = await fetchFleetStatus();
      setFleet(data.robots || []);
      setEmergencyStop(Boolean(data.emergency_stop));
      setSelectedRobot(cur => cur || data.robots?.[0]?.robot_id || null);
      setError('');
    } catch {
      setError('Unable to reach the fleet service. Make sure the API is running on port 8000.');
    }
  };

  useEffect(() => {
    loadFleet();

    // Establish real-time WebSocket connection to backend 2Hz telemetry stream
    let ws;
    try {
      const wsUrl = getTelemetryWsUrl();
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsStreaming(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event_type === 'TELEMETRY_TICK') {
            setFleet(payload.robots || []);
            setEmergencyStop(Boolean(payload.emergency_stopped));
            setTickCount(c => c + 1);
          }
        } catch {}
      };

      ws.onclose = () => {
        setIsStreaming(false);
      };

      ws.onerror = () => {
        setIsStreaming(false);
      };
    } catch {
      setIsStreaming(false);
    }

    // Polling fallback every 2.5s if WebSocket is not active
    const pollInterval = setInterval(() => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        fetchFleetStatus()
          .then(data => {
            setFleet(data.robots || []);
            setEmergencyStop(Boolean(data.emergency_stop));
            setTickCount(c => c + 1);
          })
          .catch(() => {});
      }
    }, 2500);

    return () => {
      clearInterval(pollInterval);
      if (ws) ws.close();
    };
  }, []);

  const summary = useMemo(() => {
    const total   = fleet.length;
    const moving  = fleet.filter(r => String(r.state).toUpperCase() === 'MOVING').length;
    const avgBat  = total ? Math.round(fleet.reduce((s, r) => s + Number(r.battery || 0), 0) / total) : 100;
    const attn    = fleet.filter(r => Number(r.battery) < 25 || String(r.state).toUpperCase() === 'ERROR').length;
    return { total: total || 4, moving, avgBat, attn };
  }, [fleet]);

  const selected = fleet.find(r => r.robot_id === selectedRobot) || fleet[0];

  // Animate nodes along the execution path with a delay between each step
  function animatePath(path, onDone) {
    clearTimeout(animTimer.current);
    setActiveNodes([]);
    setCurrentStep(null);
    let idx = 0;
    function step() {
      if (idx >= path.length) { onDone?.(); return; }
      const nodeId = path[idx];
      setActiveNodes(prev => [...prev, nodeId]);
      setCurrentStep(NODE_STEP_MAP[nodeId] || null);
      idx++;
      animTimer.current = setTimeout(step, STEP_DELAY_MS);
    }
    animTimer.current = setTimeout(step, 80);
  }

  async function handlePlan(e) {
    e?.preventDefault();
    if (!orderText.trim()) return;
    setPlanning(true);
    setError('');
    setPlan(null);
    setActiveNodes(['start']);
    setCurrentStep('Initialising agent workflow…');

    // Preliminary in-flight animation while waiting for LLM
    const inFlightPath = ['start', 'parse_order', 'decompose_tasks', 'assign_robot'];
    animatePath(inFlightPath, undefined);

    try {
      const result = await dispatchOrder({ order_text: orderText.trim() });
      const finalPath = getPath(result);
      animatePath(finalPath, () => {
        setCurrentStep(null);
        setPlanning(false);
        setPlan(result);
        if (result.assigned_robot_id) setSelectedRobot(result.assigned_robot_id);
      });
    } catch (err) {
      setError(err.message || 'Task Planning agent could not create a plan. Check backend service on port 8000.');
      setActiveNodes([]);
      setCurrentStep(null);
      setPlanning(false);
    }
  }

  async function handleEmergencyStop() {
    try {
      const nextState = !emergencyStop;
      const result = await triggerEmergencyStop(nextState);
      setEmergencyStop(Boolean(result.emergency_stop));
      await loadFleet();
    } catch {
      setError('Emergency control request failed.');
    }
  }

  async function handleCompliance(e) {
    e.preventDefault();
    setIsVerifying(true);
    setError('');
    try {
      const res = await checkCompliance(complianceForm);
      setComplianceResult(res);
    } catch {
      setError('Compliance verification is temporarily unavailable.');
    } finally {
      setIsVerifying(false);
    }
  }

  const navItems = [
    ['agent',      'Agent Visualizer', '✦'],
    ['fleet',      'Fleet Command',    '◉'],
    ['compliance', 'Compliance & SOP', '✓'],
    ['overview',   'Operations Center', '⌂'],
  ];

  return (
    <div className="app-shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">W</div>
          <div className="brand-text">
            <strong>WareFlow AI</strong>
            <span>Autonomous Logistics</span>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map(([id, label, icon]) => (
            <button
              key={id}
              onClick={() => setActiveView(id)}
              className={`nav-item ${activeView === id ? 'active' : ''}`}
            >
              <i>{icon}</i>{label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="pulse-dot" /> Live Orchestrator Connected<br />
          <small>LangGraph v0.2 · Multi-Agent</small>
        </div>
      </aside>

      {/* ── Main Workspace ── */}
      <main className="workspace">
        <header className="topbar">
          <div className="topbar-titles">
            <p className="overline">Operations / <span>{activeView}</span></p>
            <h1>Warehouse Command Center</h1>
          </div>
          <div className="header-actions">
            <div className="live-indicator" title="Simulation engine telemetry stream">
              <span className="pulse-dot" style={{ background: isStreaming ? '#34d399' : '#38bdf8' }} />
              {isStreaming ? 'STREAM 2Hz' : 'POLL ACTIVE'} · #{tickCount}
            </div>

            <button className="icon-button" onClick={loadFleet} title="Refresh fleet telemetry">
              ↻
            </button>

            <span className={`system-state ${emergencyStop ? 'critical' : ''}`}>
              <b /> {emergencyStop ? 'E-STOP ACTIVE' : 'SYSTEM ONLINE'}
            </span>

            <button
              onClick={handleEmergencyStop}
              className={`stop-button ${emergencyStop ? 'resume' : ''}`}
            >
              {emergencyStop ? '✓ Resume Fleet' : '⚠ Emergency Stop'}
            </button>
          </div>
        </header>

        {error && (
          <div className="notice error">
            <span>{error}</span>
            <button onClick={() => setError('')}>✕</button>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            VIEW: AGENT VISUALIZER (Default)
        ══════════════════════════════════════════════════════════════ */}
        {activeView === 'agent' && (
          <div className="agent-view">
            {/* Hero banner */}
            <section className="agent-hero">
              <div className="agent-hero-text">
                <p className="overline">LANGGRAPH · MULTI-AGENT TASK PLANNER</p>
                <h2>Agent Execution Visualizer</h2>
                <p>
                  Dispatch natural language warehouse directives and monitor the agent's internal
                  StateGraph execution in real time. Inspect entity extraction, task decomposition,
                  and fleet assignment with complete transparency.
                </p>
              </div>
              <div className="hero-ring">
                <div className={`hero-ring-core ${planning ? 'spinning' : ''}`}>AI</div>
                <span className="hero-ring-label">STATEGRAPH</span>
              </div>
            </section>

            {/* Two-column layout: graph + form */}
            <div className="agent-columns">
              {/* LEFT — LangGraph workflow diagram */}
              <div className="card graph-card">
                <div className="card-title">
                  <div>
                    <p className="overline">LANGGRAPH TOPOLOGY</p>
                    <h2>Workflow Execution Graph</h2>
                  </div>
                  <span className={`graph-status ${planning ? 'running' : plan ? (plan.status === 'assigned' ? 'done' : 'warn') : 'idle'}`}>
                    {planning ? 'Executing…' : plan ? plan.status || 'Complete' : 'Standby'}
                  </span>
                </div>

                <GraphDiagram activeNodes={activeNodes} />

                {currentStep && (
                  <div className="current-step">
                    <span className="step-blink">▶</span> {currentStep}
                  </div>
                )}
              </div>

              {/* RIGHT — Input form + live trace */}
              <div className="right-col">
                <div className="card planner-card">
                  <div className="card-title">
                    <div>
                      <p className="overline">OPERATION REQUEST</p>
                      <h2>Dispatch Natural Language Order</h2>
                    </div>
                  </div>

                  <form onSubmit={handlePlan}>
                    <label className="field-label" htmlFor="order-input">
                      Instruction prompt (LLM will parse items, locations & subtasks)
                    </label>
                    <textarea
                      id="order-input"
                      rows={3}
                      value={orderText}
                      onChange={e => setOrderText(e.target.value)}
                      maxLength={500}
                      placeholder="e.g. Move 5 cartons of surgical gloves from Shelf-B2 to Packing-Station-3"
                    />

                    {/* Quick Preset Chips */}
                    <div className="prompt-chips">
                      {ORDER_PRESETS.map((preset, idx) => (
                        <button
                          key={idx}
                          type="button"
                          className="chip-btn"
                          onClick={() => setOrderText(preset.text)}
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>

                    <div className="form-footer">
                      <span className="char-count">{orderText.length} / 500 chars</span>
                      <button className="glow-button" disabled={planning || !orderText.trim()}>
                        {planning ? 'Running Agent…' : 'Run Task Planner'} <b>→</b>
                      </button>
                    </div>
                  </form>
                </div>

                {/* Execution trace — appears once done */}
                {plan && <ExecutionTrace plan={plan} />}
              </div>
            </div>

            {/* Full-width result breakdown */}
            {plan && <PlanResult plan={plan} />}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            VIEW: FLEET COMMAND
        ══════════════════════════════════════════════════════════════ */}
        {activeView === 'fleet' && (
          <div>
            <section className="metric-grid">
              <Metric label="Fleet Online"     value={`${summary.total}/${summary.total}`} note="AMRs connected"    icon="◉" color="cyan"   />
              <Metric label="Tasks in Motion"  value={summary.moving}                      note="Active navigation" icon="↗" color="violet" />
              <Metric label="Average Battery"  value={`${summary.avgBat}%`}                note="Fleet health"      icon="⚡" color="lime"   />
              <Metric label="Attention Needed" value={summary.attn}                        note="Review required"   icon="!" color="orange" />
            </section>

            <div className="dashboard-grid">
              {/* 2D Interactive Digital Twin Map */}
              <div className="card fleet-map-card">
                <div className="card-title">
                  <div>
                    <p className="overline">2D DIGITAL TWIN · TELEMETRY GRID</p>
                    <h2>Warehouse Floor Map (20 × 15)</h2>
                  </div>
                  <button className="icon-button" onClick={loadFleet} title="Refresh coordinates">↻</button>
                </div>

                <div className="map-legend">
                  <span><b className="dot cyan" /> Idle / Ready</span>
                  <span><b className="dot violet" /> Moving</span>
                  <span><b className="dot emerald" /> Charging Docks (D1–D4)</span>
                  <span><b className="dot shelf" /> Storage Racks (A–D)</span>
                  <span><b className="dot orange" /> Attention / Error</span>
                </div>

                <div className="warehouse-map">
                  {Array.from({ length: 300 }, (_, i) => {
                    const x = i % 20;
                    const y = Math.floor(i / 20);
                    const coordKey = `${x},${y}`;

                    const isDock    = CHARGING_DOCKS.has(coordKey);
                    const isDropoff = DROPOFF_BAYS.has(coordKey);
                    const isShelf   = SHELF_COORDS.has(coordKey);

                    // Find robot at this coordinate (check both r.x/r.y and r.position)
                    const robot = fleet.find(r => {
                      const rx = r.x ?? r.position?.[0];
                      const ry = r.y ?? r.position?.[1];
                      return Number(rx) === x && Number(ry) === y;
                    });

                    let cellClass = 'grid-cell';
                    if (isDock) cellClass += ' cell-dock';
                    else if (isDropoff) cellClass += ' cell-dropoff';
                    else if (isShelf) cellClass += ' cell-shelf';

                    return (
                      <div className={cellClass} key={i} title={`Cell (${x}, ${y})`}>
                        {robot && (
                          <button
                            onClick={() => setSelectedRobot(robot.robot_id)}
                            className={`robot ${String(robot.state).toLowerCase()} ${selectedRobot === robot.robot_id ? 'selected' : ''}`}
                            title={`${robot.robot_id} · ${robot.state} · ${robot.battery}%`}
                          >
                            {robot.robot_id}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Selected AMR Detail Card */}
              <div className="card robot-card">
                <div className="card-title">
                  <div>
                    <p className="overline">AMR TELEMETRY</p>
                    <h2>Unit Telemetry Panel</h2>
                  </div>
                </div>

                <div className="robot-head">
                  <div className="robot-avatar">⌘</div>
                  <div>
                    <strong>{selected?.robot_id || 'AMR-01'}</strong>
                    <span className={`state-label ${String(selected?.state || 'idle').toLowerCase()}`}>
                      {selected?.state || 'IDLE'}
                    </span>
                  </div>
                </div>

                <div className="telemetry-list">
                  <div>
                    <span>Battery Status</span>
                    <strong>{selected ? `${selected.battery}%` : '100%'}</strong>
                  </div>
                  <div>
                    <span>Current Coordinates</span>
                    <strong>{selected ? `(${selected.x ?? selected.position?.[0] ?? 0}, ${selected.y ?? selected.position?.[1] ?? 0})` : '(0, 0)'}</strong>
                  </div>
                  <div>
                    <span>Speed Vector</span>
                    <strong>{selected?.speed_ms ? `${selected.speed_ms} m/s` : '1.0 m/s'}</strong>
                  </div>
                  <div>
                    <span>Mission Mode</span>
                    <strong>{emergencyStop ? 'Emergency Halt' : 'Autonomous'}</strong>
                  </div>
                  <div>
                    <span>Waypoints Left</span>
                    <strong>{selected?.waypoints_remaining ?? 0}</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* Fleet Status Table */}
            <div className="card">
              <div className="card-title">
                <div>
                  <p className="overline">LIVE FLEET REGISTRY</p>
                  <h2>AMR Operational Matrix</h2>
                </div>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>UNIT ID</th>
                      <th>STATE</th>
                      <th>BATTERY LEVEL</th>
                      <th>LOCATION (X, Y)</th>
                      <th>SPEED</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fleet.map(r => {
                      const bat = Number(r.battery || 0);
                      const batClass = bat > 50 ? 'high' : bat > 20 ? 'mid' : 'low';
                      const rx = r.x ?? r.position?.[0] ?? 0;
                      const ry = r.y ?? r.position?.[1] ?? 0;

                      return (
                        <tr
                          key={r.robot_id}
                          onClick={() => setSelectedRobot(r.robot_id)}
                          className={selectedRobot === r.robot_id ? 'selected-row' : ''}
                        >
                          <td><b>{r.robot_id}</b></td>
                          <td>
                            <span className={`table-state ${String(r.state).toLowerCase()}`}>
                              {r.state}
                            </span>
                          </td>
                          <td>
                            <div className="battery-gauge">
                              <div className="battery-bar">
                                <div
                                  className={`battery-bar-fill ${batClass}`}
                                  style={{ width: `${Math.min(100, bat)}%` }}
                                />
                              </div>
                              <span>{bat}%</span>
                            </div>
                          </td>
                          <td>({rx}, {ry})</td>
                          <td>{r.speed_ms || 1.0} m/s</td>
                        </tr>
                      );
                    })}
                    {!fleet.length && (
                      <tr>
                        <td colSpan={5} className="empty-state">
                          Connecting to fleet telemetry…
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            VIEW: COMPLIANCE & SAFETY GATE
        ══════════════════════════════════════════════════════════════ */}
        {activeView === 'compliance' && (
          <div className="compliance-container">
            <div className="card compliance-card">
              <div className="card-title">
                <div>
                  <p className="overline">SOP SAFETY GATE</p>
                  <h2>Compliance Verification Simulator</h2>
                </div>
              </div>

              <form onSubmit={handleCompliance}>
                <div className="field-row">
                  <div>
                    <label className="field-label">Payload Weight (kg)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={complianceForm.payload_weight}
                      onChange={e => setComplianceForm({ ...complianceForm, payload_weight: Number(e.target.value) })}
                    />
                  </div>
                  <div>
                    <label className="field-label">Speed Limit (m/s)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="3.0"
                      value={complianceForm.speed}
                      onChange={e => setComplianceForm({ ...complianceForm, speed: Number(e.target.value) })}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: 16 }}>
                  <label className="field-label">Target Zone</label>
                  <select
                    value={complianceForm.target_zone}
                    onChange={e => setComplianceForm({ ...complianceForm, target_zone: e.target.value })}
                  >
                    <option value="Zone-A">Zone-A (General Storage)</option>
                    <option value="Zone-B">Zone-B (Chemical Vault)</option>
                    <option value="Cold-Storage">Cold Storage Vault</option>
                    <option value="Packing-Bay">Packing & Conveyor Bay</option>
                  </select>
                </div>

                <label className="switch-line">
                  <input
                    type="checkbox"
                    checked={complianceForm.is_hazmat}
                    onChange={e => setComplianceForm({ ...complianceForm, is_hazmat: e.target.checked })}
                  />
                  <span>Hazardous Materials (HAZMAT safety constraints active)</span>
                </label>

                <button className="secondary-button" disabled={isVerifying}>
                  {isVerifying ? 'Checking RAG & Rules…' : 'Verify Operational Compliance'}
                </button>
              </form>

              {complianceResult && (
                <div className={`compliance-result-box ${complianceResult.is_compliant ? 'pass' : 'fail'}`}>
                  <strong>
                    {complianceResult.is_compliant ? '✓ Operation Approved by Safety Gate' : '✗ Compliance Violation Detected'}
                  </strong>
                  {complianceResult.violations?.length > 0 && (
                    <ul style={{ margin: '8px 0 0 16px', fontSize: 12 }}>
                      {complianceResult.violations.map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                    </ul>
                  )}
                  {complianceResult.sop_citations?.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <p style={{ fontSize: 11, color: '#cbd5e1' }}>Authoritative SOP Citations (Qdrant RAG):</p>
                      {complianceResult.sop_citations.map((cite, i) => (
                        <span key={i} className="sop-tag">📄 {cite}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* SOP Reference Guide Card */}
            <div className="card">
              <div className="card-title">
                <div>
                  <p className="overline">REGULATORY FRAMEWORK</p>
                  <h2>Active Warehouse SOP Guidelines</h2>
                </div>
              </div>

              <div className="trace-list">
                <div className="trace-row">
                  <span className="trace-idx">01</span>
                  <div>
                    <strong>SOP-HAZ-002: Hazmat Speed Throttling</strong>
                    <span>AMRs carrying hazardous cargo must never exceed 0.8 m/s under any circumstance.</span>
                  </div>
                </div>
                <div className="trace-row">
                  <span className="trace-idx">02</span>
                  <div>
                    <strong>SOP-WGT-004: Maximum Payload Constraint</strong>
                    <span>Payload weight cannot exceed 40.0 kg for standard AMRs to preserve stability.</span>
                  </div>
                </div>
                <div className="trace-row">
                  <span className="trace-idx">03</span>
                  <div>
                    <strong>SOP-SAF-001: Emergency Proximity Stop</strong>
                    <span>Instant halt triggered whenever personnel or obstruction is detected within 1.0m.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            VIEW: OPERATIONS OVERVIEW
        ══════════════════════════════════════════════════════════════ */}
        {activeView === 'overview' && (
          <div>
            <section className="hero">
              <div>
                <p className="overline">AI MULTI-AGENT ORCHESTRATION</p>
                <h2>One Unified Console. Every Warehouse Move.</h2>
                <p>
                  Direct your autonomous mobile robot fleet with conversational English. The Task Planning
                  LangGraph agent decomposes complex operations into deterministic, collision-safe actions.
                </p>
                <button className="glow-button" onClick={() => setActiveView('agent')}>
                  Open Agent Visualizer <span>→</span>
                </button>
              </div>

              <div className="hero-orbit">
                <div className="orbit-core">AI</div>
                <i className="orbit-node n1" />
                <i className="orbit-node n2" />
                <i className="orbit-node n3" />
              </div>
            </section>

            <section className="metric-grid">
              <Metric label="Fleet Online"     value={`${summary.total}/${summary.total}`} note="AMRs connected"    icon="◉" color="cyan"   />
              <Metric label="Tasks in Motion"  value={summary.moving}                      note="Active navigation" icon="↗" color="violet" />
              <Metric label="Average Battery"  value={`${summary.avgBat}%`}                note="Fleet health"      icon="⚡" color="lime"   />
              <Metric label="Attention Needed" value={summary.attn}                        note="Review required"   icon="!" color="orange" />
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   GRAPH DIAGRAM — Renders LangGraph Nodes & Edges
───────────────────────────────────────────────────────────────────────────── */
function GraphDiagram({ activeNodes }) {
  const mainNodes = GRAPH_NODES.filter(n => ['start', 'parse_order', 'decompose_tasks', 'assign_robot', 'end'].includes(n.id));
  const altNodes  = GRAPH_NODES.filter(n => ['clarify_order', 'escalate_to_human'].includes(n.id));

  return (
    <div className="graph-diagram">
      {/* Main Happy Path */}
      <div className="graph-col main-col">
        {mainNodes.map((node, idx) => (
          <div key={node.id}>
            <GraphNode node={node} active={activeNodes.includes(node.id)} />
            {idx < mainNodes.length - 1 && <div className="graph-edge-v" />}
          </div>
        ))}
      </div>

      {/* Alternative Branches */}
      <div className="graph-col alt-col">
        <div className="alt-col-label">Conditional Branches</div>
        {altNodes.map(node => (
          <div key={node.id} className="alt-node-wrap">
            <div className="graph-edge-h" />
            <GraphNode node={node} active={activeNodes.includes(node.id)} alt />
          </div>
        ))}
      </div>
    </div>
  );
}

function GraphNode({ node, active, alt }) {
  const typeClass = node.type === 'terminal' ? 'node-terminal' : alt ? 'node-alt' : 'node-main';
  return (
    <div className={`graph-node ${typeClass} ${active ? 'node-active' : ''}`} title={node.desc || node.label}>
      <span className="node-icon">{node.icon}</span>
      <div className="node-info">
        <strong>{node.label}</strong>
        {node.desc && <span className="node-desc">{node.desc}</span>}
      </div>
      {active && <span className="node-pulse" />}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   EXECUTION TRACE — Step-by-Step Execution Log
───────────────────────────────────────────────────────────────────────────── */
function ExecutionTrace({ plan }) {
  const steps = [];
  if (plan.parsed_order) {
    steps.push({
      label: 'parse_order',
      status: 'ok',
      detail: `Extracted: ${plan.parsed_order.item || 'Item'} × ${plan.parsed_order.quantity || 1} | ${plan.parsed_order.source} ➔ ${plan.parsed_order.destination}`
    });
  }
  if (plan.subtasks?.length) {
    steps.push({
      label: 'decompose_tasks',
      status: 'ok',
      detail: `Generated ${plan.subtasks.length} atomic robot action${plan.subtasks.length !== 1 ? 's' : ''}`
    });
  }
  if (plan.status === 'assigned') {
    steps.push({
      label: 'assign_robot',
      status: 'ok',
      detail: `Mission successfully assigned to ${plan.assigned_robot_id}`
    });
  } else if (plan.requires_escalation) {
    steps.push({
      label: 'escalate_to_human',
      status: 'warn',
      detail: plan.escalation_reason || 'No available robot meet criteria'
    });
  }

  return (
    <div className="card trace-card">
      <div className="card-title">
        <div>
          <p className="overline">TRACE LOG</p>
          <h2>Execution Audit Trace</h2>
        </div>
      </div>
      <div className="trace-list">
        {steps.map((s, i) => (
          <div key={i} className={`trace-row ${s.status}`}>
            <span className="trace-idx">{i + 1}</span>
            <div>
              <strong>{s.label}</strong>
              <span>{s.detail}</span>
            </div>
            <span className="trace-badge">{s.status === 'ok' ? '✓ OK' : '! WARN'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   PLAN RESULT — Full Breakdown of Generated Plan
───────────────────────────────────────────────────────────────────────────── */
function PlanResult({ plan }) {
  const success = plan.status === 'assigned';
  return (
    <section className={`plan-result card ${success ? 'success' : 'warning'}`}>
      <div className="plan-summary">
        <div className="result-icon">{success ? '✓' : '!'}</div>
        <div>
          <p className="overline">PLANNING ARTIFACT</p>
          <h2>{success ? 'Mission Plan Ready for Execution' : 'Plan Requires Operator Review'}</h2>
          <p>
            {plan.assigned_robot_id
              ? `Autonomous Mobile Robot ${plan.assigned_robot_id} allocated for this mission.`
              : plan.escalation_reason || 'No AMR could be assigned.'}
          </p>
        </div>
        <span className="result-status">{plan.status || 'Pending'}</span>
      </div>

      {plan.parsed_order && (
        <div className="extracted">
          <div>
            <span>TARGET ITEM</span>
            <b>{plan.parsed_order.item || '—'} × {plan.parsed_order.quantity || 1}</b>
          </div>
          <div>
            <span>SOURCE LOCATION</span>
            <b>{plan.parsed_order.source || '—'}</b>
          </div>
          <div>
            <span>DESTINATION BAY</span>
            <b>{plan.parsed_order.destination || '—'}</b>
          </div>
        </div>
      )}

      {plan.subtasks?.length > 0 && (
        <div>
          <p className="overline" style={{ margin: '18px 0 12px' }}>DECOMPOSED SUBTASK SEQUENCE</p>
          <div className="task-grid">
            {plan.subtasks.map((task, i) => (
              <div key={i} className="task-card">
                <div className="task-card-num">{i + 1}</div>
                <div className="task-card-body">
                  <strong>{String(task.action || 'Task').replace(/_/g, ' ')}</strong>
                  <span>{task.target || task.description || task.item || 'Warehouse Operation'}</span>
                </div>
                <div className="task-card-status">Queued</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   METRIC CARD COMPONENT
───────────────────────────────────────────────────────────────────────────── */
function Metric({ label, value, note, icon, color }) {
  return (
    <div className={`metric ${color}`}>
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{note}</small>
      </div>
    </div>
  );
}

export default App;
