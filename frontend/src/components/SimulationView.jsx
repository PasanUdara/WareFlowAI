import { useEffect, useState } from 'react';
import WarehouseMap, { statusMeta, PathReroutingLegend } from './WarehouseMap';
import { Play, Pause, Activity, Cpu, Maximize2, Zap, LayoutDashboard, X, AlertTriangle, Battery, Construction, RotateCcw, Check, Plus, Package } from './icons';
import { dispatchOrder } from '../api';

const SIM_PRESETS = [
  { label: 'Pallet Delivery', text: 'Move 5 pallets from Shelf A2 to Packing Station 3.' },
  { label: 'Hazmat Transfer', text: 'Transport 1 drum of solvent from Hazmat Aisle 4 to Station 2' },
  { label: 'Medical Kits', text: 'Fetch 2 medical kits from Shelf A1 to Station 1' },
  { label: 'Heavy Equipment', text: 'Move 2 heavy motor assemblies (24kg) from Receiving to Shelf B1' }
];

export default function SimulationView({
  fleet = [],
  blockedCells = [],
  selectedRobotId,
  onSelectRobot,
  onClose,
  onInject,
  onClear,
  onRunScenario = null,
  events = [],
  mockMode,
  setMockMode,
  initialMapFocus = false,
  initialOpenOrder = false,
  highlightedTargetId = null,
  onTargetSelect = null,
  activeOrderRoute = null,
  activeOrderRoutes = null,
  taskQueue = [],
  onDispatchOrder = null
}) {
  const selected = fleet.find((robot) => robot.robot_id === selectedRobotId) || fleet[0];
  const [mapFocus, setMapFocus] = useState(initialMapFocus);
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [showRerouteLegend, setShowRerouteLegend] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [speed, setSpeed] = useState('1x');
  const [isNativeFullscreen, setIsNativeFullscreen] = useState(
    Boolean(typeof document !== 'undefined' && document.fullscreenElement)
  );

  // Create Order Popup Modal State
  const [showOrderModal, setShowOrderModal] = useState(Boolean(initialOpenOrder));
  const [orderInputText, setOrderInputText] = useState('');
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState(null);
  const [dispatchError, setDispatchError] = useState('');

  const activeDetourRobot = fleet.find((r) => r.is_rerouted || r.detour_path || r.avoiding_obstacle);

  useEffect(() => {
    if (initialOpenOrder) {
      setShowOrderModal(true);
    }
  }, [initialOpenOrder]);

  useEffect(() => {
    const onFsChange = () => {
      setIsNativeFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  useEffect(() => {
    if (initialMapFocus) {
      setMapFocus(true);
      if (!document.fullscreenElement) {
        try {
          document.documentElement.requestFullscreen().catch(() => {});
        } catch (err) {}
      }
    }
  }, [initialMapFocus]);

  const toggleFullscreen = () => {
    try {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    } catch (err) {}
  };

  const handleExit = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    onClose?.();
  };

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        if (showOrderModal) {
          setShowOrderModal(false);
          return;
        }
        if (mapFocus) {
          if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {});
          }
          setMapFocus(false);
        } else {
          handleExit();
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, mapFocus, showOrderModal]);

  const handleModalDispatch = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const trimmed = orderInputText.trim();
    if (!trimmed) return;

    setIsDispatching(true);
    setDispatchError('');
    setDispatchResult(null);

    try {
      let result;
      if (onDispatchOrder) {
        result = await onDispatchOrder(trimmed);
      } else {
        result = await dispatchOrder({ order_text: trimmed });
      }
      setDispatchResult(result);
      setOrderInputText('');
    } catch (err) {
      setDispatchError(err.message || 'Failed to dispatch order to fleet.');
    } finally {
      setIsDispatching(false);
    }
  };

  const selectedMeta = selected ? statusMeta(selected) : null;
  const selectedBattery = selected ? Math.round(Number(selected.battery ?? 100)) : 100;

  return (
    <section
      className={`simulation-overlay ${
        mapFocus
          ? `map-focus ratio-${aspectRatio.replace(':', '-')} ${
              showRerouteLegend && activeDetourRobot ? 'has-reroute-panel' : ''
            }`
          : ''
      }`}
      role="dialog"
      aria-modal="true"
      aria-label="Fullscreen warehouse simulation"
    >
      {/* 0. FLOATING HUD FOR MAP FOCUS MODE (Leaves whole screen to the warehouse map) */}
      {mapFocus && (
        <aside className="map-focus-floating-hud" aria-label="Expanded Map HUD Controls">
          <div className="focus-hud-pill">
            <span className="live-dot" />
            <span className="focus-hud-title">20 × 15 Digital Twin</span>
            <button
              className="focus-hud-btn"
              onClick={() => setIsPaused((p) => !p)}
              title={isPaused ? 'Resume Simulation' : 'Pause Simulation'}
            >
              {isPaused ? <><Play size={12} /> Play</> : <><Pause size={12} /> Pause</>}
            </button>
            <button
              className="focus-hud-btn"
              onClick={() => setMockMode((v) => !v)}
              title="Toggle Live / Mock Telemetry"
            >
              {mockMode ? <><Activity size={12} /> Live</> : <><Cpu size={12} /> Mock</>}
            </button>
            <button
              className="focus-hud-btn"
              onClick={() =>
                setAspectRatio((r) => {
                  if (r === '16:9') return 'fill';
                  if (r === 'fill') return '4:3';
                  if (r === '4:3') return '1:1';
                  return '16:9';
                })
              }
              title="Toggle Aspect Ratio (1080p 16:9, Edge-to-Edge Fill, 4:3 Grid, 1:1 Square)"
            >
              <Maximize2 size={12} />{' '}
              {aspectRatio === '16:9'
                ? '1080p (16:9)'
                : aspectRatio === 'fill'
                ? '1080p Fill'
                : aspectRatio === '4:3'
                ? '4:3 Grid'
                : '1:1 Square'}
            </button>
            <button
              className={`focus-hud-btn ${isNativeFullscreen ? 'primary' : ''}`}
              onClick={toggleFullscreen}
              title={isNativeFullscreen ? 'Exit 1080p Fullscreen (Esc)' : 'Enter 1080p Fullscreen'}
            >
              <Maximize2 size={12} /> {isNativeFullscreen ? '1080p Full' : 'Fullscreen'}
            </button>
            {activeDetourRobot && (
              <button
                className={`focus-hud-btn ${showRerouteLegend ? 'primary' : ''}`}
                onClick={() => setShowRerouteLegend((s) => !s)}
                title="Toggle Path Rerouting (A*) Legend Card outside the map"
              >
                <Zap size={12} /> {showRerouteLegend ? 'Hide A* Card' : 'Show A* Card'}
              </button>
            )}
            <button
              className="focus-hud-btn order-create-hud-btn"
              onClick={() => {
                setShowOrderModal(true);
                setDispatchError('');
                setDispatchResult(null);
              }}
              title="Create and Dispatch Fleet Order"
            >
              <Plus size={12} /> Create Order
            </button>
            <button
              className="focus-hud-btn"
              onClick={() => {
                if (document.fullscreenElement) {
                  document.exitFullscreen().catch(() => {});
                }
                setMapFocus(false);
              }}
              title="Restore Side Panels and Controls"
            >
              <LayoutDashboard size={12} /> Show Panels
            </button>
            <button
              className="focus-hud-btn exit"
              onClick={handleExit}
              title="Exit Fullscreen (Esc)"
            >
              <X size={12} /> Exit <kbd>Esc</kbd>
            </button>
          </div>
        </aside>
      )}
      {/* 1. TOP HEADER */}
      <header className="simulation-header">
        <div className="sim-header-brand">
          <div className="iso-cube-mini">
            <svg viewBox="0 0 36 36">
              <polygon points="18,3 33,11 18,19 3,11" fill="#3b82f6" />
              <polygon points="3,11 18,19 18,34 3,26" fill="#1d4ed8" />
              <polygon points="18,19 33,11 33,26 18,34" fill="#2563eb" />
            </svg>
          </div>
          <div>
            <div className="sim-brand-title">
              WareFlow AI <span>Live Warehouse Simulation</span>
            </div>
            <div className="sim-brand-sub">
              <span className="live-dot" /> {mockMode ? 'DEMO TELEMETRY' : 'LIVE 2Hz TELEMETRY'}
            </div>
          </div>
        </div>

        <div className="simulation-controls">
          <button
            className={`sim-button ${isPaused ? '' : 'primary'}`}
            onClick={() => setIsPaused((p) => !p)}
          >
            {isPaused ? <><Play size={13} /> Play</> : <><Pause size={13} /> Pause</>}
          </button>
          <button className="sim-button">Step</button>
          <label className="sim-select">
            Speed
            <select value={speed} onChange={(e) => setSpeed(e.target.value)}>
              <option value="0.5x">0.5x</option>
              <option value="1x">1x</option>
              <option value="2x">2x</option>
              <option value="4x">4x</option>
            </select>
          </label>
          <button
            className="sim-button"
            onClick={() => onRunScenario ? onRunScenario('full_demo') : setMockMode((v) => !v)}
            title="Run full automated fleet demo scenario"
          >
            <Cpu size={13} /> Run Mock Demo
          </button>
          <button
            className="sim-button order-btn"
            onClick={() => {
              setShowOrderModal(true);
              setDispatchError('');
              setDispatchResult(null);
            }}
            title="Create and Dispatch Fleet Order"
          >
            <Plus size={13} /> Create Order
          </button>
          <button
            className="sim-button focus"
            onClick={() => {
              const next = !mapFocus;
              setMapFocus(next);
              if (next && !document.fullscreenElement) {
                try {
                  document.documentElement.requestFullscreen().catch(() => {});
                } catch (e) {}
              }
            }}
          >
            {mapFocus ? <><LayoutDashboard size={13} /> Show Panels</> : <><Maximize2 size={13} /> Expand Map</>}
          </button>
          <button className="sim-button exit" onClick={handleExit}>
            <X size={13} /> Exit Fullscreen <kbd>Esc</kbd>
          </button>
        </div>
      </header>

      {/* 2. THREE-COLUMN SIMULATION LAYOUT */}
      <div className="simulation-layout">
        {/* LEFT PANEL: FLEET STATUS */}
        <aside className="simulation-side fleet-side">
          <div className="sim-panel-heading">
            <span>FLEET TELEMETRY</span>
            <b>{fleet.length} AMRs ACTIVE</b>
          </div>

          <div className="sim-fleet-list">
            {fleet.map((robot) => {
              const meta = statusMeta(robot);
              const isSelected = robot.robot_id === selected?.robot_id;
              const battery = Math.round(Number(robot.battery ?? 100));

              return (
                <button
                  className={`sim-fleet-card ${isSelected ? 'active' : ''} ${meta.key}`}
                  key={robot.robot_id}
                  onClick={() => onSelectRobot(robot.robot_id)}
                >
                  <div className="sim-robot-avatar">
                    <span className="avatar-ring" style={{ borderColor: meta.color }} />
                    <span className="avatar-puck">{robot.robot_id}</span>
                  </div>

                  <div className="sim-robot-info">
                    <div className="sim-robot-title-row">
                      <strong>{robot.robot_id}</strong>
                      <span className={`sim-state-pill ${meta.key}`}>
                        {meta.label}
                      </span>
                    </div>
                    <small className="sim-task-text">
                      {robot.current_task || 'Available for dispatch'}
                    </small>
                    <div className="sim-battery-row">
                      <div className="sim-battery-track">
                        <div
                          className="sim-battery-fill"
                          style={{
                            width: `${battery}%`,
                            backgroundColor:
                              battery > 60 ? '#38bdf8' : battery >= 30 ? '#f59e0b' : '#ef4444'
                          }}
                        />
                      </div>
                      <span className="sim-battery-pct">{battery}%</span>
                      <span className="sim-coords">
                        ({robot.x ?? robot.position?.[0] ?? 0}, {robot.y ?? robot.position?.[1] ?? 0})
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* CENTER STAGE: FULL PHOTOREALISTIC WAREHOUSE DIGITAL TWIN MAP */}
        <main className="simulation-stage">
          <div className="stage-caption">
            <span>20 × 15 OPERATIONS FLOOR · FULL DIGITAL TWIN</span>
            <div className="stage-caption-actions">
              <span>{mapFocus ? 'Map Focus Mode (Click Expand Map to restore panels)' : 'Click any AMR or coordinate to inspect'}</span>
              <button
                className="stage-quick-order-btn"
                onClick={() => {
                  setShowOrderModal(true);
                  setDispatchError('');
                  setDispatchResult(null);
                }}
                title="Create Warehouse Order"
              >
                <Plus size={11} /> Create Order
              </button>
            </div>
          </div>

          <div className="fullscreen-map-wrapper">
            {/* Path Rerouting Card OUTSIDE the map */}
            {mapFocus && showRerouteLegend && activeDetourRobot && (
              <PathReroutingLegend
                activeRobot={activeDetourRobot}
                onClose={() => setShowRerouteLegend(false)}
              />
            )}

            <WarehouseMap
              fleet={fleet}
              selectedRobotId={selectedRobotId}
              onSelectRobot={onSelectRobot}
              blockedCells={blockedCells}
              showGrid={true}
              showRoutes={true}
              showReroutePanel={false}
              highlightedTargetId={highlightedTargetId}
              onTargetSelect={onTargetSelect}
              showTargetDropdown={false}
              activeOrderRoute={activeOrderRoute}
              activeOrderRoutes={activeOrderRoutes}
              taskQueue={taskQueue}
            />
          </div>

          <div className="simulation-scenarios">
            <span className="scenarios-kicker">SCENARIO INJECTION:</span>
            <button
              className="sim-scen-btn"
              style={{ borderColor: 'rgba(59, 130, 246, 0.4)', color: '#93c5fd' }}
              onClick={() => onRunScenario ? onRunScenario('all_active') : null}
              title="Dispatch all 4 fleet robots to active operational missions"
            >
              <Activity size={13} /> ⚡ Start All
            </button>
            <button
              className="sim-scen-btn block"
              onClick={() => onRunScenario ? onRunScenario('block_and_reroute') : onInject?.('block_path', selectedRobotId)}
              title="Place dynamic obstacle on path, triggering Exception Handling Agent A* detour avoidance"
            >
              <Construction size={13} /> 🚧 Avoid Obstacle
            </button>
            <button
              className="sim-scen-btn battery"
              onClick={() => onRunScenario ? onRunScenario('battery_drain_handover') : onInject?.('low_battery', selectedRobotId)}
              title="Drain moving robot battery to 10%, recharge at bay, and hand over task to another AMR"
            >
              <Battery size={13} /> 🔋 Battery Handover
            </button>
            <button className="sim-scen-btn stuck" onClick={() => onInject && onInject('stuck', selectedRobotId)}>
              <AlertTriangle size={13} /> ⚠️ Stall
            </button>
            <button className="sim-scen-btn clear" onClick={onClear}>
              <RotateCcw size={13} /> 🧹 Clear
            </button>
          </div>
        </main>

        {/* RIGHT PANEL: SELECTED ROBOT TELEMETRY & CONTROLS */}
        <aside className="simulation-side detail-side">
          <div className="sim-panel-heading">
            <span>SELECTED AMR TELEMETRY</span>
            <b>{selected?.robot_id || '—'}</b>
          </div>

          {selected ? (
            <div className="sim-detail-content">
              {/* Header Box */}
              <div className="selected-robot-header">
                <div className="selected-puck-display">
                  <div
                    className="puck-large"
                    style={{
                      borderColor: selectedMeta?.color,
                      boxShadow: `0 0 16px ${selectedMeta?.color}55`
                    }}
                  >
                    <span>{selected.robot_id}</span>
                  </div>
                </div>
                <div>
                  <strong className="selected-full-title">
                    Warehouse AMR {selected.robot_id}
                  </strong>
                  <div className="selected-state-row">
                    <span className={`sim-state-pill ${selectedMeta?.key}`}>
                      {selectedMeta?.label}
                    </span>
                    <span className="sublabel-text">{selectedMeta?.sublabel}</span>
                  </div>
                </div>
              </div>

              {/* Data Table */}
              <div className="selected-specs-grid">
                <div className="spec-item">
                  <span className="spec-label">Battery Level</span>
                  <strong
                    style={{
                      color:
                        selectedBattery > 60
                          ? '#38bdf8'
                          : selectedBattery >= 30
                          ? '#f59e0b'
                          : '#ef4444'
                    }}
                  >
                    {selectedBattery}%
                  </strong>
                </div>
                <div className="spec-item">
                  <span className="spec-label">Grid Position</span>
                  <strong>
                    ({selected.x ?? selected.position?.[0] ?? 0},{' '}
                    {selected.y ?? selected.position?.[1] ?? 0})
                  </strong>
                </div>
                <div className="spec-item full">
                  <span className="spec-label">Assigned Task</span>
                  <strong className="text-truncate">
                    {selected.current_task || 'No active task (Standby)'}
                  </strong>
                </div>
                <div className="spec-item full">
                  <span className="spec-label">Navigation Route</span>
                  <strong>
                    {selected.is_rerouted
                      ? <><Zap size={12} color="#fbbf24" /> A* Detour Active</>
                      : selected.waypoints?.length
                      ? `${selected.waypoints.length} waypoints remaining`
                      : 'Idle at Station'}
                  </strong>
                </div>
              </div>

              {/* Task Steps Pipeline */}
              <div className="task-checklist">
                <b>MISSION PIPELINE</b>
                <span className="done"><Check size={11} /> 1. Navigate to Source Shelf</span>
                <span className={selected.state === 'PICKING' ? 'current' : 'done'}>
                  {selected.state === 'PICKING' ? <Play size={10} /> : <Check size={11} />} 2. Pick Payload from Rack
                </span>
                <span className={['MOVING', 'IDLE'].includes(String(selected.state).toUpperCase()) ? 'current' : ''}>
                  3. Navigate to Packing Station
                </span>
                <span>4. Deposit at Station Conveyor</span>
              </div>

              {/* Rerouting Legend in Sidebar (Never covers map) */}
              {activeDetourRobot && (
                <PathReroutingLegend activeRobot={activeDetourRobot} className="sidebar-legend" />
              )}
            </div>
          ) : (
            <p className="no-select-msg">No robot selected.</p>
          )}
        </aside>
      </div>

      {/* 3. BOTTOM LIVE AGENT ACTIVITY TICKER */}
      <footer className="simulation-feed">
        <span className="feed-kicker">AGENT ACTIVITY STREAM:</span>
        <div className="feed-ticker-wrap">
          {events.slice(0, 3).map((event, index) => (
            <div key={index} className="feed-item">
              <b className="feed-source">{event.source || 'Simulation'}:</b>
              <span className="feed-summary">
                {event.summary || event.message || event.event_type}
              </span>
            </div>
          ))}
          {!events.length && (
            <p className="feed-empty">
              System is operating smoothly. Telemetry streaming at 2 Hz.
            </p>
          )}
        </div>
      </footer>

      {/* 4. CREATE ORDER POPUP MODAL (Available in Expanded Map & Fullscreen) */}
      {showOrderModal && (
        <div
          className="sim-order-modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowOrderModal(false);
          }}
        >
          <div className="sim-order-modal-card" role="dialog" aria-modal="true" aria-labelledby="sim-order-title">
            <div className="sim-order-modal-header">
              <div className="sim-order-title-wrap">
                <div className="sim-order-icon-badge">
                  <Zap size={16} />
                </div>
                <div>
                  <h3 id="sim-order-title">Create Warehouse Order</h3>
                  <p>Dispatch natural language instructions to fleet AMRs with real-time digital twin routing.</p>
                </div>
              </div>
              <button
                className="sim-order-close-btn"
                onClick={() => setShowOrderModal(false)}
                title="Close (Esc)"
              >
                <X size={16} />
              </button>
            </div>

            {/* Quick Preset Chips */}
            <div className="sim-order-presets">
              <span className="sim-order-presets-label">QUICK PRESETS:</span>
              <div className="sim-order-chips">
                {SIM_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="sim-order-chip"
                    onClick={() => {
                      setOrderInputText(preset.text);
                      setDispatchError('');
                      setDispatchResult(null);
                    }}
                  >
                    <Package size={11} /> {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Order Textarea Input */}
            <form onSubmit={handleModalDispatch}>
              <div className="sim-order-input-wrapper">
                <label htmlFor="sim-order-textarea" className="visually-hidden">
                  Order instruction text
                </label>
                <textarea
                  id="sim-order-textarea"
                  className="sim-order-textarea"
                  rows={3}
                  maxLength={500}
                  autoFocus
                  value={orderInputText}
                  onChange={(e) => {
                    setOrderInputText(e.target.value);
                    if (dispatchError) setDispatchError('');
                  }}
                  placeholder="e.g. Move 5 pallets from Shelf A2 to Packing Station 3, or Fetch medical kit from Shelf A1 to Station 1..."
                />
                <div className="sim-order-input-meta">
                  <span className="sim-order-char-count">{orderInputText.length}/500 chars</span>
                  {orderInputText && (
                    <button
                      type="button"
                      className="sim-order-clear-btn"
                      onClick={() => setOrderInputText('')}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Status / Feedback Banner */}
              {dispatchError && (
                <div className="sim-order-feedback error">
                  <AlertTriangle size={14} />
                  <span>{dispatchError}</span>
                </div>
              )}

              {dispatchResult && (
                <div className="sim-order-feedback success">
                  <Check size={14} />
                  <div>
                    <strong>
                      {dispatchResult.status === 'queued'
                        ? `Order queued (Position #${dispatchResult.queue_position})`
                        : `Assigned to ${dispatchResult.assigned_robot_id || 'AMR'}`}
                    </strong>
                    {dispatchResult.parsed_order && (
                      <small>
                        {dispatchResult.parsed_order.quantity ? `${dispatchResult.parsed_order.quantity} ` : ''}
                        {dispatchResult.parsed_order.item || 'Items'} · {dispatchResult.parsed_order.source} → {dispatchResult.parsed_order.destination}
                      </small>
                    )}
                  </div>
                </div>
              )}

              {/* Actions Footer */}
              <div className="sim-order-modal-actions">
                <button
                  type="button"
                  className="sim-order-cancel-btn"
                  onClick={() => setShowOrderModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="sim-order-submit-btn"
                  disabled={isDispatching || !orderInputText.trim()}
                >
                  {isDispatching ? (
                    <>
                      <RotateCcw size={13} className="spin" /> Dispatching...
                    </>
                  ) : (
                    <>
                      <Zap size={13} /> Dispatch Task
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
