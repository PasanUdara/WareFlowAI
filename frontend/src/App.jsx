import { useEffect, useMemo, useState } from 'react';
import { fetchFleetStatus, dispatchOrder, triggerEmergencyStop, checkCompliance } from './api';

const defaultForm = {
  order_text: 'Fetch 2 medical kits from Shelf-A1 to Station-1'
};

const defaultCompliance = {
  payload_weight: 15,
  speed: 1.2,
  is_hazmat: false,
  target_zone: 'Zone-A'
};

function StatCard({ label, value, accent = 'blue' }) {
  return (
    <div className={`stat-card ${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function App() {
  const [fleet, setFleet] = useState([]);
  const [dispatchForm, setDispatchForm] = useState(defaultForm);
  const [dispatchResult, setDispatchResult] = useState(null);
  const [complianceForm, setComplianceForm] = useState(defaultCompliance);
  const [complianceResult, setComplianceResult] = useState(null);
  const [emergencyStop, setEmergencyStop] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFleet = async () => {
      try {
        const data = await fetchFleetStatus();
        setFleet(data.robots || []);
        setEmergencyStop(Boolean(data.emergency_stop));
      } catch (error) {
        console.error('Failed to fetch fleet status:', error);
      } finally {
        setLoading(false);
      }
    };

    loadFleet();
  }, []);

  const summary = useMemo(() => {
    const total = fleet.length;
    const avgBattery = total
      ? Math.round(fleet.reduce((sum, robot) => sum + Number(robot.battery || 0), 0) / total)
      : 0;
    const alerts = fleet.filter((robot) => Number(robot.battery || 0) < 25 || robot.state === 'ERROR').length;

    return {
      active: total,
      avgBattery,
      alerts,
      ordersToday: 18
    };
  }, [fleet]);

  const handleDispatch = async (event) => {
    event.preventDefault();
    const result = await dispatchOrder(dispatchForm);
    setDispatchResult(result);
  };

  const handleComplianceCheck = async (event) => {
    event.preventDefault();
    const result = await checkCompliance(complianceForm);
    setComplianceResult(result);
  };

  const handleEmergencyStop = async () => {
    const result = await triggerEmergencyStop(!emergencyStop);
    setEmergencyStop(Boolean(result.emergency_stop));
  };

  return (
    <div className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Warehouse Automation</p>
          <h1>WareFlow AI Dashboard</h1>
        </div>

        <div className="topbar-actions">
          <span className={`status-pill ${emergencyStop ? 'danger' : 'online'}`}>
            {emergencyStop ? 'Emergency Stop' : 'System Online'}
          </span>
          <button className="primary-btn" onClick={handleEmergencyStop}>
            {emergencyStop ? 'Clear Stop' : 'Trigger Stop'}
          </button>
        </div>
      </header>

      <aside className="sidebar">
        <nav>
          <button className="nav active">Overview</button>
          <button className="nav">Fleet</button>
          <button className="nav">Orders</button>
          <button className="nav">Compliance</button>
          <button className="nav">Alerts</button>
        </nav>
      </aside>

      <main className="main-panel">
        <section className="stats-grid">
          <StatCard label="Active Robots" value={String(summary.active)} accent="blue" />
          <StatCard label="Avg Battery" value={`${summary.avgBattery}%`} accent="green" />
          <StatCard label="Critical Alerts" value={String(summary.alerts)} accent="amber" />
          <StatCard label="Orders Today" value={String(summary.ordersToday)} accent="purple" />
        </section>

        <section className="content-grid">
          <div className="panel wide-panel">
            <div className="panel-header">
              <h2>Warehouse Overview</h2>
            </div>
            <div className="warehouse-map">
              {Array.from({ length: 20 }).map((_, rowIndex) => (
                <div className="map-row" key={`row-${rowIndex}`}>
                  {Array.from({ length: 20 }).map((__, colIndex) => {
                    const robot = fleet.find(
                      (item) => Number(item.x) === colIndex && Number(item.y) === rowIndex
                    );

                    return (
                      <div key={`cell-${rowIndex}-${colIndex}`} className="map-cell">
                        {robot ? <span className="robot-marker">R{robot.robot_id.split('_')[1]}</span> : ''}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Dispatch Order</h2>
            </div>
            <form onSubmit={handleDispatch} className="stacked-form">
              <textarea
                value={dispatchForm.order_text}
                onChange={(e) => setDispatchForm({ ...dispatchForm, order_text: e.target.value })}
                rows={4}
              />
              <button className="primary-btn" type="submit">Dispatch</button>
            </form>
            {dispatchResult && (
              <div className="result-box">
                <strong>Status:</strong> {dispatchResult.status}
                <br />
                <strong>Assigned:</strong> {dispatchResult.assigned_robot_id || 'Not assigned'}
              </div>
            )}
          </div>
        </section>

        <section className="content-grid lower-grid">
          <div className="panel">
            <div className="panel-header">
              <h2>Fleet Status</h2>
            </div>

            {loading ? (
              <p>Loading fleet...</p>
            ) : (
              <table className="fleet-table">
                <thead>
                  <tr>
                    <th>Robot</th>
                    <th>Battery</th>
                    <th>Pos</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {fleet.map((robot) => (
                    <tr key={robot.robot_id}>
                      <td>{robot.robot_id}</td>
                      <td>{robot.battery}%</td>
                      <td>{robot.x}, {robot.y}</td>
                      <td>{robot.state}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Compliance</h2>
            </div>
            <form onSubmit={handleComplianceCheck} className="stacked-form compact">
              <label>
                Payload Weight
                <input
                  type="number"
                  value={complianceForm.payload_weight}
                  onChange={(e) => setComplianceForm({ ...complianceForm, payload_weight: Number(e.target.value) })}
                />
              </label>

              <label>
                Speed
                <input
                  type="number"
                  step="0.1"
                  value={complianceForm.speed}
                  onChange={(e) => setComplianceForm({ ...complianceForm, speed: Number(e.target.value) })}
                />
              </label>

              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={complianceForm.is_hazmat}
                  onChange={(e) => setComplianceForm({ ...complianceForm, is_hazmat: e.target.checked })}
                />
                Hazardous Material
              </label>

              <label>
                Target Zone
                <input
                  type="text"
                  value={complianceForm.target_zone}
                  onChange={(e) => setComplianceForm({ ...complianceForm, target_zone: e.target.value })}
                />
              </label>

              <button className="primary-btn" type="submit">Check</button>
            </form>
            {complianceResult && (
              <div className="result-box">
                <strong>{complianceResult.status}</strong>
                <br />
                <span>{complianceResult.allowed ? 'Allowed to proceed' : 'Requires attention'}</span>
              </div>
            )}
          </div>
        </section>
      </main>

      <aside className="right-panel">
        <div className="panel">
          <div className="panel-header">
            <h2>Selected Robot</h2>
          </div>
          <div className="mini-card">
            <strong>Robot 1</strong>
            <p>Battery: 86%</p>
            <p>Location: 6, 8</p>
            <p>State: Moving</p>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Alerts</h2>
          </div>
          <ul className="alert-list">
            <li className="alert low">Battery below threshold on Robot 3</li>
            <li className="alert medium">Route congestion near Zone B</li>
            <li className="alert high">Emergency stop ready</li>
          </ul>
        </div>
      </aside>
    </div>
  );
}

export default App;
