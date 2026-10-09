#!/usr/bin/env bash

set -u

PROJECT_DIR="$HOME/robber/mining-rescue-rover"
DASHBOARD_DIR="$PROJECT_DIR/dashboard"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/.pids"

CAMERA_PID="$PID_DIR/camera.pid"
DASHBOARD_PID="$PID_DIR/dashboard.pid"

mkdir -p "$LOG_DIR" "$PID_DIR"

# ------------------------------------------
# Display startup banner
# ------------------------------------------

clear

echo "================================================"
echo "       MINING RESCUE ROVER - ROVEROS"
echo "================================================"
echo
echo "[INFO] Initializing all rover services..."
echo

cd "$PROJECT_DIR" || exit 1

# ------------------------------------------
# Check Python virtual environment
# ------------------------------------------

if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
    echo "[ERROR] Python virtual environment not found."
    echo "Create it using:"
    echo "python3 -m venv --system-site-packages .venv"
    exit 1
fi

PYTHON="$PROJECT_DIR/.venv/bin/python"

# ------------------------------------------
# Function: Check process
# ------------------------------------------

is_running() {
    local pid_file="$1"

    if [ ! -f "$pid_file" ]; then
        return 1
    fi

    local pid
    pid=$(cat "$pid_file")

    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi

    rm -f "$pid_file"
    return 1
}

# ------------------------------------------
# Start combined camera + sensor API server
# ------------------------------------------

echo "[1/2] Checking rover monitoring server..."

if is_running "$CAMERA_PID"; then
    echo "[RUNNING] Camera and sensor API server already started."
else
    echo "[STARTING] Camera and sensor API server..."

    nohup "$PYTHON" -m rover.camera.streaming \
        > "$LOG_DIR/camera.log" 2>&1 &

    echo $! > "$CAMERA_PID"

    sleep 3

    if kill -0 "$(cat "$CAMERA_PID")" 2>/dev/null; then
        echo "[OK] Monitoring server process started."
    else
        echo "[ERROR] Monitoring server failed to start."
        rm -f "$CAMERA_PID"
        echo "Check: $LOG_DIR/camera.log"
    fi
fi

# ------------------------------------------
# Start React dashboard
# ------------------------------------------

echo
echo "[2/2] Checking React dashboard..."

if [ ! -f "$DASHBOARD_DIR/package.json" ]; then
    echo "[ERROR] Dashboard package.json not found."
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "[ERROR] npm is not installed or not in PATH."
    exit 1
fi

if is_running "$DASHBOARD_PID"; then
    echo "[RUNNING] React dashboard already started."
else
    echo "[STARTING] React dashboard..."

    if [ ! -d "$DASHBOARD_DIR/node_modules" ]; then
        echo "[INFO] Installing dashboard dependencies..."
        (
            cd "$DASHBOARD_DIR" &&
            npm install
        ) || exit 1
    fi

    cd "$DASHBOARD_DIR" || exit 1

    nohup npm run dev -- --host 0.0.0.0 \
        > "$LOG_DIR/dashboard.log" 2>&1 &

    echo $! > "$DASHBOARD_PID"

    sleep 3

    if kill -0 "$(cat "$DASHBOARD_PID")" 2>/dev/null; then
        echo "[OK] Dashboard process started."
    else
        echo "[ERROR] Dashboard failed to start."
        rm -f "$DASHBOARD_PID"
        echo "Check: $LOG_DIR/dashboard.log"
    fi
fi

# ------------------------------------------
# Show service status
# ------------------------------------------

echo
echo "================================================"
echo "               ROVEROS STATUS"
echo "================================================"

PI_IP=$(hostname -I | awk '{print $1}')

echo
echo "Raspberry Pi IP: $PI_IP"
echo
echo "Dashboard:      http://$PI_IP:5173"
echo "Live Camera:    http://$PI_IP:5000"
echo "Camera Stream:  http://$PI_IP:5000/video_feed"
echo "Sensor API:     http://$PI_IP:5000/api/sensors"
echo "Status API:     http://$PI_IP:5000/api/status"
echo
echo "Logs directory: $LOG_DIR"
echo
echo "Stop all services using:"
echo "./stop.sh"
echo
echo "================================================"
echo "         STARTUP COMMAND COMPLETED"
echo "================================================"
