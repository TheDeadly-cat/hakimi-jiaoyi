"""Schedule policy behavior on fictional inputs; no market or broker calls."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.equity_dataset import build_equity_snapshot
from hakimi_research.equity_events import build_equity_event, verify_equity_event, event_snapshot_eligibility
from hakimi_research.equity_event_context import build_event_context, verify_event_context, EventSchedulePolicy, DISABLED, RULE_VERSION
from hakimi_research.equity_research import EquityExperimentRunner, EquityExperimentSpec, EquityResearchReport, replay_equity_report, verify_equity_report
from hakimi_research.models import Signal
from hakimi_research.equity_schedule_comparison import run_schedule_comparison, build_schedule_comparison, verify_schedule_comparison
if __package__:
    from .test_equity_research import stock_snapshot, stock_inputs, spec_document, reseal
    from .test_equity_cli import snapshot_fixture, event_fixture
else:
    # The installed acceptance harness discovers copied siblings as top-level
    # modules, without the checkout's tests package or an injected PYTHONPATH.
    from test_equity_research import stock_snapshot, stock_inputs, spec_document, reseal
    from test_equity_cli import snapshot_fixture, event_fixture


def schedule_metadata(day='2024-11-04', public='2024-10-31T13:00:00Z', previous=None, status='ANNOUNCED'):
    raw=('Fictional schedule '+status+' '+str(day)+' after market close.').encode()
    metadata={'event_id':'SYNTHETIC:SCHEDULE:Q3','security_id':'SYNTHETIC:RESEARCH:TEST','event_kind':'EARNINGS_SCHEDULE',
        'version':1 if previous is None else previous['version']+1,
        'prior_version_hash':None if previous is None else previous['event_hash'],
        'source':{'url':'https://example.invalid/schedule','kind':'SYNTHETIC_FIXTURE','document_type':'PRESS_RELEASE',
                  'disclosure_items':[],'official_source_status':'DECLARED_UNVERIFIED'},
        'first_public_at':public if previous is None else previous['first_public_at'],'version_public_at':public,
        'publication_clock':{'status':'ATTESTED','verification_method':'SYNTHETIC_FIXTURE','evidence':'Fictional publication clock'},
        'retrieved_at':'2024-12-05T00:00:00Z','timing':{'mode':'HISTORICAL_RECONSTRUCTION','received_at':None,
            'extraction_completed_at':'2024-12-05T00:01:00Z','collection_delay_seconds':1,'processing_delay_seconds':1},
        'scheduled_release_at':None,'facts':[],'uncertainties':['Synthetic schedule, not market evidence'],
        'schedule':{'status':status,'date':day,'time_precision':'AFTER_MARKET_CLOSE' if day else None,
            'timezone':'America/New_York','evidence':[{'quote':raw.decode()}],
            'reason':None if status=='ANNOUNCED' else 'Fictional cancellation or uncertainty'}}
    return raw,metadata


def schedule(*args, **kwargs):
    return build_equity_event(*schedule_metadata(*args, **kwargs))


def context(events):
    return build_event_context(events,'SYNTHETIC:RESEARCH:TEST')


def event_run(snapshot, events, *, rule=RULE_VERSION, strategy='buy_and_hold', specification=None):
    archive=context(events)
    value=copy.deepcopy(specification) if specification is not None else spec_document(snapshot,strategy,fee=0.001,slip=0.001)
    value.update(schema_version='us-equity-experiment-spec-v2',event_context_hash=archive['context_hash'],event_rule=rule)
    return EquityExperimentRunner().run(snapshot,EquityExperimentSpec.from_document(value),event_context=archive)


class EquityScheduleFilterTests(unittest.TestCase):
    def test_date_precision_keeps_exact_clock_null_and_old_event_verification_unchanged(self):
        event=schedule()
        self.assertEqual(event['schema_version'],'equity-event-v2')
        self.assertIsNone(event['scheduled_release_at'])
        self.assertEqual(verify_equity_event(event),event)
        old=event_fixture('2024-11-29T13:00:00Z')
        self.assertEqual(old['schema_version'],'equity-event-v1')
        self.assertEqual(canonical_bytes(verify_equity_event(old)),canonical_bytes(old))

    def test_coarse_dates_reject_invented_exact_time_wrong_evidence_and_actual_release_kind(self):
        for change, expected in [({'scheduled_release_at':'2024-11-04T21:05:00Z'},'must_not_invent'),
                                 ({'event_kind':'EARNINGS'},'requires_us_earnings_schedule')]:
            raw,metadata=schedule_metadata();metadata.update(change)
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,expected):
                build_equity_event(raw,metadata)
        raw,metadata=schedule_metadata();metadata['schedule']['evidence']=[{'quote':'absent date claim'}]
        with self.assertRaisesRegex(ValueError,'quote_mismatch'):
            build_equity_event(raw,metadata)

    def test_unknown_clock_is_retained_but_cannot_admit_a_historical_filter(self):
        raw,metadata=schedule_metadata()
        metadata['publication_clock']={'status':'UNKNOWN','verification_method':None,'evidence':None}
        event=build_equity_event(raw,metadata)
        self.assertIsNone(event['availability']['available_at'])
        with self.assertRaisesRegex(ValueError,'NOT_RUN_no_historical'):
            event_run(stock_snapshot(),[event])

    def test_empty_missing_or_actual_release_input_is_not_a_schedule_comparison(self):
        with self.assertRaisesRegex(ValueError,'requires_schedule_versions'):
            context([])
        with self.assertRaisesRegex(ValueError,'requires_schedule_versions'):
            context([event_fixture('2024-11-29T13:00:00Z')])
        value=spec_document(stock_snapshot());value.update(schema_version='us-equity-experiment-spec-v2',event_context_hash='0'*64,event_rule=RULE_VERSION)
        with self.assertRaisesRegex(ValueError,'context_required'):
            EquityExperimentRunner().run(stock_snapshot(),EquityExperimentSpec.from_document(value))

    def test_context_lineage_and_security_are_bound_and_input_mutation_is_detached(self):
        first=schedule();second=schedule('2024-11-05','2024-11-01T13:00:00Z',previous=first)
        archive=context([second,first,first]);self.assertEqual(len(archive['events']),2)
        self.assertEqual(verify_event_context(archive),archive)
        with self.assertRaisesRegex(ValueError,'lineage_incomplete'):
            context([second])
        policy=EventSchedulePolicy(archive,rule=RULE_VERSION,security_id=first['security_id'],purpose='SYNTHETIC_REGRESSION')
        archive['events'][0]['schedule']['date']='1900-01-01'
        self.assertEqual(policy.known_at('2024-10-31T13:00:02Z')[0]['schedule']['date'],'2024-11-04')
        with self.assertRaises(ValueError):
            verify_event_context(archive)

    def test_disabled_event_rule_preserves_entire_price_result(self):
        snapshot=stock_snapshot()
        base=EquityExperimentRunner().run(snapshot,EquityExperimentSpec.from_document(spec_document(snapshot,'buy_and_hold',fee=0.001,slip=0.001)))
        disabled=event_run(snapshot,[schedule()],rule=DISABLED)
        self.assertEqual(canonical_bytes(base.document['result']),canonical_bytes(disabled.document['result']))
        verify_equity_report(disabled.document)

    def test_known_schedule_blocks_single_buy_hold_intent_without_postponing_it(self):
        report=event_run(stock_snapshot(),[schedule()]).document
        verify_equity_report(report)
        first=report['result']['signals'][0]
        self.assertEqual(first['event_filter']['decision']['input_action'],'BUY')
        self.assertGreater(first['event_filter']['decision']['input_signal']['size_pct'],0)
        self.assertEqual(first['event_filter']['decision']['disposition'],'BLOCK_NEW_BUY')
        self.assertEqual(first['action'],'HOLD')
        # Buy-and-hold makes only its initial decision. Blocking that intent
        # leaves this whole comparison at cash; it must not be retried tomorrow.
        self.assertEqual(report['result']['fills'],[])

    def test_schedule_becoming_available_overnight_blocks_execution_not_the_past_decision(self):
        event=schedule(public='2024-11-04T13:00:00Z')
        report=event_run(stock_snapshot(),[event]).document;verify_equity_report(report)
        first=report['result']['signals'][0]['event_filter']
        self.assertEqual(first['decision']['known_versions'],[])
        self.assertEqual(first['decision']['disposition'],'ALLOW_PRICE_BUY')
        self.assertEqual(first['execution']['disposition'],'BLOCK_NEW_BUY')
        self.assertFalse(any(fill['fill_time'].startswith('2024-11-04') for fill in report['result']['fills']))

    def test_publication_before_open_but_processing_crosses_open_cannot_filter_that_open(self):
        event=schedule(public='2024-11-04T14:29:59Z')
        report=event_run(stock_snapshot(),[event]).document;verify_equity_report(report)
        first=report['result']['signals'][0]['event_filter']
        self.assertEqual(first['execution']['known_versions'],[])
        self.assertTrue(report['result']['fills'][0]['fill_time'].startswith('2024-11-04'))

    def test_future_revisions_do_not_change_prior_decisions_or_economics(self):
        first=schedule()
        changed=schedule('2024-12-06','2024-12-04T13:00:00Z',previous=first)
        before=event_run(stock_snapshot(),[first]).document
        after=event_run(stock_snapshot(),[first,changed]).document
        for key in ('signals','fills','orders','equity_curve','total_return','total_fees','exposure_ratio'):
            self.assertEqual(before['result'][key],after['result'][key],key)
        self.assertNotEqual(before['event_context']['context_hash'],after['event_context']['context_hash'])

    def test_cancellation_does_not_revive_an_already_blocked_buy(self):
        first=schedule()
        cancelled=schedule(None,'2024-11-04T13:00:00Z',previous=first,status='CANCELLED')
        report=event_run(stock_snapshot(),[first,cancelled]).document;verify_equity_report(report)
        reviews=report['result']['signals'][0]['event_filter']
        self.assertEqual(reviews['decision']['disposition'],'BLOCK_NEW_BUY')
        self.assertEqual(reviews['execution']['known_versions'][0]['schedule']['status'],'CANCELLED')
        self.assertEqual(reviews['execution']['disposition'],'NO_PENDING_BUY')
        self.assertEqual(report['result']['fills'],[])

    def test_dual_ma_can_enter_only_on_a_new_crossover_after_a_block(self):
        snapshot,spec=dual_ma_fixture()
        event=schedule(snapshot.document['sessions'][7]['date'])
        base=EquityExperimentRunner().run(snapshot,EquityExperimentSpec.from_document(spec)).document
        report=event_run(snapshot,[event],specification=spec).document;verify_equity_report(report)
        self.assertTrue(base['result']['fills'])
        first=report['result']['signals'][0]
        self.assertEqual(first['event_filter']['decision']['disposition'],'BLOCK_NEW_BUY')
        buys=[fill for fill in report['result']['fills'] if fill['action']=='BUY']
        self.assertTrue(buys,'Fixture must include a later independent crossover')
        self.assertGreater(buys[0]['signal_time'],first['time'])
        self.assertNotEqual(buys[0]['fill_time'],base['result']['fills'][0]['fill_time'])

    def test_schedule_on_protective_exit_day_does_not_block_the_exit(self):
        snapshot,spec=dual_ma_fixture()
        base=EquityExperimentRunner().run(snapshot,EquityExperimentSpec.from_document(spec)).document
        sales=[fill for fill in base['result']['fills'] if fill['action']=='SELL']
        self.assertTrue(sales,'Fixture must exercise a real shared-engine exit')
        event=schedule(sales[0]['fill_time'][:10])
        report=event_run(snapshot,[event],specification=spec).document;verify_equity_report(report)
        for key in ('fills','orders','equity_curve','total_fees','total_return'):
            self.assertEqual(base['result'][key],report['result'][key],key)

    def test_uncertain_revision_blocks_additions_without_liquidating_existing_holdings(self):
        first=schedule('2024-11-20')
        uncertain=schedule(None,'2024-11-05T13:00:00Z',previous=first,status='UNKNOWN')
        report=event_run(stock_snapshot(),[first,uncertain]).document;verify_equity_report(report)
        self.assertEqual(len(report['result']['fills']),1)
        self.assertEqual(report['result']['fills'][0]['action'],'BUY')
        self.assertGreater(report['result']['open_position_qty'],0)

    def test_resealed_future_or_missing_review_cannot_pass_report_verification(self):
        report=event_run(stock_snapshot(),[schedule()]).document
        for mutation in ('future','missing'):
            bad=copy.deepcopy(report)
            if mutation=='future':
                bad['result']['signals'][0]['event_filter']['decision']['known_versions'][0]['available_at']='2099-01-01T00:00:00Z'
            else:
                bad['result']['signals'][0]['event_filter'].pop('execution')
            reseal(bad,result_changed=True)
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,'equity_event_'):
                verify_equity_report(bad)

    def test_shared_calendar_entry_rejects_left_gap_without_cli(self):
        snapshot=snapshot_fixture().document
        result=event_snapshot_eligibility(event_fixture('2024-11-29T03:55:00Z'),snapshot)
        self.assertEqual(result['reason'],'EVENT_AVAILABILITY_PRECEDES_CALENDAR_COVERAGE')
        self.assertIsNone(result['earliest_entry_at'])
        weekend=event_snapshot_eligibility(event_fixture('2024-11-30T12:00:00Z'),snapshot)
        self.assertEqual(weekend['earliest_entry_at'],'2024-12-03T14:30:00Z')

    def test_synthetic_schedule_cannot_enter_descriptive_real_data_claim(self):
        archive=context([schedule()])
        with self.assertRaisesRegex(ValueError,'synthetic_event'):
            EventSchedulePolicy(archive,rule=RULE_VERSION,security_id=archive['security_id'],purpose='DESCRIPTIVE_DEVELOPMENT')

    def test_schedule_report_replays_shared_ledger(self):
        snapshot=stock_snapshot();report=event_run(snapshot,[schedule()])
        result=replay_equity_report(snapshot,report)
        self.assertTrue(result['result_matches'])
        self.assertTrue(result['source_matches'])
        self.assertTrue(result['environment_verified'])
        self.assertTrue(result['replay_verified'])

    def test_intraday_after_early_close_and_weekend_publications_use_the_correct_stage(self):
        snapshot=stock_snapshot()
        spec=spec_document(snapshot,'buy_and_hold');spec['score_start_session']='2024-12-02'
        for public,blocked_at_decision in [('2024-11-29T17:00:00Z',True),('2024-11-29T18:05:00Z',False),('2024-11-30T12:00:00Z',False)]:
            with self.subTest(public=public):
                report=event_run(snapshot,[schedule('2024-12-02',public)],specification=spec).document
                verify_equity_report(report)
                first=report['result']['signals'][0]
                self.assertTrue(first['time'].startswith('2024-11-29 18:01:00'))
                self.assertEqual(first['event_filter']['decision']['disposition']=='BLOCK_NEW_BUY',blocked_at_decision)
                self.assertEqual(first['event_filter']['execution']['disposition']=='BLOCK_NEW_BUY',not blocked_at_decision)
                self.assertEqual(report['result']['fills'],[])

    def test_comparison_keeps_no_trade_and_lost_participation_with_one_common_spec(self):
        snapshot=stock_snapshot();base=EquityExperimentSpec.from_document(spec_document(snapshot,'buy_and_hold',fee=0.001,slip=0.001))
        a,b,comparison=run_schedule_comparison(snapshot,base,context([schedule()]))
        verify_schedule_comparison(comparison,a.document,b.document)
        self.assertEqual(comparison['sample_units']['company_count'],1)
        self.assertEqual(comparison['sample_units']['announced_event_count_in_scoring_window'],1)
        self.assertEqual(comparison['B']['metrics']['outcome'],'NO_TRADE')
        self.assertEqual(comparison['B']['metrics']['blocked_new_buy_intents'],1)
        self.assertEqual(comparison['B_minus_A']['buy_fill_count'],-1)
        self.assertLess(comparison['B_minus_A']['total_return'],0)
        bad=copy.deepcopy(comparison);bad['B']['metrics']['total_return']=99
        bad['comparison_hash']=digest({key:value for key,value in bad.items() if key!='comparison_hash'})
        with self.assertRaisesRegex(ValueError,'comparison_binding'):
            verify_schedule_comparison(bad,a.document,b.document)
        different=copy.deepcopy(base.document);different['fee_rate']=0.002
        changed=event_run(snapshot,[schedule()],specification=different)
        with self.assertRaisesRegex(ValueError,'identical_inputs'):
            build_schedule_comparison(a.document,changed.document)

    def test_cli_context_compare_and_each_report_replay_use_saved_artifacts(self):
        from hakimi_research.equity_cli import main
        from hakimi_research.equity_dataset import save_equity_snapshot
        from hakimi_research.equity_events import save_equity_event
        with tempfile.TemporaryDirectory(prefix='hakimi-schedule-cli-') as directory:
            root=Path(directory);snapshot=stock_snapshot()
            snapshot_path=save_equity_snapshot(snapshot,root/'snapshots')
            save_equity_event(schedule(),root/'events')
            spec=root/'spec.json';spec.write_bytes(canonical_bytes(spec_document(snapshot,'buy_and_hold')))
            def invoke(args):
                output=io.StringIO()
                with patch('hakimi_research.equity_cli.sys.addaudithook') as audit,redirect_stdout(output):
                    main([*args,'--output-dir',str(root/'output')])
                audit.assert_called_once()
                return json.loads(output.getvalue())
            archive=invoke(['event-context','--event-dir',str(root/'events'),'--security-id',snapshot.document['security']['security_id']])
            comparison=invoke(['event-compare','--snapshot',str(snapshot_path),'--spec',str(spec),'--event-context',archive['event_context']])
            self.assertEqual(comparison['B']['outcome'],'NO_TRADE')
            self.assertTrue(Path(comparison['comparison']).is_file())
            for key in ('A_report','B_report'):
                receipt=invoke(['replay','--snapshot',str(snapshot_path),'--report',comparison[key]])
                self.assertTrue(receipt['replay_verified'])


def dual_ma_fixture():
    raw,metadata=stock_inputs()
    days=[row for row in metadata['calendar']['days'] if row['kind']=='OPEN']
    closes=[100,100,100,100,99,101,103,104,105,104,102,100,100,101,103,105,106,107,108,109,110,111]
    rows=['session_date,open,high,low,close,volume']
    for index,day in enumerate(days):
        close=closes[index];opened=closes[max(0,index-1)]
        rows.append(f"{day['date']},{opened},{max(opened,close)+0.1},{min(opened,close)-0.1},{close},10000")
    raw=('\n'.join(rows)+'\n').encode()
    import base64
    metadata['price_source']['raw_base64']=base64.b64encode(raw).decode()
    snapshot=build_equity_snapshot(raw,metadata)
    spec=spec_document(snapshot,fee=0.001,slip=0.001)
    spec['strategy']={'name':'dual_ma','params':{'fast_window':2,'slow_window':3,'position_pct':0.25,'stop_loss_pct':0.03,'take_profit_pct':0.8}}
    spec['score_start_session']=days[7]['date']
    return snapshot,spec


if __name__=='__main__':
    unittest.main()
