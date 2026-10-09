import time
import threading

from picamera2 import Picamera2

from rover.camera.camera_settings import (
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    CAMERA_FPS,
    CAMERA_FORMAT,
)


class CameraManager:

    def __init__(self):
        self.camera = Picamera2()
        self.latest_frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

        config = self.camera.create_video_configuration(
            main={
                "size": (CAMERA_WIDTH, CAMERA_HEIGHT),
                "format": CAMERA_FORMAT,
            },
            controls={
                "FrameRate": CAMERA_FPS,
            },
            buffer_count=4,
        )

        self.camera.configure(config)

    def start(self):
        if self.running:
            return

        self.camera.start()
        time.sleep(2)

        self.running = True

        self.thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
        )

        self.thread.start()

        print("Camera started successfully.")

    def _capture_loop(self):
        while self.running:
            frame = self.camera.capture_array()

            with self.lock:
                self.latest_frame = frame

    def get_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None

            return self.latest_frame.copy()

    def stop(self):
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

        self.camera.stop()

        print("Camera stopped.")
