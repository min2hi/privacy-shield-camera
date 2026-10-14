from __future__ import annotations

import numpy as np
from app.core.virtual_camera import VirtualCameraOutput


class FakeCamera:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.frames = []
        self.closed = False

    def send(self, frame):
        self.frames.append(frame.copy())

    def sleep_until_next_frame(self):
        pass

    def close(self):
        self.closed = True


class FakeBackend:
    class PixelFormat:
        RGB = "rgb"

    def __init__(self):
        self.created = None

    def Camera(self, **kwargs):
        self.created = FakeCamera(**kwargs)
        return self.created


def test_virtual_camera_converts_processed_bgr_to_rgb_and_closes():
    backend = FakeBackend()
    output = VirtualCameraOutput(4, 3, 30, backend=backend)
    output.open()
    processed = np.zeros((3, 4, 3), dtype=np.uint8)
    processed[0, 0] = [10, 20, 30]
    output.send_bgr(processed)

    assert backend.created.frames[0][0, 0].tolist() == [30, 20, 10]
    output.close()
    assert backend.created.closed
