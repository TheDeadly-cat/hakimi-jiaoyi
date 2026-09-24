"""Recheck retained announcement candidates; never generate human approval."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.equity_content_protocol import digest, utc, validate_approval
from tools.prepare_announcement_review import extract


def recheck(packet_path, source_root, receipt=None):
    packet_path, source_root = Path(packet_path), Path(source_root)
    packet = json.loads(packet_path.read_text(encoding="utf-8-sig"))
    approved = validate_approval(packet, receipt)
    index_bytes = (source_root / "source-index.json").read_bytes()
    if hashlib.sha256(index_bytes).hexdigest() != packet["sources_index_sha256"]:
        raise ValueError("announcement_source_index_changed")
    sources = json.loads(index_bytes)["receipts"]
    if len(sources) != len(packet["events"]) or len({s["fiscal_quarter"] for s in sources}) != len(sources):
        raise ValueError("announcement_source_coverage_mismatch")
    by_quarter = {s["fiscal_quarter"]: s for s in sources}
    checked = []
    for candidate in packet["events"]:
        if candidate["candidate_hash"] != digest({k: v for k, v in candidate.items() if k != "candidate_hash"}):
            raise ValueError("announcement_candidate_changed")
        source = by_quarter[candidate["fiscal_quarter"]]
        if Path(source["file"]).name != source["file"]:
            raise ValueError("announcement_source_basename_required")
        raw = (source_root / source["file"]).read_bytes()
        if (source["status"] != 200 or len(raw) != source["size"]
                or hashlib.sha256(raw).hexdigest() != source["sha256"]
                or candidate["raw_sha256"] != source["sha256"]
                or candidate["source_url"] != source["url"]
                or candidate["retrieved_at"] != source["retrieved_at"]):
            raise ValueError("announcement_retained_source_mismatch")
        regenerated, text = extract(raw.decode("utf-8"), candidate["fiscal_quarter"])
        for field in ("facts", "fiscal_quarter", "first_public_at", "publication_precision", "plain_text_sha256"):
            if candidate[field] != regenerated[field]:
                raise ValueError("announcement_extraction_mismatch:" + field)
        # prepare() used platform text newlines; the packet hashes normalized LF text.
        if (packet_path.parent / (candidate["fiscal_quarter"] + ".txt")).read_text(encoding="utf-8") != text:
            raise ValueError("announcement_retained_plain_text_changed")
        for fact in candidate["facts"]:
            evidence = fact["evidence"]
            if text[evidence["plain_text_start"]:evidence["plain_text_end"]] != evidence["quote"]:
                raise ValueError("announcement_quote_offset_mismatch")
        if not utc(candidate["first_public_at"]) <= utc(candidate["retrieved_at"]) <= utc(candidate["extraction_completed_at"]):
            raise ValueError("announcement_clock_order_invalid")
        checked.append({"fiscal_quarter": candidate["fiscal_quarter"],
                        "candidate_hash": candidate["candidate_hash"], "raw_sha256": source["sha256"],
                        "quote_count": len(candidate["facts"]), "first_public_at": candidate["first_public_at"]})
    return {"schema_version": "announcement-retained-recheck-v1", "packet_hash": packet["packet_hash"],
            "packet_file_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
            "status": "PASS", "rows": checked, "human_approved_rows": len(approved),
            "scope": "Retained bytes, deterministic extraction, quote offsets, units, periods and UTC clock binding. Not historical page immutability or independent publisher authentication.",
            "order_allowed": False}
