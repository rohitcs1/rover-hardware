import time
import board
import adafruit_dht

# DHT11 DATA pin -> Raspberry Pi GPIO4 (Physical Pin 7)
sensor = adafruit_dht.DHT11(board.D4)

try:
    while True:
        try:
            temperature = sensor.temperature
            humidity = sensor.humidity

            if temperature is not None and humidity is not None:
                print(f"Temperature: {temperature:.1f} °C")
                print(f"Humidity: {humidity:.1f} %")
                print("-" * 30)
            else:
                print("Sensor reading unavailable")

        except RuntimeError as error:
            print(f"Temporary sensor read error: {error}")

        time.sleep(2)

except KeyboardInterrupt:
    print("\nSensor test stopped.")

finally:
    sensor.exit()
