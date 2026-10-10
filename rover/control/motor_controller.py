class MotorController:
    """
    Safe placeholder until the actual motor driver and GPIO wiring
    are configured.

    This controller deliberately does not energize any motor pins.
    """

    def __init__(self):
        self.current_command = "STOP"
        print("[MOTOR] Safe placeholder initialized; no motor GPIO configured")

    def stop(self):
        self.current_command = "STOP"
        print("[MOTOR] STOP")

    def forward(self):
        self.stop()
        print("[MOTOR] Forward unavailable: motor driver not configured")

    def turn_left(self):
        self.stop()
        print("[MOTOR] Left turn unavailable: motor driver not configured")

    def turn_right(self):
        self.stop()
        print("[MOTOR] Right turn unavailable: motor driver not configured")

    def execute_navigation(self, direction):
        # Never move wheels without verified driver configuration.
        self.stop()
        return {
            "requestedDirection": direction,
            "motorCommand": "STOP",
            "reason": "Motor driver GPIO mapping is not configured",
        }

    def close(self):
        self.stop()
