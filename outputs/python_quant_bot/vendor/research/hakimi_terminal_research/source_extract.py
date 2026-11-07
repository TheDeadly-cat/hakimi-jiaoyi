"""Build an offline human-review packet from retained official AMD HTML.

Extraction creates UNCERTAIN candidates, never human approvals or trade signals.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.ignored = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}: self.ignored += 1
        if tag in {"p", "div", "li", "tr", "h1", "h2"}: self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"}: self.ignored -= 1
        if tag in {"p", "div", "li", "tr"}: self.parts.append("\n")
    def handle_data(self, data):
        if not self.ignored: self.parts.append(data)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def extract(raw, quarter):
    parser = PlainText(); parser.feed(raw)
    text = "\n".join(" ".join(line.split()) for line in "".join(parser.parts).splitlines() if line.strip())
    lead = re.search(r"today announced revenue for the ([a-z]+) quarter of (20\d\d) of \$(\d+(?:\.\d+)?) billion,(.*?)(?:\n|$)", text)
    outlook = re.search(r"For the ([a-z]+) quarter of (20\d\d), AMD expects revenue to be approximately \$(\d+(?:\.\d+)?) billion, plus or minus \$(\d+(?:\.\d+)?) million", text)
    clock = re.search(r'<time datetime="([0-9T:-]+)" class="date">\s*([^<]+)</time>', raw)
    if not lead or not outlook or not clock:
        raise ValueError("announcement_expected_fields_missing:" + quarter)
    qnum = {"first":1,"second":2,"third":3,"fourth":4}
    if lead[2] + "Q" + str(qnum[lead[1]]) != quarter:
        raise ValueError("announcement_fiscal_period_mismatch")
    nxt = (int(quarter[:4]) + (quarter[-1] == "4"), int(quarter[-1]) % 4 + 1)
    if (int(outlook[2]), qnum[outlook[1]]) != nxt:
        raise ValueError("announcement_guidance_not_next_quarter")
    before_non_gaap, _, non_gaap = lead[4].partition("On a non-GAAP")
    eps = re.search(r"diluted (earnings|loss) per share of \$(\d+(?:\.\d+)?)", before_non_gaap)
    adjusted_eps = re.search(r"diluted earnings per share (?:was|of) \$(\d+(?:\.\d+)?)", non_gaap)
    if not eps or not adjusted_eps:
        raise ValueError("announcement_eps_basis_not_identified")
    local = datetime.fromisoformat(clock[1]).replace(tzinfo=ZoneInfo("America/New_York"))
    if local.tzname() not in clock[2]:
        raise ValueError("announcement_clock_timezone_label_mismatch")
    def fact(name, value, unit, scale, period, basis, quote, precision="SOURCE_DECIMAL"):
        at = text.index(quote)
        return {"name":name, "status":"UNCERTAIN", "value":str(value), "currency":"USD", "unit":unit,
            "scale":str(scale), "fiscal_period":period, "basis":basis, "precision":precision,
            "evidence":{"plain_text_start":at,"plain_text_end":at+len(quote),"quote":quote},
            "reason":"PENDING_HUMAN_SEMANTIC_REVIEW"}
    actual = fact("actual_revenue",lead[3],"CURRENCY",1000000000,quarter,"GAAP",f'of ${lead[3]} billion',"SOURCE_ROUNDED_HEADLINE_BILLION")
    facts = [actual,
        fact("diluted_eps",-Decimal(eps[2]) if eps[1] == "loss" else Decimal(eps[2]),"CURRENCY_PER_SHARE",1,quarter,"GAAP",f'{eps[1]} per share of ${eps[2]}'),
        fact("non_gaap_diluted_eps",adjusted_eps[1],"CURRENCY_PER_SHARE",1,quarter,"NON_GAAP",adjusted_eps[0]),
        fact("next_revenue_guidance_midpoint",outlook[3],"CURRENCY",1000000000,f'{nxt[0]}Q{nxt[1]}',"REVENUE_OUTLOOK",f'approximately ${outlook[3]} billion'),
        fact("next_revenue_guidance_half_range",outlook[4],"CURRENCY",1000000,f'{nxt[0]}Q{nxt[1]}',"REVENUE_OUTLOOK",f'plus or minus ${outlook[4]} million')]
    return {"fiscal_quarter":quarter,"first_public_at":local.astimezone(timezone.utc).isoformat().replace("+00:00","Z"),
        "publication_precision":"MINUTE_FROM_CURRENT_PUBLISHER_HTML", "plain_text_sha256":hashlib.sha256(text.encode()).hexdigest(),
        "facts":facts, "consensus":{"status":"MISSING","value":None,"reason":"NO_HISTORICAL_PRE_RELEASE_CONSENSUS_SOURCE"},
        "prior_guidance":{"status":"MISSING","reason":"NOT_YET_CROSS_REFERENCED"},
        "revision_status":"CURRENT_HTML_NOT_PROVEN_UNCHANGED_SINCE_PUBLICATION", "human_review":{"status":"PENDING","reviewer":None,"reviewed_at":None}}, text


def prepare(source_root, output):
    index_path = source_root / "source-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    rows, text_files = [], {}
    for source in index["receipts"]:
        if source["status"] != 200:
            rows.append({"fiscal_quarter":source["fiscal_quarter"],"status":"SOURCE_UNAVAILABLE"}); continue
        path = source_root / source["file"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("announcement_source_identity_changed")
        candidate, plain = extract(raw.decode("utf-8"), source["fiscal_quarter"])
        candidate.update(source_url=source["url"],raw_sha256=source["sha256"],retrieved_at=source["retrieved_at"],
            extraction_completed_at=datetime.now(timezone.utc).isoformat(),event_id="AMD:"+source["fiscal_quarter"]+":EARNINGS",
            security_id="US:COMMON:CUSIP:007903107",version=1,prior_version_hash=None)
        rows.append(candidate); text_files[path.stem + ".txt"] = plain
    for previous, current in zip(rows, rows[1:]):
        if "facts" not in previous or "facts" not in current: continue
        prev = next(f for f in previous["facts"] if f["name"] == "next_revenue_guidance_midpoint")
        if prev["fiscal_period"] == current["fiscal_quarter"]:
            current["prior_guidance"] = {"status":"UNCERTAIN", "midpoint":prev["value"], "scale":prev["scale"],
                "currency":"USD", "source_url":previous["source_url"],"raw_sha256":previous["raw_sha256"],
                "public_at":previous["first_public_at"],"fiscal_period":current["fiscal_quarter"],
                "reason":"PREVIOUS_QUARTER_RELEASE_ONLY; NOT_PROOF_OF_LATEST_PRE_RELEASE_GUIDANCE"}
    for row in rows:
        if row["fiscal_quarter"] == "2022Q3":
            row["prior_guidance"]["reason"] += "; KNOWN_2022_10_06_PRELIMINARY_RELEASE_REQUIRES_REVIEW"
        row["candidate_hash"] = digest(row)
    packet = {"schema_version":"announcement-human-review-candidates-v1", "sources_index_sha256":hashlib.sha256(index_path.read_bytes()).hexdigest(),
        "purpose":"ALREADY_SEEN_DEVELOPMENT_DIAGNOSIS_NOT_CONFIRMATION", "order_allowed":False,
        "human_approved_rows":0, "candidate_count":len(rows),"events":rows}
    packet["packet_hash"] = digest(packet)
    output.mkdir(parents=True,exist_ok=False)
    (output/"candidates.json").write_text(json.dumps(packet,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    # Full normalized originals remain private beside original source bytes.
    for name, text in text_files.items(): (output/name).write_text(text,encoding="utf-8")
    lines=["# AMD 公告字段人工核准表", "", "以下为待核准候选，当前批准数为 0。营收采用公告首段四舍五入的十亿美元数值；不是财务表中精确百万美元数值。EPS 单位为美元/股，括号损失转为负号。新指引为下一财季公司营收指引，不是分析师预期。", "", "| 财季／原文 | 当季营收（十亿美元） | GAAP EPS | 非 GAAP EPS | 下一财季营收中点 ± 范围（十亿美元） | 公布时间 UTC |", "|---|---:|---:|---:|---:|---|"]
    for row in rows:
        if "facts" not in row:
            lines.append(f'| {row["fiscal_quarter"]} | 原文缺失 | — | — | — | — |');continue
        facts={f["name"]:f for f in row["facts"]}
        lines.append(f'| [{row["fiscal_quarter"]}]({row["source_url"]}) | {facts["actual_revenue"]["value"]} | {facts["diluted_eps"]["value"]} | {facts["non_gaap_diluted_eps"]["value"]} | {facts["next_revenue_guidance_midpoint"]["value"]} ± {Decimal(facts["next_revenue_guidance_half_range"]["value"])/1000} | {row["first_public_at"]} |')
    lines += ["", "核对范围：数字、单位、财季、GAAP/非GAAP和公布时间。每个字段在 candidates.json 中有来源摘要、规范文本偏移与短引用，可回查同目录私有文本和官方原文。", "", "此前公司指引只追溯本批次前一季原文，尚不代表完整修订历史；2022Q1 缺本批次之前的原文，2022Q3 另有已知 10 月 6 日初步业绩需单独核对。不把这些缺口填成零或超预期。", "", "2026 年取回的当前页面不能证明 2022—2024 年原文从未修订。人工核准是本次语义核对，不伪装成历史实时接收。C/D 仅保留开发诊断身份，未运行新经济研究。", "", "packet_hash: `"+packet["packet_hash"]+"`"]
    (output/"REVIEW.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return packet


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--source-root",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(); result=prepare(a.source_root,a.output)
    print(json.dumps({"candidate_count":result["candidate_count"],"approved":0,"packet_hash":result["packet_hash"]}))
