"""
logging_config.py — Cấu hình logging chuẩn cho Privacy Shield Camera.
Sử dụng Python standard logging thay vì safe_print() tùy chỉnh.
"""

import logging
import sys
from pathlib import Path


def setup_logging(level=logging.INFO, log_file=None):
    """Khởi tạo logging cho toàn bộ ứng dụng.
    
    Args:
        level: Mức log (DEBUG, INFO, WARNING, ERROR)
        log_file: Đường dẫn file log (None = chỉ console)
    """
    root_logger = logging.getLogger("privacy_shield")
    
    # Tránh thêm handler trùng lặp khi gọi nhiều lần
    if root_logger.handlers:
        return root_logger
    
    root_logger.setLevel(level)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Console handler (luôn bật)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (nếu được chỉ định)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name):
    """Lấy logger con cho module cụ thể.
    
    Usage:
        from app.utils.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Pipeline started")
    """
    return logging.getLogger(f"privacy_shield.{name}")
