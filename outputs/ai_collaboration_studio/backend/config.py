from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_DIR / "runtime"
DATABASE_PATH = RUNTIME_DIR / "collaboration_studio.sqlite3"
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"


def _load_local_env() -> None:
    candidates = [PROJECT_DIR / ".env.local"]
    candidates.extend(parent / ".env.local" for parent in PROJECT_DIR.parents[:4])
    for path in candidates:
        if not path.is_file():
            continue
        try:
            for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                clean_name = name.strip()
                if clean_name not in {
                    "OPENAI_API_KEY",
                    "OPENAI_BASE_URL",
                    "OPENAI_MODEL",
                }:
                    continue
                clean_value = value.strip().strip('"').strip("'")
                if clean_value:
                    os.environ.setdefault(clean_name, clean_value)
            return
        except OSError:
            continue


_load_local_env()
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
HOST = os.getenv("AI_STUDIO_HOST", "127.0.0.1")
PORT = int(os.getenv("AI_STUDIO_PORT", "8770"))

