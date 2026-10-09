import threading
import time

from gpiozero import OutputDevice


class BuzzerController:
    """
    Centralized active-high buzzer controller.

    Temperature alert:
        Short repeated beeps.

    Obstacle caution:
        Slow beeps.

    Obstacle danger:
        Fast beeps.

    Priority:
        Temperature alert > Obstacle danger > Obstacle caution.
    """

    def __init__(self, pin=17):
        self.pin = pin

        self.temperature_alert = False
        self.obstacle_pattern = "OFF"

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None

        self.buzzer = None
        self.status = "Unavailable"

        try:
            self.buzzer = OutputDevice(
                pin,
                active_high=True,
                initial_value=False,
            )

            self.status = "OFF"

            self.thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="buzzer-controller",
            )

            self.thread.start()

            print(f"[BUZZER] Controller ready on GPIO{pin}")

        except Exception as error:
            print(f"[BUZZER] Initialization failed: {error}")

    def set_temperature_alert(self, active):
        with self.lock:
            self.temperature_alert = bool(active)

    def set_obstacle_pattern(self, pattern):
        allowed = {"OFF", "SLOW", "FAST"}

        if pattern not in allowed:
            pattern = "OFF"

        with self.lock:
            self.obstacle_pattern = pattern

    def get_status(self):
        with self.lock:
            return {
                "buzzerStatus": self.status,
                "temperatureAlert": self.temperature_alert,
                "obstaclePattern": self.obstacle_pattern,
            }

    def _get_pattern(self):
        with self.lock:
            temperature_alert = self.temperature_alert
            obstacle_pattern = self.obstacle_pattern

        if temperature_alert:
            # Short beeps: 0.15 s ON, 0.15 s OFF.
            return 0.15, 0.15, "TEMPERATURE"

        if obstacle_pattern == "FAST":
            # Very close obstacle.
            return 0.10, 0.10, "OBSTACLE_DANGER"

        if obstacle_pattern == "SLOW":
            # Nearby obstacle.
            return 0.20, 0.60, "OBSTACLE_CAUTION"

        return None, None, "OFF"

    def _run(self):
        while not self.stop_event.is_set():
            on_time, off_time, mode = self._get_pattern()

            if self.buzzer is None:
                self.stop_event.wait(0.2)
                continue

            try:
                if mode == "OFF":
                    self.buzzer.off()

                    with self.lock:
                        self.status = "OFF"

                    self.stop_event.wait(0.1)
                    continue

                self.buzzer.on()

                with self.lock:
                    self.status = mode

                if self.stop_event.wait(on_time):
                    break

                self.buzzer.off()

                with self.lock:
                    self.status = "OFF"

                self.stop_event.wait(off_time)

            except Exception as error:
                print(f"[BUZZER] Runtime error: {error}")
                self.stop_event.wait(0.5)

        if self.buzzer is not None:
            try:
                self.buzzer.off()
            except Exception:
                pass

    def close(self):
        self.stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

        if self.buzzer is not None:
            try:
                self.buzzer.off()
                self.buzzer.close()
            except Exception:
                pass

        self.status = "OFF"
        print("[BUZZER] Controller closed")
