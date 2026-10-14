"""Virtual camera adapter that only accepts already-processed frames."""

from __future__ import annotations

import cv2


class VirtualCameraOutput:
    def __init__(self, width, height, fps, backend=None):
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps)
        self.backend = backend
        self.camera = None

    def open(self):
        if self.camera is not None:
            return
        if self.backend is None:
            import pyvirtualcam

            self.backend = pyvirtualcam
        self.camera = self.backend.Camera(
            width=self.width,
            height=self.height,
            fps=self.fps,
            fmt=self.backend.PixelFormat.RGB,
        )

    def send_bgr(self, processed_frame):
        if self.camera is None:
            raise RuntimeError("Virtual camera is not open")
        if processed_frame.shape[:2] != (self.height, self.width):
            processed_frame = cv2.resize(processed_frame, (self.width, self.height))
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        self.camera.send(rgb_frame)
        self.camera.sleep_until_next_frame()

    def close(self):
        if self.camera is not None:
            self.camera.close()
            self.camera = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
