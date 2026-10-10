import { useState, useEffect } from 'react';
import WarehouseMap, { statusMeta } from './WarehouseMap';
import { ShoppingCart, BarChart3, AlertTriangle, Play, Pause, X, Activity, Cpu, Maximize2, Bot, ClipboardList, Battery, Construction, RotateCcw } from './icons';

const ROBOT_DESTINATIONS = {
  R1: { target: 'To Aisle B3', route: '(4, 6) → (4, 2)' },
  R2: { target: 'To Aisle C1', route: '(10, 4) → (10, 1)' },
  R3: { target: 'In Aisle B2', route: '(5, 2) [Blocked]' },
  R4: { target: 'To Packing Station', route: '(14, 10) → (16, 13)' }
};

export default function ControlRoom({
  fleet = [],
  blockedCells = [],
  selectedRobotId,
  onSelectRobot,
  onFullscreen,
  onInject,
  onClear,
  events = [],
  mockMode,
  setMockMode,
  summary,
  highlightedTargetId,
  onTargetSelect,
  activeOrderRoute = null,
  activeOrderRoutes = null,
  taskQueue = []
}) {
  const [currentTime, setCurrentTime] = useState('');
  const [simMode, setSimMode] = useState('Normal');
  const [isPlaying, setIsPlaying] = useState(true);
  const [simSpeed, setSimSpeed] = useState('1x');
  const [showExceptionBanner, setShowExceptionBanner] = useState(true);
  const [railTab, setRailTab] = useState('feed'); // 'feed' | 'tasks'

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }) +
          ' ' +
          now.toLocaleTimeString('en-US', { hour12: false })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const movingCount = fleet.filter((r) => String(r.state).toUpperCase() === 'MOVING').length;
  const stuckRobot = fleet.find(
    (r) => ['STUCK', 'ERROR'].includes(String(r.state).toUpperCase()) || r.enabled === false
  );
  const exceptionCount = stuckRobot ? 1 : 0;
  const totalFleet = fleet.length || 4;
  const utilization = Math.round((movingCount / totalFleet) * 100);

  const activeTasks = fleet.filter((r) => r.current_task).slice(0, 5);

  return (
    <section className="control-room-v2">
      {/* 1. TOP HEADER & TELEMETRY STRIP (Image 2 & 3 Style) */}
      <header className="telemetry-top-header">
        {/* Brand & Live Indicator */}
        <div className="telemetry-brand">
          <div className="iso-cube-logo">
            <svg viewBox="0 0 36 36" className="cube-svg">
              <polygon points="18,3 33,11 18,19 3,11" fill="#3b82f6" />
              <polygon points="3,11 18,19 18,34 3,26" fill="#1d4ed8" />
              <polygon points="18,19 33,11 33,26 18,34" fill="#2563eb" />
            </svg>
          </div>
          <div>
            <div className="brand-title">
              WareFlow <span>AI</span>
            </div>
            <div className="brand-subtitle">Live Telemetry</div>
          </div>
        </div>

        {/* KPI Metric Chips */}
        <div className="telemetry-metrics-bar">
          {/* Orders Completed */}
          <div className="telemetry-chip">
            <span className="chip-icon cart-icon"><ShoppingCart size={15} /></span>
            <div className="chip-content">
              <span className="chip-label">Orders Completed</span>
              <div className="chip-value-row">
                <strong>124</strong>
                <span className="chip-delta positive">↑ 12%</span>
              </div>
              <small className="chip-sub">of 150 target</small>
            </div>
          </div>

          {/* Utilization */}
          <div className="telemetry-chip">
            <span className="chip-icon chart-icon"><BarChart3 size={15} /></span>
            <div className="chip-content">
              <span className="chip-label">Utilization</span>
              <div className="chip-value-row">
                <strong>{utilization || 78}%</strong>
                <span className="chip-delta positive">↑ 5%</span>
              </div>
              <small className="chip-sub">fleet active</small>
            </div>
          </div>

          {/* Active Exceptions */}
          <div className={`telemetry-chip ${exceptionCount > 0 ? 'is-alert' : ''}`}>
            <span className="chip-icon warning-icon"><AlertTriangle size={15} /></span>
            <div className="chip-content">
              <span className="chip-label">Active Exceptions</span>
              <div className="chip-value-row">
                <strong className={exceptionCount > 0 ? 'text-red' : ''}>{exceptionCount}</strong>
                {exceptionCount > 0 && <span className="chip-delta negative">↑ 1</span>}
              </div>
              <small className="chip-sub">
                {exceptionCount > 0 ? 'Requires attention' : 'All clear'}
              </small>
            </div>
          </div>

          {/* Timestamp & Live Pulse */}
          <div className="telemetry-clock-card">
            <span className="clock-time">{currentTime || 'Oct 09, 2026 14:32:18'}</span>
            <span className="live-status-pill">
              <i className="pulse-green-dot" /> Live
            </span>
          </div>
        </div>

        {/* Simulation Execution Controls */}
        <div className="telemetry-controls-group">
          <div className="playback-buttons">
            <button
              className={`play-btn ${isPlaying ? 'active' : ''}`}
              onClick={() => setIsPlaying(true)}
              title="Play Simulation"
            >
              <Play size={12} /> Play
            </button>
            <button
              className={`pause-btn ${!isPlaying ? 'active' : ''}`}
              onClick={() => setIsPlaying(false)}
              title="Pause Simulation"
            >
              <Pause size={12} /> Pause
            </button>
            <select
              className="speed-dropdown"
              value={simSpeed}
              onChange={(e) => setSimSpeed(e.target.value)}
              aria-label="Simulation speed"
            >
              <option value="0.5x">0.5x</option>
              <option value="1x">1x</option>
              <option value="2x">2x</option>
              <option value="4x">4x</option>
            </select>
          </div>

          <div className="mode-toggle-group">
            {['Normal', 'Peak', 'Maintenance'].map((mode) => (
              <button
                key={mode}
                className={`mode-btn ${simMode === mode ? 'selected' : ''}`}
                onClick={() => setSimMode(mode)}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* 2. EXCEPTION ALERT BANNER (Image 2 Style) */}
      {showExceptionBanner && stuckRobot && (
        <div className="exception-alert-banner">
          <div className="banner-content">
            <span className="banner-alert-icon"><AlertTriangle size={15} /></span>
            <div className="banner-text">
              <strong>Exception: {stuckRobot.robot_id} stuck at ({stuckRobot.x ?? 5}, {stuckRobot.y ?? 2})</strong>
              <span>Movement blocked. A* Replanning and SOP compliance evaluation required.</span>
            </div>
          </div>
          <button
            className="banner-close-btn"
            onClick={() => setShowExceptionBanner(false)}
            aria-label="Dismiss banner"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* 3. MAIN CONTENT: MAP + SIDEBAR RAILS */}
      <div className="control-content-grid">
        {/* LEFT / CENTER: WAREHOUSE DIGITAL TWIN MAP */}
        <main className="map-view-card">
          <div className="map-header-bar">
            <div className="map-title-row">
              <h3>Warehouse floor</h3>
              <span className="map-dim-badge">20 × 15 live operational map</span>
            </div>
            <div className="map-actions-row">
              <button
                className="map-subaction-btn"
                onClick={() => setMockMode((v) => !v)}
              >
                {mockMode ? <><Activity size={12} /> Live Telemetry</> : <><Cpu size={12} /> Mock Scenarios</>}
              </button>
              <button
                className="map-subaction-btn fullscreen"
                onClick={() => {
                  try {
                    if (!document.fullscreenElement) {
                      document.documentElement.requestFullscreen().catch(() => {});
                    }
                  } catch (e) {}
                  onFullscreen?.(true);
                }}
                title="Expand map to whole 1080p fullscreen"
              >
                <Maximize2 size={12} /> Expand map
              </button>
            </div>
          </div>

          {/* Warehouse Map Canvas */}
          <WarehouseMap
            fleet={fleet}
            blockedCells={blockedCells}
            selectedRobotId={selectedRobotId}
            onSelectRobot={onSelectRobot}
            showGrid={true}
            showRoutes={true}
            showReroutePanel={true}
            highlightedTargetId={highlightedTargetId}
            onTargetSelect={onTargetSelect}
            showTargetDropdown={true}
            activeOrderRoute={activeOrderRoute}
            activeOrderRoutes={activeOrderRoutes}
            taskQueue={taskQueue}
          />

          {/* BOTTOM MAP LEGEND (Image 2 & 3 Style) */}
          <footer className="map-footer-legend">
            <span className="legend-title">Legend:</span>
            <span className="legend-item">
              <i className="legend-dot idle" /> Robot (Idle)
            </span>
            <span className="legend-item">
              <i className="legend-dot moving" /> Robot (Moving)
            </span>
            <span className="legend-item">
              <i className="legend-line normal" /> Route (Normal)
            </span>
            <span className="legend-item">
              <i className="legend-line detour" /> Route (A* Detour)
            </span>
            <span className="legend-item">
              <i className="legend-hatch-box" /> Restricted Zone
            </span>
            <span className="legend-item">
              <i className="legend-dot charging" /> Charging Station
            </span>
            <span className="legend-item">
              <i className="legend-flag" /> Goal Location
            </span>
          </footer>
        </main>

        {/* RIGHT SIDEBAR: FLEET STATUS & ACTIVITY FEED */}
        <aside className="control-side-rail">
          {/* A. FLEET STATUS CARD */}
          <section className="rail-panel fleet-status-panel">
            <header className="panel-header">
              <div className="panel-title-group">
                <span className="panel-icon"><Bot size={15} /></span>
                <h4>Fleet Status</h4>
              </div>
              <button className="panel-view-all">View All</button>
            </header>

            <div className="fleet-robots-list">
              {fleet.map((robot) => {
                const meta = statusMeta(robot);
                const isSelected = robot.robot_id === selectedRobotId;
                const destInfo = ROBOT_DESTINATIONS[robot.robot_id] || {
                  target: robot.current_task || 'Available for dispatch',
                  route: `(${robot.x}, ${robot.y})`
                };
                const battery = Math.round(Number(robot.battery ?? 100));

                return (
                  <button
                    key={robot.robot_id}
                    className={`fleet-robot-row ${isSelected ? 'selected' : ''} ${meta.key}`}
                    onClick={() => onSelectRobot(robot.robot_id)}
                  >
                    {/* Mini AMR Avatar with State Glow */}
                    <div className="robot-mini-avatar">
                      <div className="mini-amr-ring" style={{ borderColor: meta.color }} />
                      <div className="mini-amr-puck">
                        <span>{robot.robot_id}</span>
                      </div>
                    </div>

                    {/* Robot Details */}
                    <div className="robot-main-meta">
                      <div className="robot-header-line">
                        <strong className="robot-name">{robot.robot_id}</strong>
                        <span className={`robot-state-pill ${meta.key}`}>
                          {meta.label}
                        </span>
                      </div>
                      <div className="robot-dest-text">{destInfo.target}</div>
                      <div className="robot-coords-text">{destInfo.route}</div>
                    </div>

                    {/* Battery Bar & Percentage */}
                    <div className="robot-battery-cell">
                      <div className="battery-pct-num">{battery}%</div>
                      <div className="battery-bar-track">
                        <div
                          className="battery-bar-fill"
                          style={{
                            width: `${battery}%`,
                            backgroundColor:
                              battery > 60 ? '#38bdf8' : battery >= 30 ? '#f59e0b' : '#ef4444'
                          }}
                        />
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* B. AGENT ACTIVITY FEED & TASK QUEUE (Image 2 & 3 Style) */}
          <section className="rail-panel feed-panel">
            <header className="panel-header">
              <div className="panel-tab-toggle">
                <button
                  className={`tab-btn ${railTab === 'feed' ? 'active' : ''}`}
                  onClick={() => setRailTab('feed')}
                >
                  Agent Activity Feed
                </button>
                <button
                  className={`tab-btn ${railTab === 'tasks' ? 'active' : ''}`}
                  onClick={() => setRailTab('tasks')}
                >
                  Task Queue
                </button>
              </div>
              <button className="panel-view-all">View All</button>
            </header>

            {railTab === 'feed' ? (
              <div className="agent-activity-timeline">
                {/* 1. Exception Agent */}
                <div className="timeline-entry exception">
                  <div className="agent-badge exception-agent">
                    <span className="agent-icon"><AlertTriangle size={13} /></span>
                    <strong>Exception Agent</strong>
                    <time>14:32:17</time>
                  </div>
                  <p className="timeline-text">
                    R3 is stuck at (5, 2). Obstacle detected in aisle. Robot is unable to proceed.
                  </p>
                </div>

                {/* 2. Task Planning Agent */}
                <div className="timeline-entry planner">
                  <div className="agent-badge planner-agent">
                    <span className="agent-icon"><Cpu size={13} /></span>
                    <strong>Task Planning Agent</strong>
                    <time>14:32:18</time>
                  </div>
                  <p className="timeline-text">
                    Recomputing path for R3 using A* algorithm. Original route blocked. Finding
                    nearest alternative route via Aisle C.
                  </p>
                </div>

                {/* 3. Knowledge/Compliance Agent */}
                <div className="timeline-entry compliance">
                  <div className="agent-badge compliance-agent">
                    <span className="agent-icon"><ClipboardList size={13} /></span>
                    <strong>Knowledge/Compliance Agent</strong>
                    <time>14:32:19</time>
                  </div>
                  <p className="timeline-text">
                    R3 task paused and reassigned to R4. Updated task queue and notified fleet
                    manager. Compliance check: safe reroute.
                  </p>
                </div>

                {/* 4. System */}
                <div className="timeline-entry system">
                  <div className="agent-badge system-agent">
                    <span className="agent-icon"><Activity size={13} /></span>
                    <strong>System</strong>
                    <time>14:32:20</time>
                  </div>
                  <p className="timeline-text">
                    New path assigned to R4. Estimated arrival time: 3 min.
                  </p>
                </div>
              </div>
            ) : (
              <div className="task-queue-table-wrap">
                <table className="task-queue-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Task</th>
                      <th>Robot</th>
                      <th>Status</th>
                      <th>ETA</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>1</td>
                      <td>Pick items (A3)</td>
                      <td><span className="robot-tag r1">R1</span></td>
                      <td><span className="status-pill in-progress">In Progress</span></td>
                      <td>1 min</td>
                    </tr>
                    <tr>
                      <td>2</td>
                      <td>Move to C1</td>
                      <td><span className="robot-tag r2">R2</span></td>
                      <td><span className="status-pill in-progress">In Progress</span></td>
                      <td>2 min</td>
                    </tr>
                    <tr>
                      <td>3</td>
                      <td>Pick items (D2)</td>
                      <td><span className="robot-tag r3">R3</span></td>
                      <td><span className="status-pill queued">Queued</span></td>
                      <td>4 min</td>
                    </tr>
                    <tr>
                      <td>4</td>
                      <td>Deliver to Packing</td>
                      <td><span className="robot-tag r4">R4</span></td>
                      <td><span className="status-pill in-progress">In Progress</span></td>
                      <td>2 min</td>
                    </tr>
                    <tr>
                      <td>5</td>
                      <td>Return to Charging</td>
                      <td>—</td>
                      <td><span className="status-pill queued">Queued</span></td>
                      <td>6 min</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </aside>
      </div>

      {/* 4. BOTTOM INTERACTIVE DEMO SCENARIOS BAR */}
      <footer className="control-scenarios-footer">
        <span className="scenarios-title">DEMO SCENARIOS:</span>
        <button className="scenario-action-btn stuck" onClick={() => onInject('stuck')}>
          <AlertTriangle size={13} /> Force Robot Stuck
        </button>
        <button className="scenario-action-btn battery" onClick={() => onInject('low_battery')}>
          <Battery size={13} /> Drain Battery (10%)
        </button>
        <button className="scenario-action-btn block" onClick={() => onInject('block_path')}>
          <Construction size={13} /> Block Path (Dynamic Obstacle)
        </button>
        <button className="scenario-action-btn clear" onClick={onClear}>
          <RotateCcw size={13} /> Clear All Obstacles
        </button>
        <div className="scenarios-meta">
          <span>Fleet Size: {fleet.length}</span>
          <span>Tick Rate: 2 Hz</span>
          <span>Simulation: Live</span>
        </div>
      </footer>
    </section>
  );
}
