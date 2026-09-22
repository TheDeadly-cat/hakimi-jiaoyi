"""Package an accepted research wheel and a separate Windows Futu toolkit; no deployment."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

from release_wheel_bundle import export_bundle
from supervised_preview import canonical, sha, verify_bundle


ROOT = Path(__file__).resolve().parents[1]
FUTU_FILES = ("futu_simulation_cycle.py", "futu_simulation_adapter.py", "execution_state_lab.py", "observation_job.py")
EVIDENCE = {
    "evidence/amd-research-summary.json": "docs/research-evidence/real-amd-rth-20260913/research-summary.json",
    "evidence/futu-readonly.json": "docs/research-evidence/real-amd-rth-20260913/futu-readonly.json",
    "evidence/futu-preflight-20260920.json": "docs/research-evidence/futu-preflight-20260920/preflight.json",
    "evidence/futu-readonly-followup.json": "docs/research-evidence/futu-preflight-20260920/readonly-followup.json",
    "evidence/futu-followup-tests.json": "docs/research-evidence/futu-preflight-20260920/followup-tests.json",
    "evidence/futu-resolution-followup.md": "docs/research-evidence/futu-preflight-20260920/resolution-followup.md",
    "evidence/equity-events/study-final-results.json": "docs/research-evidence/equity-events-20260920/study-final-results.json",
    "evidence/equity-events/actual-study-final.md": "docs/research-evidence/equity-events-20260920/actual-study-final.md",
    "evidence/equity-events/source-crosschecks-final.json": "docs/research-evidence/equity-events-20260920/source-crosschecks-final.json",
    "evidence/CURRENT_STATUS.md": "CURRENT_STATUS.md",
}


def deterministic_zip(root, destination):
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                entry = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_STORED
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, path.read_bytes())


def write_bundle(output, kind, files, metadata):
    core = {"schema_version": "supervised-preview-bundle-v1", "kind": kind,
            **metadata, "files": {name: sha(data) for name, data in sorted(files.items())}}
    build_id = "supervised-" + kind + "-" + sha(canonical(core))
    manifest = {**core, "build_id": build_id}
    target = output / build_id
    target.mkdir(parents=True, exist_ok=False)
    for name, data in sorted(files.items()):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    (target / "preview-manifest.json").write_bytes(json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    verify_bundle(target)
    archive = output / (build_id + ".zip")
    deterministic_zip(target, archive)
    return {"build_id": build_id, "directory": target.name, "archive": archive.name, "archive_sha256": sha(archive.read_bytes())}


def build(receipt, output, *, root=ROOT, observation_summary=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("preview_output_exists_use_new_directory")
    # Reuse the existing exact-wheel gate, including its metadata/privacy checks.
    with tempfile.TemporaryDirectory(prefix="hakimi-preview-export-") as temp:
        accepted = Path(temp) / "accepted"
        public = export_bundle(receipt, accepted)
        spec = importlib.util.spec_from_file_location("preview_source_identity", root / "src/hakimi_research/source_identity.py")
        identity_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(identity_module)
        current = identity_module.package_content_identity(root / "src/hakimi_research")
        if current["content_sha256"] != public["source_content_sha256"]:
            raise ValueError("accepted_wheel_not_current_research_source")
        for name, expected in receipt["build_inputs_sha256"].items():
            if sha((root / name).read_bytes()) != expected:
                raise ValueError("accepted_build_input_changed:" + name)
        shared = {name: (root / source).read_bytes() for name, source in EVIDENCE.items()}
        shared["preview.py"] = (root / "tools/supervised_preview.py").read_bytes()
        shared["README.md"] = (root / "docs/supervised-research-preview.md").read_bytes()
        extra = {}
        if observation_summary:
            path = Path(observation_summary).resolve()
            if not path.is_relative_to(root / "docs/research-evidence") or path.suffix != ".json" or path.is_symlink():
                raise ValueError("observation_summary_must_be_public_research_evidence_json")
            raw = path.read_bytes()
            if len(raw) > 1024 * 1024:
                raise ValueError("observation_summary_too_large")
            json.loads(raw)
            shared["evidence/observation-closeout/closeout.json"] = raw
            extra["observation_summary"] = "evidence/observation-closeout/closeout.json"
            for name in ("README.md", "driver-failures.json"):
                sibling = path.with_name(name)
                if sibling.is_symlink():
                    raise ValueError("observation_evidence_regular_file_required")
                if sibling.is_file():
                    shared["evidence/observation-closeout/" + name] = sibling.read_bytes()
        research = dict(shared)
        research.update({"research/" + path.name: path.read_bytes() for path in accepted.iterdir()})
        research["requirements.research.lock"] = (root / "requirements.research.lock").read_bytes()
        research["tools/equity_event_diagnostics.py"] = (root / "tools/equity_event_diagnostics.py").read_bytes()
        for name in ("plan.json", "reference-results.json", "prepared-inputs.json", "README.md", "future-noninterference.json", "collection-review.json"):
            research["evidence/equity-events/" + name] = (root / "docs/research-evidence/equity-events-20260920" / name).read_bytes()
        futu = dict(shared)
        for name in FUTU_FILES:
            futu["tools/" + name] = (root / "tools" / name).read_bytes()
        futu["requirements.futu-sdk.lock"] = (root / "requirements.futu-sdk.lock").read_bytes()
        futu["futu-official-cycle.md"] = (root / "docs/futu-official-cycle.md").read_bytes()
        with zipfile.ZipFile(receipt["wheel"]) as wheel:
            name = next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))
            version = next(line.removeprefix("Version: ") for line in wheel.read(name).decode().splitlines() if line.startswith("Version: "))
        common = {"source": {"repository": "https://github.com/TheDeadly-cat/hakimi-jiaoyi", "wheel_build_git": public["build_git"]},
                  "automatic_account_connection": False, "automatic_monitor_start": False, "automatic_orders": False, **extra}
        if identity_module.package_content_identity(root / "src/hakimi_research") != current:
            raise ValueError("research_source_changed_during_packaging")
        for name in FUTU_FILES:
            if (root / "tools" / name).read_bytes() != futu["tools/" + name]:
                raise ValueError("futu_source_changed_during_packaging")
        output.mkdir(parents=True)
        records = [
            write_bundle(output, "research", research, {**common, "version": version, "research_source_sha256": current["content_sha256"],
                         "wheel": "research/" + public["wheel"], "wheel_sha256": public["wheel_sha256"]}),
            write_bundle(output, "windows-futu", futu, {**common, "version": "SDK 10.7.6708; content-addressed Windows toolkit", "supported_platform": "Windows"}),
        ]
        # No timestamp in the bundle: identical accepted bytes and inputs yield identical archives.
        index = {"schema_version": "supervised-preview-delivery-v1", "formal_release_changed": False,
                 "wheel_version": version, "bundles": records,
                 "scope": "LOCAL_SUPERVISED_PREVIEW_NOT_A_RELEASE_OR_BROKER_ACCEPTANCE"}
        (output / "delivery.json").write_bytes(json.dumps(index, sort_keys=True, indent=2).encode() + b"\n")
        return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--observation-summary", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(json.loads(args.acceptance.read_bytes()), args.output, observation_summary=args.observation_summary), indent=2))
