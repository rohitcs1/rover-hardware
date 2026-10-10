from gpiozero import AngularServo
from time import sleep


class ServoController:
    def __init__(self, pin=18):
        self.servo = AngularServo(
            pin,
            min_angle=-45,
            max_angle=45,
            min_pulse_width=0.0005,
            max_pulse_width=0.0025,
            initial_angle=0
        )

        self.current_angle = 0
        sleep(0.5)

    def move_smoothly(self, target_angle, step=2, delay=0.04):
        """Move servo smoothly in small angle steps."""
        target_angle = max(-45, min(45, target_angle))

        direction = 1 if target_angle > self.current_angle else -1

        while self.current_angle != target_angle:
            next_angle = self.current_angle + direction * step

            if direction == 1:
                next_angle = min(next_angle, target_angle)
            else:
                next_angle = max(next_angle, target_angle)

            self.servo.angle = next_angle
            self.current_angle = next_angle
            sleep(delay)

    def center(self):
        self.move_smoothly(0)

    def scan_once(self):
        """Scan LEFT, RIGHT, then return to CENTER."""
        print("Servo scanning LEFT...")
        self.move_smoothly(-45)
        sleep(0.3)

        print("Servo scanning RIGHT...")
        self.move_smoothly(45)
        sleep(0.3)

        print("Servo returning to CENTER...")
        self.move_smoothly(0)

    def close(self):
        self.servo.close()
