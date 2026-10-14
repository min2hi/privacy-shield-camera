"""
console.py — Backward-compatible wrapper quanh logging module.
safe_print() vẫn hoạt động nhưng giờ đi qua Python standard logging.
"""

import logging
import sys

# Logger mặc định cho các module chưa migrate sang get_logger()
_logger = logging.getLogger("privacy_shield.legacy")


def safe_print(message=""):
    """Backward-compatible: ghi log qua logging module.
    
    Các module mới nên dùng:
        from app.utils.logging_config import get_logger
        logger = get_logger(__name__)
    """
    if not _logger.handlers and not logging.getLogger("privacy_shield").handlers:
        # Fallback nếu logging chưa được setup (e.g., trong tests)
        stream = sys.stdout
        if stream is None:
            return
        text = f"{message}\n"
        buffer = getattr(stream, "buffer", None)
        if buffer is not None:
            buffer.write(text.encode("utf-8", errors="backslashreplace"))
            buffer.flush()
            return
        stream.write(text)
        stream.flush()
        return
    _logger.info("%s", message)

