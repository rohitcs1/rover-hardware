from time import sleep
from gpiozero import DistanceSensor

from rover.navigation.servo_controller import ServoController


TRIGGER_DISTANCE_CM = 30

sensor = None
servo = None

try:
    # Ultrasonic sensor: TRIG GPIO23, ECHO GPIO24
    sensor = DistanceSensor(
        echo=24,
        trigger=23,
        max_distance=2.0,
        queue_len=3
    )

    servo = ServoController(pin=18)

    print("Automatic Servo Scan Started")
    print(f"Object detection distance: {TRIGGER_DISTANCE_CM} cm")
    print("Press CTRL+C to stop.")

    object_detected = False

    while True:
        distance_cm = sensor.distance * 100

        print(f"Distance: {distance_cm:.1f} cm")

        if distance_cm <= TRIGGER_DISTANCE_CM and not object_detected:
            object_detected = True

            print("\nObject detected! Starting one scan.")
            servo.scan_once()
            print("Scan complete.\n")

        elif distance_cm > TRIGGER_DISTANCE_CM:
            # Reset only after the object moves away
            object_detected = False

        sleep(0.2)

except KeyboardInterrupt:
    print("\nStopping automatic servo scan...")

finally:
    if servo is not None:
        servo.close()

    if sensor is not None:
        sensor.close()

    print("Stopped safely.")
