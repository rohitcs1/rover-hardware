import threading
import time

from rover.navigation.servo_controller import ServoController
from rover.navigation.ultrasonic_sensor import UltrasonicSensor
from rover.navigation.obstacle_avoidance import ObstacleAvoidance


class NavigationManager:
    """
    Servo scanning and ultrasonic-based direction selection.

    This module does not assume any motor driver GPIO mapping.
    It selects a direction and keeps motorCommand at STOP until
    a verified motor driver is integrated.
    """

    def __init__(
        self,
        servo_pin=18,
        trigger_pin=23,
        echo_pin=24,
        obstacle_distance=50.0,
        minimum_clearance=25.0,
    ):
        self.servo = ServoController(pin=servo_pin)

        self.ultrasonic = UltrasonicSensor(
            trigger_pin=trigger_pin,
            echo_pin=echo_pin,
        )

        self.obstacle_logic = ObstacleAvoidance(
            caution_distance=obstacle_distance,
            danger_distance=20.0,
        )

        self.obstacle_distance = obstacle_distance
        self.minimum_clearance = minimum_clearance

        self._lock = threading.Lock()
        self._scan_lock = threading.Lock()

        self.state = {
            "navigationMode": "READY",
            "currentDirection": "CENTER",
            "frontDistance": None,
            "leftDistance": None,
            "rightDistance": None,
            "selectedDirection": "STOP",
            "obstacleDetected": None,
            "obstacleLevel": "UNKNOWN",
            "obstacleMessage": "Waiting for sensor reading",
            "motorCommand": "STOP",
            "buzzerPattern": "OFF",
            "cameraDirection": "CENTER",
        }

        print("[NAV] Navigation manager initialized")

    def get_status(self):
        with self._lock:
            return dict(self.state)

    def _set_state(self, **kwargs):
        with self._lock:
            self.state.update(kwargs)

    def _read_distance(self):
        try:
            distance = self.ultrasonic.read_distance()

            if distance is None:
                return None

            distance = float(distance)

            if distance <= 0 or distance > 400:
                return None

            return round(distance, 1)

        except Exception as exc:
            print(f"[NAV] Ultrasonic error: {exc}")
            return None

    def _scan_at(self, direction):
        if direction == "LEFT":
            servo_state = self.servo.scan_left()
        elif direction == "RIGHT":
            servo_state = self.servo.scan_right()
        else:
            servo_state = self.servo.center()

        self._set_state(
            currentDirection=direction,
            cameraDirection=direction,
        )

        # Allow the sensor and servo to settle before reading.
        time.sleep(0.15)
        distance = self._read_distance()

        return distance

    def scan_and_choose(self):
        """Scan left/right and select a side with measured clearance."""

        if not self._scan_lock.acquire(blocking=False):
            return self.get_status()

        try:
            self._set_state(
                navigationMode="SCANNING",
                selectedDirection="STOP",
                motorCommand="STOP",
                obstacleMessage="Scanning both sides",
            )

            front = self._scan_at("CENTER")
            left = self._scan_at("LEFT")
            right = self._scan_at("RIGHT")

            # Return the camera/sensor to forward-facing position.
            self.servo.center()

            valid_left = (
                left is not None
                and left >= self.minimum_clearance
            )
            valid_right = (
                right is not None
                and right >= self.minimum_clearance
            )

            if valid_left and valid_right:
                if left > right:
                    selected = "LEFT"
                elif right > left:
                    selected = "RIGHT"
                else:
                    selected = "STOP"

            elif valid_left:
                selected = "LEFT"

            elif valid_right:
                selected = "RIGHT"

            else:
                selected = "STOP"

            if selected == "STOP":
                message = (
                    "No verified safe side; keep the rover stopped"
                )
            else:
                message = (
                    f"{selected} has the greater verified clearance"
                )

            obstacle_info = self.obstacle_logic.analyze_distance(front)

            self._set_state(
                navigationMode="DECISION_READY",
                currentDirection="CENTER",
                cameraDirection="CENTER",
                frontDistance=front,
                leftDistance=left,
                rightDistance=right,
                selectedDirection=selected,
                obstacleDetected=obstacle_info["obstacleDetected"],
                obstacleLevel=obstacle_info["obstacleLevel"],
                obstacleMessage=message,
                buzzerPattern=obstacle_info["buzzerPattern"],
                # Safety: actual motor integration is not configured yet.
                motorCommand="STOP",
            )

            print(
                f"[NAV] front={front}cm, left={left}cm, "
                f"right={right}cm, selected={selected}"
            )

            return self.get_status()

        except Exception as exc:
            self.servo.center()

            self._set_state(
                navigationMode="ERROR",
                selectedDirection="STOP",
                motorCommand="STOP",
                obstacleMessage=f"Navigation error: {exc}",
            )

            print(f"[NAV] Scan failed: {exc}")
            return self.get_status()

        finally:
            self._scan_lock.release()

    def update(self):
        """Check front distance and scan when an obstacle is nearby."""

        front = self._scan_at("CENTER")

        if front is None:
            self._set_state(
                navigationMode="SENSOR_ERROR",
                frontDistance=None,
                selectedDirection="STOP",
                motorCommand="STOP",
                obstacleDetected=None,
                obstacleLevel="UNKNOWN",
                obstacleMessage="Sensor unavailable; stop rover",
                buzzerPattern="OFF",
            )
            return self.get_status()

        obstacle_info = self.obstacle_logic.analyze_distance(front)

        self._set_state(
            frontDistance=front,
            obstacleDetected=obstacle_info["obstacleDetected"],
            obstacleLevel=obstacle_info["obstacleLevel"],
            buzzerPattern=obstacle_info["buzzerPattern"],
        )

        if front <= self.obstacle_distance:
            return self.scan_and_choose()

        self._set_state(
            navigationMode="PATH_CLEAR",
            selectedDirection="FORWARD",
            motorCommand="STOP",
            obstacleMessage="Front path clear; motors not connected",
        )

        return self.get_status()

    def close(self):
        try:
            self.servo.center()
        except Exception:
            pass

        self.servo.close()
        self.ultrasonic.close()
        print("[NAV] Navigation manager closed")
