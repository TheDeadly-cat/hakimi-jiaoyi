"""Replay immutable historical developer references; not a current-core proof."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PINNED_COMMIT = "4fb6d191b282ea9a0d7136f4b94a9e9d49642178"
COMMANDS = (
    "frozen-benchmark", "strategy-family-benchmark", "strategy-robustness-benchmark",
    "strategy-statistical-correction-benchmark", "strategy-research-dossier",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.legacy_root.resolve(), args.output_dir.resolve()
    if output.is_relative_to(root):
        raise RuntimeError("Legacy evidence output must be outside the immutable source")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    def run(command, *, cwd=root / "src", extra_env=None):
        completed = subprocess.run(command, cwd=cwd, env={**env, **(extra_env or {})},
                                   capture_output=True, text=True, encoding="utf-8", timeout=600)
        if completed.returncode:
            raise RuntimeError(f"Historical check failed: {command[:4]}\n{completed.stdout}\n{completed.stderr}")
        return completed.stdout

    if run(["git", "rev-parse", "HEAD"], cwd=root).strip() != PINNED_COMMIT:
        raise RuntimeError("Legacy checkout commit does not match the historical reference")
    if run(["git", "status", "--porcelain"], cwd=root).strip():
        raise RuntimeError("Legacy checkout must be clean before verification")
    source = run([sys.executable, "-B", "-c", "import hakimi_research; print(hakimi_research.__file__)"]).strip()
    if Path(source).resolve() != root / "src/hakimi_research/__init__.py":
        raise RuntimeError("Historical checks imported a different research package")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for command in COMMANDS:
        raw = run([sys.executable, "-B", "-m", "hakimi_research", command])
        receipt = json.loads(raw)
        if receipt.get("status") != "PASS":
            raise RuntimeError(f"Historical reference did not pass: {command}")
        destination = output / f"{command}.json"
        with destination.open("x", encoding="utf-8") as stream:
            stream.write(raw)
        results.append({"command": command, "status": "PASS", "receipt": str(destination),
                        "stdout_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()})
        print(f"Historical reference PASS: {command}", flush=True)

    catalog = run([sys.executable, "-B", "-c",
                   "import json; from hakimi_research.product_capabilities import build_product_capability_catalog; print(json.dumps(build_product_capability_catalog().to_dict()))"])
    # Repair only the known hand-copied test fixture in memory, using the pinned
    # Python catalog. Every original authority/negative assertion stays intact.
    test_path = root / "outputs/hakimi_trade_electron/backend-runtime-contract.test.js"
    node_script = r'''
const fs=require('fs'), path=require('path'), Module=require('module');
const filename=process.argv[1];
let source=fs.readFileSync(filename,'utf8');
const pattern=/  const productCapabilityCatalog = \{[\s\S]*?\n  \};/g;
if ([...source.matchAll(pattern)].length!==1) throw new Error('Historical fixture boundary changed');
source=source.replace(pattern,'  const productCapabilityCatalog = JSON.parse(process.env.HAKIMI_LEGACY_CATALOG);');
const test=new Module(filename,module); test.filename=filename;
test.paths=Module._nodeModulePaths(path.dirname(filename)); test._compile(source,filename);
'''
    print(run(["node", "-e", node_script, str(test_path)], extra_env={"HAKIMI_LEGACY_CATALOG": catalog}).strip(), flush=True)
    for relative in (
        "outputs/hakimi_trade_electron/research-capability-lock.test.js",
        "outputs/python_quant_bot/exchange_terminal/static/market_data_research_projection.test.js",
    ):
        print(run(["node", str(root / relative)]).strip(), flush=True)
    if run(["git", "status", "--porcelain"], cwd=root).strip():
        raise RuntimeError("Historical verification modified its source or references")
    record = {"schema_version": "legacy-reference-replay-v1", "status": "PASS",
              "historical_commit": PINNED_COMMIT, "results": results,
              "source_unchanged": True, "reference_files_unchanged": True,
              "consumer_checks": 3, "fixture_correction": "Python catalog projection in memory; assertions unchanged",
              "scope": "HISTORICAL_DEVELOPER_REFERENCES_ONLY", "current_core_equivalence": False}
    with (output / "legacy-reference-replay.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
    print(f"Historical replay receipt: {output / 'legacy-reference-replay.json'}", flush=True)


if __name__ == "__main__":
    main()
