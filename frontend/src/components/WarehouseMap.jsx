import { useEffect, useMemo, useRef, useState } from 'react';
import { Zap, AlertTriangle, Package, ArrowRight, Pause, X, ChevronUp, Flag } from './icons';

const COLS = 20;
const ROWS = 15;

// Precision coordinate calibration for warehouse-grid-bg.jpg (1024x1024)
export const cellToPixels = (x, y) => ({
  x: 63 + Number(x) * 44.84,
  y: 83 + Number(y) * 59.8
});

export const cellToPercent = (x, y) => ({
  left: `${((63 + Number(x) * 44.84) / 1024) * 100}%`,
  top: `${((83 + Number(y) * 59.8) / 1024) * 100}%`
});

export const ACCENTS = {
  R1: '#00f0ff', // Electric Neon Cyan
  R2: '#00ff88', // Vivid Neon Lime Green (Peak Contrast & Luminance)
  R3: '#ef4444', // Danger Crimson (Stuck) / Safety Gold (#fbbf24) when rerouted
  R4: '#d946ef', // Electric Magenta / Orchid
  default: '#00f0ff'
};

export const statusMeta = (robot) => {
  const state = String(robot.state || robot.status || 'idle').toLowerCase();
  const isStuck = robot.enabled === false || state === 'stuck' || state === 'error';
  const isCharging = state === 'charging';
  const isPicking = state === 'picking' || Boolean(robot.payload);
  const isMoving = state === 'moving';
  const isRerouting = Boolean(robot.is_rerouted || robot.detour_path || robot.avoiding_obstacle);

  if (isStuck) return { key: 'stuck', icon: 'x', label: 'STUCK', sublabel: 'Cannot proceed', color: '#ef4444' };
  if (isCharging) return { key: 'charging', icon: 'zap', label: 'CHARGING', sublabel: 'Recharging battery', color: '#22c55e' };
  if (isPicking) return { key: 'picking', icon: 'package', label: 'PICKING', sublabel: 'Collecting item from shelf', color: '#00ff88' };
  if (isRerouting) return { key: 'rerouting', icon: 'alert', label: 'ATTENTION', sublabel: 'Obstacle detected ahead', color: '#fbbf24' };
  if (isMoving) return { key: 'moving', icon: 'arrow-right', label: 'MOVING', sublabel: 'Following assigned route', color: ACCENTS[robot.robot_id] || '#00f0ff' };
  return { key: 'idle', icon: 'pause', label: 'IDLE', sublabel: 'Waiting for next task', color: '#00f0ff' };
};

function cellPoint(cell) {
  if (Array.isArray(cell) && cell.length >= 2) return { x: Number(cell[0]), y: Number(cell[1]) };
  if (cell && typeof cell === 'object' && 'x' in cell && 'y' in cell) return { x: Number(cell.x), y: Number(cell.y) };
  return null;
}

function robotPoint(robot) {
  return {
    x: Number(robot.x ?? robot.position?.[0] ?? 0),
    y: Number(robot.y ?? robot.position?.[1] ?? 0)
  };
}

function useInterpolatedRobots(robots) {
  const targetRef = useRef(new Map());
  const currentRef = useRef(new Map());
  const [rendered, setRendered] = useState([]);

  useEffect(() => {
    robots.forEach((robot) => {
      const target = robotPoint(robot);
      const current = currentRef.current.get(robot.robot_id);
      targetRef.current.set(robot.robot_id, {
        ...target,
        since: performance.now(),
        from: current ? { x: current.x, y: current.y } : target
      });
      if (!current) currentRef.current.set(robot.robot_id, { ...target, heading: 0 });
    });
  }, [robots]);

  useEffect(() => {
    let frame;
    const draw = (now) => {
      const next = robots.map((robot) => {
        const target = targetRef.current.get(robot.robot_id) || {
          ...robotPoint(robot),
          since: now,
          from: robotPoint(robot)
        };
        const progress = Math.min(1, (now - target.since) / 600);
        const eased = 1 - Math.pow(1 - progress, 3);
        const x = target.from.x + (target.x - target.from.x) * eased;
        const y = target.from.y + (target.y - target.from.y) * eased;
        const old = currentRef.current.get(robot.robot_id) || { x, y, heading: 0 };
        const dx = target.x - old.x;
        const dy = target.y - old.y;
        const heading = Math.abs(dx) + Math.abs(dy) > 0.01 ? (Math.atan2(dy, dx) * 180) / Math.PI + 90 : old.heading;
        const accent = ACCENTS[robot.robot_id] || ACCENTS.default;
        const value = { ...robot, x, y, heading, accent };
        currentRef.current.set(robot.robot_id, value);
        return value;
      });
      setRendered(next);
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [robots]);

  return rendered;
}

export function RobotSprite({ robot, selected, onSelect }) {
  const meta = statusMeta(robot);
  const battery = Math.round(Number(robot.battery ?? 100));
  const isMoving = meta.key === 'moving';
  const isStuck = meta.key === 'stuck';
  const isCharging = meta.key === 'charging';
  const isPicking = meta.key === 'picking';
  const isAttention = meta.key === 'rerouting';

  const posStyle = cellToPercent(robot.x, robot.y);

  // Battery gauge color
  const batteryColor =
    battery > 60 ? '#00d4ff' : battery >= 30 ? '#f59e0b' : '#ef4444';

  return (
    <div
      className={`amr-v2-container ${meta.key} ${selected ? 'is-selected' : ''}`}
      style={{
        ...posStyle,
        '--robot-accent': meta.color,
        '--robot-heading': `${robot.heading}deg`
      }}
      onClick={() => onSelect?.(robot.robot_id)}
      role="button"
      tabIndex={0}
      title={`${robot.robot_id} · ${meta.label} · Battery: ${battery}%`}
    >
      {/* 1. Dynamic State Underglow / Radar Shockwave */}
      <div className="amr-underglow" />
      {isStuck && (
        <div className="amr-radar-wave">
          <span className="radar-ring r1" />
          <span className="radar-ring r2" />
          <span className="radar-ring r3" />
        </div>
      )}

      {/* 2. Top Battery Gauge Arc */}
      <div className="amr-battery-arc">
        <svg viewBox="0 0 44 24" className="battery-gauge-svg">
          <path
            d="M 6 20 A 16 16 0 0 1 38 20"
            fill="none"
            stroke="rgba(255,255,255,0.18)"
            strokeWidth="3.2"
            strokeLinecap="round"
          />
          <path
            d="M 6 20 A 16 16 0 0 1 38 20"
            fill="none"
            stroke={batteryColor}
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeDasharray="50"
            strokeDashoffset={`${50 - (battery / 100) * 50}`}
          />
        </svg>
        <span className="battery-pct-label" style={{ color: batteryColor }}>
          <i className="battery-icon"><Zap size={10} /></i>
          {battery}%
        </span>
      </div>

      {/* 3. AMR Chassis (Photorealistic Puck Design) */}
      <div className="amr-chassis">
        {/* Metal Corner Bumper Guards */}
        <span className="bumper corner-tl" />
        <span className="bumper corner-tr" />
        <span className="bumper corner-bl" />
        <span className="bumper corner-br" />

        {/* State LED Light Bars (Sides and Front) */}
        <span className="led-rail led-left" />
        <span className="led-rail led-right" />
        <span className="led-rail led-front" />

        {/* Center Circular Sensor Hub with Robot ID */}
        <div className="amr-sensor-hub">
          <div className="sensor-lens" />
          <strong className="robot-id-text">{robot.robot_id}</strong>
        </div>

        {/* Directional Chevron if Moving */}
        {isMoving && <span className="direction-chevron"><ChevronUp size={11} strokeWidth={2.5} /></span>}

        {/* 3D Cargo Box if Picking / Carrying */}
        {isPicking && (
          <div className="cargo-box-3d" title="Payload Box">
            <div className="box-face box-top" />
            <div className="box-face box-front">
              <span className="box-tape" />
            </div>
            <div className="box-face box-side" />
          </div>
        )}
      </div>

      {/* 4. State Floating Badges / Speech Callouts */}
      {isStuck && <span className="amr-state-icon-badge error"><X size={10} strokeWidth={3} /></span>}
      {isAttention && <span className="amr-state-icon-badge warning"><AlertTriangle size={10} /></span>}
      {isCharging && <span className="amr-state-icon-badge charging"><Zap size={10} /></span>}

      {/* 5. Laser Alignment Beam to Shelf for Picking */}
      {isPicking && <div className="shelf-laser-beam" />}

      {/* 6. Speech Bubble for Rerouting / Exceptions */}
      {(robot.rerouting_msg || (isStuck && selected)) && (
        <div className="amr-speech-callout">
          <span>{robot.rerouting_msg || `Rerouting ${robot.robot_id} via Aisle B`}</span>
        </div>
      )}
    </div>
  );
}

const ROUTE_CONFIGS = {
  R1: {
    color: '#00f0ff', // Electric Neon Cyan
    halo: '#00f0ff',
    glowFilter: 'url(#glow-cyan)',
    label: 'R1 Atlas'
  },
  R2: {
    color: '#00ff88', // Vivid Neon Lime Green (Peak Contrast & Luminance)
    halo: '#00ff88',
    glowFilter: 'url(#glow-green)',
    label: 'R2 Nova'
  },
  R3: {
    color: '#fbbf24', // Safety Gold / Electric Amber
    halo: '#f59e0b',
    glowFilter: 'url(#glow-amber)',
    label: 'R3 Orion'
  },
  R4: {
    color: '#d946ef', // Electric Magenta
    halo: '#c026d3',
    glowFilter: 'url(#glow-magenta)',
    label: 'R4 Lyra'
  },
  default: {
    color: '#00f0ff',
    halo: '#38bdf8',
    glowFilter: 'url(#glow-cyan)',
    label: 'AMR'
  }
};

const BLOCKED_STYLE = {
  color: '#ff2244',
  halo: '#dc2626',
  glowFilter: 'url(#glow-red)'
};

function RouteOverlay({ fleet, blockedCells = [] }) {
  const { normalRoutes, detourRoutes, blockedRoutes } = useMemo(() => {
    const normal = [];
    const detour = [];
    const blocked = [];

    fleet.forEach((robot) => {
      const isDetour = Boolean(robot.is_rerouted || robot.detour_path);
      const isStuck = String(robot.state).toLowerCase() === 'stuck';
      const conf = ROUTE_CONFIGS[robot.robot_id] || ROUTE_CONFIGS.default;

      if (isDetour) {
        // 1. Original Blocked Route (Dashed Danger Red with dark casing)
        const origPath = robot.original_path || (isStuck && robot.destination ? [
          [robot.x, robot.y],
          ...(blockedCells.length ? blockedCells : [[11, 6]]),
          robot.destination
        ] : null);

        if (origPath && origPath.length >= 2) {
          const origPoints = [];
          origPath.forEach((pt) => {
            const c = cellPoint(pt);
            if (c) origPoints.push(cellToPixels(c.x, c.y));
          });
          if (origPoints.length >= 2) {
            blocked.push({
              robotId: robot.robot_id,
              points: origPoints,
              color: BLOCKED_STYLE.color,
              haloColor: BLOCKED_STYLE.halo,
              glowFilter: BLOCKED_STYLE.glowFilter
            });
          }
        }

        // 2. New A* Detour Route (Vivid Safety Gold with animated pulse)
        const detourPath = robot.detour_path || robot.waypoints || [];
        const detourPoints = [cellToPixels(robot.x, robot.y)];
        detourPath.forEach((pt) => {
          const c = cellPoint(pt);
          if (c) detourPoints.push(cellToPixels(c.x, c.y));
        });

        const goal = cellPoint(robot.destination || robot.goal || robot.final_destination);
        const goalPx = goal ? cellToPixels(goal.x, goal.y) : null;

        if (detourPoints.length >= 2) {
          detour.push({
            robotId: robot.robot_id,
            points: detourPoints,
            color: '#fbbf24',
            haloColor: '#f59e0b',
            glowFilter: 'url(#glow-amber)',
            goalPx,
            isDetour: true
          });
        }
      } else {
        // Normal Operational Route (e.g. R1 Cyan, R2 Vivid Neon Lime Green)
        const waypoints = robot.path || robot.waypoints || [];
        const points = [cellToPixels(robot.x, robot.y)];
        waypoints.forEach((pt) => {
          const c = cellPoint(pt);
          if (c) points.push(cellToPixels(c.x, c.y));
        });

        const goal = cellPoint(robot.destination || robot.goal || robot.final_destination);
        const goalPx = goal ? cellToPixels(goal.x, goal.y) : null;

        if (points.length >= 2) {
          normal.push({
            robotId: robot.robot_id,
            points,
            color: conf.color,
            haloColor: conf.halo,
            glowFilter: conf.glowFilter,
            goalPx,
            isDetour: false
          });
        }
      }
    });

    return { normalRoutes: normal, detourRoutes: detour, blockedRoutes: blocked };
  }, [fleet, blockedCells]);

  return (
    <svg className="routes-svg-layer" viewBox="0 0 1024 1024" preserveAspectRatio="none">
      <defs>
        {/* Glow Filters */}
        <filter id="glow-cyan" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-green" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-amber" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-red" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="4.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-magenta" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Arrow Marker Definitions */}
        <marker id="arrow-cyan" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#00f0ff" />
        </marker>
        <marker id="arrow-green" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#00ff88" />
        </marker>
        <marker id="arrow-amber" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#fbbf24" />
        </marker>
        <marker id="arrow-red" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#ff2244" />
        </marker>
      </defs>

      {/* 1. Original Blocked Paths (Dashed Danger Red with dark casing underlay) */}
      {blockedRoutes.map((rt) => {
        if (rt.points.length < 2) return null;
        const d = rt.points.reduce((acc, p, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`, '');

        return (
          <g key={`blocked-${rt.robotId}`} className="route-group blocked">
            {/* Dark Casing Underlay */}
            <path
              d={d}
              fill="none"
              stroke="#020617"
              strokeWidth="8"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeOpacity="0.95"
            />
            {/* Red Danger Halo */}
            <path
              d={d}
              fill="none"
              stroke={rt.color}
              strokeWidth="6"
              strokeOpacity="0.45"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter={rt.glowFilter}
            />
            {/* Dashed Red Blocked Line */}
            <path
              d={d}
              fill="none"
              stroke={rt.color}
              strokeWidth="3.6"
              strokeDasharray="8 6"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="blocked-dash-flow"
            />
            {/* Blocked waypoint cross markers */}
            {rt.points.slice(1).map((p, i) => (
              <g key={i} transform={`translate(${p.x}, ${p.y})`}>
                <circle r="7" fill="#020617" stroke={rt.color} strokeWidth="1.5" />
                <path d="M-2.5 -2.5 L2.5 2.5 M2.5 -2.5 L-2.5 2.5" stroke={rt.color} strokeWidth="1.8" strokeLinecap="round" />
              </g>
            ))}
          </g>
        );
      })}

      {/* 2. Normal Operational Routes (R1 Cyan, R2 Vivid Neon Lime Green, etc.) */}
      {normalRoutes.map((rt) => {
        if (rt.points.length < 2) return null;
        const d = rt.points.reduce((acc, p, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`, '');

        return (
          <g key={`normal-${rt.robotId}`} className="route-group normal">
            {/* 1. Deep Contrast Black Casing Underlay */}
            <path
              d={d}
              fill="none"
              stroke="#020617"
              strokeWidth="8"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeOpacity="0.95"
            />
            {/* 2. Intense Colored Glow Halo */}
            <path
              d={d}
              fill="none"
              stroke={rt.color}
              strokeWidth="5.5"
              strokeOpacity="0.45"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter={rt.glowFilter}
            />
            {/* 3. High-Luminance Main Route Stroke */}
            <path
              d={d}
              fill="none"
              stroke={rt.color}
              strokeWidth="3.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="route-path-pulse"
            />
            {/* 4. White Center Laser Core Highlight */}
            <path
              d={d}
              fill="none"
              stroke="rgba(255, 255, 255, 0.9)"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Waypoint Markers */}
            {rt.points.slice(1, -1).map((p, i) => (
              <g key={i} className="waypoint-marker-group">
                <circle cx={p.x} cy={p.y} r="5" fill="#020617" />
                <circle cx={p.x} cy={p.y} r="4" fill={rt.color} filter={rt.glowFilter} />
                <circle cx={p.x} cy={p.y} r="1.8" fill="#ffffff" />
              </g>
            ))}

            {/* Destination Goal Flag & Robot Badge */}
            {rt.goalPx && (
              <g transform={`translate(${rt.goalPx.x}, ${rt.goalPx.y})`} className="goal-flag-marker">
                <circle r="14" fill={rt.color} fillOpacity="0.22" stroke={rt.color} strokeWidth="1.6" />
                <circle r="6" fill="#020617" stroke={rt.color} strokeWidth="2.5" />
                <circle r="2.5" fill="#ffffff" />
                <g transform="translate(6, -17)" className="flag-glyph">
                  <path d="M2 13s1-1 3-1 3 2 6 2 3-1 3-1V3s-1 1-3 1-3-2-6-2-3 1-3 1z" fill={rt.color} stroke={rt.color} strokeWidth="1" />
                  <line x1="2" x2="2" y1="18" y2="13" stroke="#e2e8f0" strokeWidth="1.5" strokeLinecap="round" />
                </g>
                <g transform="translate(10, 13)">
                  <rect x="-4" y="-9" width="30" height="13" rx="3" fill="#020617" stroke={rt.color} strokeWidth="1" />
                  <text x="11" y="1" fontSize="9" fontWeight="800" fill={rt.color} textAnchor="middle">
                    {rt.robotId}
                  </text>
                </g>
              </g>
            )}
          </g>
        );
      })}

      {/* 3. A* Detour Routes (R3 Safety Gold with Animated Dashes) */}
      {detourRoutes.map((rt) => {
        if (rt.points.length < 2) return null;
        const d = rt.points.reduce((acc, p, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`, '');

        return (
          <g key={`detour-${rt.robotId}`} className="route-group detour">
            {/* 1. Deep Contrast Black Casing Underlay */}
            <path
              d={d}
              fill="none"
              stroke="#020617"
              strokeWidth="9"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeOpacity="0.95"
            />
            {/* 2. Intense Safety Gold Glow Halo */}
            <path
              d={d}
              fill="none"
              stroke={rt.haloColor}
              strokeWidth="6.5"
              strokeOpacity="0.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter={rt.glowFilter}
            />
            {/* 3. Animated Gold Dashed Path */}
            <path
              d={d}
              fill="none"
              stroke={rt.color}
              strokeWidth="4.2"
              strokeDasharray="10 7"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="animated-detour-dash"
            />
            {/* 4. White Center Laser Highlight */}
            <path
              d={d}
              fill="none"
              stroke="rgba(255, 255, 255, 0.95)"
              strokeWidth="1.6"
              strokeDasharray="10 7"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="animated-detour-dash"
            />

            {/* Glowing Waypoint Dots along A* Detour */}
            {rt.points.slice(1, -1).map((p, i) => (
              <g key={i} className="waypoint-marker-group">
                <circle cx={p.x} cy={p.y} r="5.5" fill="#020617" />
                <circle cx={p.x} cy={p.y} r="4.5" fill={rt.color} filter={rt.glowFilter} />
                <circle cx={p.x} cy={p.y} r="2" fill="#ffffff" />
              </g>
            ))}

            {/* Destination Goal Flag & Robot Badge */}
            {rt.goalPx && (
              <g transform={`translate(${rt.goalPx.x}, ${rt.goalPx.y})`} className="goal-flag-marker">
                <circle r="15" fill={rt.color} fillOpacity="0.25" stroke={rt.color} strokeWidth="1.8" />
                <circle r="6" fill="#020617" stroke={rt.color} strokeWidth="2.5" />
                <circle r="2.5" fill="#ffffff" />
                <g transform="translate(6, -17)" className="flag-glyph">
                  <path d="M2 13s1-1 3-1 3 2 6 2 3-1 3-1V3s-1 1-3 1-3-2-6-2-3 1-3 1z" fill={rt.color} stroke={rt.color} strokeWidth="1" />
                  <line x1="2" x2="2" y1="18" y2="13" stroke="#e2e8f0" strokeWidth="1.5" strokeLinecap="round" />
                </g>
                <g transform="translate(10, 13)">
                  <rect x="-4" y="-9" width="30" height="13" rx="3" fill="#020617" stroke={rt.color} strokeWidth="1" />
                  <text x="11" y="1" fontSize="9" fontWeight="800" fill={rt.color} textAnchor="middle">
                    {rt.robotId}
                  </text>
                </g>
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export default function WarehouseMap({
  fleet = [],
  selectedRobotId,
  onSelectRobot,
  blockedCells = [],
  onCellSelect,
  showGrid = true,
  showRoutes = true,
  showReroutePanel = true
}) {
  const renderedRobots = useInterpolatedRobots(fleet);
  const [hover, setHover] = useState(null);
  const blocked = useMemo(() => new Set(blockedCells.map((cell) => `${cell[0]}:${cell[1]}`)), [blockedCells]);

  // Filter out static warehouse infrastructure (shelves, docks) so hazard boxes ONLY show for real dynamic obstacles
  const isStaticInfrastructure = (x, y) => {
    const nx = Number(x);
    const ny = Number(y);
    const isShelf = [4, 5, 8, 9, 12, 13, 16, 17].includes(nx) && ny >= 3 && ny <= 11;
    const isChargingDock = ny === 0 && nx >= 1 && nx <= 4;
    const isWorkstation = ny === 14 && nx >= 1 && nx <= 4;
    return isShelf || isChargingDock || isWorkstation;
  };

  const dynamicObstacles = useMemo(() => {
    return blockedCells
      .map(cellPoint)
      .filter((c) => c && !isStaticInfrastructure(c.x, c.y));
  }, [blockedCells]);

  // Check if any robot has active detour
  const activeDetourRobot = renderedRobots.find((r) => r.is_rerouted || r.detour_path || r.avoiding_obstacle);

  return (
    <div className={`warehouse-digital-twin-container ${showGrid ? 'show-grid-lines' : ''}`}>
      {/* HIGH-RES PHOTOREALISTIC WAREHOUSE DIGITAL TWIN FLOOR */}
      <div className="warehouse-canvas" onMouseLeave={() => setHover(null)}>
        {/* Background Image is set via CSS on .warehouse-canvas */}

        {/* 1. Dynamic SVG Routes Overlay */}
        {showRoutes && <RouteOverlay fleet={renderedRobots} blockedCells={dynamicObstacles} />}

        {/* 2. Dynamic Blocked Hazard Containers - Only on REAL dynamic obstacles (Image 4 Style) */}
        {dynamicObstacles.map((c, idx) => {
          return (
            <div key={idx} className="hazard-obstacle-container" style={cellToPercent(c.x, c.y)}>
              <div className="hazard-box">
                <span className="hazard-stripes" />
                <span className="hazard-warning-icon"><AlertTriangle size={18} /></span>
              </div>
              <span className="hazard-cross-marker"><X size={11} strokeWidth={2.8} /></span>
            </div>
          );
        })}

        {/* 3. Interactive Grid Hover Cells */}
        {Array.from({ length: COLS * ROWS }, (_, index) => {
          const x = index % COLS;
          const y = Math.floor(index / COLS);
          const key = `${x}:${y}`;
          return (
            <button
              key={key}
              className="digital-grid-cell"
              style={cellToPercent(x, y)}
              onMouseEnter={() => setHover({ x, y })}
              onFocus={() => setHover({ x, y })}
              onClick={() => onCellSelect?.(x, y)}
              aria-label={`Grid position ${x}, ${y}`}
            />
          );
        })}

        {/* 4. Photorealistic AMR Robot Sprites */}
        {renderedRobots.map((robot) => (
          <RobotSprite
            key={robot.robot_id}
            robot={robot}
            selected={robot.robot_id === selectedRobotId}
            onSelect={onSelectRobot}
          />
        ))}

        {/* 5. Interactive Coordinate Tooltip */}

        {/* 6. Interactive Coordinate Tooltip */}
        {hover && (
          <div className="grid-cell-tooltip" style={cellToPercent(hover.x, hover.y)}>
            <strong>({hover.x}, {hover.y})</strong>
            <small>
              {hover.y <= 2
                ? 'Receiving Dock'
                : hover.y >= 11 && hover.x <= 4
                ? 'Charging Bay'
                : hover.y >= 11 && hover.x >= 7 && hover.x <= 12
                ? 'Restricted Zone'
                : hover.y >= 11 && hover.x >= 14
                ? 'Packing Station'
                : hover.x >= 4 && hover.x <= 5
                ? 'Aisle A'
                : hover.x >= 8 && hover.x <= 9
                ? 'Aisle B'
                : hover.x >= 12 && hover.x <= 13
                ? 'Aisle C'
                : hover.x >= 16 && hover.x <= 17
                ? 'Aisle D'
                : 'Transit Aisle'}
            </small>
          </div>
        )}
      </div>
    </div>
  );
}

export function PathReroutingLegend({ activeRobot, onClose, className = '' }) {
  return (
    <aside className={`path-rerouting-card outside-map ${className}`}>
      <div className="reroute-card-header">
        <div className="reroute-title-wrap">
          <span className="reroute-icon"><Zap size={14} /></span>
          <h4>Path Rerouting (A* Algorithm)</h4>
        </div>
        {onClose && (
          <button className="reroute-close-btn" onClick={onClose} title="Dismiss legend">
            <X size={14} />
          </button>
        )}
      </div>
      <ul>
        <li>
          <span className="legend-indicator blocked-dash" />
          <span>Original Path (Blocked)</span>
        </li>
        <li>
          <span className="legend-indicator detour-dash" />
          <span>New Path (A* Detour)</span>
        </li>
        <li>
          <span className="legend-indicator waypoint-dots">
            <span className="dot" /><span className="dot" /><span className="dot" />
          </span>
          <span>Path Progress</span>
        </li>
        <li>
          <span className="legend-indicator obstacle-box"><AlertTriangle size={13} /></span>
          <span>Obstacle (Blocked)</span>
        </li>
        <li>
          <span className="legend-indicator goal-flag"><Flag size={13} color="#38bdf8" /></span>
          <span>Goal Location</span>
        </li>
      </ul>

      {/* AMR Route Visibility Color Guide */}
      <div className="reroute-fleet-colors">
        <span className="fleet-colors-title">AMR Route Colors</span>
        <div className="fleet-color-chips">
          <div className="fleet-color-chip" title="R1 (Atlas) - Electric Cyan Route">
            <span className="color-swatch r1" />
            <span className="robot-name"><b>R1:</b> Electric Cyan</span>
          </div>
          <div className="fleet-color-chip" title="R2 (Nova) - Vivid Neon Lime Green Route">
            <span className="color-swatch r2" />
            <span className="robot-name"><b>R2:</b> Neon Green</span>
          </div>
          <div className="fleet-color-chip" title="R3 (Orion) - Safety Gold Detour">
            <span className="color-swatch r3" />
            <span className="robot-name"><b>R3:</b> Gold Detour</span>
          </div>
        </div>
      </div>

      <div className="reroute-card-footer">
        <small>Detour target: <b>{activeRobot ? activeRobot.robot_id : 'R3'}</b></small>
      </div>
    </aside>
  );
}

