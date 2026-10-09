import time
import threading

from gpiozero import DistanceSensor


class UltrasonicSensor:
    """
    HC-SR04 ultrasonic distance sensor.

    Default pins:
        TRIG: BCM GPIO23
        ECHO: BCM GPIO24

    ECHO must be protected from 5V using
    a suitable voltage divider or level shifter.
    """

    def __init__(
        self,
        trigger_pin=23,
        echo_pin=24,
        max_distance=2.0,
    ):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.max_distance = max_distance

        self.sensor = None
        self.lock = threading.Lock()

        self.last_distance_cm = None
        self.last_update = None
        self.status = "Initializing"

        try:
            self.sensor = DistanceSensor(
                echo=self.echo_pin,
                trigger=self.trigger_pin,
                max_distance=self.max_distance,
                queue_len=3,
            )

            self.status = "Connected"
            print(
                f"[ULTRASONIC] Ready: "
                f"TRIG=GPIO{trigger_pin}, "
                f"ECHO=GPIO{echo_pin}"
            )

        except Exception as error:
            self.status = "Unavailable"
            print(f"[ULTRASONIC] Initialization failed: {error}")

    def read_distance(self):
        """Return the latest distance in centimeters."""

        if self.sensor is None:
            return None

        try:
            distance_cm = self.sensor.distance * 100.0

            with self.lock:
                self.last_distance_cm = round(distance_cm, 1)
                self.last_update = time.time()
                self.status = "Connected"

            return round(distance_cm, 1)

        except Exception as error:
            print(f"[ULTRASONIC] Reading error: {error}")

            with self.lock:
                self.status = "Read error"

            return None

    def get_data(self):
        with self.lock:
            return {
                "distance": self.last_distance_cm,
                "sensorStatus": self.status,
                "lastSensorUpdate": self.last_update,
            }

    def close(self):
        if self.sensor is not None:
            self.sensor.close()
            self.sensor = None
            print("[ULTRASONIC] Sensor closed")
