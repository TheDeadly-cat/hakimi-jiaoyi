"""Extract a private trade table from hash-bound existing reports; no reruns."""
from __future__ import annotations
import argparse
from datetime import datetime
from decimal import Decimal as D
import csv
import hashlib
import json
from pathlib import Path
from hakimi_research.equity_research import verify_equity_report
from hakimi_research.equity_dataset import verify_equity_snapshot
from equity_event_diagnostics import _position_at_release


def read(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stamp(value):return datetime.fromisoformat(value.replace("Z","+00:00"))
def number(value):return D(str(value))


def extract_report(report, snapshot, expected_event):
    report=verify_equity_report(report);snapshot=verify_equity_snapshot(snapshot);result=report["result"]
    if snapshot["snapshot_id"]!=report["dataset"]["snapshot_id"]:
        raise ValueError("attribution_snapshot_report_identity_mismatch")
    orders={row["order_id"]:(i,row) for i,row in enumerate(result["orders"])}
    sessions={stamp(row["open_utc"]):row for row in snapshot["sessions"]}
    candles={stamp(row[0]):(i,row) for i,row in enumerate(snapshot["candles"])}
    initial=number(report["spec"]["initial_cash"]);cash=initial;active=None;rows=[]
    exposure=_position_at_release(report,expected_event)
    for fi,fill in enumerate(result["fills"]):
        oi,order=orders[fill["order_id"]]
        qty,price,fee,ref=(number(fill["quantity"]),number(fill["price"]),number(fill["fee"]),number(order["reference_price"]))
        if fill["partial_fill"] or qty<=0:raise ValueError("attribution_v1_requires_full_simple_positions")
        if fill["action"]=="BUY":
            if active is not None:raise ValueError("attribution_v1_requires_one_position")
            signal_indices=[i for i,row in enumerate(result["signals"]) if stamp(row["time"])==stamp(fill["signal_time"])]
            if len(signal_indices)!=1:raise ValueError("attribution_entry_signal_not_unique")
            signal=result["signals"][signal_indices[0]]
            active={"q":qty,"price":price,"ref":ref,"fee":fee,"fill":fill,"fi":fi,"oi":oi,"signal":signal,
                    "signal_index":signal_indices[0],"cash_before":cash}
            cash-=qty*price+fee
        else:
            if active is None or fill["action"]!="SELL" or active["q"]!=qty:
                raise ValueError("attribution_v1_requires_matched_full_exit")
            row=_row(report,snapshot,active,fi,oi,fill,ref,fee,exposure,sessions,candles)
            cash+=qty*price-fee;rows.append(row);active=None
    if active:
        rows.append(_row(report,snapshot,active,None,None,None,number(result["end_mark_price"]),D(0),exposure,sessions,candles))
    net=sum(number(row["net_pnl"]) for row in rows)
    if abs(net-(number(result["final_equity"])-initial))>D("1e-8"):
        raise ValueError("attribution_accounting_does_not_reconcile")
    if abs(cash-number(result["final_cash"]))>D("1e-8"):
        raise ValueError("attribution_cash_does_not_reconcile")
    release=stamp(expected_event["actual_release_at"])
    for row in rows:
        row["this_trade_held_at_release"]=(stamp(row["entry_fill_open_label"]) <= release
            and (row["exit_fill_open_label"] is None or release < stamp(row["exit_fill_open_label"]))) if exposure["status"]=="MODELLED_OUTSIDE_RTH_RELEASE" else None
    return rows


def _row(report,snapshot,entry,fi,oi,exit_fill,exit_ref,exit_fee,exposure,sessions,candles):
    q=entry["q"];entry_at=stamp(entry["fill"]["fill_time"]);initial=number(report["spec"]["initial_cash"])
    exit_price=number(exit_fill["price"]) if exit_fill else exit_ref
    reference_pnl=q*(exit_ref-entry["ref"])
    entry_slip=q*(entry["price"]-entry["ref"]);exit_slip=q*(exit_ref-exit_price)
    fees=entry["fee"]+exit_fee;net=reference_pnl-entry_slip-exit_slip-fees
    both=None;exit_candle=None
    if exit_fill:
        exit_at=stamp(exit_fill["fill_time"]);session=sessions[exit_at];ci,candle=candles[exit_at]
        high,low=number(candle[2]),number(candle[3])
        stop=entry["price"]*(1-number(entry["signal"]["effective_stop_loss_pct"]))
        take=entry["signal"].get("requested_take_profit_pct")
        both=low<=stop and take is not None and high>=entry["price"]*(1+number(take))
        lower=(exit_at-entry_at).total_seconds()/3600
        upper=(stamp(session["close_utc"])-entry_at).total_seconds()/3600 if exit_fill["fill_basis"].startswith("INTRABAR") else lower
        exit_candle=f'/candles/{ci}'
    else:
        lower=(stamp(report["result"]["scoring"]["end_time"])-entry_at).total_seconds()/3600;upper=None
    return {"report_hash":report["report_hash"],"snapshot_id":snapshot["snapshot_id"],
        "status":"CLOSED" if exit_fill else "OPEN_MARKED", "entry_signal_time":entry["fill"]["signal_time"],
        "model_signal_available_at":entry["signal"]["time"],"actual_wall_clock_signal_generation":"NOT_RECORDED",
        "entry_fill_open_label":entry["fill"]["fill_time"],"exit_fill_open_label":exit_fill["fill_time"] if exit_fill else None,
        "exit_reason":exit_fill["reason"] if exit_fill else "END_MARK_ONLY", "exit_basis":exit_fill["fill_basis"] if exit_fill else "END_MARK_ONLY",
        "opening_gap_exit":bool(exit_fill and exit_fill["fill_basis"]=="GAP_OPEN"),"intrabar_dual_touch":both,
        "quantity":str(q),"entry_reference_price":str(entry["ref"]),"entry_fill_price":str(entry["price"]),
        "exit_reference_price":str(exit_ref),"exit_fill_price":str(exit_price) if exit_fill else None,
        "reference_price_pnl":str(reference_pnl),"entry_slippage":str(entry_slip),"exit_slippage":str(exit_slip),"fees":str(fees),"net_pnl":str(net),
        "initial_cash":str(initial),"pre_entry_cash":str(entry["cash_before"]),
        "reference_entry_allocation":str(q*entry["ref"]/entry["cash_before"]),
        "filled_notional_allocation":str(q*entry["price"]/entry["cash_before"]),
        "entry_cash_outflow_fraction":str((q*entry["price"]+entry["fee"])/entry["cash_before"]),
        "holding_hours_lower":lower,"holding_hours_upper":upper,
        "release_position_status":exposure["status"],"report_position_held_at_release":exposure.get("position_held"),
        "report_close_mark_exposure_ratio":report["result"]["exposure_ratio"],
        "entry_signal_pointer":f'/result/signals/{entry["signal_index"]}',"entry_fill_pointer":f'/result/fills/{entry["fi"]}',
        "entry_order_pointer":f'/result/orders/{entry["oi"]}',"exit_fill_pointer":f'/result/fills/{fi}' if exit_fill else None,
        "exit_order_pointer":f'/result/orders/{oi}' if exit_fill else None,"exit_candle_pointer":exit_candle,
        "not_a_zero_cost_counterfactual":True}


def extract(study_path,root,output):
    if output.resolve().is_relative_to(root.resolve()):raise ValueError("attribution_output_must_not_be_inside_originals")
    study=read(study_path);files={str(study_path.resolve()):sha(study_path)};rows=[];reports=[]
    paths={}
    for phase in ("actual-study-first","actual-study-final"):
        for path in (root/phase).rglob("equity_research_*.json"):
            key=path.stem.removeprefix("equity_research_" )
            if key in paths:raise ValueError("attribution_duplicate_report_identity")
            paths[key]=path
    for event in study["events"]:
        for cell in event.get("cells",[]):
            for variant,wanted in cell["report_hashes"].items():
                path=paths[wanted];files[str(path.resolve())]=sha(path);report=read(path)
                if report["report_hash"]!=wanted:raise ValueError("attribution_report_identity_mismatch")
                snapshot_path=path.parents[2]/"snapshot"/('equity_dataset_'+report["dataset"]["snapshot_id"]+'.json')
                files[str(snapshot_path.resolve())]=sha(snapshot_path);snapshot=read(snapshot_path)
                identity=f'{event["fiscal_quarter"]}/cost-{cell["cost_multiplier"]}/{variant}'
                expected=event["retrospective_release_clock"]
                trade_rows=extract_report(report,snapshot,expected)
                for row in trade_rows:row.update(identity=identity,report_file=str(path.resolve()),actual_release_at=expected["actual_release_at"])
                rows.extend(trade_rows)
                reports.append({"identity":identity,"report_hash":wanted,"trade_rows":len(trade_rows),
                    "net_pnl":str(sum(number(row["net_pnl"]) for row in trade_rows)),"position_at_release":_position_at_release(report,expected)})
    if len(reports)!=42 or len({row["report_hash"] for row in reports})!=42:raise ValueError("attribution_expected_42_distinct_reports")
    if any(sha(path)!=value for path,value in files.items()):raise ValueError("attribution_original_changed")
    output.mkdir(parents=True,exist_ok=False)
    with (output/"trades.private.csv").open("x",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result={"schema_version":"retained-equity-trade-attribution-v1","reports":reports,"rows":len(rows),
        "source_files_sha256":files,"original_bytes_unchanged":True,"new_backtests":0,"new_provider_requests":0,
        "scope":"RETAINED_PATH_LEDGER_ATTRIBUTION_ONLY_NOT_ZERO_COST_OR_CAUSAL"}
    (output/"index.private.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"reports":len(reports),"rows":len(rows),"new_backtests":0,"original_bytes_unchanged":True}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--study",type=Path,required=True);p.add_argument("--private-root",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();extract(a.study,a.private_root,a.output)
