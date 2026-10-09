import time
import threading

import cv2

from flask import Flask, Response, jsonify
from flask_cors import CORS

from rover.camera.camera_manager import CameraManager
from rover.camera.camera_settings import JPEG_QUALITY


# DHT11 support
try:
    import board
    import adafruit_dht

    dht_sensor = adafruit_dht.DHT11(board.D4)
    DHT_AVAILABLE = True

except Exception as error:
    print(f"[DHT] Sensor initialization failed: {error}")
    dht_sensor = None
    DHT_AVAILABLE = False


app = Flask(__name__)
CORS(app)

camera = CameraManager()

sensor_lock = threading.Lock()

latest_sensor_data = {
    "temperature": None,
    "humidity": None,
    "sensorStatus": "Initializing",
    "lastSensorUpdate": None,
}


def read_dht_sensor():
    """Read DHT11 temperature and humidity."""

    if not DHT_AVAILABLE:
        return {
            "temperature": None,
            "humidity": None,
            "sensorStatus": "DHT11 unavailable",
            "lastSensorUpdate": None,
        }

    try:
        temperature = dht_sensor.temperature
        humidity = dht_sensor.humidity

        if temperature is None or humidity is None:
            raise RuntimeError("Sensor returned empty readings")

        return {
            "temperature": round(float(temperature), 1),
            "humidity": round(float(humidity), 1),
            "sensorStatus": "Connected",
            "lastSensorUpdate": time.time(),
        }

    except RuntimeError as error:
        print(f"[DHT] Temporary reading error: {error}")

        return None

    except Exception as error:
        print(f"[DHT] Reading failed: {error}")

        return None


def generate_frames():
    while True:
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
        headers={
            "Cache-Control": "no-cache, no-store",
        },
    )


@app.route("/api/status")
def api_status():
    with sensor_lock:
        sensor_data = dict(latest_sensor_data)

    return jsonify({
        **sensor_data,
        "roverStatus": "Connected",
        "cameraStatus": "Running",
        "sensorStatus": sensor_data["sensorStatus"],
        "alerts": [],
    })


@app.route("/api/sensors")
def api_sensors():
    # Preserve the last valid reading if a DHT11 read fails.
    new_reading = read_dht_sensor()

    if new_reading is not None:
        with sensor_lock:
            latest_sensor_data.update(new_reading)

    with sensor_lock:
        data = dict(latest_sensor_data)

    return jsonify(data)


@app.route("/api/alerts")
def api_alerts():
    return jsonify([])


def main():
    print("[ROVER] Starting camera...")
    camera.start()

    try:
        print("[ROVER] Server listening on port 5000")

        app.run(
            host="0.0.0.0",
            port=5000,
            threaded=True,
            debug=False,
        )

    finally:
        camera.stop()

        if dht_sensor is not None:
            try:
                dht_sensor.exit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
