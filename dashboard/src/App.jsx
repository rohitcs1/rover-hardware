import { useEffect, useState } from "react";
import {
  Activity, AlertTriangle, Camera, CheckCircle2, ChevronRight,
  Cpu, Gauge, Home, Menu, Radio, RefreshCw, Settings, Shield,
  Thermometer, Users, Waves, Wind, Wifi, X, Zap, ArrowUp,
  ArrowDown, ArrowLeft, ArrowRight, Square, Monitor, Clock,
  Server, Droplets, Eye, CircleStop
} from "lucide-react";

const API = `http://${window.location.hostname}:5000`;

const navigation = [
  { name: "Dashboard", icon: Home },
  { name: "Live Camera", icon: Camera },
  { name: "Human Detection", icon: Users },
  { name: "Obstacle Detection", icon: Waves },
  { name: "Gas Monitoring", icon: Wind },
  { name: "Environment", icon: Thermometer },
  { name: "Rover Control", icon: Gauge },
  { name: "Alerts", icon: AlertTriangle },
  { name: "System Status", icon: Server },
  { name: "Settings", icon: Settings },
];

function formatValue(value, unit = "") {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number" && !Number.isFinite(value)) return "—";
  return `${value}${unit}`;
}

function MetricCard({ title, value, unit, icon: Icon, color, note }) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span className="metric-label">{title}</span>
        <span className={`metric-icon ${color || ""}`}>
          <Icon size={19} />
        </span>
      </div>
      <div className="metric-value">
        {formatValue(value, unit)}
      </div>
      <div className="metric-note">{note}</div>
    </div>
  );
}

function SectionTitle({ title, subtitle, action }) {
  return (
    <div className="section-title">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="empty-state">
      <Activity size={25} />
      <p>{message}</p>
    </div>
  );
}

export default function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [cameraError, setCameraError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [commandStatus, setCommandStatus] = useState("");

  const [telemetry, setTelemetry] = useState({
    distance: null,
    humans: null,
    gas: null,
    temperature: null,
    humidity: null,
    cpu: null,
    memory: null,
    roverStatus: "Unknown",
    cameraStatus: "Checking",
    alerts: [],
    sensorStatus: "Waiting for backend"
  });

  async function refreshData() {
    setRefreshing(true);

    try {
      const response = await fetch(`${API}/api/status`, {
        signal: AbortSignal.timeout(2500),
      });

      if (!response.ok) throw new Error("Status API unavailable");

      const status = await response.json();

      setApiOnline(true);
      setTelemetry(previous => ({
        ...previous,
        ...status,
        roverStatus: status.roverStatus ?? status.rover_status ?? previous.roverStatus,
        cameraStatus: status.cameraStatus ?? status.camera_status ?? previous.cameraStatus,
      }));

      try {
        const sensorResponse = await fetch(`${API}/api/sensors`, {
          signal: AbortSignal.timeout(2500),
        });

        if (sensorResponse.ok) {
          const sensors = await sensorResponse.json();
          setTelemetry(previous => ({ ...previous, ...sensors }));
        }
      } catch {
        // Sensor endpoint may not be implemented yet.
      }

      try {
        const alertResponse = await fetch(`${API}/api/alerts`, {
          signal: AbortSignal.timeout(2500),
        });

        if (alertResponse.ok) {
          const alertData = await alertResponse.json();
          setTelemetry(previous => ({
            ...previous,
            alerts: Array.isArray(alertData)
              ? alertData
              : alertData.alerts || [],
          }));
        }
      } catch {
        // Alert endpoint may not be implemented yet.
      }

      setLastUpdated(new Date());
    } catch {
      setApiOnline(false);
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    refreshData();
    const timer = setInterval(refreshData, 3000);
    return () => clearInterval(timer);
  }, []);

  async function sendCommand(command) {
    setCommandStatus(`Sending ${command}...`);

    try {
      const response = await fetch(`${API}/api/rover/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
        signal: AbortSignal.timeout(3000),
      });

      if (!response.ok) throw new Error("Command rejected");

      setCommandStatus(`${command} command sent`);
    } catch {
      setCommandStatus(
        "Control API unavailable. Rover was not commanded."
      );
    }
  }

  function navigate(page) {
    setActivePage(page);
    setSidebarOpen(false);
    setCommandStatus("");
  }

  const pageDescriptions = {
    Dashboard: "Overview of your mining rescue rover.",
    "Live Camera": "Live video feed from the Raspberry Pi camera.",
    "Human Detection": "Monitor human detections from the camera.",
    "Obstacle Detection": "Monitor ultrasonic distance and obstacles.",
    "Gas Monitoring": "Monitor gas sensor readings and warnings.",
    Environment: "Temperature and humidity monitoring.",
    "Rover Control": "Rover movement and emergency stop controls.",
    Alerts: "Review active rover alerts.",
    "System Status": "Monitor Raspberry Pi and service connectivity.",
    Settings: "Camera and monitoring configuration.",
  };

  const connectedLabel = apiOnline ? "Backend connected" : "Backend offline";

  function renderCamera() {
    return (
      <div className="camera-panel">
        <div className="panel-heading">
          <div>
            <h3>Live camera feed</h3>
            <p>Raspberry Pi Camera · MJPEG stream</p>
          </div>
          <span className={`status-pill ${cameraError ? "offline" : ""}`}>
            <span className="status-dot" />
            {cameraError ? "Stream unavailable" : "Stream endpoint"}
          </span>
        </div>

        <div className="camera-screen">
          {cameraError ? (
            <div className="camera-placeholder">
              <Camera size={42} />
              <h3>Camera stream unavailable</h3>
              <p>
                Check whether the Flask camera server is running on port 5000.
              </p>
              <button className="secondary-btn" onClick={() => setCameraError(false)}>
                <RefreshCw size={15} /> Retry stream
              </button>
            </div>
          ) : (
            <img
              src={`${API}/video_feed`}
              alt="Raspberry Pi live camera feed"
              onError={() => setCameraError(true)}
              onLoad={() => setCameraError(false)}
            />
          )}
          {!cameraError && (
            <div className="camera-overlay">
              <span><span className="status-dot live" /> LIVE</span>
              <span>640 × 360 target</span>
            </div>
          )}
        </div>

        <div className="camera-footer">
          <span><Radio size={15} /> Source: Raspberry Pi</span>
          <span><Wifi size={15} /> {apiOnline ? "Backend online" : "Backend not connected"}</span>
        </div>
      </div>
    );
  }

  function renderDashboard() {
    return (
      <>
        <div className="welcome-banner">
          <div>
            <span className="eyebrow">MISSION CONTROL</span>
            <h2>Mining Rescue Rover</h2>
            <p>Live monitoring and rover telemetry in one place.</p>
          </div>
          <div className="banner-icon"><Shield size={35} /></div>
        </div>

        <div className="metric-grid">
          <MetricCard
            title="Human Count"
            value={telemetry.humans}
            icon={Users}
            color="purple"
            note="Waiting for detection API"
          />
          <MetricCard
            title="Obstacle Distance"
            value={telemetry.distance}
            unit={telemetry.distance != null ? " cm" : ""}
            icon={Waves}
            color="blue"
            note="Ultrasonic sensor"
          />
          <MetricCard
            title="Temperature"
            value={telemetry.temperature}
            unit={telemetry.temperature != null ? " °C" : ""}
            icon={Thermometer}
            color="orange"
            note="Environmental sensor"
          />
          <MetricCard
            title="Humidity"
            value={telemetry.humidity}
            unit={telemetry.humidity != null ? " %" : ""}
            icon={Droplets}
            color="cyan"
            note="Environmental sensor"
          />
        </div>

        <div className="main-grid">
          <div>{renderCamera()}</div>

          <div className="panel sensor-overview">
            <div className="panel-heading">
              <div>
                <h3>Sensor overview</h3>
                <p>Latest available readings</p>
              </div>
              <Activity size={19} className="muted-icon" />
            </div>

            <div className="sensor-row">
              <span className="sensor-symbol gas"><Wind size={18} /></span>
              <div className="sensor-info">
                <strong>Gas sensor</strong>
                <small>Gas reading</small>
              </div>
              <b>{formatValue(telemetry.gas)}</b>
            </div>

            <div className="sensor-row">
              <span className="sensor-symbol temp"><Thermometer size={18} /></span>
              <div className="sensor-info">
                <strong>Temperature</strong>
                <small>Ambient temperature</small>
              </div>
              <b>{formatValue(telemetry.temperature, telemetry.temperature != null ? " °C" : "")}</b>
            </div>

            <div className="sensor-row">
              <span className="sensor-symbol humidity"><Droplets size={18} /></span>
              <div className="sensor-info">
                <strong>Humidity</strong>
                <small>Relative humidity</small>
              </div>
              <b>{formatValue(telemetry.humidity, telemetry.humidity != null ? " %" : "")}</b>
            </div>

            <div className="sensor-row">
              <span className="sensor-symbol distance"><Waves size={18} /></span>
              <div className="sensor-info">
                <strong>Ultrasonic</strong>
                <small>Obstacle distance</small>
              </div>
              <b>{formatValue(telemetry.distance, telemetry.distance != null ? " cm" : "")}</b>
            </div>
          </div>
        </div>

        <div className="bottom-grid">
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h3>System connectivity</h3>
                <p>Connection status</p>
              </div>
            </div>
            <div className="connection-row">
              <span><Server size={17} /> Flask backend</span>
              <b className={apiOnline ? "text-green" : "text-red"}>
                {apiOnline ? "Connected" : "Offline"}
              </b>
            </div>
            <div className="connection-row">
              <span><Camera size={17} /> Camera endpoint</span>
              <b className="text-blue">Port 5000</b>
            </div>
            <div className="connection-row">
              <span><Activity size={17} /> Telemetry</span>
              <b>{lastUpdated ? "Received" : "Waiting"}</b>
            </div>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div>
                <h3>Recent alerts</h3>
                <p>Latest backend alerts</p>
              </div>
              <button className="text-btn" onClick={() => navigate("Alerts")}>
                View all <ChevronRight size={15} />
              </button>
            </div>
            {telemetry.alerts.length ? (
              telemetry.alerts.slice(0, 4).map((alert, index) => (
                <div className="alert-row" key={index}>
                  <AlertTriangle size={17} />
                  <span>{typeof alert === "string" ? alert : alert.message || alert.title || "Alert"}</span>
                </div>
              ))
            ) : (
              <EmptyState message="No alerts received from backend." />
            )}
          </div>
        </div>
      </>
    );
  }

  function renderPage() {
    switch (activePage) {
      case "Dashboard":
        return renderDashboard();

      case "Live Camera":
        return (
          <>
            <SectionTitle title="Live Camera" subtitle="Monitor the rover camera in real time." />
            {renderCamera()}
          </>
        );

      case "Human Detection":
        return (
          <>
            <SectionTitle title="Human Detection" subtitle="AI-powered human detection status." />
            <div className="metric-grid">
              <MetricCard title="Current Human Count" value={telemetry.humans} icon={Users} color="purple" note="Current frame count from backend" />
              <MetricCard title="Camera Feed" value={cameraError ? "Offline" : "Available"} icon={Eye} color="blue" note="Stream endpoint status" />
            </div>
            {renderCamera()}
            <div className="notice">
              <Eye size={18} />
              Human detection requires an AI model and a backend detection endpoint.
              The count will remain unavailable until that module is connected.
            </div>
          </>
        );

      case "Obstacle Detection":
        return (
          <>
            <SectionTitle title="Obstacle Detection" subtitle="Live ultrasonic distance and buzzer status." />
            <div className="metric-grid">
              <MetricCard
                title="Distance"
                value={telemetry.distance}
                unit={telemetry.distance != null ? " cm" : ""}
                icon={Waves}
                color="blue"
                note={telemetry.ultrasonicStatus || "Ultrasonic sensor"}
              />
              <MetricCard
                title="Obstacle Level"
                value={telemetry.obstacleLevel || "UNKNOWN"}
                icon={AlertTriangle}
                color="orange"
                note={telemetry.obstacleMessage || "Waiting for reading"}
              />
              <MetricCard
                title="Buzzer"
                value={telemetry.buzzerStatus || "OFF"}
                icon={Activity}
                color="purple"
                note={`Obstacle pattern: ${telemetry.obstacleBuzzerPattern || "OFF"}`}
              />
            </div>
            <div className="panel">
              <h3>Obstacle telemetry</h3>
              <div className="sensor-row">
                <span className="sensor-symbol distance"><Waves size={18} /></span>
                <div className="sensor-info">
                  <strong>Ultrasonic sensor</strong>
                  <small>{telemetry.ultrasonicStatus || "Waiting"}</small>
                </div>
                <b>{formatValue(telemetry.distance, telemetry.distance != null ? " cm" : "")}</b>
              </div>
              <div className="sensor-row">
                <span className="sensor-symbol temp"><AlertTriangle size={18} /></span>
                <div className="sensor-info">
                  <strong>Obstacle status</strong>
                  <small>{telemetry.obstacleMessage || "No reading yet"}</small>
                </div>
                <b>{telemetry.obstacleLevel || "UNKNOWN"}</b>
              </div>
              <div className="sensor-row">
                <span className="sensor-symbol humidity"><Activity size={18} /></span>
                <div className="sensor-info">
                  <strong>Temperature alert</strong>
                  <small>Separate temperature alarm</small>
                </div>
                <b>{telemetry.temperatureAlert ? "ACTIVE" : "OFF"}</b>
              </div>
            </div>
          </>
        );

      case "Gas Monitoring":
        return (
          <>
            <SectionTitle title="Gas Monitoring" subtitle="Gas readings and safety monitoring." />
            <div className="metric-grid">
              <MetricCard title="Gas Reading" value={telemetry.gas} icon={Wind} color="orange" note="Raw value or calibrated value, as supplied by backend" />
            </div>
            <div className="notice warning">
              <AlertTriangle size={19} />
              No calibrated gas reading is available. Do not use this dashboard alone for mine safety decisions.
            </div>
            <div className="panel">
              <h3>Gas sensor status</h3>
              <EmptyState message="Waiting for the gas sensor backend. Sensor-specific calibration is required." />
            </div>
          </>
        );

      case "Environment":
        return (
          <>
            <SectionTitle title="Environment Monitoring" subtitle="Temperature and relative humidity." />
            <div className="metric-grid">
              <MetricCard title="Temperature" value={telemetry.temperature} unit={telemetry.temperature != null ? " °C" : ""} icon={Thermometer} color="orange" note="Live sensor reading" />
              <MetricCard title="Humidity" value={telemetry.humidity} unit={telemetry.humidity != null ? " %" : ""} icon={Droplets} color="cyan" note="Live sensor reading" />
            </div>
            <div className="panel">
              <h3>Environmental readings</h3>
              <EmptyState message="Live charts will appear when historical sensor data is provided by the backend." />
            </div>
          </>
        );

      case "Rover Control":
        return (
          <>
            <SectionTitle title="Rover Control" subtitle="Movement commands are sent to the backend." />
            <div className="panel control-panel">
              <div className="control-warning">
                <Shield size={19} />
                Test with the wheels lifted and a physical emergency stop available.
              </div>
              <div className="direction-pad">
                <button aria-label="Move forward" onClick={() => sendCommand("forward")}><ArrowUp /></button>
                <button aria-label="Turn left" onClick={() => sendCommand("left")}><ArrowLeft /></button>
                <button className="stop-button" aria-label="Stop rover" onClick={() => sendCommand("stop")}><CircleStop /></button>
                <button aria-label="Turn right" onClick={() => sendCommand("right")}><ArrowRight /></button>
                <button aria-label="Move backward" onClick={() => sendCommand("backward")}><ArrowDown /></button>
              </div>
              <p className="command-status" aria-live="polite">
                {commandStatus || "Control API must be implemented before commands can operate the rover."}
              </p>
            </div>
          </>
        );

      case "Alerts":
        return (
          <>
            <SectionTitle title="Alerts & Events" subtitle="Warnings received from the rover backend." />
            <div className="panel">
              {telemetry.alerts.length ? telemetry.alerts.map((alert, index) => (
                <div className="alert-row" key={index}>
                  <AlertTriangle size={18} />
                  <span>{typeof alert === "string" ? alert : alert.message || alert.title || "Alert"}</span>
                </div>
              )) : <EmptyState message="No alerts received. The alert API may not be implemented yet." />}
            </div>
          </>
        );

      case "System Status":
        return (
          <>
            <SectionTitle title="System Status" subtitle="Raspberry Pi and backend connectivity." />
            <div className="metric-grid">
              <MetricCard title="Backend" value={apiOnline ? "Online" : "Offline"} icon={Server} color="blue" note="HTTP status API" />
              <MetricCard title="CPU Usage" value={telemetry.cpu} unit={telemetry.cpu != null ? " %" : ""} icon={Cpu} color="purple" note="From backend telemetry" />
              <MetricCard title="Memory Usage" value={telemetry.memory} unit={telemetry.memory != null ? " %" : ""} icon={Activity} color="orange" note="From backend telemetry" />
            </div>
            <div className="panel">
              <div className="connection-row"><span>API base</span><b>{API}</b></div>
              <div className="connection-row"><span>Last update</span><b>{lastUpdated ? lastUpdated.toLocaleTimeString() : "Not received"}</b></div>
              <div className="connection-row"><span>Refresh interval</span><b>3 seconds</b></div>
            </div>
          </>
        );

      case "Settings":
        return (
          <>
            <SectionTitle title="Settings" subtitle="Current dashboard connection configuration." />
            <div className="panel">
              <div className="connection-row"><span>Camera stream URL</span><b>{API}/video_feed</b></div>
              <div className="connection-row"><span>Backend API URL</span><b>{API}</b></div>
              <div className="connection-row"><span>Refresh interval</span><b>3000 ms</b></div>
              <button className="primary-btn" onClick={refreshData} disabled={refreshing}>
                <RefreshCw size={16} /> Test backend connection
              </button>
              <p className="settings-note">
                The dashboard uses the current browser hostname and port 5000.
                Keep the Flask server and browser on a reachable network.
              </p>
            </div>
          </>
        );

      default:
        return renderDashboard();
    }
  }

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="mobile-overlay"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Shield size={23} /></div>
          <div>
            <strong>ROVER<span>OS</span></strong>
            <small>MINING RESCUE SYSTEM</small>
          </div>
          <button className="mobile-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu">
            <X size={20} />
          </button>
        </div>

        <div className="nav-caption">WORKSPACE</div>
        <nav className="nav-menu">
          {navigation.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.name}
                className={`nav-item ${activePage === item.name ? "active" : ""}`}
                onClick={() => navigate(item.name)}
              >
                <Icon size={18} />
                <span>{item.name}</span>
                {activePage === item.name && <span className="nav-indicator" />}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="rover-mini">
            <div className="rover-mini-icon"><Zap size={18} /></div>
            <div>
              <strong>Rover Unit 01</strong>
              <small>{apiOnline ? "Backend connected" : "Awaiting connection"}</small>
            </div>
          </div>
          <div className="sidebar-version">Mining Rescue Rover · v1.0</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
              <Menu size={22} />
            </button>
            <div>
              <div className="breadcrumb">ROVEROS <ChevronRight size={13} /> {activePage.toUpperCase()}</div>
              <h1>{activePage}</h1>
            </div>
          </div>

          <div className="topbar-actions">
            <span className={`connection-badge ${apiOnline ? "connected" : ""}`}>
              <span className="status-dot" />
              {connectedLabel}
            </span>
            <button className="icon-button" onClick={refreshData} disabled={refreshing} aria-label="Refresh data">
              <RefreshCw size={18} className={refreshing ? "spin" : ""} />
            </button>
          </div>
        </header>

        <div className="content">
          <div className="page-intro">
            <p>{pageDescriptions[activePage]}</p>
            <span><Clock size={14} /> {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "Waiting for telemetry"}</span>
          </div>
          {renderPage()}
          <footer className="footer">
            <span>ROVEROS · Mining Rescue Rover</span>
            <span><Shield size={13} /> Monitoring interface</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
