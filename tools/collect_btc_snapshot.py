"""Explicit public history capture. Not imported by research/replay or desktop.

Only GET https://www.okx.com/api/v5/market/history-candles is permitted. No
credentials, account routes, fallback, or cache merge. Retries require an explicit
finite CLI budget; the default remains one attempt. Existing deployments are not
modified. A caller-owned process supplies the hard overall execution deadline.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from pathlib import Path
import time
import urllib.parse
import urllib.request

from capture_diagnostics import Trace, get_public_page

from hakimi_research.dataset_registry import ENDPOINT, ORIGIN, build_snapshot, save_snapshot, utc_time, utc_text
from hakimi_research.data import parse_okx_candle_response
from hakimi_research.documents import parse_document
from hakimi_research.reporting import save_json_report


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("public_capture_redirect_rejected")


def collect(start: str, end: str, output: Path, *, max_http_attempts=1):
    first, last = utc_time(start), utc_time(end)
    if first >= last or (last - first).total_seconds() > 50000 * 3600:
        raise ValueError("explicit_bounded_range_required")
    if last.timestamp() > datetime.now(timezone.utc).timestamp():
        raise ValueError("capture_end_must_be_in_the_past")
    if type(max_http_attempts) is not int or not 1 <= max_http_attempts <= 3:
        raise ValueError("capture_attempt_budget_invalid")
    output.mkdir(parents=True, exist_ok=True)
    # Exclusive receipt prevents a duplicate attempt from silently refetching.
    with (output / "public_capture_trace.jsonl").open("x", encoding="utf-8") as sink:
        trace = Trace(sink)
        trace.emit("COLLECTION", "STARTED", max_http_attempts=max_http_attempts,
                   hard_deadline_owner="CALLER_OWNED_PROCESS", cache_fallback=False)
        return _collect_pages(first, last, output, trace, max_http_attempts)


def _collect_pages(first, last, output, trace, max_http_attempts):
    oldest = int(last.timestamp() * 1000)
    first_ms = int(first.timestamp() * 1000)
    pages = []
    for _ in range(170):
        params = {"instId": "BTC-USDT", "bar": "1H", "limit": 300, "after": oldest}
        url = ORIGIN + ENDPOINT + "?" + urllib.parse.urlencode(params)
        raw = get_public_page(url, trace, max_attempts=max_http_attempts)
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with trace.phase("CONTENT_VALIDATION"):
            payload = parse_document(raw, maximum_bytes=8 * 1024 * 1024)
            if payload.get("code") != "0" or not payload.get("data"):
                raise ValueError("public_capture_failed_or_empty")
            parse_okx_candle_response(raw, endpoint=ENDPOINT, params=params, retrieved_at=retrieved_at)
            if len(payload["data"]) > params["limit"] or any(int(row[0]) >= oldest for row in payload["data"]):
                raise ValueError("public_capture_response_outside_request")
        page = {"raw_base64": base64.b64encode(raw).decode("ascii"), "origin": ORIGIN,
                "endpoint": ENDPOINT, "params": params, "retrieved_at": retrieved_at}
        pages.append(page)
        next_oldest = min(int(row[0]) for row in payload["data"])
        if next_oldest >= oldest:
            raise ValueError("public_capture_cursor_did_not_advance")
        oldest = next_oldest
        if oldest <= first_ms:
            break
        time.sleep(0.25)
    else:
        raise ValueError("public_capture_page_budget_exhausted")
    capture = {"schema_version": "okx-public-capture-v1", "pages": pages,
               "start": utc_text(first), "end_exclusive": utc_text(last), "as_of": utc_text(last),
               "evidence_kind": "PUBLIC_HTTP_CAPTURE"}
    with trace.phase("SNAPSHOT_VALIDATION"):
        snapshot = build_snapshot(pages, start=capture["start"], end=capture["end_exclusive"],
                                  as_of=capture["as_of"], evidence_kind=capture["evidence_kind"])
    with trace.phase("OUTPUT_PERSISTENCE"):
        capture_path = save_json_report(capture, output / "captures", "capture", artifact_id=snapshot.snapshot_id)
        snapshot_path = save_snapshot(snapshot, output / "datasets")
    trace.emit("COLLECTION", "SUCCEEDED", requests=trace.calls, pages=len(pages))
    print(__import__("json").dumps({"capture": str(capture_path), "snapshot": str(snapshot_path),
                                  "snapshot_id": snapshot.snapshot_id, "data_hash": snapshot.document["data_hash"],
                                  "quality": snapshot.document["quality"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-http-attempts", type=int, choices=(1, 2, 3), default=1)
    arguments = parser.parse_args()
    collect(arguments.start, arguments.end, arguments.output_dir, max_http_attempts=arguments.max_http_attempts)
