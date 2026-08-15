from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import tempfile


_requested_runtime = str(os.getenv("HAKIMI_TEST_RUNTIME_DIR") or "").strip()
if _requested_runtime:
    TEST_RUNTIME_DIR = Path(_requested_runtime).expanduser().resolve()
    TEST_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
else:
    TEST_RUNTIME_DIR = Path(tempfile.mkdtemp(prefix="hakimi-trade-tests-"))
    atexit.register(shutil.rmtree, TEST_RUNTIME_DIR, ignore_errors=True)

os.environ["HAKIMI_TEST_MODE"] = "1"
os.environ["HAKIMI_RUNTIME_DIR"] = str(TEST_RUNTIME_DIR)
