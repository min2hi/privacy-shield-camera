"""Encoding-safe console output for Windows terminals."""

from __future__ import annotations

import sys


def safe_print(message=""):
    text = f"{message}\n"
    stream = sys.stdout
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        buffer.write(text.encode("utf-8", errors="backslashreplace"))
        buffer.flush()
        return
    stream.write(text)
    stream.flush()
