from gpiozero import AngularServo
from time import sleep

# Servo signal: BCM GPIO18
servo = AngularServo(
    18,
    min_angle=-90,
    max_angle=90,
    min_pulse_width=0.0005,
    max_pulse_width=0.0025
)

try:
    while True:
        print("Center: 0 degrees")
        servo.angle = 0
        sleep(2)

        print("Left: -45 degrees")
        servo.angle = -45
        sleep(2)

        print("Center: 0 degrees")
        servo.angle = 0
        sleep(2)

        print("Right: +45 degrees")
        servo.angle = 45
        sleep(2)

except KeyboardInterrupt:
    print("\nServo test stopped.")

finally:
    servo.detach()
    servo.close()
