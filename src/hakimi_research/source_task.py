"""Run one manifest-bounded, offline disclosure task; never execute a strategy.

Local source bytes are copied into an immutable task directory. Source adapters,
the existing decimal comparison, and optional existing equity snapshots are used;
the fixed AMD packet, approvals and reports are not rewritten.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
from hakimi_research.documents import read_document
from hakimi_research.equity_cli import _deny_network
from hakimi_research.reporting import _save_encoded_report
from .content_protocol import digest, utc
from .source_pairs import interval_comparison

PERMISSIONS=dict(network_allowed=False,account_allowed=False,order_allowed=False,
                economic_execution_allowed=False,monitor_deployment_allowed=False)
STATUSES={'ABOVE','BELOW','UNCERTAIN_PRECISION','NOT_COMPARABLE'}


def require(condition,reason):
    if not condition:raise ValueError('source_task:'+reason)


def shape(value,keys,label):
    require(type(value) is dict and set(value)==set(keys.split()),label+'_shape')


def identifier(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',value),'identifier')
    return value


def sha(raw):return hashlib.sha256(raw).hexdigest()


def stamp():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def code_identity():
    names=('source_task.py','source_adapters.py','source_pairs.py','content_protocol.py','source_audit.py','source_extract.py')
    return {name:sha((ROOT/name).read_bytes()) for name in names}


def read_bounded(path,limit):
    require(path.is_file() and not path.is_symlink(),'regular_local_file_required')
    with path.open('rb') as file:raw=file.read(limit+1)
    require(0<len(raw)<=limit,'source_size_budget_exceeded')
    return raw


def local(base,name):
    require(type(name) is str and name and '://' not in name,'local_path_required')
    path=Path(name)
    return (path if path.is_absolute() else base/path).resolve()


def validate_manifest(manifest):
    shape(manifest,'schema_version task_id evidence_kind security selection source_scope budget timing events sources output_dir previous_packet market_snapshot','manifest')
    require(manifest['schema_version']=='equity-source-task-v1','manifest_schema')
    require(manifest['evidence_kind'] in ('SYNTHETIC_FIXTURE','CURRENT_OFFICIAL_HTML'),'evidence_kind_required')
    identifier(manifest['task_id'])
    shape(manifest['security'],'security_id symbol name currency adapter','security')
    for key in ('security_id','symbol','adapter'):identifier(manifest['security'][key])
    require(manifest['security']['currency']=='USD','unsupported_currency')
    require(type(manifest['security']['name']) is str and manifest['security']['name'].strip(),'issuer_name_required')
    shape(manifest['selection'],'purpose basis selected_before_price_review minimum_opportunities price_rule economic_scope','selection')
    selection=manifest['selection']
    require(selection['purpose']=='SOURCE_WORKFLOW_ENGINEERING' and selection['selected_before_price_review'] is True,'source_task_purpose_required')
    require(type(selection['basis']) is str and bool(selection['basis'].strip()),'selection_basis_required')
    require(type(selection['minimum_opportunities']) is int and selection['minimum_opportunities']>=2,'predeclared_stop_threshold_required')
    require(selection['price_rule']=='FIXED_C_PRICE_CONFIRMATION_V1' and selection['economic_scope']=='NOT_REQUESTED_COSTS_AND_RETURNS_NOT_COMPUTED','explicit_price_and_cost_scope_required')
    shape(manifest['source_scope'],'description included_types uncovered_channels','source_scope')
    scope=manifest['source_scope']
    require(all(type(scope[k]) is list and scope[k] and all(type(x) is str and x.strip() for x in scope[k]) for k in ('included_types','uncovered_channels')),'bounded_source_scope_required')
    shape(manifest['budget'],'max_events max_sources max_source_bytes max_total_bytes max_network_requests max_economic_runs','budget')
    b=manifest['budget']
    require(all(type(v) is int and v>=0 for v in b.values()),'integer_budgets_required')
    require(1<=b['max_events']<=100 and 1<=b['max_sources']<=300 and 1<=b['max_source_bytes']<=8*1024*1024 and b['max_source_bytes']<=b['max_total_bytes']<=64*1024*1024,'local_budget_limits')
    require(b['max_network_requests']==b['max_economic_runs']==0,'offline_zero_execution_budget_required')
    shape(manifest['timing'],'mode collection_delay_seconds processing_delay_seconds','timing')
    require(manifest['timing']['mode']=='HISTORICAL_RECONSTRUCTION','historical_scope_required')
    require(all(type(manifest['timing'][k]) is int and 0<manifest['timing'][k]<=86400 for k in ('collection_delay_seconds','processing_delay_seconds')),'explicit_timing_assumptions_required')
    require(type(manifest['events']) is list and 1<=len(manifest['events'])<=b['max_events'],'event_budget_exceeded')
    require(type(manifest['sources']) is list and len(manifest['sources'])<=b['max_sources'],'source_budget_exceeded')
    ids=[]
    for source in manifest['sources']:
        shape(source,'source_id path sha256 url retrieved_at legal_use declaration_version prior_source_id coverage','source')
        ids.append(identifier(source['source_id']))
        require(type(source['sha256']) is str and re.fullmatch('[0-9a-f]{64}',source['sha256']),'source_sha256_required')
        uses=('SYNTHETIC_TEST',) if manifest['evidence_kind']=='SYNTHETIC_FIXTURE' else ('PUBLIC_OFFICIAL_RESEARCH','USER_ATTESTED_LOCAL_RESEARCH')
        require(source['legal_use'] in uses,'legal_use_declaration_required')
        utc(source['retrieved_at'])
        require(type(source['declaration_version']) is int and source['declaration_version']>=1,'source_version_required')
        require((source['declaration_version']==1 and source['prior_source_id'] is None) or (source['declaration_version']>1 and type(source['prior_source_id']) is str),'source_prior_version_required')
        require(source['coverage'] is None or type(source['coverage']) is str and source['coverage'].strip(),'source_coverage')
    require(len(set(ids))==len(ids),'duplicate_source_id')
    source_map={s['source_id']:s for s in manifest['sources']}
    for source in manifest['sources']:
        if source['prior_source_id'] is not None:
            parent=source_map.get(source['prior_source_id'])
            require(parent is not None and parent['declaration_version']+1==source['declaration_version'],'source_lineage_missing')
    events=[]
    for event in manifest['events']:
        shape(event,'event_id event_kind fiscal_quarter window_start window_end actual_source_id prior_source_ids known_material_source_ids','event')
        events.append(identifier(event['event_id']))
        require(event['event_kind']=='EARNINGS','unsupported_event_kind')
        require(type(event['fiscal_quarter']) is str and re.fullmatch(r'20\d\dQ[1-4]',event['fiscal_quarter']),'fiscal_quarter_required')
        require(utc(event['window_start'])<utc(event['window_end']),'disclosure_window_order')
        identifier(event['actual_source_id'])
        for key in ('prior_source_ids','known_material_source_ids'):
            require(type(event[key]) is list and len(set(event[key]))==len(event[key]),'known_versions_list_required')
            for value in event[key]:identifier(value)
    require(len(set(events))==len(events),'duplicate_event_id')
    require(type(manifest['output_dir']) is str and manifest['output_dir'],'output_directory_required')
    return manifest


def publication_before(left,right):
    """Prove order without treating a missing time as the start of its day.

    Exact clocks take precedence over source-local calendar labels. Coarse
    dates retain the issuer's calendar-date ordering; for mixed precision also
    require UTC dates to agree with that order, avoiding offset-boundary guesses.
    This source-selection rule does not establish an intraday availability time.
    """
    if left['public_at'] and right['public_at']:
        return utc(left['public_at'])<utc(right['public_at'])
    left_day=utc(left['public_at']).date().isoformat() if left['public_at'] else left['publication_date']
    right_day=utc(right['public_at']).date().isoformat() if right['public_at'] else right['publication_date']
    return left['publication_date']<right['publication_date'] and left_day<right_day


def compare_event(event,sources,security):
    """Every selected/known disclosure must be present before a comparison."""
    from .source_adapters import extract, audit_fact
    row=dict(event,comparison=None,status='NOT_EVALUATED',actual=None,prior_disclosures=[],latest_prior=None,
             source_audit='NOT_RUN',prior_order='NOT_EVALUATED',human_review='NOT_APPROVED',research_admitted=False,
             model_available_at=None,new_content_intervention=None,issues=[])
    wanted=[event['actual_source_id']]+event['prior_source_ids']
    if not set(event['known_material_source_ids'])<=set(wanted):
        row.update(status='MISSING_KNOWN_DISCLOSURE',issues=['KNOWN_MATERIAL_SOURCE_NOT_SELECTED']);return row
    missing=[id for id in set(wanted)|set(event['known_material_source_ids']) if id not in sources or sources[id]['status']!='IMPORTED']
    if missing:
        row.update(status='MISSING_SOURCE',issues=['SOURCE_UNAVAILABLE:'+id for id in sorted(missing)]);return row
    if not event['prior_source_ids']:
        row.update(status='MISSING_PRIOR',issues=['PRIOR_DISCLOSURE_REQUIRED']);return row
    facts=[]
    try:
        for id in wanted:
            source=sources[id]
            kind='ACTUAL' if id==event['actual_source_id'] else 'PRIOR'
            fact=extract(security,source,event['fiscal_quarter'],kind)
            audit_fact(security,source,event['fiscal_quarter'],kind,fact)
            require(fact['publication_date']>=event['window_start'][:10] and fact['publication_date']<=event['window_end'][:10],'source_outside_disclosure_window')
            if fact['public_at']:
                require(utc(event['window_start'])<=utc(fact['public_at'])<=utc(event['window_end']),'source_clock_outside_disclosure_window')
                require(utc(fact['public_at'])<=utc(source['retrieved_at']),'retrieval_before_publication')
            else:
                require(fact['publication_date']<=source['retrieved_at'][:10],'retrieval_before_publication')
            facts.append(fact)
        actual=facts[0]
        # Source-id ordering is for stable presentation only, never chronology.
        priors=sorted(facts[1:],key=lambda f:f['evidence']['source_id'])
        row.update(actual=actual,prior_disclosures=priors,source_audit='PASS')
        if not actual['public_at']:row['issues'].append('PUBLICATION_TIME_UNKNOWN_DATE_ONLY')
        row['issues']+=['CURRENT_HTML_HISTORICAL_IMMUTABILITY_NOT_PROVEN','COVERAGE_IS_DECLARED_REQUIRES_SEMANTIC_REVIEW']
        by_source={field['evidence']['source_id']:field for field in facts}
        for id in wanted:
            parent_id=sources[id]['prior_source_id']
            if parent_id is None:continue
            require(parent_id in by_source,'revision_parent_not_selected')
            parent,child=by_source[parent_id],by_source[id]
            require(parent['kind']==child['kind'],'revision_amount_kind_changed')
            require(publication_before(parent,child),'revision_not_after_parent')
        require(all(publication_before(p,actual) for p in priors),'prior_not_before_actual')
        latest_candidates=[p for p in priors if all(other is p or publication_before(other,p) for other in priors)]
        if len(latest_candidates)!=1:
            row.update(status='AMBIGUOUS_PRIOR_ORDER',prior_order='AMBIGUOUS')
            row['issues'].append('LATEST_PRIOR_NOT_UNIQUELY_DETERMINED');return row
        latest=latest_candidates[0]
        row.update(latest_prior=latest,prior_order='UNIQUE_LATEST')
        if actual['coverage'] is None or latest['coverage'] is None:
            row.update(status='UNKNOWN_COVERAGE',issues=['COVERAGE_NOT_DECLARED'],actual=actual,prior_disclosures=priors,latest_prior=latest,source_audit='PASS');return row
        comparison=interval_comparison(actual,latest)
        row.update(status=comparison['status'],comparison=comparison,actual=actual,prior_disclosures=priors,latest_prior=latest,source_audit='PASS')
        return row
    except ValueError as exc:
        row.update(status='SOURCE_REJECTED',issues=[str(exc)]);return row


def prepare(manifest_path):
    manifest_raw=read_bounded(manifest_path,1024*1024)
    manifest=validate_manifest(read_document(manifest_path));base=manifest_path.resolve().parent
    output=local(base,manifest['output_dir'])
    sources={};total=0;input_paths={};blobs={}
    for declared in manifest['sources']:
        id=declared['source_id'];source={k:v for k,v in declared.items() if k!='path'}
        path=local(base,declared['path']);input_paths[id]=path
        require(not path.is_relative_to(output),'input_inside_output_not_allowed')
        try:
            raw=read_bounded(path,manifest['budget']['max_source_bytes'])
            total+=len(raw);require(total<=manifest['budget']['max_total_bytes'],'total_byte_budget_exceeded')
            require(sha(raw)==declared['sha256'],'source_bytes_changed:'+id)
            raw.decode('utf-8')
            source.update(status='IMPORTED',raw=raw,retained_path='originals/'+declared['sha256']+'.html')
            blobs[source['retained_path']]=raw
        except (OSError,UnicodeDecodeError,ValueError) as exc:
            source.update(status='IMPORT_STOPPED',error=str(exc))
        sources[id]=source
        if total>manifest['budget']['max_total_bytes']:break
    for declared in manifest['sources']:
        if declared['source_id'] not in sources:
            sources[declared['source_id']]={**{k:v for k,v in declared.items() if k!='path'},'status':'BUDGET_NOT_READ','error':'TOTAL_BYTE_BUDGET_EXHAUSTED'}
    extracted_at=stamp()
    require(all(utc(s['retrieved_at'])<=utc(extracted_at) for s in sources.values()),'retrieval_in_future')
    rows=[compare_event(e,sources,manifest['security']) for e in manifest['events']]
    previous=None;version=1
    if manifest['previous_packet'] is not None:
        old=read_document(local(base,manifest['previous_packet']))
        require(old.get('packet_hash')==digest({k:v for k,v in old.items() if k!='packet_hash'}),'previous_packet_hash')
        require(old['task_id']==manifest['task_id'],'previous_task_identity')
        previous=old['packet_hash'];version=old['version']+1
    public_manifest={k:v for k,v in manifest.items() if k not in ('sources','output_dir','previous_packet','market_snapshot')}
    packet=dict(schema_version='equity-source-task-packet-v1',task_id=manifest['task_id'],version=version,prior_packet_hash=previous,
        manifest_sha256=sha(manifest_raw),definition=public_manifest,extraction_completed_at=extracted_at,code_identity=code_identity(),
        sources=[{k:v for k,v in s.items() if k!='raw'} for s in sources.values()],events=rows,
        market=dict(status='NOT_PROVIDED',available_events=0,price_signals=None),permissions=PERMISSIONS,
        complete_historical_chain_proven=False,purpose='SEEN_ENGINEERING_DATA_NOT_UNSEEN_VALIDATION')
    # Optional prices reuse the existing verified snapshot format. No CSV guessing,
    # provider access, or strategy execution occurs in this workflow.
    if manifest['market_snapshot'] is not None:
        from hakimi_research.equity_dataset import load_equity_snapshot
        market_path=local(base,manifest['market_snapshot'])
        market_raw=read_bounded(market_path,manifest['budget']['max_total_bytes']-total)
        snapshot=load_equity_snapshot(market_path)
        require(all(snapshot.document['security'][k]==manifest['security'][k] for k in ('security_id','symbol','currency')),'snapshot_security_mismatch')
        require(market_path.read_bytes()==market_raw,'market_changed_during_read')
        market_name='inputs/market-'+sha(market_raw)+'.json';blobs[market_name]=market_raw
        packet['market']=price_diagnostics(packet,snapshot)
        packet['market'].update(retained_path=market_name,sha256=sha(market_raw))
    for id,path in input_paths.items():
        if id in sources and sources[id]['status']=='IMPORTED':require(sha(path.read_bytes())==sources[id]['sha256'],'input_changed_during_read')
    require(manifest_path.read_bytes()==manifest_raw,'manifest_changed_during_read')
    packet['packet_hash']=digest(packet)
    destination=output/('task-'+packet['packet_hash']);destination.mkdir(parents=True,exist_ok=False)
    (destination/'originals').mkdir()
    (destination/'inputs').mkdir()
    for name,raw in blobs.items():(destination/name).write_bytes(raw)
    (destination/'manifest.private.json').write_bytes(manifest_raw)
    write_json(destination/'packet.json',packet)
    return destination/'packet.json'


def write_json(path,data):
    with path.open('x',encoding='utf-8',newline='\n') as file:json.dump(data,file,ensure_ascii=False,indent=2,allow_nan=False);file.write('\n')


def verify_packet(packet_path):
    packet=read_document(packet_path)
    require(packet.get('schema_version')=='equity-source-task-packet-v1','packet_schema')
    require(packet.get('packet_hash')==digest({k:v for k,v in packet.items() if k!='packet_hash'}),'packet_hash')
    require(packet['permissions']==PERMISSIONS and packet['complete_historical_chain_proven'] is False,'permission_escalation')
    require(packet['code_identity']==code_identity(),'audit_code_identity_changed_prepare_new_version')
    manifest_path=packet_path.parent/'manifest.private.json'
    require(sha(read_bounded(manifest_path,1024*1024))==packet['manifest_sha256'],'manifest_binding')
    manifest=validate_manifest(read_document(manifest_path))
    definition={k:v for k,v in manifest.items() if k not in ('sources','output_dir','previous_packet','market_snapshot')}
    require(packet['definition']==definition and packet['task_id']==manifest['task_id'],'manifest_definition_binding')
    declarations={s['source_id']:{k:v for k,v in s.items() if k!='path'} for s in manifest['sources']}
    sources={}
    for entry in packet['sources']:
        require(entry['source_id'] not in sources and entry['source_id'] in declarations,'source_identity')
        require(all(entry[k]==v for k,v in declarations[entry['source_id']].items()),'source_declaration_binding')
        source=dict(entry)
        if entry['status']=='IMPORTED':
            require(entry['retained_path']=='originals/'+entry['sha256']+'.html','retained_filename_identity')
            raw=read_bounded(packet_path.parent/entry['retained_path'],packet['definition']['budget']['max_source_bytes'])
            require(sha(raw)==entry['sha256'],'retained_source_changed')
            source['raw']=raw
        sources[entry['source_id']]=source
    require(set(sources)==set(declarations),'source_catalog_coverage')
    expected=[compare_event(e,sources,packet['definition']['security']) for e in packet['definition']['events']]
    require(expected==packet['events'],'extraction_or_comparison_changed')
    if manifest['market_snapshot'] is None:
        require(packet['market']==dict(status='NOT_PROVIDED',available_events=0,price_signals=None),'market_not_provided')
    else:
        from hakimi_research.equity_dataset import load_equity_snapshot
        market=packet['market'];require(market['retained_path']=='inputs/market-'+market['sha256']+'.json','market_filename')
        path=packet_path.parent/market['retained_path'];require(sha(read_bounded(path,manifest['budget']['max_total_bytes']))==market['sha256'],'market_identity')
        expected=price_diagnostics(packet,load_equity_snapshot(path))
        require(expected=={k:v for k,v in market.items() if k not in ('retained_path','sha256')},'market_diagnostic_binding')
    return packet


def price_diagnostics(packet,snapshot):
    """Reuse the fixed price predicate and point-in-time calendar guard only."""
    from datetime import timedelta
    from hakimi_research.equity_events import build_equity_event, event_snapshot_eligibility
    from .content_protocol import price_confirmation
    data=snapshot.document;definition=packet['definition'];security=definition['security']
    require(all(data['security'][k]==security[k] for k in ('security_id','symbol','currency')),'snapshot_security_mismatch')
    sources={s['source_id']:s for s in packet['sources']};rows=[]
    for event in packet['events']:
        row=dict(event_id=event['event_id'],status='NOT_EVALUATED',price_condition=None,confirmation_at=None)
        rows.append(row);actual=event['actual']
        if actual is None or actual['public_at'] is None:
            row['status']='PUBLICATION_TIME_UNAVAILABLE';continue
        timing=definition['timing']
        if timing['collection_delay_seconds']+timing['processing_delay_seconds']!=120:
            row['status']='FIXED_PRICE_TIMING_ASSUMPTION_NOT_MET';continue
        source=sources[actual['evidence']['source_id']]
        protocol_event=build_equity_event(actual['evidence']['quote'].encode(),dict(
            event_id=event['event_id'],security_id=security['security_id'],event_kind='EARNINGS',version=1,prior_version_hash=None,
            source=dict(url=source['url'],kind='COMPANY_IR',document_type='PRESS_RELEASE',disclosure_items=[],official_source_status='DECLARED_UNVERIFIED'),
            first_public_at=actual['public_at'],version_public_at=actual['public_at'],
            publication_clock=dict(status='ATTESTED',verification_method='SOURCE_PAGE_CLOCK_FOR_HISTORICAL_DIAGNOSTIC_ONLY',evidence='retained_sha256='+source['sha256']),
            retrieved_at=source['retrieved_at'],timing=dict(timing,received_at=None,extraction_completed_at=packet['extraction_completed_at']),
            scheduled_release_at=None,facts=[],uncertainties=['Historical page immutability and first availability not authenticated; no research admission.']))
        alignment=event_snapshot_eligibility(protocol_event,data)
        if alignment['status']!='READY':row['status']=alignment['reason'];continue
        sessions=data['sessions'];bars=[]
        for candle,session in zip(data['candles'],sessions):
            available=(utc(session['close_utc'])+timedelta(seconds=data['bar_availability_lag_seconds'])).isoformat().replace('+00:00','Z')
            bars.append(dict(session=session['date'],close=str(candle[4]),available_at=available,completed=True))
        if not any(utc(s['close_utc'])<=utc(actual['public_at']) for s in sessions):
            row['status']='PRE_RELEASE_PRICE_BASELINE_MISSING';continue
        at=alignment['confirmation_available_at']
        decision=price_confirmation(release_at=actual['public_at'],decision_at=at,sessions=sessions,bars=bars)
        row.update(status='PRICE_CONDITION_EVALUATED',price_condition=decision['action']=='BUY',confirmation_at=at)
    available=sum(r['status']=='PRICE_CONDITION_EVALUATED' for r in rows)
    return dict(status='READONLY_PRICE_DIAGNOSTIC',snapshot_id=snapshot.snapshot_id,available_events=available,
        price_signals=sum(r['price_condition'] is True for r in rows) if available else None,rows=rows,
        authority='NO_EXECUTION_OR_HUMAN_APPROVAL_GRANTED')


def report(packet_path,approval_path=None):
    from .source_task_card import render
    packet=verify_packet(packet_path);approved=set();approval_sha=None
    if approval_path is not None:
        receipt=read_document(approval_path)
        shape(receipt,'schema_version packet_hash reviewer_kind reviewer source_user_confirmation reviewed_at approved_event_ids decision','approval')
        require(receipt['schema_version']=='source-task-human-review-v1' and receipt['packet_hash']==packet['packet_hash'],'approval_identity')
        require(receipt['reviewer_kind']=='HUMAN_ATTESTATION' and receipt['decision']=='APPROVE_SOURCE_FIELDS_ONLY' and all(type(receipt[k]) is str and receipt[k].strip() for k in ('reviewer','source_user_confirmation')),'human_attestation_required')
        require(utc(receipt['reviewed_at'])>=utc(packet['extraction_completed_at']),'approval_before_extraction')
        ids=receipt['approved_event_ids'];eligible={r['event_id'] for r in packet['events'] if r['status'] in STATUSES}
        require(type(ids) is list and len(ids)==len(set(ids)) and set(ids)<=eligible,'approval_scope')
        approved=set(ids);approval_sha=sha(approval_path.read_bytes())
    comparable=sum(r['status'] in ('ABOVE','BELOW','UNCERTAIN_PRECISION') for r in packet['events'])
    evaluated=[r for r in packet['market'].get('rows',[]) if r['status']=='PRICE_CONDITION_EVALUATED']
    above={r['event_id'] for r in packet['events'] if r['status']=='ABOVE'}
    intersection=sum(r['price_condition'] is True and r['event_id'] in above for r in evaluated) if evaluated else None
    result=dict(schema_version='equity-source-task-report-v1',packet_hash=packet['packet_hash'],
        approval_receipt_sha256=approval_sha,human_approved_event_ids=sorted(approved),
        counts=dict(events=len(packet['events']),comparable_sources=comparable,human_approved_events=len(approved),
                    market_available_events=packet['market']['available_events'],price_signals=packet['market']['price_signals'],
                    numeric_above=len(above),price_numeric_intersection=intersection,
                    content_interventions=None,new_economic_runs=0,new_research_admitted=0),
        decision='STOP_AT_SOURCE_WORKFLOW_NO_ECONOMIC_RUN',opportunity_threshold_met=intersection is not None and intersection>=packet['definition']['selection']['minimum_opportunities'],
        renderer_identity={name:sha((ROOT/name).read_bytes()) for name in ('source_task_card.py','report_style.py','source_fact_card.py')},permissions=PERMISSIONS)
    result['report_hash']=digest(result)
    dest=packet_path.parent/('report-'+result['report_hash']);html=render(packet,result)
    files={'result.json':(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'),
           'index.html':html.encode('utf-8')}
    # Validate every existing member before completing an interrupted report.
    # The shared atomic no-replace publisher preserves conflicting evidence.
    for name,encoded in files.items():
        path=dest/name
        if path.exists():require(path.read_bytes()==encoded,'existing_report_changed')
    for name,encoded in files.items():
        _save_encoded_report(encoded,dest/name)
    return dest


def main(argv=None):
    sys.addaudithook(_deny_network)
    parser=argparse.ArgumentParser(description='离线公告导入、原件核对与只读报告；不连接账户或运行收益研究')
    parser.add_argument('command',choices=('run','report','verify'))
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--packet',type=Path)
    parser.add_argument('--approval',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=='run':
            require(args.manifest is not None and args.approval is None and args.packet is None,'run_manifest_required')
            packet=prepare(args.manifest);output=report(packet)
        else:
            require(args.packet is not None and args.manifest is None,'packet_required')
            require(args.command!='verify' or args.approval is None,'verify_does_not_import_approval')
            packet=args.packet
            output=report(packet,args.approval) if args.command=='report' else None
            if args.command=='verify':verify_packet(packet)
        data=read_document(packet)
        stopped=[row['event_id'] for row in data['events'] if row['status'] not in STATUSES]
        print(json.dumps(dict(ok=not stopped,status='STOPPED_WITH_SOURCE_GAPS' if stopped else 'SOURCE_WORKFLOW_CHECKED',
            stopped_event_ids=stopped,packet=str(packet),report=str(output) if output else None,permissions=PERMISSIONS),ensure_ascii=False))
        if stopped:return 2
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps(dict(ok=False,error=str(exc),permissions=PERMISSIONS),ensure_ascii=False));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
