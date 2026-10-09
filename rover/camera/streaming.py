import time
import threading

import cv2
from flask import Flask, Response, jsonify
from flask_cors import CORS

from rover.camera.camera_manager import CameraManager
from rover.camera.camera_settings import JPEG_QUALITY


# =========================================================
# DHT11 SENSOR INITIALIZATION
# =========================================================

try:
    import board
    import adafruit_dht

    dht_sensor = adafruit_dht.DHT11(board.D4)
    DHT_AVAILABLE = True

    print("[DHT] DHT11 initialized on GPIO4")

except Exception as error:
    print(f"[DHT] Sensor initialization failed: {error}")

    dht_sensor = None
    DHT_AVAILABLE = False


# =========================================================
# BUZZER INITIALIZATION
# =========================================================

try:
    from gpiozero import OutputDevice

    # BCM GPIO17 = Physical Pin 11
    # Assumes an active-high buzzer module.
    buzzer = OutputDevice(
        17,
        active_high=True,
        initial_value=False,
    )

    BUZZER_AVAILABLE = True

    print("[BUZZER] Buzzer initialized on GPIO17")

except Exception as error:
    print(f"[BUZZER] Initialization failed: {error}")

    buzzer = None
    BUZZER_AVAILABLE = False


# =========================================================
# FLASK AND CAMERA
# =========================================================

app = Flask(__name__)
CORS(app)

camera = CameraManager()


# =========================================================
# SENSOR SETTINGS
# =========================================================

SENSOR_INTERVAL = 2.0

TEMPERATURE_THRESHOLD = 38.0
TEMPERATURE_RESET = 37.5

sensor_lock = threading.Lock()

latest_sensor_data = {
    "temperature": None,
    "humidity": None,
    "sensorStatus": "Initializing",
    "lastSensorUpdate": None,
    "temperatureAlert": False,
    "buzzerStatus": "OFF",
}

buzzer_alert_active = False
shutdown_event = threading.Event()


# =========================================================
# SENSOR READING FUNCTION
# =========================================================

def read_dht_sensor():
    """Read temperature and humidity from DHT11."""

    if not DHT_AVAILABLE or dht_sensor is None:
        return None

    try:
        temperature = dht_sensor.temperature
        humidity = dht_sensor.humidity

        if temperature is None or humidity is None:
            raise RuntimeError("Empty sensor reading")

        return {
            "temperature": round(float(temperature), 1),
            "humidity": round(float(humidity), 1),
            "sensorStatus": "Connected",
            "lastSensorUpdate": time.time(),
        }

    except RuntimeError as error:
        # DHT sensors can occasionally produce temporary read errors.
        print(f"[DHT] Temporary reading error: {error}")
        return None

    except Exception as error:
        print(f"[DHT] Reading failed: {error}")
        return None


# =========================================================
# BACKGROUND SENSOR MONITOR
# =========================================================

def sensor_monitor_loop():
    """Read DHT11 periodically without blocking dashboard requests."""

    global buzzer_alert_active

    print("[SENSOR] Background monitoring started")

    while not shutdown_event.is_set():

        if not DHT_AVAILABLE:
            with sensor_lock:
                latest_sensor_data["sensorStatus"] = "DHT11 unavailable"

            shutdown_event.wait(SENSOR_INTERVAL)
            continue

        reading = read_dht_sensor()

        if reading is None:
            # Keep the previous valid temperature and humidity.
            # Mark the sensor status so the dashboard can show an issue.
            with sensor_lock:
                latest_sensor_data["sensorStatus"] = "Read error"

            shutdown_event.wait(SENSOR_INTERVAL)
            continue

        temperature = reading["temperature"]

        # Apply hysteresis to prevent rapid ON/OFF switching.
        with sensor_lock:
            latest_sensor_data.update(reading)

            if temperature > TEMPERATURE_THRESHOLD:
                buzzer_alert_active = True

            elif temperature <= TEMPERATURE_RESET:
                buzzer_alert_active = False

            latest_sensor_data["temperatureAlert"] = (
                buzzer_alert_active
            )

        print(
            f"[SENSOR] Temperature: {temperature} C | "
            f"Humidity: {reading['humidity']}% | "
            f"Alert: {buzzer_alert_active}"
        )

        shutdown_event.wait(SENSOR_INTERVAL)


# =========================================================
# BUZZER MONITOR
# =========================================================

def buzzer_loop():
    """Beep while the high-temperature alert is active."""

    print("[BUZZER] Background monitoring started")

    while not shutdown_event.is_set():

        with sensor_lock:
            alert_active = latest_sensor_data["temperatureAlert"]

        if not BUZZER_AVAILABLE or buzzer is None:
            with sensor_lock:
                latest_sensor_data["buzzerStatus"] = "Unavailable"

            shutdown_event.wait(0.2)
            continue

        if alert_active:
            try:
                buzzer.on()

                with sensor_lock:
                    latest_sensor_data["buzzerStatus"] = "ON"

                if shutdown_event.wait(0.25):
                    break

                buzzer.off()

                with sensor_lock:
                    latest_sensor_data["buzzerStatus"] = "OFF"

                if shutdown_event.wait(0.25):
                    break

            except Exception as error:
                print(f"[BUZZER] Error: {error}")

                try:
                    buzzer.off()
                except Exception:
                    pass

                shutdown_event.wait(0.5)

        else:
            try:
                buzzer.off()
            except Exception:
                pass

            with sensor_lock:
                latest_sensor_data["buzzerStatus"] = "OFF"

            shutdown_event.wait(0.2)

    if BUZZER_AVAILABLE and buzzer is not None:
        try:
            buzzer.off()
        except Exception:
            pass


# =========================================================
# CAMERA STREAM
# =========================================================

def generate_frames():

    while not shutdown_event.is_set():

        frame = camera.get_frame()

        if frame is None:
            time.sleep(0.02)
            continue

        # CameraManager provides RGB frames.
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        success, buffer = cv2.imencode(
            ".jpg",
            frame,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                JPEG_QUALITY,
            ],
        )

        if not success:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mining Rescue Rover</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <style>
            body {
                background: #101820;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
            }

            h1 {
                color: #00ff99;
            }

            img {
                width: 100%;
                max-width: 900px;
                border: 2px solid #00ff99;
                border-radius: 10px;
            }
        </style>
    </head>

    <body>
        <h1>MINING RESCUE ROVER</h1>
        <p>LIVE CAMERA</p>
        <img src="/video_feed" alt="Rover Camera Stream">
    </body>
    </html>
    """


# =========================================================
# CAMERA API
# =========================================================

@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store",
        },
    )


# =========================================================
# STATUS API
# =========================================================

@app.route("/api/status")
def api_status():

    with sensor_lock:
        data = dict(latest_sensor_data)

    alerts = []

    if data["temperatureAlert"]:
        alerts.append({
            "type": "temperature",
            "severity": "critical",
            "message": (
                f"High temperature detected: "
                f"{data['temperature']} C"
            ),
        })

    if data["sensorStatus"] in (
        "DHT11 unavailable",
        "Read error",
    ):
        alerts.append({
            "type": "sensor",
            "severity": "warning",
            "message": (
                f"Temperature/humidity sensor status: "
                f"{data['sensorStatus']}"
            ),
        })

    return jsonify({
        **data,
        "roverStatus": "Connected",
        "cameraStatus": "Running",
        "alerts": alerts,
    })


# =========================================================
# SENSOR API
# =========================================================

@app.route("/api/sensors")
def api_sensors():

    # Return cached readings immediately.
    # Hardware reads happen in the background thread.
    with sensor_lock:
        data = dict(latest_sensor_data)

    return jsonify(data)


# =========================================================
# ALERT API
# =========================================================

@app.route("/api/alerts")
def api_alerts():

    with sensor_lock:
        data = dict(latest_sensor_data)

    alerts = []

    if data["temperatureAlert"]:
        alerts.append({
            "type": "temperature",
            "severity": "critical",
            "message": (
                f"Temperature is above "
                f"{TEMPERATURE_THRESHOLD} C"
            ),
        })

    if data["sensorStatus"] in (
        "DHT11 unavailable",
        "Read error",
    ):
        alerts.append({
            "type": "sensor",
            "severity": "warning",
            "message": (
                f"Sensor problem: {data['sensorStatus']}"
            ),
        })

    return jsonify(alerts)


# =========================================================
# APPLICATION STARTUP
# =========================================================

def main():

    print("[ROVER] Starting Mining Rescue Rover...")

    sensor_thread = threading.Thread(
        target=sensor_monitor_loop,
        daemon=True,
        name="sensor-monitor",
    )

    buzzer_thread = threading.Thread(
        target=buzzer_loop,
        daemon=True,
        name="buzzer-monitor",
    )

    try:
        camera.start()
        print("[CAMERA] Camera started")

        sensor_thread.start()
        buzzer_thread.start()

        print("[ROVER] Camera and sensor API: port 5000")

        app.run(
            host="0.0.0.0",
            port=5000,
            threaded=True,
            debug=False,
            use_reloader=False,
        )

    except KeyboardInterrupt:
        print("\n[ROVER] Shutdown requested")

    finally:
        shutdown_event.set()

        if BUZZER_AVAILABLE and buzzer is not None:
            try:
                buzzer.off()
                buzzer.close()
            except Exception:
                pass

        if dht_sensor is not None:
            try:
                dht_sensor.exit()
            except Exception:
                pass

        camera.stop()

        print("[ROVER] Shutdown complete")


if __name__ == "__main__":
    main()
