import time
import threading

import cv2
from flask import Flask, Response, jsonify
from flask_cors import CORS

from rover.camera.camera_manager import CameraManager
from rover.camera.camera_settings import JPEG_QUALITY
from rover.navigation.ultrasonic_sensor import UltrasonicSensor
from rover.navigation.obstacle_avoidance import ObstacleAvoidance
from rover.control.buzzer_controller import BuzzerController
from rover.navigation.servo_controller import ServoController


# ---------------- DHT11 ----------------

try:
    import board
    import adafruit_dht

    dht_sensor = adafruit_dht.DHT11(board.D4)
    DHT_AVAILABLE = True
    print("[DHT] Initialized on GPIO4")

except Exception as error:
    print(f"[DHT] Initialization failed: {error}")
    dht_sensor = None
    DHT_AVAILABLE = False


# ---------------- Flask and devices ----------------

app = Flask(__name__)
CORS(app)

camera = CameraManager()

ultrasonic = None
obstacle_logic = ObstacleAvoidance()
buzzer_controller = None
servo_controller = None
obstacle_scan_active = False
servo_scan_lock = threading.Lock()
SERVO_TRIGGER_DISTANCE_CM = 30.0


sensor_lock = threading.Lock()
shutdown_event = threading.Event()

TEMPERATURE_THRESHOLD = 38.0
TEMPERATURE_RESET = 37.5

temperature_alert_active = False

latest_sensor_data = {
    "temperature": None,
    "humidity": None,
    "sensorStatus": "Initializing",
    "lastSensorUpdate": None,
    "temperatureAlert": False,
    "distance": None,
    "ultrasonicStatus": "Initializing",
    "obstacleDetected": None,
    "obstacleLevel": "UNKNOWN",
    "obstacleMessage": "Waiting for ultrasonic reading",
    "buzzerStatus": "OFF",
    "obstacleBuzzerPattern": "OFF",
    "roverStatus": "Connected",
    "cameraStatus": "Initializing",
    "alerts": [],
}


# ---------------- Background monitoring ----------------

def sensor_monitor_loop():
    global temperature_alert_active

    print("[SENSOR] Monitoring started")

    while not shutdown_event.is_set():

        # Read temperature and humidity
        if DHT_AVAILABLE and dht_sensor is not None:
            try:
                temperature = dht_sensor.temperature
                humidity = dht_sensor.humidity

                if temperature is not None and humidity is not None:
                    temperature = round(float(temperature), 1)
                    humidity = round(float(humidity), 1)

                    with sensor_lock:
                        latest_sensor_data.update({
                            "temperature": temperature,
                            "humidity": humidity,
                            "sensorStatus": "Connected",
                            "lastSensorUpdate": time.time(),
                        })

                        if temperature > TEMPERATURE_THRESHOLD:
                            temperature_alert_active = True
                        elif temperature <= TEMPERATURE_RESET:
                            temperature_alert_active = False

                        latest_sensor_data["temperatureAlert"] = (
                            temperature_alert_active
                        )

                    if buzzer_controller is not None:
                        buzzer_controller.set_temperature_alert(
                            temperature_alert_active
                        )

                    print(
                        f"[DHT] Temp={temperature} C, "
                        f"Humidity={humidity}%"
                    )

            except RuntimeError as error:
                # DHT11 can have occasional temporary read errors.
                print(f"[DHT] Temporary read error: {error}")

            except Exception as error:
                print(f"[DHT] Read error: {error}")

        else:
            with sensor_lock:
                latest_sensor_data["sensorStatus"] = "DHT11 unavailable"

        shutdown_event.wait(2.0)


def scan_servo_once():
    if servo_controller is None:
        print("[SERVO] Controller unavailable")
        return

    if not servo_scan_lock.acquire(blocking=False):
        return

    try:
        print("[SERVO] LEFT")
        servo_controller.move_smoothly(-45)
        time.sleep(0.3)

        print("[SERVO] RIGHT")
        servo_controller.move_smoothly(45)
        time.sleep(0.3)

        print("[SERVO] CENTER")
        servo_controller.move_smoothly(0)
        print("[SERVO] Scan complete")
    except Exception as error:
        print(f"[SERVO] Scan error: {error}")
    finally:
        servo_scan_lock.release()


def ultrasonic_monitor_loop():
    global obstacle_scan_active
    print("[ULTRASONIC] Monitoring started")

    while not shutdown_event.is_set():

        distance = None

        if ultrasonic is not None:
            distance = ultrasonic.read_distance()

        if distance is None:
            result = obstacle_logic.analyze_distance(None)

            with sensor_lock:
                latest_sensor_data.update({
                    "distance": None,
                    "ultrasonicStatus": (
                        ultrasonic.get_data()["sensorStatus"]
                        if ultrasonic is not None
                        else "Unavailable"
                    ),
                    **result,
                })

            if buzzer_controller is not None:
                buzzer_controller.set_obstacle_pattern("OFF")

        else:
            result = obstacle_logic.analyze_distance(distance)

            if distance <= SERVO_TRIGGER_DISTANCE_CM:
                if not obstacle_scan_active:
                    obstacle_scan_active = True
                    threading.Thread(
                        target=scan_servo_once,
                        daemon=True,
                        name="servo-obstacle-scan",
                    ).start()
            else:
                obstacle_scan_active = False

            with sensor_lock:
                latest_sensor_data.update({
                    "distance": distance,
                    "ultrasonicStatus": "Connected",
                    **result,
                })

            if buzzer_controller is not None:
                buzzer_controller.set_obstacle_pattern(
                    result["buzzerPattern"]
                )

            print(
                f"[ULTRASONIC] Distance={distance} cm | "
                f"Level={result['obstacleLevel']} | "
                f"Buzzer={result['buzzerPattern']}"
            )

        shutdown_event.wait(0.15)


# ---------------- Camera stream ----------------

def generate_frames():
    while not shutdown_event.is_set():
        frame = camera.get_frame()

        if frame is None:
            time.sleep(0.02)
            continue

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        success, buffer = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY],
        )

        if not success:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


# ---------------- API helpers ----------------

def build_alerts(data):
    alerts = []

    if data.get("temperatureAlert"):
        alerts.append({
            "type": "temperature",
            "severity": "critical",
            "message": (
                f"High temperature: {data.get('temperature')} C"
            ),
        })

    if data.get("obstacleLevel") == "DANGER":
        alerts.append({
            "type": "obstacle",
            "severity": "critical",
            "message": data.get("obstacleMessage"),
        })

    elif data.get("obstacleLevel") == "CAUTION":
        alerts.append({
            "type": "obstacle",
            "severity": "warning",
            "message": data.get("obstacleMessage"),
        })

    if data.get("ultrasonicStatus") in ("Unavailable", "Read error"):
        alerts.append({
            "type": "ultrasonic",
            "severity": "warning",
            "message": (
                "Ultrasonic sensor is unavailable or has a reading error"
            ),
        })

    return alerts


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
            h1 { color: #00ff99; }
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


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store"},
    )


@app.route("/api/status")
def api_status():
    with sensor_lock:
        data = dict(latest_sensor_data)

    data["alerts"] = build_alerts(data)
    return jsonify(data)


@app.route("/api/sensors")
def api_sensors():
    with sensor_lock:
        return jsonify(dict(latest_sensor_data))


@app.route("/api/alerts")
def api_alerts():
    with sensor_lock:
        data = dict(latest_sensor_data)

    return jsonify(build_alerts(data))


# ---------------- Application startup ----------------

def main():
    global ultrasonic, buzzer_controller, servo_controller

    print("[ROVER] Starting Mining Rescue Rover")

    try:
        # Create one shared buzzer controller.
        buzzer_controller = BuzzerController(pin=17)

        try:
            servo_controller = ServoController(pin=18)
            print("[SERVO] Initialized on GPIO18")
        except Exception as error:
            servo_controller = None
            print(f"[SERVO] Initialization failed: {error}")

        # Initialize ultrasonic sensor.
        try:
            ultrasonic = UltrasonicSensor(
                trigger_pin=23,
                echo_pin=24,
            )
        except Exception as error:
            ultrasonic = None
            print(f"[ULTRASONIC] Initialization failed: {error}")

        camera.start()

        with sensor_lock:
            latest_sensor_data["cameraStatus"] = "Running"

        sensor_thread = threading.Thread(
            target=sensor_monitor_loop,
            daemon=True,
            name="sensor-monitor",
        )

        ultrasonic_thread = threading.Thread(
            target=ultrasonic_monitor_loop,
            daemon=True,
            name="ultrasonic-monitor",
        )

        sensor_thread.start()
        ultrasonic_thread.start()

        print("[ROVER] API available on port 5000")

        app.run(
            host="0.0.0.0",
            port=5000,
            threaded=True,
            debug=False,
            use_reloader=False,
        )

    except KeyboardInterrupt:
        print("[ROVER] Shutdown requested")

    finally:
        shutdown_event.set()

        if buzzer_controller is not None:
            buzzer_controller.close()

        if ultrasonic is not None:
            ultrasonic.close()

        if servo_controller is not None:
            servo_controller.close()

        if dht_sensor is not None:
            try:
                dht_sensor.exit()
            except Exception:
                pass

        camera.stop()
        print("[ROVER] Shutdown complete")


if __name__ == "__main__":
    main()
