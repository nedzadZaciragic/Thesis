import logging
import sys
from typing import Optional


class AppLogger:
    """Centralized logger with consistent structured prefixing."""

    def __init__(self, name: str = "myhostiq", level: Optional[int] = None) -> None:
        self.logger = logging.getLogger(name)
        if level is not None:
            self.logger.setLevel(level)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
        self.logger.propagate = False

    def log(self, method_name: str, message: str, **kwargs) -> None:
        payload = f"[{method_name}] {message}"
        if kwargs:
            payload = f"{payload} | {kwargs}"
        self.logger.info(payload)

    def error(self, method_name: str, message: str, **kwargs) -> None:
        payload = f"[{method_name}] {message}"
        if kwargs:
            payload = f"{payload} | {kwargs}"
        self.logger.error(payload)


def get_logger(name: str = "myhostiq") -> AppLogger:
    return AppLogger(name=name)
