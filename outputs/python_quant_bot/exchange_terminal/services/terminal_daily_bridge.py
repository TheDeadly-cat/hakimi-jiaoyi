"""Pure canonical-daily -> original-strategy input receipts, with no I/O.

The caller explicitly retains the exact verified ``raw`` bytes in the fixed
daily-originals path, then stores the independently sealed native receipt.
Neither function imports into the frozen core or runs any strategy. A REVIEW
receipt allows descriptive native research only, never source authentication.
"""
from __future__ import annotations

from hashlib import sha256
import re


NAMESPACE = "canonical-daily-v1"
REFERENCE_SCHEMA = "hakimi-terminal-daily-reference-v1"
_ID = re.compile(r"canon-[0-9a-f]{32}\Z")
_LAYOUT_ERROR = (
    "terminal_daily_saved_layout_required: "
    "请从当前股票日线资料的保存流程获得可复用输入；散放或改名文件仍可只读查看，本桥不移动文件。"
)


def _verified(raw, supplied=None):
    # This is intentionally the current canonical verifier, not the frozen
    # hakimi_terminal_research package and not the independent action adapter.
    from hakimi_research.documents import canonical_bytes, parse_document
    from hakimi_research.equity_dataset import verify_equity_snapshot

    snapshot = verify_equity_snapshot(parse_document(raw))
    if supplied is not None:
        if type(supplied) is not dict:
            raise ValueError("terminal_daily_verified_snapshot_dict_required")
        checked = verify_equity_snapshot(supplied)
        if canonical_bytes(checked) != canonical_bytes(snapshot):
            raise ValueError("terminal_daily_raw_snapshot_identity_conflict")
    return snapshot


def _saved_binding(snapshot, raw, canonical_id):
    """Bind only the existing input_workflow._retain content-addressed layout.

    TerminalDailyResearch._id hashes the POSIX relative storage path. The
    official save/freeze flow uses this exact path; arbitrary renamed files
    cannot have their canonical reference verified from raw bytes alone.
    """
    file_hash = sha256(raw).hexdigest()
    relative = "data/snapshots/" + snapshot["snapshot_id"] + "/" + file_hash + ".json"
    expected = "canon-" + sha256(relative.encode("utf-8")).hexdigest()[:32]
    if type(canonical_id) is not str or _ID.fullmatch(canonical_id) is None or canonical_id != expected:
        raise ValueError(_LAYOUT_ERROR)
    return file_hash, relative


def _receipt(raw, snapshot, canonical_id):
    # Lazy import avoids a cycle when TerminalResearchService adds its explicit
    # daily-reference read branch. Reuse its existing data/admission checks;
    # discard the intermediate core reference before sealing our own receipt.
    from .terminal_research import _core_input_adapter, _seal

    file_hash, relative = _saved_binding(snapshot, raw, canonical_id)
    common = _core_input_adapter(snapshot, canonical_id, file_hash)
    meta = dict(common["meta"])
    meta.update(daily_snapshot_id=meta.pop("core_snapshot_id"),
                daily_research_admission=meta.pop("core_research_admission"),
                daily_input_id=canonical_id, source_namespace=NAMESPACE,
                canonical_package="hakimi_research")
    quality = dict(common["quality"])
    quality["frozen_core_import_allowed"] = quality.pop("core_us_equity_import_allowed")
    quality["blockers"] = ["daily_" + reason[5:] if reason.startswith("core_") else reason
                           for reason in quality["blockers"]]
    reference = {
        "schema_version": REFERENCE_SCHEMA, "record_namespace": NAMESPACE,
        "canonical_package": "hakimi_research",
        "verifier": "hakimi_research.equity_dataset.verify_equity_snapshot",
        "canonical_input_id": canonical_id, "canonical_storage_ref": relative,
        "snapshot_hash": snapshot["snapshot_id"], "file_sha256": file_hash,
        "source_manifest_hash": snapshot["raw_input"]["manifest_sha256"],
        "csv_sha256": snapshot["raw_input"]["csv_sha256"],
        "original_schema": snapshot["schema_version"],
        "original_bytes_path": "terminal-inputs/daily-originals/" + file_hash + ".json",
        "original_byte_count": len(raw), "original_rewritten": False,
    }
    core = {key: value for key, value in common.items() if key not in {"id", "core_reference"}}
    core.update(source_id="daily-canonical-price-snapshot:" + snapshot["snapshot_id"],
                meta=meta, quality=quality, daily_reference=reference)
    return _seal(core)


def build_native_daily_input(raw, verified_snapshot, canonical_id):
    """Build a separate sealed native receipt; BLOCK is for preview only.

    ``raw`` must be the exact bytes obtained from the trusted daily reader and
    ``verified_snapshot`` its canonical document. Both are verified again. The
    canonical ID must belong to the existing save/freeze storage layout. No
    caller-supplied filesystem path is accepted, read, or written.
    """
    if type(verified_snapshot) is not dict:
        raise ValueError("terminal_daily_verified_snapshot_dict_required")
    return _receipt(raw, _verified(raw, verified_snapshot), canonical_id)


def verify_native_daily_input(record, raw):
    """Rebuild every field from retained bytes and require native admission.

    The caller reads only ``terminal-inputs/daily-originals/<file_sha256>.json``
    after validating the hash and workspace containment; never follow a path
    taken from a client or receipt. Returned data is freshly reconstructed.
    """
    from .terminal_research import _bytes

    if type(record) is not dict or type(record.get("daily_reference")) is not dict:
        raise ValueError("terminal_daily_reference_required")
    if "core_reference" in record:
        raise ValueError("terminal_daily_core_reference_ambiguous")
    reference = record["daily_reference"]
    expected = _receipt(raw, _verified(raw), reference.get("canonical_input_id"))
    # Canonical serialization distinguishes JSON booleans from 0/1, unlike
    # Python dict equality. It also rejects non-finite or non-JSON drift.
    try:
        matches = _bytes(record) == _bytes(expected)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("terminal_daily_reference_changed") from exc
    if not matches:
        raise ValueError("terminal_daily_reference_changed")
    if expected["quality"]["status"] != "REVIEW" or expected["quality"]["blockers"]:
        raise ValueError("terminal_daily_input_blocked:" + ";".join(expected["quality"]["blockers"]))
    return expected
