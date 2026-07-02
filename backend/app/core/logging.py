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

    def _emit(self, level: int, method_name: str, message: str, **kwargs) -> None:
        payload = f"[{method_name}] {message}"
        if kwargs:
            payload = f"{payload} | {kwargs}"
        self.logger.log(level, payload)

    def debug(self, method_name: str, message: str, **kwargs) -> None:
        self._emit(logging.DEBUG, method_name, message, **kwargs)

    def info(self, method_name: str, message: str, **kwargs) -> None:
        self._emit(logging.INFO, method_name, message, **kwargs)

    def warning(self, method_name: str, message: str, **kwargs) -> None:
        self._emit(logging.WARNING, method_name, message, **kwargs)

    def error(self, method_name: str, message: str, **kwargs) -> None:
        self._emit(logging.ERROR, method_name, message, **kwargs)

    def critical(self, method_name: str, message: str, **kwargs) -> None:
        self._emit(logging.CRITICAL, method_name, message, **kwargs)

    def log(self, method_name: str, message: str, **kwargs) -> None:
        self.info(method_name, message, **kwargs)


def get_logger(name: str = "myhostiq") -> AppLogger:
    return AppLogger(name=name)
