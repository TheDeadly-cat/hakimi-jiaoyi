"""Generate/check Node's committed JSON projection from canonical Python data."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def generated_bytes(root: Path) -> bytes:
    source = root / "src/hakimi_research/capability_definition.py"
    spec = importlib.util.spec_from_file_location("_canonical_capability_definition", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return (json.dumps(module.build_product_capability_definition(), indent=2, ensure_ascii=True,
                       allow_nan=False) + "\n").encode("ascii")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = root / "src/hakimi_research/contracts/product-capabilities.json"
    expected = generated_bytes(root)
    if args.check:
        if not target.is_file() or target.read_bytes() != expected:
            raise SystemExit("Capability projection drift: run python tools/generate_product_capabilities.py")
        print("Canonical Python capability projection: PASS")
    else:
        target.write_bytes(expected)
        print("Generated capability projection from canonical Python definitions")


if __name__ == "__main__":
    main()
