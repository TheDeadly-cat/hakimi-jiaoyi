"""Fail-closed logging configuration for the local research CLI."""

from __future__ import annotations

import logging
from pathlib import Path


RESEARCH_LOGGING_SCHEMA_VERSION = "research-logging-v1"

_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _validate_log_directory(log_dir: str) -> Path:
    if type(log_dir) is not str or not log_dir or log_dir != log_dir.strip():
        raise ValueError("log_dir must be an exact non-empty string")
    if "\x00" in log_dir:
        raise ValueError("log_dir contains a null byte")
    return Path(log_dir)


def _validate_log_level(level: str) -> int:
    if type(level) is not str or level not in _LOG_LEVELS:
        raise ValueError("logging level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
    return _LOG_LEVELS[level]


def setup_logging(log_dir: str, level: str = "INFO") -> None:
    """Configure file and warning-console handlers after validating all inputs."""

    directory = _validate_log_directory(log_dir)
    log_level = _validate_log_level(level)

    directory.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(directory / "bot.log", encoding="utf-8")
    file_handler.setLevel(log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[file_handler, console_handler],
        force=True,
    )


__all__ = ["RESEARCH_LOGGING_SCHEMA_VERSION", "setup_logging"]
