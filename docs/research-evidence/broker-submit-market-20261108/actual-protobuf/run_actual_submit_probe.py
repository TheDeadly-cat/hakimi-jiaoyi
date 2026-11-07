"""Bound one actual-source/private-runtime probe; no source/package mutation."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def main():
    base = Path(__file__).resolve().parent
    source = Path(r"C:\Users\Administrator\.codex\worktrees\broker-submit-market-20261108\哈基米v2交易")
    package = Path(r"C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029\HakimiTrade-0.7.0.dev3-candidate-r7")
    name = sys.argv[1]
    assert name.startswith("run-") and name.replace("-", "").isalnum()
    output = base / name
    assert not output.exists()
    output.mkdir()
    for child in ("temp", "profile"):
        (output / child).mkdir()
    manifest_sha = "db2e63e4b02a49d35bcfe612ce28e6a2dc26e1bf9677ffbf015a5d91a372859c"
    assert sha256((package / "terminal-manifest.json").read_bytes()).hexdigest() == manifest_sha
    manifest = json.loads((package / "terminal-manifest.json").read_bytes())
    assert manifest["source_provenance"]["git"]["commit"] == "708ec3f08abdeeae2578726b765483c8c109daa9"
    paths = []
    for folder in (source / "src", source / "outputs/python_quant_bot/exchange_terminal", source / "outputs/python_quant_bot/tests"):
        paths.extend(path for path in folder.rglob("*") if path.is_file() and "__pycache__" not in path.parts
                     and path.suffix in {".py", ".json", ".csv", ".lock", ".toml", ".html"})
    source_hashes = {path.relative_to(source).as_posix(): sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    scripts = output / "scripts"
    scripts.mkdir()
    for filename in ("private_submit_bootstrap.py", "actual_submit_controller.py", "run_actual_submit_probe.py"):
        shutil.copyfile(base / filename, scripts / filename)
    bootstrap, controller = scripts / "private_submit_bootstrap.py", scripts / "actual_submit_controller.py"
    spec = dict(source=str(source), package=str(package), output_root=str(output), manifest_sha256=manifest_sha,
        package_source_commit="708ec3f08abdeeae2578726b765483c8c109daa9", package_bundle_id=manifest["bundle_id"],
        bootstrap=str(bootstrap), bootstrap_sha256=sha256(bootstrap.read_bytes()).hexdigest(),
        controller=str(controller), controller_sha256=sha256(controller.read_bytes()).hexdigest(),
        source_sha256=source_hashes)
    if len(sys.argv) == 3:
        assert sys.argv[2] == "positive-only"
        spec["case_names"] = ["test_six_original_observations_submit_ack_and_reopen_without_new_tcp"]
    specification = output / "input-spec.json"
    specification.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    interpreter = package / "runtime/python/python.exe"
    assert sha256(interpreter.read_bytes()).hexdigest() == manifest["files"]["runtime/python/python.exe"]
    command = [str(interpreter), "-I", "-S", "-B", "-X", "utf8", str(controller), str(specification)]
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SystemDrive") if key in os.environ}
    env.update(PATH=str(interpreter.parent), TEMP=str(output / "temp"), TMP=str(output / "temp"),
               USERPROFILE=str(output / "profile"), APPDATA=str(output / "profile"), LOCALAPPDATA=str(output / "profile"))
    (output / "invocation.json").write_text(json.dumps(dict(command=command, cwd=str(output),
        created_at=datetime.now(timezone.utc).isoformat(), interpreter_sha256=sha256(interpreter.read_bytes()).hexdigest(),
        environment_scope="ONLY_WINDOWS_BASE_PLUS_FRESH_TEST_DATA_PATHS"), indent=2), encoding="utf-8")
    start = time.monotonic()
    with (output / "stdout.log").open("xb") as stdout, (output / "stderr.log").open("xb") as stderr:
        process = subprocess.run(command, cwd=output, env=env, stdout=stdout, stderr=stderr, timeout=420)
    unchanged = all(sha256((source / name).read_bytes()).hexdigest() == value for name, value in source_hashes.items())
    receipt = dict(exit_code=process.returncode, seconds=time.monotonic() - start, outer_timeout_seconds=420,
        source_inputs_unchanged=unchanged,
        package_manifest_unchanged=sha256((package / "terminal-manifest.json").read_bytes()).hexdigest() == manifest_sha)
    (output / "process-result.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt))
    if process.returncode:
        print((output / "stderr.log").read_text(encoding="utf-8", errors="replace"))
        if (output / "actual-tests.log").exists():
            print((output / "actual-tests.log").read_text(encoding="utf-8", errors="replace"))
    return process.returncode or (0 if unchanged and receipt["package_manifest_unchanged"] else 2)


if __name__ == "__main__":
    raise SystemExit(main())
