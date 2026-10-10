from rover.navigation.navigation_manager import NavigationManager
import time

nav = None

try:
    nav = NavigationManager()

    print("\nNavigation test started.")
    print("Press Ctrl+C to stop.\n")

    while True:
        result = nav.update()

        print("\n----- NAVIGATION STATUS -----")
        for key, value in result.items():
            print(f"{key}: {value}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nNavigation test stopped.")

finally:
    if nav is not None:
        nav.close()
