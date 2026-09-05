from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_dir: str, level: str = "INFO") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    file_handler = logging.FileHandler(Path(log_dir) / "bot.log", encoding="utf-8")
    file_handler.setLevel(numeric_level)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            file_handler,
            stream_handler,
        ],
        force=True,
    )
