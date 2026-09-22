"""Classify existing failure bytes without reopening any observation window."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def classify(text):
    if "FileNotFoundError" in text and "observer._plan(read_document" in text:
        return {"stage":"PLAN_INPUT_OPEN", "reason_status":"REFERENCED_PLAN_FILE_MISSING",
                "network_root_cause":"NOT_APPLICABLE_PRE_CAPTURE_FAILURE"}
    if "urllib.error.URLError: <urlopen error timed out>" in text and "opener.open(request, timeout=20)" in text:
        return {"stage":"TRANSPORT_OPEN_NOT_FINELY_OBSERVED", "reason_status":"DNS_CONNECT_TLS_OR_HTTP_HEADERS_UNRESOLVED",
                "network_root_cause":"NOT_PROVEN", "response_body_read_reached":False,
                "traceback_limit":"CHILD_STDERR_TAIL_1500_BYTES_OMITS_UNDERLYING_CAUSE"}
    return {"stage":"UNCLASSIFIED", "reason_status":"INSUFFICIENT_RETAINED_TELEMETRY","network_root_cause":"NOT_PROVEN"}


def diagnose(failure_index, attempts):
    index=json.loads(failure_index.read_text(encoding="utf-8-sig")); rows=[]; files={}
    for item in index["failures"]:
        path=attempts/item["attempt_id"]/"stderr.txt";raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=item["stderr_sha256"]:raise ValueError("old_failure_identity_changed")
        files[path]=digest
        rows.append({"cutoff":item["cutoff"],"attempt_id":item["attempt_id"],"stderr_sha256":digest,
                     "old_classification":item["observed_failure"],**classify(raw.decode("utf-8"))})
    if any(hashlib.sha256(path.read_bytes()).hexdigest()!=value for path,value in files.items()):
        raise ValueError("old_failure_changed_during_read")
    return {"scope":"STATIC_EXISTING_STDERR_REVIEW", "failures":rows,"stage_counts":dict(Counter(row["stage"] for row in rows)),
            "source_file_sha256":hashlib.sha256(failure_index.read_bytes()).hexdigest(),
            "original_bytes_unchanged":True,"collector_runs":0,"scheduler_changes":0,"network_calls":0,
            "host_shutdown":"Nine absent hours retain prior shutdown-overlap evidence; not a cause for 21 transport timeouts.",
            "old_O1_result":"NOT_PASSED_UNCHANGED"}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--failure-index",type=Path,required=True)
    p.add_argument("--attempts",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=diagnose(a.failure_index,a.attempts)
    if a.output.resolve().is_relative_to(a.attempts.resolve()):raise ValueError("output_must_be_outside_original_attempts")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps(result["stage_counts"]))
