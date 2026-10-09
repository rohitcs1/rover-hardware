#!/usr/bin/env bash

PROJECT_DIR="$HOME/robber/mining-rescue-rover"
PID_DIR="$PROJECT_DIR/.pids"

echo "======================================"
echo "     MINING RESCUE ROVER SHUTDOWN"
echo "======================================"

for service in dashboard camera; do

    PID_FILE="$PID_DIR/$service.pid"

    if [ -f "$PID_FILE" ]; then

        PID=$(cat "$PID_FILE")

        if [[ "$PID" =~ ^[0-9]+$ ]] && kill -0 "$PID" 2>/dev/null; then

            echo "[STOPPING] $service (PID $PID)"

            kill "$PID" 2>/dev/null || true

        else
            echo "[INFO] $service is not running."
        fi

        rm -f "$PID_FILE"

    else
        echo "[INFO] No PID file for $service."
    fi

done

echo
echo "Shutdown commands sent."
echo "======================================"
