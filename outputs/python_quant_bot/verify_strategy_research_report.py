from __future__ import annotations

import argparse
import json
from pathlib import Path

from exchange_terminal.services.strategy_research_evidence import verify_strategy_research_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a nested strategy research report and its governance receipts.")
    parser.add_argument("report")
    parser.add_argument("--allow-development", action="store_true")
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "status": "BLOCK",
            "blockers": [f"research_report_unavailable:{type(exc).__name__}"],
            "report": str(report_path),
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False, indent=2))
        return 2
    verification = verify_strategy_research_report(
        payload,
        require_formal=not args.allow_development,
    )
    print(json.dumps({
        **verification,
        "report": str(report_path),
    }, ensure_ascii=False, indent=2))
    return 0 if verification.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
