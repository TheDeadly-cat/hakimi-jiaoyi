"""Original pipeline evidence, read in place without migration or re-signing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import stat


_REPORT_NAME = re.compile(r"strategy_research_[A-Za-z0-9][A-Za-z0-9_.-]{0,140}\.json\Z")
_FILE_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_REPORT_PAGE_SIZE = 50
_REPORT_SCOPE_LIMIT = 200
_REPORT_MAX_BYTES = 16 * 1024 * 1024


def _no_report_links(path):
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("terminal_report_reparse_path")


def _report_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("terminal_report_duplicate_json_key")
        result[key] = value
    return result


def _report_metadata(value, default=None):
    if type(value) not in (str, int, float, bool):
        return default
    if type(value) is str and len(value) > 1024:
        return default
    return value


def _report_summary(value):
    """List only a small scalar preview; the detail retains the complete JSON."""
    if value is None:
        return None, False
    if type(value) in (str, int, float, bool):
        if type(value) is str and len(value) > 256:
            return None, True
        return value, False
    if type(value) is not dict:
        return None, True
    preview, omitted = {}, False
    for key, item in value.items():
        if (len(preview) >= 12 or len(key) > 128
                or type(item) not in (str, int, float, bool, type(None))
                or (type(item) is str and len(item) > 256)):
            omitted = True
            continue
        candidate = dict(preview, **{key: item})
        if len(json.dumps(candidate, ensure_ascii=False, allow_nan=False).encode()) > 2048:
            omitted = True
            continue
        preview = candidate
    return preview, omitted


class TerminalHistoryReader:
    def __init__(self, runtime_dir):
        self.path = Path(runtime_dir).absolute() / "strategy_pipeline.sqlite3"
        self.report_dir = Path(runtime_dir).absolute() / "reports"

    @staticmethod
    def _report_bytes(path):
        _no_report_links(path)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("terminal_report_not_regular_file")
        if info.st_size > _REPORT_MAX_BYTES:
            raise ValueError("terminal_report_too_large")
        with path.open("rb") as stream:
            raw = stream.read(_REPORT_MAX_BYTES + 1)
        if len(raw) > _REPORT_MAX_BYTES:
            raise ValueError("terminal_report_too_large")
        return raw, (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

    def _report_view(self, path, *, detail=False):
        raw, before = self._report_bytes(path)
        document = json.loads(raw, object_pairs_hook=_report_object,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError("terminal_report_nonfinite_json")))
        if type(document) is not dict:
            raise ValueError("terminal_report_document_invalid")
        repeated, after = self._report_bytes(path)
        if raw != repeated or before != after:
            raise ValueError("terminal_report_changed_during_read")
        fingerprint = hashlib.sha256(raw).hexdigest()
        summary = document.get("summary")
        summary_preview, summary_omitted = _report_summary(summary)
        historical_status = document.get("status")
        if historical_status is None and type(summary) is dict:
            historical_status = summary.get("status")
        view = {"id": fingerprint, "file_name": path.name, "file_sha256": fingerprint,
                "file_size_bytes": len(raw), "historical_schema": _report_metadata(document.get("schema_version")),
                "status": _report_metadata(historical_status, "NOT_RECORDED"),
                "created_at": _report_metadata(document.get("created_at")), "summary": summary_preview,
                "summary_omitted": summary_omitted, "summary_available_in_detail": summary_omitted,
                "file_read_status": "STABLE", "original_report_validation": "NOT_RUN",
                "is_historical_file": True, "current": False, "source": "original_strategy_research_file",
                "read_only": True, "research_only": True, "replay_available": False,
                "paper_allowed": False, "live_allowed": False, "order_allowed": False,
                "new_economic_runs": 0,
                "notice": "原历史文件及原始字节身份；未选择为当前报告，未重算、重签或重新授权。"}
        if detail:
            view["payload"] = document
        return view

    def reports(self, identity=None):
        """Read fixed historical report files; never select or publish a current pointer.

        List IDs are exact file SHA256s. A changed file no longer resolves under
        its prior ID. Safe basenames address current bytes explicitly. Reserved
        page-N identities page through at most 200 files, 50 at a time; omitted
        files are counted rather than silently disappearing from the response.
        """
        offset = 0
        if identity is not None:
            if type(identity) is not str:
                raise ValueError("terminal_report_identity_invalid")
            if re.fullmatch(r"page-(?:0|[1-9][0-9]{0,5})", identity):
                offset = int(identity[5:])
                if offset >= _REPORT_SCOPE_LIMIT or offset % _REPORT_PAGE_SIZE:
                    raise ValueError("terminal_report_page_invalid")
                identity = None
            elif not (_FILE_SHA256.fullmatch(identity) or _REPORT_NAME.fullmatch(identity)):
                raise ValueError("terminal_report_identity_invalid")
        _no_report_links(self.report_dir)
        if not self.report_dir.exists():
            if identity is not None:
                raise FileNotFoundError("terminal_report_not_found")
            return {"items": [], "warnings": ["original_report_directory_not_present"], "total_count": 0,
                    "scope_limit": _REPORT_SCOPE_LIMIT, "offset": offset, "page_size": _REPORT_PAGE_SIZE,
                    "page_file_count": 0, "next_page": None, "omitted_by_scope": 0,
                    "source": "original_strategy_research_files", "read_only": True,
                    "is_historical_file": True, "current": False, "paper_allowed": False,
                    "live_allowed": False, "order_allowed": False, "new_economic_runs": 0}
        names = sorted(path.name for path in self.report_dir.iterdir() if _REPORT_NAME.fullmatch(path.name))
        scoped = names[:_REPORT_SCOPE_LIMIT]
        if identity is not None and _REPORT_NAME.fullmatch(identity):
            # A direct safe filename remains accessible even beyond the list cap.
            path = self.report_dir / identity
            if not path.exists():
                raise FileNotFoundError("terminal_report_not_found")
            return self._report_view(path, detail=True)
        warnings, items = [], []
        chosen = scoped if identity is not None else scoped[offset:offset + _REPORT_PAGE_SIZE]
        for name in chosen:
            try:
                view = self._report_view(self.report_dir / name)
            except (OSError, ValueError, TypeError, RecursionError) as error:
                warnings.append({"file_name": name, "error": str(error)[:300]})
                continue
            if identity is not None:
                if view["file_sha256"] == identity:
                    detail = self._report_view(self.report_dir / name, detail=True)
                    if detail["file_sha256"] != identity:
                        raise ValueError("terminal_report_changed_during_read")
                    return detail
            else:
                items.append(view)
        if identity is not None:
            raise FileNotFoundError("terminal_report_hash_not_found_or_changed")
        next_offset = offset + _REPORT_PAGE_SIZE
        return {"items": items, "warnings": warnings, "total_count": len(names), "scope_limit": _REPORT_SCOPE_LIMIT,
                "offset": offset, "page_size": _REPORT_PAGE_SIZE, "page_file_count": len(chosen),
                "next_page": "page-" + str(next_offset) if next_offset < len(scoped) else None,
                "omitted_by_scope": max(0, len(names) - _REPORT_SCOPE_LIMIT),
                "source": "original_strategy_research_files", "read_only": True, "is_historical_file": True,
                "current": False, "paper_allowed": False, "live_allowed": False, "order_allowed": False,
                "new_economic_runs": 0}

    def _stable_identity(self):
        for path in (self.path, *self.path.parents):
            if not path.exists():
                continue
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("terminal_history_reparse_path")
        for suffix in ("-wal", "-journal"):
            sidecar = Path(str(self.path) + suffix)
            if sidecar.exists() and sidecar.stat().st_size:
                raise ValueError("terminal_history_database_busy")
        info = self.path.stat()
        if info.st_size > 128 * 1024 * 1024:
            raise ValueError("terminal_history_database_too_large")
        return (info.st_size, info.st_mtime_ns, hashlib.sha256(self.path.read_bytes()).hexdigest())

    @staticmethod
    def _document(raw):
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("terminal_history_document_invalid")
        return value

    def _view(self, connection, row, *, detail):
        run = self._document(row["payload_json"])
        if run.get("run_id") != row["run_id"] or run.get("strategy_id") != row["strategy_id"] or run.get("symbol") != row["symbol"]:
            raise ValueError("terminal_history_run_identity_mismatch")
        version_id = str(run.get("strategy_version_id") or "")
        version = connection.execute(
            "SELECT version_id, strategy_id, fingerprint, spec_json FROM strategy_versions WHERE version_id=?", (version_id,)
        ).fetchone() if version_id else None
        artifact = connection.execute(
            "SELECT artifact_id, run_id, report_hash, payload_json FROM backtest_artifacts WHERE run_id=?", (row["run_id"],)
        ).fetchone()
        issues = []
        version_view = None
        if version:
            spec = self._document(version["spec_json"])
            version_ok = (hashlib.sha256(version["spec_json"].encode()).hexdigest() == version["fingerprint"]
                          and version["strategy_id"] == row["strategy_id"] and spec.get("strategy_id") == row["strategy_id"])
            if not version_ok:
                issues.append("original_version_hash_or_identity_mismatch")
            version_view = {"id": version["version_id"], "fingerprint": version["fingerprint"], "spec": spec,
                            "integrity_status": "PASS" if version_ok else "BLOCK"}
        else:
            issues.append("original_version_not_available")
        artifact_view = None
        if artifact:
            payload = self._document(artifact["payload_json"])
            valid = hashlib.sha256(artifact["payload_json"].encode()).hexdigest() == artifact["report_hash"]
            if not valid:
                issues.append("original_report_hash_mismatch")
            artifact_view = {"id": artifact["artifact_id"], "run_id": artifact["run_id"],
                             "report_hash": artifact["report_hash"], "payload": payload,
                             "integrity_status": "PASS" if valid else "BLOCK"}
        view = {"id": row["run_id"], "run_id": row["run_id"], "title": row["strategy_id"],
                "strategy_id": row["strategy_id"], "symbol": row["symbol"], "status": row["status"],
                "updated_at": row["updated_at"], "engine_id": "terminal.original_pipeline",
                "strategy_version_id": version_id, "has_report": artifact is not None,
                "report_hash": artifact["report_hash"] if artifact else None,
                "integrity_status": "BLOCK" if issues else "PASS", "warnings": issues,
                "read_only": True, "replay_available": False,
                "replay_reason": "旧记录没有在此接口封存可核对的完整行情，不能用当前行情替换历史输入。",
                "paper_allowed": False, "live_allowed": False}
        if detail:
            view.update(run=run, version=version_view, artifact=artifact_view)
        return view

    def __call__(self, identity=None):
        if identity is not None and (not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identity)):
            raise ValueError("terminal_history_identity_invalid")
        if not self.path.exists():
            if identity is not None:
                raise FileNotFoundError("terminal_history_not_found")
            return {"items": [], "warnings": ["original_pipeline_database_not_present"]}
        before = self._stable_identity()
        connection = sqlite3.connect(self.path.as_uri() + "?mode=ro&immutable=1", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA query_only=ON")
            columns = "run_id,strategy_id,symbol,status,updated_at,payload_json"
            rows = connection.execute("SELECT " + columns + " FROM strategy_runs WHERE run_id=?", (identity,)).fetchall() if identity else connection.execute(
                "SELECT " + columns + " FROM strategy_runs ORDER BY updated_at DESC LIMIT 500").fetchall()
            items, warnings = [], []
            for row in rows:
                try:
                    items.append(self._view(connection, row, detail=identity is not None))
                except (ValueError, TypeError, KeyError) as error:
                    if identity is not None:
                        raise
                    warnings.append({"id": row["run_id"], "error": str(error)})
        finally:
            connection.close()
        if self._stable_identity() != before:
            raise ValueError("terminal_history_changed_during_read")
        if identity is not None:
            if not items:
                raise FileNotFoundError("terminal_history_not_found")
            return items[0]
        return {"items": items, "warnings": warnings, "source": "original_strategy_pipeline",
                "read_only": True, "paper_allowed": False, "live_allowed": False}
