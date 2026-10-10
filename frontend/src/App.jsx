import { useEffect, useMemo, useState, useRef } from 'react';
import {
  checkCompliance,
  clearAuthToken,
  clearDynamicObstacles,
  createRobot,
  disableRobot,
  dispatchOrder,
  enableRobot,
  fetchEventHistory,
  fetchActiveException,
  fetchFleetStatus,
  getAuthToken,
  injectRobotAnomaly,
  loginUser,
  triggerEmergencyStop
} from './api';
import WarehouseMap from './components/WarehouseMap';
import { MOCK_BLOCKED_CELLS, MOCK_FLEET } from './mockTelemetry';
import SimulationView from './components/SimulationView';
import ControlRoom from './components/ControlRoom';
import { TARGET_GROUPS, ALL_TARGET_AREAS, resolveTargetLocation } from './targetAreas';
import {
  LayoutDashboard,
  Package,
  ListChecks,
  Bot,
  ShieldCheck,
  AlertTriangle,
  Activity,
  ShieldAlert,
  Layers,
  RefreshCw,
  Bell,
  LogOut,
  OctagonAlert,
  Play,
  Zap,
  Truck,
  HelpCircle,
  Battery,
  Construction,
  RotateCcw,
  User,
  X,
  Check,
  Lock
} from './components/icons';

const defaultOrder = '';

const PRESET_ORDERS = [
  { Icon: Package, label: 'Standard Delivery', text: 'Move 5 pallets from Shelf A2 to Packing Station 3.' },
  { Icon: AlertTriangle, label: 'Hazmat Transfer', text: 'Transport 1 drum of solvent from Hazmat Aisle 4 to Station 2' },
  { Icon: Truck, label: 'Heavy Equipment', text: 'Move 2 heavy motor assemblies (24kg) from Receiving to Shelf B1' },
  { Icon: HelpCircle, label: 'Ambiguous Order', text: 'Bring the blue box from somewhere over there' }
];

const COMPLIANCE_PRESETS = [
  {
    id: 'std_safe',
    label: 'Standard Pallet (Safe)',
    type: 'pass',
    payload_weight: 15.0,
    speed: 1.2,
    is_hazmat: false,
    target_zone: 'Packing Station 1'
  },
  {
    id: 'haz_safe',
    label: 'Hazmat Transfer (Safe)',
    type: 'pass',
    payload_weight: 12.0,
    speed: 0.7,
    is_hazmat: true,
    target_zone: 'Hazmat Bay'
  },
  {
    id: 'haz_fast',
    label: 'Hazmat Overspeed Violation',
    type: 'fail',
    payload_weight: 15.0,
    speed: 1.4,
    is_hazmat: true,
    target_zone: 'Packing Station 2'
  },
  {
    id: 'overweight',
    label: 'Overweight Payload Violation',
    type: 'fail',
    payload_weight: 125.0,
    speed: 1.0,
    is_hazmat: false,
    target_zone: 'Shelf A1'
  }
];

const NAV_GROUPS = [
  {
    label: 'OPERATIONS',
    items: [
      { id: 'overview', Icon: LayoutDashboard, label: 'Dashboard' },
      { id: 'orders', Icon: Package, label: 'Orders' },
      { id: 'tasks', Icon: ListChecks, label: 'Tasks' }
    ]
  },
  {
    label: 'FLEET',
    items: [{ id: 'fleet', Icon: Bot, label: 'Robots' }]
  },
  {
    label: 'INTELLIGENCE',
    items: [{ id: 'compliance', Icon: ShieldCheck, label: 'Compliance' }]
  },
  {
    label: 'MONITORING',
    items: [
      { id: 'exception', Icon: AlertTriangle, label: 'Exceptions' },
      { id: 'events', Icon: Activity, label: 'Events' }
    ]
  },
  {
    label: 'SYSTEM',
    items: [
      { id: 'emergency', Icon: ShieldAlert, label: 'Emergency Stop' },
      { id: 'commercial', Icon: Layers, label: 'Plans & Deployment' }
    ]
  }
];

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(getAuthToken()));
  const [currentUser, setCurrentUser] = useState(localStorage.getItem('wareflow_user') || '');
  const [userRole, setUserRole] = useState(localStorage.getItem('wareflow_role') || '');
  const [activeTab, setActiveTab] = useState('overview');

  // Login Form State
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Dashboard Data State
  const [fleet, setFleet] = useState([]);
  const [emergencyStop, setEmergencyStop] = useState(null);
  const [selectedRobotId, setSelectedRobotId] = useState('R1');
  const [globalError, setGlobalError] = useState('');
  const [wsStatus, setWsStatus] = useState('Disconnected');
  const [fleetLoading, setFleetLoading] = useState(false);
  const [fleetError, setFleetError] = useState('');
  const [fleetHasLoaded, setFleetHasLoaded] = useState(false);
  const [exceptionLoading, setExceptionLoading] = useState(false);
  const [exceptionError, setExceptionError] = useState('');
  const [eventLoading, setEventLoading] = useState(false);
  const [eventError, setEventError] = useState('');
  const [events, setEvents] = useState([]);
  const [eventSearch, setEventSearch] = useState('');
  const [taskFilter, setTaskFilter] = useState('all');
  const [showEmergencyModal, setShowEmergencyModal] = useState(false);
  const [emergencyBusy, setEmergencyBusy] = useState(false);

  // Member 2 Exception Handling State
  const [activeException, setActiveException] = useState(null);
  const [blockedCells, setBlockedCells] = useState([]);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [mapOptions, setMapOptions] = useState({ grid: true, routes: true, labels: true });
  const [playbackSpeed, setPlaybackSpeed] = useState('1x');
  const [mockMode, setMockMode] = useState(false);
  const [simulationOpen, setSimulationOpen] = useState(false);
  const [simulationInitialFocus, setSimulationInitialFocus] = useState(false);
  // Task Planner State
  const [orderText, setOrderText] = useState(defaultOrder);
  const [plan, setPlan] = useState(null);
  const [planning, setPlanning] = useState(false);
  const [dispatchHistory, setDispatchHistory] = useState([]);

  // Target Highlight & Active Order Route State
  const [mapTargetHighlight, setMapTargetHighlight] = useState('');
  const [activeOrderRoute, setActiveOrderRoute] = useState(null);
  const [activeOrderRoutes, setActiveOrderRoutes] = useState({});
  const [taskQueue, setTaskQueue] = useState([]);

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
  const [complianceLoading, setComplianceLoading] = useState(false);

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
      localStorage.removeItem('wareflow_user');
      localStorage.removeItem('wareflow_role');
      setLoginPassword('');
      setCurrentUser('');
      setUserRole('');
      setLoginError('Session expired. Please sign in again.');
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
    let reconnectTimer;
    let isSubscribed = true;

    const connectWebSocket = () => {
      try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}/ws/telemetry`;
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (isSubscribed) setWsStatus('Connected');
        };

        socket.onmessage = (event) => {
          if (!isSubscribed) return;
          try {
            const data = JSON.parse(event.data);
            if (data.task_queue !== undefined) {
              setTaskQueue(data.task_queue);
            }
            if (data.robots) {
              setFleet(data.robots);
              setActiveOrderRoute((prev) => {
                if (!prev) return prev;
                const assignedRobot = data.robots.find((r) => r.robot_id === prev.robotId);
                if (assignedRobot) {
                  if (assignedRobot.loaded || assignedRobot.source_active === false) {
                    return { ...prev, sourceActive: false };
                  }
                }
                return prev;
              });
              setActiveOrderRoutes((prev) => {
                const next = { ...prev };
                let changed = false;
                data.robots.forEach((robot) => {
                  const route = next[robot.robot_id];
                  if (route && (robot.loaded || robot.source_active === false) && route.sourceActive) {
                    next[robot.robot_id] = { ...route, sourceActive: false };
                    changed = true;
                  }
                });
                return changed ? next : prev;
              });
              if (data.emergency_stopped !== undefined) {
                setEmergencyStop(Boolean(data.emergency_stopped));
              }
            }
            if (data.active_exception) {
              setActiveException(data.active_exception);
            }
            if (data.dynamic_blocked_cells !== undefined) {
              setBlockedCells(data.dynamic_blocked_cells);
            } else if (data.blocked_cells) {
              setBlockedCells(data.blocked_cells);
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
            reconnectTimer = setTimeout(connectWebSocket, 3000);
          } else {
            setWsStatus('Disconnected');
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
    loadExceptionData();

    return () => {
      isSubscribed = false;
      clearTimeout(reconnectTimer);
      if (socket) socket.close();
    };
  }, [isAuthenticated]);

  const loadFleetData = async () => {
    setFleetLoading(true);
    setFleetError('');
    try {
      const data = await fetchFleetStatus();
      setFleet(data.robots || []);
      setEmergencyStop(Boolean(data.emergency_stop));
      setFleetHasLoaded(true);
    } catch (err) {
      setFleetError(err.message || 'Unable to load robot fleet.');
    } finally {
      setFleetLoading(false);
    }
  };

  const loadExceptionData = async () => {
    setExceptionLoading(true);
    setExceptionError('');
    try {
      const data = await fetchActiveException();
      setActiveException(data.lifecycle || null);
      setBlockedCells(data.dynamic_blocked_cells !== undefined ? data.dynamic_blocked_cells : data.blocked_cells || []);
    } catch (err) {
      setExceptionError(err.message || 'Unable to load exception lifecycle.');
    } finally {
      setExceptionLoading(false);
    }
  };

  const loadEventHistory = async () => {
    setEventLoading(true);
    setEventError('');
    try {
      const data = await fetchEventHistory(25);
      setEvents(data.events || []);
      if (data.events) {
        const formatted = data.events.map((e) => ({
          time: e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '—',
          source: e.source,
          type: e.event_type,
          summary: `${e.source} → ${e.destination}: ${JSON.stringify(e.payload).substring(0, 120)}`
        }));
        setActivityLogs(formatted);
      }
    } catch (err) {
      setEventError(err.message || 'Unable to load event history.');
    } finally {
      setEventLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Computed Summaries
  // ---------------------------------------------------------------------------
  const fleetSummary = useMemo(() => {
    const total = fleet.length;
    const moving = fleet.filter((r) => String(r.state).toUpperCase() === 'MOVING').length;
    const charging = fleet.filter((r) => String(r.state).toUpperCase() === 'CHARGING').length;
    const available = fleet.filter((r) => String(r.state).toUpperCase() === 'IDLE' && r.enabled !== false).length;
    const attention = fleet.filter(
      (r) => (r.battery !== null && r.battery !== undefined && Number.isFinite(Number(r.battery)) && Number(r.battery) < 25)
        || ['ERROR', 'STUCK'].includes(String(r.state).toUpperCase())
        || r.enabled === false
    ).length;
    const batteries = fleet.map((r) => Number(r.battery)).filter(Number.isFinite);
    const avgBattery = batteries.length
      ? Math.round(batteries.reduce((sum, battery) => sum + battery, 0) / batteries.length)
      : null;
    const activeTaskCount = fleet.filter((r) => Boolean(r.current_task)).length;
    const exceptionActive = activeException
      ? ['DETECTED', 'ANALYZING', 'RECOVERING'].includes(activeException.status)
      : null;
    return { total, moving, charging, available, attention, avgBattery, activeTaskCount, exceptionActive };
  }, [fleet, activeException]);

  const mapFleet = mockMode ? MOCK_FLEET : fleet;
  const mapBlockedCells = mockMode ? MOCK_BLOCKED_CELLS : blockedCells;

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
      setUserRole(data.role || '');
      setLoginPassword('');
      localStorage.setItem('wareflow_user', data.username);
      if (data.role) localStorage.setItem('wareflow_role', data.role);
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
    localStorage.removeItem('wareflow_role');
    setIsAuthenticated(false);
    setLoginPassword('');
    setCurrentUser('');
    setUserRole('');
    setActiveTab('overview');
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
      setDispatchHistory((previous) => [
        { id: `${Date.now()}`, orderText: orderText.trim(), result, createdAt: new Date().toISOString() },
        ...previous
      ]);
      if (result.status === 'queued') {
        addActivityLog('Gateway', 'ORDER_QUEUED', `Queued (Pos #${result.queue_position}): "${orderText.substring(0, 30)}..."`);
        await loadEventHistory();
        setActiveTab('overview');
      } else if (result.assigned_robot_id) {
        setSelectedRobotId(result.assigned_robot_id);

        // Automatically activate source and destination indicators on digital twin map
        const srcName = result.parsed_order?.source || 'Shelf A2';
        const destName = result.parsed_order?.destination || 'Packing Station 3';
        const resolvedSrc = resolveTargetLocation(srcName) || { x: 3, y: 4, name: srcName };
        const resolvedDest = resolveTargetLocation(destName) || { x: 17, y: 12, name: destName };
        const itemStr = `${result.parsed_order?.quantity ?? ''} ${result.parsed_order?.item ?? ''}`.trim() || 'items';

        const routeData = {
          robotId: result.assigned_robot_id,
          sourceName: resolvedSrc.name || srcName,
          destinationName: resolvedDest.name || destName,
          sourceCoords: [resolvedSrc.x, resolvedSrc.y],
          destCoords: [resolvedDest.x, resolvedDest.y],
          sourceActive: true,
          item: itemStr,
          orderText: orderText.trim(),
          timestamp: Date.now()
        };

        setActiveOrderRoute(routeData);
        setActiveOrderRoutes((prev) => ({
          ...prev,
          [result.assigned_robot_id]: routeData
        }));

        addActivityLog('Gateway', 'ORDER_DISPATCH', `Dispatched to ${result.assigned_robot_id}: "${orderText.substring(0, 30)}..."`);
        await loadEventHistory();
        // Immediately switch to the Overview Map so operator sees indicators and robot execution!
        setActiveTab('overview');
      }
    } catch (err) {
      setGlobalError(err.message || 'Task Planning agent could not execute request.');
    } finally {
      setPlanning(false);
    }
  };

  const handleToggleEmergencyStop = async (resume = false) => {
    setEmergencyBusy(true);
    try {
      const result = await triggerEmergencyStop(resume);
      setEmergencyStop(Boolean(result.emergency_stop));
      addActivityLog('Gateway', resume ? 'SYSTEM_RESUMED' : 'EMERGENCY_STOP', result.message);
      setShowEmergencyModal(false);
      await loadFleetData();
      await loadEventHistory();
    } catch (err) {
      setGlobalError(err.message || 'Emergency control request failed.');
    } finally {
      setEmergencyBusy(false);
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

  const handleInjectAnomaly = async (anomalyType) => {
    if (!selectedRobot) return;
    setAnomalyLoading(true);
    setGlobalError('');
    try {
      await injectRobotAnomaly(selectedRobot.robot_id, anomalyType);
      addActivityLog('ExceptionAgent', 'ANOMALY_TRIGGERED', `${selectedRobot.robot_id}: ${anomalyType}`);
      await loadFleetData();
      await loadEventHistory();
    } catch (err) {
      setGlobalError(err.message || `Failed to inject anomaly '${anomalyType}'`);
    } finally {
      setAnomalyLoading(false);
    }
  };

  const handleClearObstacles = async () => {
    try {
      await clearDynamicObstacles();
      setBlockedCells([]);
      addActivityLog('Simulation', 'CLEAR_OBSTACLES', 'Dynamic blocked obstacles cleared');
      await loadFleetData();
    } catch (err) {
      setGlobalError(err.message || 'Failed to clear obstacles');
    }
  };
  const handleCheckCompliance = async (e) => {
    e.preventDefault();
    setGlobalError('');
    setComplianceLoading(true);
    try {
      const res = await checkCompliance(complianceForm);
      setComplianceResult(res);
      addActivityLog('ComplianceAgent', res.is_compliant ? 'COMPLIANCE_APPROVED' : 'COMPLIANCE_REJECTED', `Zone: ${complianceForm.target_zone}`);
      await loadEventHistory();
    } catch (err) {
      setGlobalError(err.message || 'Compliance verification unavailable.');
    } finally {
      setComplianceLoading(false);
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

  const activePage = NAV_GROUPS.flatMap((group) => group.items).find((item) => item.id === activeTab);
  const exceptionStatusLabel = activeException?.status || (exceptionLoading ? 'LOADING' : 'UNAVAILABLE');
  const visibleEvents = events.filter((event) => {
    const query = eventSearch.trim().toLowerCase();
    if (!query) return true;
    return [
      event.event_type,
      event.source,
      event.destination,
      event.correlation_id,
      JSON.stringify(event.payload || {})
    ].some((value) => String(value || '').toLowerCase().includes(query));
  });
  const liveTaskRows = fleet
    .filter((robot) => robot.current_task)
    .map((robot) => ({
      id: `${robot.robot_id}-live`,
      taskId: robot.current_task,
      robotId: robot.robot_id,
      status: String(robot.state || 'unknown').toLowerCase(),
      description: robot.current_task,
      createdAt: null,
      origin: 'Live telemetry'
    }));
  const recentDispatchRows = dispatchHistory
    .map((entry) => ({
      id: entry.id,
      taskId: entry.result.task_id || 'Dispatch response',
      robotId: entry.result.assigned_robot_id || 'Unassigned',
      status: String(entry.result.status || 'unknown').toLowerCase(),
      description: entry.orderText,
      createdAt: entry.createdAt,
      origin: 'API dispatch response'
    }));
  const visibleTaskRows = [...liveTaskRows, ...recentDispatchRows].filter((task) => {
    if (taskFilter === 'all') return true;
    return task.status === taskFilter || (taskFilter === 'running' && task.status === 'moving');
  });

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
            <p>Warehouse Operations Control Center</p>
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
                placeholder="Enter your username"
                required
                autoComplete="username"
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
            </label>

            <button type="submit" className="glow-button full-width" disabled={loginLoading}>
              {loginLoading ? 'Authenticating...' : 'Sign In to Command Center →'}
            </button>
          </form>

          <p className="login-footnote">Sign in with an account configured by your WareFlow administrator.</p>
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

        <nav className="nav-list" aria-label="Main navigation">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.items.map((item) => (
                <button
                  key={item.id}
                  className={`nav-item ${activeTab === item.id ? 'active' : ''} ${item.id === 'emergency' ? 'nav-emergency' : ''}`}
                  onClick={() => {
                    setActiveTab(item.id);
                    if (item.id === 'events') loadEventHistory();
                    if (item.id === 'exception') loadExceptionData();
                  }}
                  aria-current={activeTab === item.id ? 'page' : undefined}
                >
                  <i aria-hidden="true" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    {item.Icon ? <item.Icon size={16} /> : null}
                  </i>
                  {item.label}
                  {item.id === 'events' && events.length > 0 && <small className="nav-count">{events.length}</small>}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile">
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <User size={13} />
              <strong>{currentUser}</strong>
              {userRole && <small className="role-label">{userRole}</small>}
            </span>
            <button className="text-button" onClick={handleLogout}>Sign Out</button>
          </div>
          <div className="system-status-indicator">
            <span className={`pulse-dot ${emergencyStop ? 'critical' : wsStatus === 'Connected' ? 'healthy' : 'offline'}`} />
            WS: {wsStatus}
          </div>
        </div>
      </aside>

      {/* WORKSPACE */}
      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="overline">WAREHOUSE OPERATIONS / <span className="tab-highlight">{activePage?.label || 'Dashboard'}</span></p>
            <h1>{activePage?.label === 'Dashboard' ? 'Warehouse Command Center' : activePage?.label}</h1>
          </div>

          <div className="header-actions">
            <button className="icon-button" onClick={() => { loadFleetData(); loadEventHistory(); }} title="Refresh fleet and events" aria-label="Refresh fleet and events" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
              <RefreshCw size={15} />
            </button>
            <button className="icon-button notification-button" onClick={() => { setActiveTab('events'); loadEventHistory(); }} title="View event notifications" aria-label="View event notifications" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bell size={15} />{events.length > 0 && <span className="notification-dot" />}
            </button>
            <button className="icon-button" onClick={handleLogout} title="Sign Out / Switch User" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
              <Lock size={15} />
            </button>
            <span className={`system-badge ${emergencyStop || wsStatus !== 'Connected' ? 'critical' : 'online'}`}>
              <b /> {wsStatus === 'Connected' ? 'LIVE' : wsStatus.toUpperCase()}
            </span>
            {emergencyStop ? (
              <button onClick={() => handleToggleEmergencyStop(true)} className="stop-button resume" disabled={emergencyBusy} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <Play size={14} /> Resume Fleet
              </button>
            ) : (
              <button onClick={() => setShowEmergencyModal(true)} className="stop-button stop" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <OctagonAlert size={14} /> EMERGENCY STOP
              </button>
            )}
          </div>
        </header>

        {globalError && (
          <div className="notice warning-notice">
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <AlertTriangle size={15} /> {globalError}
            </span>
            <button onClick={() => setGlobalError('')}><X size={14} /></button>
          </div>
        )}
        {activeTab === 'overview' && fleetError && (
          <div className="notice error">
            <span>{fleetError}</span>
            <button className="text-button" onClick={loadFleetData}>Retry</button>
          </div>
        )}

        {/* METRICS STRIP */}
        {activeTab === 'overview' && <section className="metric-grid">
          <div className="metric cyan">
            <div className="metric-icon"><Bot size={20} /></div>
            <div>
              <span>Total Robots</span>
              <strong>{fleetLoading ? '…' : fleetHasLoaded ? fleetSummary.total : '—'}</strong>
              <small>Live fleet telemetry</small>
            </div>
          </div>
          <div className="metric violet">
            <div className="metric-icon"><Activity size={20} /></div>
            <div>
              <span>Moving Robots</span>
              <strong>{fleetLoading ? '…' : fleetHasLoaded ? fleetSummary.moving : '—'}</strong>
              <small>Current simulation state</small>
            </div>
          </div>
          <div className="metric lime">
            <div className="metric-icon"><Zap size={20} /></div>
            <div>
              <span>Available Robots</span>
              <strong>{fleetLoading ? '…' : fleetHasLoaded ? fleetSummary.available : '—'}</strong>
              <small>Idle and enabled</small>
            </div>
          </div>
          <div className="metric cyan">
            <div className="metric-icon"><ListChecks size={20} /></div>
            <div>
              <span>Active Tasks</span>
              <strong>{fleetLoading ? '…' : fleetHasLoaded ? fleetSummary.activeTaskCount : '—'}</strong>
              <small>Reported by robot telemetry</small>
            </div>
          </div>
          <div className="metric orange">
            <div className="metric-icon"><AlertTriangle size={20} /></div>
            <div>
              <span>Active Exceptions</span>
              <strong>{exceptionLoading ? '…' : activeException ? (fleetSummary.exceptionActive ? 1 : 0) : '—'}</strong>
              <small>{fleetSummary.attention} robots need attention</small>
            </div>
          </div>
          <div className={`metric ${complianceResult ? (complianceResult.is_compliant ? 'lime' : 'orange') : 'violet'}`}>
            <div className="metric-icon"><ShieldCheck size={20} /></div>
            <div>
              <span>Latest Compliance</span>
              <strong>{complianceResult ? (complianceResult.is_compliant ? 'PASS' : 'FAIL') : '—'}</strong>
              <small>{complianceResult ? 'Last check result' : 'No check run this session'}</small>
            </div>
          </div>
        </section>}

        {activeTab === 'tasks' && (
          <section className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Live data</span>
              <h2>Task Monitoring</h2>
              <p>Robot task assignments come from live telemetry. Recent dispatch results are held in this browser session; this backend does not provide a durable task-list endpoint.</p>
            </div>
            <div className="card">
              <div className="card-header task-header">
                <div>
                  <p className="overline">TASKS FROM LIVE DATA</p>
                  <h3>Assignments & Dispatch Results</h3>
                </div>
                <button className="glow-button" onClick={() => setActiveTab('orders')}>+ Create Order</button>
              </div>
              <div className="filter-row" role="group" aria-label="Filter tasks">
                {['all', 'pending', 'running', 'completed', 'failed'].map((filter) => (
                  <button key={filter} className={`filter-chip ${taskFilter === filter ? 'selected' : ''}`} onClick={() => setTaskFilter(filter)}>
                    {filter[0].toUpperCase() + filter.slice(1)}
                  </button>
                ))}
              </div>
              {fleetError && <div className="notice error">{fleetError}<button className="text-button" onClick={loadFleetData}>Retry</button></div>}
              {eventError && <div className="notice error">{eventError}<button className="text-button" onClick={loadEventHistory}>Retry</button></div>}
              <div className="table-wrap">
                <table className="fleet-table operations-table">
                  <thead><tr><th>Task / Response</th><th>Description</th><th>Robot</th><th>Status</th><th>Source</th><th>Recorded</th></tr></thead>
                  <tbody>
                    {visibleTaskRows.map((task) => (
                      <tr key={task.id}>
                        <td><strong>{task.taskId}</strong></td>
                        <td>{task.description}</td>
                        <td>{task.robotId}</td>
                        <td><span className={`state-badge ${task.status}`}>{task.status}</span></td>
                        <td>{task.origin}</td>
                        <td>{task.createdAt ? new Date(task.createdAt).toLocaleString() : 'Live'}</td>
                      </tr>
                    ))}
                    {!fleetLoading && !visibleTaskRows.length && (
                      <tr><td colSpan="6" className="empty-cell">
                        {fleet.length ? 'No matching task assignments are currently reported.' : 'Fleet data is not available yet.'}
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'events' && (
          <section className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Event Bus</span>
              <h2>Event History</h2>
              <p>Audit-style view of messages returned by the backend EventBus history API.</p>
            </div>
            <div className="card">
              <div className="card-header">
                <div><p className="overline">BACKEND EVENT HISTORY</p><h3>{events.length} recent events</h3></div>
                <button className="secondary-button refresh-events" onClick={loadEventHistory} disabled={eventLoading}>
                  {eventLoading ? 'Loading…' : <><RefreshCw size={13} style={{ marginRight: '6px', verticalAlign: '-2px' }} /> Refresh events</>}
                </button>
              </div>
              <label className="search-field">
                <span className="visually-hidden">Search events</span>
                <input value={eventSearch} onChange={(e) => setEventSearch(e.target.value)} placeholder="Search event type, agent, payload…" />
              </label>
              {eventError && <div className="notice error">{eventError}<button className="text-button" onClick={loadEventHistory}>Retry</button></div>}
              {eventLoading && <p className="empty-state">Loading event history…</p>}
              {!eventLoading && !eventError && (
                <div className="event-table">
                  {visibleEvents.map((event) => (
                    <article className="event-entry" key={event.message_id || `${event.timestamp}-${event.event_type}`}>
                      <div className="event-entry-meta">
                        <span className={`priority-badge ${String(event.priority || 'normal').toLowerCase()}`}>{event.priority || 'normal'}</span>
                        <time>{event.timestamp ? new Date(event.timestamp).toLocaleString() : 'Timestamp unavailable'}</time>
                      </div>
                      <div className="event-entry-main">
                        <strong>{event.event_type || 'Unknown event'}</strong>
                        <span>{event.source || 'unknown source'} → {event.destination || 'unknown destination'}</span>
                      </div>
                      <details>
                        <summary>View event payload</summary>
                        <pre>{JSON.stringify(event.payload || {}, null, 2)}</pre>
                      </details>
                    </article>
                  ))}
                  {!visibleEvents.length && <p className="empty-state">{events.length ? 'No events match this search.' : 'No event records were returned by the API.'}</p>}
                </div>
              )}
            </div>
          </section>
        )}

        {activeTab === 'emergency' && (
          <section className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Safety control</span>
              <h2>Emergency Stop</h2>
              <p>Use the backend emergency control to halt or resume robot movement. This action is shared across the running simulation.</p>
            </div>
            <div className={`card emergency-control-card ${emergencyStop ? 'is-stopped' : ''}`}>
              <div className="emergency-state-icon">{emergencyStop ? <OctagonAlert size={36} /> : <ShieldAlert size={36} />}</div>
              <div>
                <p className="overline">SYSTEM CONTROL</p>
                <h3>{emergencyStop === true ? 'EMERGENCY STOP ACTIVE' : emergencyStop === false && fleetHasLoaded ? 'Fleet operations are enabled' : 'Backend status unavailable'}</h3>
                <p>{emergencyStop === true ? 'Robot movement is halted by the backend simulation.' : emergencyStop === false && fleetHasLoaded ? 'An emergency stop immediately halts robot movement in the backend simulation.' : 'The backend has not returned the current emergency-stop state. You can still issue the stop command if needed.'}</p>
                {emergencyStop
                  ? <button className="stop-button resume" disabled={emergencyBusy} onClick={() => handleToggleEmergencyStop(true)}>
                      {emergencyBusy ? 'Resuming…' : <><Play size={13} style={{ marginRight: '6px' }} /> Resume System</>}
                    </button>
                  : <button className="stop-button stop emergency-action" onClick={() => setShowEmergencyModal(true)}>
                      <OctagonAlert size={14} style={{ marginRight: '6px' }} /> Stop all robots
                    </button>}
              </div>
            </div>
            <div className="card margin-top"><h3>Control status</h3><p className="subtle-text">Backend-reported status: <strong>{emergencyStop === null ? 'Unavailable' : emergencyStop ? 'Stopped' : 'Running'}</strong>. WebSocket: <strong>{wsStatus}</strong>.</p></div>
          </section>
        )}

        {activeTab === 'commercial' && (
          <section className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Product information</span>
              <h2>Plans & Deployment</h2>
              <p>Proposed Commercial Pricing — illustrative university-project pricing, not actual market revenue or a production offer.</p>
            </div>
            <div className="pricing-grid">
              {[
                { name: 'Research / Demo', price: 'LKR 0', note: 'For coursework and evaluation', features: ['Basic simulation', 'Limited robots', 'Demonstration features'] },
                { name: 'Starter', price: 'LKR 25,000', period: '/ month', note: 'Proposed pricing', features: ['Web dashboard', 'Basic task planning', 'Robot monitoring', 'Basic compliance'] },
                { name: 'Professional', price: 'LKR 75,000', period: '/ month', note: 'Proposed pricing', features: ['Multi-agent coordination', 'RAG / SOP compliance', 'Exception handling', 'Real-time telemetry and event history'] },
                { name: 'Enterprise', price: 'Custom', note: 'Proposed pricing', features: ['Private or on-premise deployment', 'Large robot fleets', 'Custom API integrations', 'Custom workflows and support'] }
              ].map((tier) => (
                <article className="card pricing-card" key={tier.name}>
                  <p className="overline">{tier.note}</p><h3>{tier.name}</h3>
                  <strong className="price">{tier.price}</strong>{tier.period && <span className="price-period">{tier.period}</span>}
                  <ul>{tier.features.map((feature) => <li key={feature}>{feature}</li>)}</ul>
                </article>
              ))}
            </div>
            <div className="commercial-grid">
              <div className="card"><p className="overline">TARGET MARKETS</p><h3>Who it serves</h3><div className="tag-list">{['Logistics companies', 'E-commerce fulfilment', 'Distribution centres', 'Manufacturing warehouses', '3PL companies'].map((market) => <span key={market}>{market}</span>)}</div></div>
              <div className="card"><p className="overline">DEPLOYMENT MODELS</p><h3>Deployment options (proposed)</h3><div className="deployment-list">{[['Cloud SaaS', 'Managed application and service hosting'], ['On-Premise', 'Customer-managed infrastructure'], ['Hybrid', 'Cloud management with local operations']].map(([name, detail]) => <div key={name}><strong>{name}</strong><span>{detail}</span></div>)}</div></div>
            </div>
            <div className="card product-positioning"><p className="overline">PRODUCT POSITIONING</p><p>WareFlow AI is an AI-powered warehouse operations and robot fleet coordination platform that integrates task planning, SOP compliance, exception handling, telemetry monitoring and human oversight into a unified control centre.</p><small>WareFlow AI is software for coordinating and managing warehouse robot fleets; it does not manufacture robots.</small></div>
          </section>
        )}

        {/* TAB 1: OVERVIEW & MAP */}
        {activeTab === 'overview' && (
          <div className="tab-view fade-in">
            <ControlRoom
              fleet={mapFleet}
              blockedCells={mapBlockedCells}
              selectedRobotId={selectedRobotId}
              onFullscreen={(focus = false) => {
                setSimulationInitialFocus(Boolean(focus));
                setSimulationOpen(true);
                try {
                  if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen().catch(() => {});
                  }
                } catch (e) {}
              }}
              onClear={handleClearObstacles}
              events={activityLogs}
              mockMode={mockMode}
              setMockMode={setMockMode}
              summary={fleetSummary}
              highlightedTargetId={mapTargetHighlight}
              onTargetSelect={setMapTargetHighlight}
              activeOrderRoute={activeOrderRoute}
              activeOrderRoutes={activeOrderRoutes}
              taskQueue={taskQueue}
            />
          </div>
        )}
        {/* TAB 2: TASK PLANNER */}
        {(activeTab === 'orders' || activeTab === 'planning') && (
          <div className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Member 1 Agent</span>
              <h2>Create Warehouse Order</h2>
              <p>Submit a natural-language instruction to the LangGraph planning engine. Source and destination markers are displayed automatically on the Digital Twin floor.</p>
            </div>

            <div className="planner-workspace">
              <div className="card">
                <p className="overline">NATURAL LANGUAGE OPERATION DISPATCH</p>
                <div className="preset-chips">
                  {PRESET_ORDERS.map((p, i) => {
                    const PresetIcon = p.Icon;
                    return (
                      <button key={i} className="chip" onClick={() => setOrderText(p.text)}>
                        {PresetIcon && <PresetIcon size={13} style={{ marginRight: '6px', verticalAlign: '-2px' }} />}
                        {p.label}
                      </button>
                    );
                  })}
                </div>

                <form onSubmit={handleDispatchOrder}>
                  <textarea
                    rows={4}
                    maxLength={500}
                    value={orderText}
                    onChange={(e) => setOrderText(e.target.value)}
                    placeholder="e.g. Move 5 pallets from Shelf A2 to Packing Station 3."
                    className="order-input"
                  />
                  <div className="planner-submit-bar">
                    <span className="char-count">{orderText.length}/500 chars</span>
                    <button type="submit" className="glow-button" disabled={planning || !orderText.trim()}>
                      {planning ? 'Running LangGraph Planner...' : <><Zap size={14} style={{ marginRight: '6px', verticalAlign: '-2px' }} /> Dispatch Task</>}
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
                      <div className="entity"><span>Item:</span> <strong>{plan.parsed_order.item || 'Not returned'}</strong></div>
                      <div className="entity"><span>Qty:</span> <strong>{plan.parsed_order.quantity ?? 'Not returned'}</strong></div>
                      <div className="entity"><span>Route:</span> <strong>{plan.parsed_order.source || 'Not returned'} → {plan.parsed_order.destination || 'Not returned'}</strong></div>
                      <div className="entity"><span>Assigned AMR:</span> <strong className="highlight-amr">{plan.assigned_robot_id || 'None'}</strong></div>
                    </div>
                  )}

                  <div className="workflow-progress" aria-label="Order processing evidence">
                    {[
                      ['Order received', true, 'Dispatch API accepted the request'],
                      ['Order parsed', Boolean(plan.parsed_order), plan.parsed_order ? 'Parsed entities returned by planner' : 'No parsed order returned'],
                      ['Tasks decomposed', Boolean(plan.subtasks?.length), plan.subtasks?.length ? `${plan.subtasks.length} subtasks returned` : 'No subtasks returned'],
                      ['Compliance', null, 'Inspect the Event History for the backend compliance event'],
                      ['Robot assignment', Boolean(plan.assigned_robot_id), plan.assigned_robot_id || 'No robot assigned'],
                      ['Execution', ['assigned', 'running', 'completed'].includes(String(plan.status).toLowerCase()), `API status: ${plan.status || 'not provided'}`]
                    ].map(([label, complete, detail], index) => (
                      <div className={`workflow-step ${complete === null ? 'unknown' : complete ? 'complete' : 'incomplete'}`} key={label}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                          {complete === null ? 'i' : complete ? <Check size={11} /> : index + 1}
                        </span>
                        <div><strong>{label}</strong><small>{detail}</small></div>
                      </div>
                    ))}
                  </div>
                  {plan.requires_escalation && (
                    <div className="notice warning-notice">
                      <strong>Human review required.</strong> {plan.escalation_reason || 'The planner requested operator review.'}
                    </div>
                  )}
                  <button className="text-button" onClick={() => { setActiveTab('events'); loadEventHistory(); }}>View related backend events →</button>

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

        {/* TAB: EXCEPTION HANDLING (MEMBER 2) */}
        {activeTab === 'exception' && (
          <div className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Member 2 Agent</span>
              <h2>Exception Handling & Anomaly Recovery Engine</h2>
              <p>Autonomous robot telemetry monitoring, fault recovery decisioning, and A* detour recalculation.</p>
            </div>

            <div className="dashboard-grid">
              <div className="card">
                <div className="card-header">
                  <div>
                    <p className="overline">EXCEPTION DEMO CONTROLS</p>
                    <h3>Manual Anomaly Injection for {selectedRobot?.robot_id || 'AMR'}</h3>
                  </div>
                </div>

                <p style={{ color: '#94a3b8', fontSize: '13px' }}>
                  Inject physical fault conditions into the selected robot. The simulation loop and Exception Handling Agent will autonomously detect the condition, evaluate SOP rules, and apply recovery actions.
                </p>

                <div className="anomaly-actions-bar" style={{ marginTop: '18px' }}>
                  <button
                    type="button"
                    className="anomaly-btn stuck"
                    disabled={anomalyLoading}
                    onClick={() => handleInjectAnomaly('stuck')}
                    style={{ padding: '12px 18px', fontSize: '12px' }}
                  >
                    <AlertTriangle size={13} style={{ marginRight: '6px', verticalAlign: '-2px' }} /> Force Robot Stuck (12s stall)
                  </button>
                  <button
                    type="button"
                    className="anomaly-btn battery"
                    disabled={anomalyLoading}
                    onClick={() => handleInjectAnomaly('low_battery')}
                    style={{ padding: '12px 18px', fontSize: '12px' }}
                  >
                    <Battery size={13} style={{ marginRight: '6px', verticalAlign: '-2px' }} /> Drain Battery to 10% (Critical)
                  </button>
                  <button
                    type="button"
                    className="anomaly-btn block"
                    disabled={anomalyLoading}
                    onClick={() => handleInjectAnomaly('block_path')}
                    style={{ padding: '12px 18px', fontSize: '12px' }}
                  >
                    <Construction size={13} style={{ marginRight: '6px', verticalAlign: '-2px' }} /> Place Obstacle on Path
                  </button>
                  <button
                    type="button"
                    className="anomaly-btn clear"
                    onClick={handleClearObstacles}
                    style={{ padding: '12px 18px', fontSize: '12px' }}
                  >
                    <RotateCcw size={13} style={{ marginRight: '6px', verticalAlign: '-2px' }} /> Clear All Obstacles
                  </button>
                </div>

                <div className="recovery-details-box" style={{ marginTop: '20px' }}>
                  <h4 style={{ margin: '0 0 8px', color: '#5ee2b1' }}>Recovery Decision Architecture (Deterministic)</h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', color: '#cbd5e1', fontSize: '12px', lineHeight: '1.8' }}>
                    <li><strong>ROBOT_STUCK (Stall &gt; 10s):</strong> Evaluates obstacle map → Calculates dynamic A* detour avoiding blocked cells → Resumes movement.</li>
                    <li><strong>LOW_BATTERY (&lt; 15%):</strong> Aborts current task → Finds closest warehouse charger via Manhattan distance → Routes to dock.</li>
                    <li><strong>PATH_BLOCKED / MOTOR_STALL:</strong> Recovery behavior depends on the backend agent decision; inspect the returned lifecycle and event history.</li>
                  </ul>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div>
                    <p className="overline">ACTIVE LIFECYCLE</p>
                    <h3>Recovery Pipeline Status</h3>
                  </div>
                  <span className={`status-pill-lg ${exceptionStatusLabel.toLowerCase()}`} style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    font: '10px "DM Mono", monospace',
                    background: activeException?.status === 'RECOVERING' ? '#1d4ed8' : activeException?.status === 'RESOLVED' ? '#047857' : activeException?.status === 'DETECTED' ? '#b91c1c' : '#1e293b',
                    color: '#fff'
                  }}>
                    {exceptionStatusLabel}
                  </span>
                </div>

                {exceptionError && <div className="notice error">{exceptionError}<button className="text-button" onClick={loadExceptionData}>Retry</button></div>}
                <div className="exception-stepper">
                  <div className={`step-badge ${['DETECTED', 'ANALYZING', 'RECOVERING', 'RESOLVED'].includes(activeException?.status) ? 'active-step' : ''}`}>
                    1. DETECTED
                  </div>
                  <div className={`step-badge ${['ANALYZING', 'RECOVERING', 'RESOLVED'].includes(activeException?.status) ? 'active-step analyzing' : ''}`}>
                    2. ANALYZING
                  </div>
                  <div className={`step-badge ${['RECOVERING', 'RESOLVED'].includes(activeException?.status) ? 'active-step recovering' : ''}`}>
                    3. RECOVERING
                  </div>
                  <div className={`step-badge ${activeException?.status === 'RESOLVED' ? 'active-step resolved' : ''}`}>
                    4. RESOLVED
                  </div>
                </div>

                {activeException?.anomaly ? (
                  <div className="telemetry-rows" style={{ marginTop: '16px' }}>
                    <div className="t-row"><span>Affected AMR</span><strong>{activeException.anomaly.robot_id}</strong></div>
                    <div className="t-row"><span>Anomaly Type</span><strong style={{ color: '#f87171' }}>{activeException.anomaly.event_type || activeException.anomaly.anomaly_type}</strong></div>
                    <div className="t-row"><span>Severity</span><strong>{activeException.anomaly.severity || 'Not provided'}</strong></div>
                    <div className="t-row"><span>Decision</span><strong style={{ color: '#38bdf8' }}>{activeException.recovery?.action_type || 'No recovery action returned yet'}</strong></div>
                    <div className="t-row"><span>Action Notes</span><small style={{ color: '#94a3b8' }}>{activeException.recovery?.notes || 'No recovery notes returned yet'}</small></div>
                  </div>
                ) : exceptionLoading ? (
                  <p className="empty-state">Loading exception lifecycle…</p>
                ) : exceptionError ? null : (
                  <p className="overline" style={{ marginTop: '20px' }}>
                    No active exception is currently reported by the simulation.
                  </p>
                )}
              </div>
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
                      <th>LAST TELEMETRY</th>
                      <th>CAPABILITIES</th>
                      <th>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fleet.map((r) => (
                      <tr key={r.robot_id} className={selectedRobotId === r.robot_id ? 'active-row' : ''}>
                        <td><button className="table-link" onClick={() => setSelectedRobotId(r.robot_id)}>{r.robot_id}</button></td>
                        <td>{r.name || `Robot ${r.robot_id}`}</td>
                        <td><span className={`state-badge ${String(r.state).toLowerCase()}`}>{r.state}</span></td>
                        <td>
                          <div className="battery-cell">
                            {r.battery !== null && r.battery !== undefined && Number.isFinite(Number(r.battery)) && <div className="battery-mini"><i style={{ width: `${Math.max(0, Math.min(100, Number(r.battery)))}%` }} /></div>}
                            {r.battery === null || r.battery === undefined || !Number.isFinite(Number(r.battery)) ? 'Not provided' : `${r.battery}%`}
                          </div>
                        </td>
                        <td>[{r.x ?? r.position?.[0] ?? '—'}, {r.y ?? r.position?.[1] ?? '—'}]</td>
                        <td>{r.current_task || 'None'}</td>
                        <td><small>{r.last_telemetry_at ? new Date(r.last_telemetry_at).toLocaleTimeString() : 'Not provided'}</small></td>
                        <td><small>{r.capabilities?.length ? r.capabilities.join(', ') : 'Not provided'}</small></td>
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
                    {!fleetLoading && !fleet.length && <tr><td colSpan="9" className="empty-cell">No robots were returned by the fleet API.</td></tr>}
                  </tbody>
                </table>
              </div>
              {fleetError && <div className="notice error">{fleetError}<button className="text-button" onClick={loadFleetData}>Retry</button></div>}
            </div>
          </div>
        )}

        {/* TAB 4: COMPLIANCE */}
        {activeTab === 'compliance' && (
          <div className="tab-view fade-in">
            <div className="section-title-box">
              <span className="member-tag">Member 3 RAG Agent</span>
              <h2>Knowledge & SOP Compliance Gate</h2>
              <p>Validates mission metrics against ingested Qdrant vector database regulations and safety limits.</p>
            </div>

            <div className="dashboard-grid">
              {/* Left Column: Mission Parameters Form & Verification Result */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <h3>Pre-Flight Mission Parameters</h3>
                    <p className="subtle-text" style={{ fontSize: '11.5px', marginTop: '2px' }}>
                      Configure mission values to test deterministic safety boundaries and Qdrant RAG rules.
                    </p>
                  </div>
                  <span className="badge-member">SOP Gate</span>
                </div>

                {/* Quick Presets Bar */}
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '10.5px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
                    Quick Test Scenarios
                  </div>
                  <div className="compliance-presets-bar">
                    {COMPLIANCE_PRESETS.map((p) => {
                      const isActive =
                        complianceForm.payload_weight === p.payload_weight &&
                        complianceForm.speed === p.speed &&
                        complianceForm.is_hazmat === p.is_hazmat &&
                        complianceForm.target_zone === p.target_zone;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          className={`compliance-preset-btn ${isActive ? 'active' : ''}`}
                          onClick={() => {
                            setComplianceForm({
                              payload_weight: p.payload_weight,
                              speed: p.speed,
                              is_hazmat: p.is_hazmat,
                              target_zone: p.target_zone
                            });
                            setComplianceResult(null);
                          }}
                        >
                          <span className={`preset-dot ${p.type}`} />
                          {p.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <form onSubmit={handleCheckCompliance} className="compliance-form">
                  <div className="compliance-form-grid">
                    {/* Payload Weight */}
                    <div className="compliance-field">
                      <div className="compliance-field-label">
                        <Package size={14} color="#38bdf8" />
                        Payload Weight
                      </div>
                      <div className="compliance-input-wrap">
                        <input
                          type="number"
                          min="0"
                          step="0.5"
                          value={complianceForm.payload_weight}
                          onChange={(e) => setComplianceForm({ ...complianceForm, payload_weight: Number(e.target.value) })}
                          required
                        />
                        <span className="compliance-unit-badge">kg</span>
                      </div>
                      <span className="compliance-field-hint">Standard: ≤50kg | Heavy AMR Cap: ≤100kg</span>
                    </div>

                    {/* Speed */}
                    <div className="compliance-field">
                      <div className="compliance-field-label">
                        <Activity size={14} color="#38bdf8" />
                        Operating Speed
                      </div>
                      <div className="compliance-input-wrap">
                        <input
                          type="number"
                          step="0.1"
                          min="0.1"
                          value={complianceForm.speed}
                          onChange={(e) => setComplianceForm({ ...complianceForm, speed: Number(e.target.value) })}
                          required
                        />
                        <span className="compliance-unit-badge">m/s</span>
                      </div>
                      <span className="compliance-field-hint">Standard aisle: ≤2.0 m/s | Hazmat: ≤0.8 m/s</span>
                    </div>
                  </div>

                  {/* Target Zone */}
                  <div className="compliance-field">
                    <div className="compliance-field-label">
                      <Bot size={14} color="#38bdf8" />
                      Target Warehouse Zone
                    </div>
                    <select
                      value={complianceForm.target_zone}
                      onChange={(e) => setComplianceForm({ ...complianceForm, target_zone: e.target.value })}
                      className="compliance-select"
                    >
                      {TARGET_GROUPS.map((grp) => (
                        <optgroup key={grp.category} label={grp.category}>
                          {grp.items.map((it) => (
                            <option key={it.id} value={it.name}>
                              {it.name} ({it.x}, {it.y})
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                    <span className="compliance-field-hint">Monitors destination restrictions and aisle transit regulations</span>
                  </div>

                  {/* Hazmat Toggle Card */}
                  <div
                    className={`hazmat-toggle-card ${complianceForm.is_hazmat ? 'active' : ''}`}
                    onClick={() => setComplianceForm({ ...complianceForm, is_hazmat: !complianceForm.is_hazmat })}
                  >
                    <input
                      type="checkbox"
                      checked={complianceForm.is_hazmat}
                      onChange={(e) => setComplianceForm({ ...complianceForm, is_hazmat: e.target.checked })}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <div className="hazmat-icon-badge">
                      <AlertTriangle size={18} />
                    </div>
                    <div className="hazmat-info">
                      <div className="hazmat-title">Hazardous Material Cargo (Hazmat)</div>
                      <div className="hazmat-desc">
                        Enforces mandatory speed cap ≤ 0.8 m/s and isolated aisle routing under SOP-HAZ-002.
                      </div>
                    </div>
                  </div>

                  {/* Submit Button */}
                  <button type="submit" className="compliance-verify-btn" disabled={complianceLoading}>
                    <ShieldCheck size={18} />
                    {complianceLoading ? 'Querying Qdrant Vector DB & SOPs…' : 'Verify Operation Compliance'}
                  </button>
                </form>

                {/* Verification Result Card */}
                {complianceResult && (
                  <div className={`compliance-result-card ${complianceResult.is_compliant ? 'pass' : 'fail'}`}>
                    <div className="compliance-result-header">
                      {complianceResult.is_compliant ? (
                        <>
                          <Check size={20} color="#10b981" />
                          <span>APPROVED — COMPLIANT WITH WAREHOUSE SOPS</span>
                        </>
                      ) : (
                        <>
                          <X size={20} color="#ef4444" />
                          <span>SAFETY VIOLATIONS DETECTED — DISPATCH BLOCKED</span>
                        </>
                      )}
                    </div>

                    {complianceResult.violations?.length > 0 && (
                      <div className="compliance-violations-list">
                        {complianceResult.violations.map((v, i) => (
                          <div key={i} className="compliance-violation-item">
                            • {v}
                          </div>
                        ))}
                      </div>
                    )}

                    {complianceResult.sop_citations?.length > 0 && (
                      <div className="sop-evidence-section">
                        <div className="sop-evidence-title">
                          <ShieldCheck size={14} color="#38bdf8" />
                          Qdrant RAG Verified Citations
                        </div>
                        <div className="sop-citation-chips">
                          {complianceResult.sop_citations.map((citation) => (
                            <span key={citation} className="sop-citation-badge">
                              {citation}
                            </span>
                          ))}
                        </div>
                        {complianceResult.sop_evidence?.map((evidence, index) => (
                          <details key={`${evidence.sop_id || index}-${index}`} className="sop-evidence-detail">
                            <summary>
                              {evidence.filename || evidence.sop_id || 'Retrieved SOP'} — similarity {typeof evidence.similarity_score === 'number' ? evidence.similarity_score.toFixed(3) : 'verified'}
                            </summary>
                            <p>{evidence.content}</p>
                          </details>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right Column: Ingested SOP Reference Guidelines & Architecture */}
              <div className="card compliance-reference-card">
                <div className="card-header">
                  <div>
                    <h3>Active Warehouse Safety Regulations</h3>
                    <p className="subtle-text" style={{ fontSize: '11.5px', marginTop: '2px' }}>
                      Standard Operating Procedures ingested into Qdrant & evaluated by Member 3.
                    </p>
                  </div>
                  <span className="system-badge healthy">Active</span>
                </div>

                <div className="sop-rules-list">
                  {/* Rule 1 */}
                  <div className="sop-rule-item">
                    <div className="sop-rule-head">
                      <span className="sop-rule-code">SOP-SPD-003</span>
                      <span className="sop-rule-badge">Velocity & Load</span>
                    </div>
                    <div className="sop-rule-title">Speed & Payload Constraints</div>
                    <p className="sop-rule-desc">
                      Standard payloads are limited to 50kg. Heavy freight must not exceed 100kg AMR structural capacity. Standard aisle velocity capped at 2.0 m/s.
                    </p>
                  </div>

                  {/* Rule 2 */}
                  <div className="sop-rule-item">
                    <div className="sop-rule-head">
                      <span className="sop-rule-code">SOP-HAZ-002</span>
                      <span className="sop-rule-badge warning">Hazmat Protocol</span>
                    </div>
                    <div className="sop-rule-title">Hazardous Materials Transport</div>
                    <p className="sop-rule-desc">
                      Hazardous substances (chemicals, flammables) strictly enforce a velocity ceiling of 0.8 m/s to prevent spillage, and require designated containment aisles.
                    </p>
                  </div>

                  {/* Rule 3 */}
                  <div className="sop-rule-item">
                    <div className="sop-rule-head">
                      <span className="sop-rule-code">SOP-BAT-001</span>
                      <span className="sop-rule-badge battery">Power Safety</span>
                    </div>
                    <div className="sop-rule-title">AMR Battery Reserve Gate</div>
                    <p className="sop-rule-desc">
                      Robots must possess at least 15% charge to accept any newly dispatched order. At ≤ 20%, AMRs enter critical return-to-charger mode.
                    </p>
                  </div>
                </div>

                {/* RAG Architecture Summary */}
                <div className="rag-architecture-box">
                  <strong>How the Compliance Gate Works:</strong>
                  <div style={{ marginTop: '4px' }}>
                    1. <strong>Deterministic Rules Engine:</strong> Validates numeric boundaries (speed, weight, battery reserves) in microseconds.
                  </div>
                  <div style={{ marginTop: '2px' }}>
                    2. <strong>Qdrant Semantic RAG:</strong> Generates vector embeddings for mission parameters and queries official warehouse SOP documents.
                  </div>
                  <div style={{ marginTop: '2px' }}>
                    3. <strong>Pre-Dispatch Gate:</strong> Blocks non-compliant tasks and displays cited evidence for safety audit logs.
                  </div>
                </div>
              </div>
            </div>
            {globalError && <div className="notice error">{globalError}</div>}
          </div>
        )}

        {showEmergencyModal && (
          <div className="modal-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowEmergencyModal(false); }}>
            <section className="modal-card card emergency-modal" role="dialog" aria-modal="true" aria-labelledby="emergency-modal-title">
              <div className="emergency-state-icon" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <OctagonAlert size={32} />
              </div>
              <p className="overline">DANGEROUS ACTION</p>
              <h3 id="emergency-modal-title">Emergency Stop</h3>
              <p>This will stop active robot operations in the connected simulation. Continue only if you intend to halt the fleet.</p>
              <div className="modal-actions">
                <button type="button" className="secondary-button" onClick={() => setShowEmergencyModal(false)} disabled={emergencyBusy}>Cancel</button>
                <button type="button" className="stop-button stop" onClick={() => handleToggleEmergencyStop(false)} disabled={emergencyBusy}>{emergencyBusy ? 'Stopping…' : 'STOP ALL ROBOTS'}</button>
              </div>
            </section>
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
      {simulationOpen && (
        <SimulationView
          fleet={mapFleet}
          blockedCells={mapBlockedCells}
          selectedRobotId={selectedRobotId}
          onSelectRobot={setSelectedRobotId}
          onClose={() => setSimulationOpen(false)}
          onInject={handleInjectAnomaly}
          onClear={handleClearObstacles}
          events={activityLogs}
          mockMode={mockMode}
          setMockMode={setMockMode}
          initialMapFocus={simulationInitialFocus}
          highlightedTargetId={mapTargetHighlight}
          onTargetSelect={setMapTargetHighlight}
          activeOrderRoute={activeOrderRoute}
          activeOrderRoutes={activeOrderRoutes}
          taskQueue={taskQueue}
        />
      )}

    </div>
  );
}

export default App;