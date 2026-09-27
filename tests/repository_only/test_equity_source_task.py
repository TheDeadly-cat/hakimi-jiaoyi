"""Synthetic full offline workflow; no remote sources or account interface."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from tools.equity_source_task import prepare,report,verify_packet,digest
from tools.equity_source_adapters import extract,audit_fact


def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')


def release(quarter=1,year=2024,revenue='7,192',guidance='11.00',published='2023-05-24'):
    nxt=quarter%4+1;ny=year+(quarter==4);words={1:'first',2:'second',3:'third',4:'fourth'}
    return (f'<html><body><h1>NVIDIA Financial Results for Q{quarter} FY{year}</h1><time datetime="{published}">{published}</time>'
        f'<h2>GAAP</h2><p>($ in millions, except earnings per share)</p><table><tr><th></th><th>Q{quarter} FY{year}</th><th>Q4 FY2023</th></tr>'
        f'<tr><td>Revenue</td><td>${revenue}</td><td>$6,051</td></tr></table>'
        f'<p>NVIDIA’s outlook for the {words[nxt]} quarter of fiscal {ny} is as follows:</p>'
        f'<ul><li>Revenue is expected to be ${guidance} billion, plus or minus 2%.</li></ul></body></html>').encode()


def fixture(root):
    declarations=[]
    for id,raw in [('prior',release(4,2023,'6,051','6.50','2023-02-22')),('actual',release())]:
        path=root/(id+'.html');path.write_bytes(raw)
        declarations.append(dict(source_id=id,path=path.name,sha256=hashlib.sha256(raw).hexdigest(),url='https://nvidianews.nvidia.com/fictional-test/'+id,
            retrieved_at='2026-09-27T00:00:00Z',legal_use='SYNTHETIC_TEST',declaration_version=1,prior_source_id=None,coverage='CONSOLIDATED_REPORTED'))
    return dict(schema_version='equity-source-task-v1',task_id='SYNTHETIC_WORKFLOW',evidence_kind='SYNTHETIC_FIXTURE',
        security=dict(security_id='SYNTHETIC:NVDA:COMMON',symbol='NVDA',name='NVIDIA Corporation',currency='USD',adapter='nvidia-earnings-html-v1'),
        selection=dict(purpose='SOURCE_WORKFLOW_ENGINEERING',basis='Fictional formatting fixture, not actual NVIDIA evidence',selected_before_price_review=True,
            minimum_opportunities=3,price_rule='FIXED_C_PRICE_CONFIRMATION_V1',economic_scope='NOT_REQUESTED_COSTS_AND_RETURNS_NOT_COMPUTED'),
        source_scope=dict(description='Two fictional disclosures',included_types=['EARNINGS_RELEASE'],uncovered_channels=['Calls','Historical versions']),
        budget=dict(max_events=2,max_sources=4,max_source_bytes=10000,max_total_bytes=40000,max_network_requests=0,max_economic_runs=0),
        timing=dict(mode='HISTORICAL_RECONSTRUCTION',collection_delay_seconds=60,processing_delay_seconds=60),
        events=[dict(event_id='SYNTHETIC:NVDA:2024Q1',event_kind='EARNINGS',fiscal_quarter='2024Q1',window_start='2023-02-01T00:00:00Z',
                     window_end='2023-05-31T23:59:59Z',actual_source_id='actual',prior_source_ids=['prior'],known_material_source_ids=['prior','actual'])],
        sources=declarations,output_dir='outputs',previous_packet=None,market_snapshot=None)


class SourceTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hakimi-source-task-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.manifest=fixture(self.root);self.path=self.root/'task.json'
    def run_task(self):save(self.path,self.manifest);return prepare(self.path)
    def change_source(self,id,old,new):
        source=next(s for s in self.manifest['sources'] if s['source_id']==id)
        p=self.root/source['path'];raw=p.read_bytes().replace(old.encode(),new.encode());p.write_bytes(raw);source['sha256']=hashlib.sha256(raw).hexdigest()
    def result(self):return verify_packet(self.run_task())['events'][0]

    def test_complete_workflow_and_date_only_time_is_not_fabricated(self):
        packet=self.run_task();data=verify_packet(packet);event=data['events'][0]
        self.assertEqual(event['status'],'ABOVE');self.assertEqual(event['actual']['value_million'],'7192')
        self.assertEqual(event['latest_prior']['business_range_million'],['6370.00','6630.00'])
        self.assertIsNone(event['model_available_at']);self.assertIsNone(event['actual']['public_at'])
        dest=report(packet);html=(dest/'index.html').read_text(encoding='utf-8');result=json.loads((dest/'result.json').read_bytes())
        self.assertIn('仅日期，时刻未知',html);self.assertIn('内容干预：未运行',html);self.assertIn('尚未人工核准',html)
        self.assertIsNone(result['counts']['price_signals']);self.assertIsNone(result['counts']['content_interventions'])
        for tag in ('<script','<form','<iframe','<input'):self.assertNotIn(tag,html)
        self.assertEqual(report(packet),dest)

    def test_different_quarter_stops_instead_of_using_first_revenue(self):
        self.manifest['events'][0]['fiscal_quarter']='2024Q2'
        self.assertEqual(self.result()['status'],'SOURCE_REJECTED')

    def test_ambiguous_actual_table_stops(self):
        self.change_source('actual','</body>',release().decode()+'</body>')
        self.assertIn('ambiguous',' '.join(self.result()['issues']))

    def test_wrong_source_unit_stops(self):
        self.change_source('actual','$ in millions','$ in billions')
        self.assertIn('unit',' '.join(self.result()['issues']))

    def test_numeric_audit_rejects_modified_value_without_reusing_extractor(self):
        s=self.manifest['sources'][0];source=dict(s,raw=(self.root/s['path']).read_bytes())
        fact=extract(self.manifest['security'],source,'2024Q1','PRIOR');fact['value_million']='5000'
        with self.assertRaisesRegex(ValueError,'audit_source_value'):audit_fact(self.manifest['security'],source,'2024Q1','PRIOR',fact)

    def test_known_preliminary_missing_stops_comparison(self):
        self.manifest['events'][0]['known_material_source_ids'].append('preliminary')
        event=self.result();self.assertEqual(event['status'],'MISSING_KNOWN_DISCLOSURE');self.assertIsNone(event['comparison'])

    def test_missing_source_retains_event_and_failure(self):
        (self.root/'prior.html').unlink()
        self.assertEqual(self.result()['status'],'MISSING_SOURCE')

    def test_missing_coverage_is_unknown_not_equal(self):
        self.manifest['sources'][0]['coverage']=None
        self.assertEqual(self.result()['status'],'UNKNOWN_COVERAGE')

    def test_different_coverage_is_not_comparable(self):
        self.manifest['sources'][0]['coverage']='EXCLUDES_ACQUIRED_BUSINESS'
        self.assertEqual(self.result()['status'],'NOT_COMPARABLE')

    def test_revised_guidance_selects_latest_declared_prior(self):
        source=deepcopy(self.manifest['sources'][0]);source.update(source_id='revision',path='revision.html',declaration_version=2,prior_source_id='prior')
        raw=release(4,2023,'6,051','7.00','2023-03-10');(self.root/'revision.html').write_bytes(raw);source['sha256']=hashlib.sha256(raw).hexdigest()
        self.manifest['sources'].append(source);self.manifest['events'][0]['prior_source_ids'].append('revision');self.manifest['events'][0]['known_material_source_ids'].append('revision')
        event=self.result();self.assertEqual(event['latest_prior']['value_million'],'7000.00')
        self.assertEqual(len(event['prior_disclosures']),2)

    def test_future_guidance_cannot_replace_prior(self):
        self.change_source('prior','2023-02-22','2023-05-25')
        self.assertIn('prior_not_before_actual',' '.join(self.result()['issues']))

    def test_changed_source_creates_new_packet_and_preserves_old(self):
        first=self.run_task();old=first.read_bytes();old_originals={p.name:p.read_bytes() for p in (first.parent/'originals').iterdir()}
        self.change_source('actual','$7,192','$7,193');self.manifest['previous_packet']=str(first)
        second=self.run_task();new=verify_packet(second)
        self.assertNotEqual(first,second);self.assertEqual(first.read_bytes(),old)
        self.assertEqual(new['version'],2);self.assertEqual(new['prior_packet_hash'],json.loads(old)['packet_hash'])
        self.assertEqual({p.name:p.read_bytes() for p in (first.parent/'originals').iterdir()},old_originals)

    def test_bytes_changed_without_manifest_update_stop(self):
        p=self.root/'actual.html';p.write_bytes(p.read_bytes()+b'changed')
        self.assertEqual(self.result()['status'],'MISSING_SOURCE')

    def test_budget_checked_before_reading_or_writing_sources(self):
        self.manifest['budget']['max_sources']=1
        with self.assertRaisesRegex(ValueError,'source_budget'):self.run_task()
        self.assertFalse((self.root/'outputs').exists())

    def test_unsupported_adapter_does_not_guess(self):
        self.manifest['security']['adapter']='other-format'
        self.assertIn('unsupported_adapter',' '.join(self.result()['issues']))

    def test_resealed_packet_cannot_change_manifest_scope(self):
        p=self.run_task();data=json.loads(p.read_bytes());data['definition']['selection']['minimum_opportunities']=1
        data['packet_hash']=digest({k:v for k,v in data.items() if k!='packet_hash'});save(p,data)
        with self.assertRaisesRegex(ValueError,'manifest_definition'):verify_packet(p)

    def test_resealed_extraction_cannot_change_source_number(self):
        p=self.run_task();data=json.loads(p.read_bytes());data['events'][0]['actual']['value_million']='9999'
        data['packet_hash']=digest({k:v for k,v in data.items() if k!='packet_hash'});save(p,data)
        with self.assertRaisesRegex(ValueError,'extraction_or_comparison'):verify_packet(p)

    def test_machine_review_cannot_be_imported_as_human_approval(self):
        p=self.run_task();data=verify_packet(p);receipt=self.root/'approval.json'
        save(receipt,dict(schema_version='source-task-human-review-v1',packet_hash=data['packet_hash'],reviewer_kind='AGENT',reviewer='fixture',source_user_confirmation='fixture',
            reviewed_at=datetime.now(timezone.utc).isoformat(),approved_event_ids=[data['events'][0]['event_id']],decision='APPROVE_SOURCE_FIELDS_ONLY'))
        with self.assertRaisesRegex(ValueError,'human_attestation'):report(p,receipt)

    def test_source_text_is_escaped_and_no_external_resources_loaded(self):
        self.manifest['selection']['basis']='<script>alert(1)</script>'
        p=self.run_task();html=(report(p)/'index.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html);self.assertNotIn('src="https://',html)

    def test_offline_entry_runs_with_manifest_without_source_edits(self):
        save(self.path,self.manifest)
        run=subprocess.run([sys.executable,'-B',str(ROOT/'tools/equity_source_task.py'),'run','--manifest',str(self.path)],cwd=self.root,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        result=json.loads(run.stdout);self.assertFalse(result['permissions']['order_allowed']);self.assertTrue(Path(result['report']).is_dir())

    def price_fixture(self,public='2024-11-29T18:05:00Z',symbol='NVDA'):
        # Reuse the existing immutable snapshot fixture and calendar contract.
        sys.path.insert(0,str(ROOT/'tests'))
        from test_equity_cli import snapshot_fixture
        from hakimi_research.equity_dataset import save_equity_snapshot,build_equity_snapshot
        import base64
        original=snapshot_fixture().document['raw_input'];meta=json.loads(base64.b64decode(original['manifest_base64']))
        meta['security'].update(symbol=symbol,exchange='XNAS',security_id='SYNTHETIC:NVDA:COMMON')
        meta['identity']['source']['raw_base64']=base64.b64encode(('Fictional stable '+symbol).encode()).decode()
        snapshot=build_equity_snapshot(base64.b64decode(original['csv_base64']),meta);path=save_equity_snapshot(snapshot,self.root/'snapshots')
        self.manifest['market_snapshot']=str(path)
        self.manifest['security']['security_id']=snapshot.document['security']['security_id']
        self.manifest['budget']['max_total_bytes']=200000
        self.change_source('prior','2023-02-22','2024-11-01')
        self.change_source('actual','2023-05-24',public)
        self.manifest['events'][0].update(window_start='2024-11-01T00:00:00Z',window_end='2024-12-03T23:59:59Z')

    def test_local_price_snapshot_uses_existing_condition_without_running_strategy(self):
        self.price_fixture();p=self.run_task();data=verify_packet(p)
        self.assertEqual(data['market']['available_events'],1);self.assertEqual(data['market']['price_signals'],1)
        result=json.loads((report(p)/'result.json').read_bytes())
        self.assertEqual(result['counts']['price_numeric_intersection'],1)
        self.assertFalse(result['opportunity_threshold_met']);self.assertEqual(result['counts']['new_economic_runs'],0)
        self.assertIsNone(result['counts']['content_interventions'])

    def test_missing_pre_release_price_cannot_be_counted_as_false_signal(self):
        self.price_fixture('2024-11-29T13:00:00Z');data=verify_packet(self.run_task())
        self.assertEqual(data['market']['rows'][0]['status'],'PRE_RELEASE_PRICE_BASELINE_MISSING')
        self.assertIsNone(data['market']['price_signals'])

    def test_reused_identity_cannot_mix_a_different_price_symbol(self):
        self.price_fixture(symbol='OTHER')
        with self.assertRaisesRegex(ValueError,'snapshot_security_mismatch'):self.run_task()

    def test_date_only_disclosure_cannot_use_prices_for_an_invented_clock(self):
        self.price_fixture('2024-11-29');data=verify_packet(self.run_task())
        self.assertEqual(data['market']['rows'][0]['status'],'PUBLICATION_TIME_UNAVAILABLE')
        self.assertIsNone(data['market']['price_signals'])

    def test_human_attestation_is_narrow_and_does_not_enable_research(self):
        p=self.run_task();data=verify_packet(p);receipt=self.root/'human.json'
        save(receipt,dict(schema_version='source-task-human-review-v1',packet_hash=data['packet_hash'],reviewer_kind='HUMAN_ATTESTATION',
            reviewer='FICTIONAL_TEST_ONLY',source_user_confirmation='SYNTHETIC_ATTESTATION_NOT_REAL_APPROVAL',
            reviewed_at=datetime.now(timezone.utc).isoformat(),approved_event_ids=[data['events'][0]['event_id']],decision='APPROVE_SOURCE_FIELDS_ONLY'))
        output=report(p,receipt);result=json.loads((output/'result.json').read_bytes())
        self.assertEqual(result['counts']['human_approved_events'],1);self.assertEqual(result['counts']['new_research_admitted'],0)
        self.assertFalse(result['permissions']['order_allowed'])
        self.assertIn('本次来源字段已获人工核准',(output/'index.html').read_text(encoding='utf-8'))

    def test_cli_missing_known_source_reports_stop_and_retains_inspectable_artifact(self):
        self.manifest['events'][0]['known_material_source_ids'].append('missing-preliminary');save(self.path,self.manifest)
        run=subprocess.run([sys.executable,'-B',str(ROOT/'tools/equity_source_task.py'),'run','--manifest',str(self.path)],cwd=self.root,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(run.returncode,2,run.stdout+run.stderr)
        response=json.loads(run.stdout);self.assertFalse(response['ok'])
        self.assertEqual(response['status'],'STOPPED_WITH_SOURCE_GAPS');self.assertTrue(Path(response['report']).is_dir())

    def test_manifest_can_choose_existing_amd_format_without_changing_engine(self):
        self.manifest['security'].update(symbol='AMD',name='Advanced Micro Devices, Inc.',adapter='amd-earnings-html-v1')
        actual=b'<html><body><h1>AMD Financial Results</h1><time datetime="2023-05-24T16:00:00" class="date">May 24, 2023 4:00 pm EDT</time><h2>GAAP Quarterly Financial Results</h2><table><tr><td></td><td>Q1 2024</td><td>Q1 2023</td></tr><tr><td>Revenue ($M)</td><td>$7,192</td><td>$6,000</td></tr></table></body></html>'
        prior=b'<html><body><h1>AMD Financial Results</h1><time datetime="2023-02-22T16:00:00" class="date">Feb 22, 2023 4:00 pm EST</time><p>For the first quarter of 2024, AMD expects revenue to be approximately $6.5 billion, plus or minus $100 million</p></body></html>'
        for source,raw in zip(self.manifest['sources'],(prior,actual)):
            (self.root/source['path']).write_bytes(raw);source['sha256']=hashlib.sha256(raw).hexdigest();source['url']='https://ir.amd.com/fictional/'+source['source_id']
        event=self.result();self.assertEqual(event['status'],'ABOVE',event['issues'])
        self.assertEqual(event['actual']['public_at'],'2023-05-24T20:00:00Z')

    def test_newsroom_article_date_short_fiscal_year_and_split_currency_cells(self):
        self.change_source('actual','<time datetime="2023-05-24">2023-05-24</time>','<div class="article-date">May 24, 2023</div><aside><time datetime="2026-09-14">Related story</time></aside>')
        self.change_source('actual','FY2024','FY24')
        self.change_source('actual','<td>$7,192</td>','<td>$</td><td>7,192</td>')
        event=self.result();self.assertEqual(event['status'],'ABOVE',event['issues'])
        self.assertEqual(event['actual']['publication_date'],'2023-05-24');self.assertIsNone(event['actual']['public_at'])

    def test_non_gaap_and_annual_tables_do_not_replace_quarterly_gaap_column(self):
        extra='<table><tr><td>Non-GAAP</td></tr><tr><td>($ in millions, except earnings per share)</td><td>Q1 FY24</td></tr><tr><td>Revenue</td><td>$9,999</td></tr></table><table><tr><td>GAAP</td></tr><tr><td>($ in millions, except earnings per share)</td><td>FY24</td></tr><tr><td>Revenue</td><td>$99,999</td></tr></table>'
        self.change_source('actual','</body>',extra+'</body>')
        event=self.result();self.assertEqual(event['status'],'ABOVE',event['issues']);self.assertEqual(event['actual']['value_million'],'7192')


if __name__=='__main__':unittest.main()
