"""Full receipt-to-bundle checks, portable into the installed acceptance suite."""
import copy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zoneinfo import ZoneInfo

from hakimi_research.collection_import import PLAN, PLAN_SHA, calendars, import_collection, verify_bundle
from hakimi_research.futu_quote_contract import requests


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def collection_fixture(root, *, split=False):
    root.mkdir()
    calendar = root / 'calendar.original'
    calendar.write_bytes(b'Fictional calendar source. Not a real Nasdaq record.')
    frozen = dict(inputs=dict(plan=PLAN, calendar_path='Z:/no-longer-present/calendar.pdf',
        calendar_sha256=hashlib.sha256(calendar.read_bytes()).hexdigest(), calendars=calendars()),
        requests=requests(), source_identity={'docs/studies/nvda-event-price-20260930.json': PLAN_SHA}, evidence_kind='SYNTHETIC_TEST')
    data = {'security': [dict(code='US.NVDA', stock_type='STOCK', exchange_type='US_NASDAQ', lot_size=1, delisting=False, stock_id=1234)], 'actions': []}
    for quarter, calendar_info in calendars().items():
        hours, daily = [], []
        for index, session in enumerate(calendar_info['sessions']):
            clock = datetime.fromisoformat(session['open_utc'].replace('Z', '+00:00'))
            close = datetime.fromisoformat(session['close_utc'].replace('Z', '+00:00'))
            row = dict(code='US.NVDA', open=20+index, high=22+index, low=19+index, close=21+index, volume=100)
            while clock < close:
                clock = min(clock + timedelta(hours=1), close)
                hours.append(dict(row, time_key=clock.astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M:%S')))
            daily.append(dict(row, time_key=session['date'], volume=800))
        data[quarter+'-K_DAY'], data[quarter+'-K_60M'] = daily, hours
    primary, resumed = root / ('first' if split else 'collection'), root / 'continuation'
    primary.mkdir()
    if split: resumed.mkdir()
    for directory in ([primary, resumed] if split else [primary]):
        write(directory/'frozen-inputs.private.json', frozen)
        write(directory/'process.private.json', dict(returncode=1 if split and directory==primary else 0,
            bounds=dict(outcome='EXITED', cleanup_confirmed=True)))
    for index, request in enumerate(requests(), 1):
        folder = primary if not split or index<=2 else resumed
        prefix = f'{index:02d}-{request["label"]}'
        write(folder/(prefix+'.started.private.json'), dict(request=request, attempt=1))
        write(folder/(prefix+'.response.private.json'), dict(completed_at='2026-09-30T00:00:00Z',
            returned_reply=dict(ret=0, rows=data[request['label']], page_req_key=None)))
    completed = dict(status='QUOTE_COLLECTION_COMPLETED_AWAITING_ADMISSION', business_method_calls=6,
        business_protocol_query_calls=6, account_queries=0, order_calls=0, sdk_version='10.7.6708')
    if split:
        (primary/'stderr.private.log').write_bytes(b'')
        write(primary/'summary.json', dict(status='STOPPED_NO_RETRY', reason='ACTION_SECURITY_IDENTITY_MISMATCH',
            business_method_calls=2, business_protocol_query_calls=2, account_queries=0, order_calls=0, windows=[], sdk_version='10.7.6708'))
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in primary.iterdir() if p.is_file()}
        identity=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
        write(resumed/'continuation.private.json', dict(prior_files=hashes, prior_identity=identity, prior_directory='Z:/old/first'))
        write(resumed/'summary.json', dict(completed, new_business_method_calls=4, reused_successful_calls=2, prior_identity=identity))
        args=dict(first=primary, continuation=resumed)
    else:
        write(primary/'summary.json', completed)
        args=dict(collection=primary)
    return dict(calendar_original=calendar, synthetic=True, **args)


class CollectionImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_first_successful_collection_imports_without_a_historical_failure(self):
        args=collection_fixture(self.root/'normal')
        folder=import_collection(**args,output_dir=self.root/'output')
        manifest=verify_bundle(folder)
        self.assertEqual(manifest['import_mode'],'COMPLETE_COLLECTION')
        self.assertEqual(len(manifest['snapshots']),2)
        self.assertTrue(all(r['daily_RTH_OHLC_mismatch_sessions']==0 and r['daily_RTH_volume_difference_sessions']==8 for r in manifest['snapshots']))
        self.assertEqual(manifest['permissions']['provider_calls'],0)
        self.assertEqual(import_collection(**args,output_dir=self.root/'output'),folder)

    def test_legitimate_split_collection_imports_and_migrates_without_old_paths(self):
        args=collection_fixture(self.root/'split',split=True)
        folder=import_collection(**args,output_dir=self.root/'output')
        migrated=self.root/'another-computer'/'inputs'
        shutil.copytree(self.root/'split',migrated)
        moved_args=dict(first=migrated/'first',continuation=migrated/'continuation',calendar_original=migrated/'calendar.original',synthetic=True)
        again=import_collection(**moved_args,output_dir=self.root/'other-output')
        self.assertEqual(verify_bundle(folder),verify_bundle(again))
        bundle_copy=self.root/'moved-bundle'
        shutil.copytree(folder,bundle_copy)
        self.assertEqual(verify_bundle(folder),verify_bundle(bundle_copy))

    def test_corrupt_receipt_stops_before_publishing_a_snapshot(self):
        args=collection_fixture(self.root/'normal')
        path=args['collection']/'03-2024Q1-K_DAY.response.private.json'
        d=json.loads(path.read_bytes());d['returned_reply']['rows'][0]['close']=999;write(path,d)
        with self.assertRaisesRegex(ValueError,'INVALID_OHLC|DAILY_RTH'):import_collection(**args,output_dir=self.root/'output')
        self.assertFalse((self.root/'output').exists())

    def test_unfinished_process_missing_file_and_extra_call_are_rejected(self):
        for case in ('process','missing','extra'):
            with self.subTest(case=case):
                args=collection_fixture(self.root/case)
                folder=args['collection']
                if case=='process':write(folder/'process.private.json',dict(returncode=0,bounds=dict(outcome='EXITED',cleanup_confirmed=False)))
                elif case=='missing':(folder/'04-2024Q1-K_60M.response.private.json').unlink()
                else:write(folder/'07-extra.started.private.json',{})
                with self.assertRaises((ValueError,OSError)):import_collection(**args,output_dir=self.root/('output-'+case))
                self.assertFalse((self.root/('output-'+case)).exists())

    def test_resume_identity_cannot_be_bypassed_by_moving_the_directory(self):
        args=collection_fixture(self.root/'split',split=True)
        path=args['first']/'01-security.response.private.json'
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'PRIOR_RECEIPT_CHANGED'):import_collection(**args,output_dir=self.root/'output')

    def test_bundle_conflict_and_traversal_are_rejected_without_overwriting(self):
        args=collection_fixture(self.root/'normal')
        folder=import_collection(**args,output_dir=self.root/'output')
        original=(folder/'bundle.json').read_bytes()
        (folder/'unexpected.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'INVENTORY'):import_collection(**args,output_dir=self.root/'output')
        self.assertEqual((folder/'bundle.json').read_bytes(),original)
        from hakimi_research.collection_import import relative_file
        with self.assertRaisesRegex(ValueError,'PATH_INVALID'):relative_file(folder,'../secret')


if __name__=='__main__':unittest.main()
