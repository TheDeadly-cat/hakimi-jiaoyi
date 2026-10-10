"""Synthetic input/version flows through the canonical task and session engine."""
import copy
from hashlib import sha256
from importlib.resources import files
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from hakimi_research import content_protocol, offline_app
from hakimi_research.documents import canonical_bytes, read_document, digest
from hakimi_research.equity_event_context import build_event_context
from hakimi_research.input_workflow import (import_input, import_price_csv, import_content_packet,
    list_inputs, check_inputs, bind_inputs, inspect_input)
from hakimi_research.offline_app import run_task, verify_run, describe_run, replay_run, recover_report
from hakimi_research.task_comparison import compare_runs
from hakimi_research.task_manager import create_family, version_options, describe_task, change_state, read_family
from hakimi_research.trade_cli import initialize_demo, main, wizard


class InputWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hakimi-m2-inputs-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = self.root/'workspace'
        initialized = initialize_demo(self.workspace)
        self.examples = initialized['input_examples']
        self.price = version_options(self.workspace/'tasks/price.json')
        self.snapshot = self.price['snapshot']
        self.family = self.workspace/'tasks/managed'

    def document(self, name, value):
        path = self.root/name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return path

    def content(self, *, approved=False, packet=None):
        packet = packet or read_document(self.examples['packet'])
        packet_path = self.document('candidate-fixture.json', packet)
        approval = None
        if approved:
            receipt = dict(schema_version='human-field-review-v1', packet_hash=packet['packet_hash'],
                decision='APPROVED_LISTED_FIELDS', reviewer_kind='HUMAN_ATTESTATION', reviewer='SYNTHETIC_FIXTURE_ONLY',
                source_user_confirmation='Fictional fixture receipt only; no actual human approval claimed',
                reviewed_at='2024-12-06T00:00:00Z', approved_candidate_hashes=[packet['events'][0]['candidate_hash']],
                approved_fields=['actual_revenue','diluted_eps','non_gaap_diluted_eps',
                    'next_revenue_guidance_midpoint','next_revenue_guidance_half_range','first_public_at'])
            approval = self.document('field-review-fixture.json', receipt)
        saved = import_content_packet(packet_path, self.workspace, event_id=self.examples['event_id'],
            texts_dir=self.examples['texts_dir'], originals_dir=self.examples['originals_dir'], approval=approval, synthetic=True)
        return Path(saved['path'])

    def create_content(self, context, name='content', strategy='content.reviewed_outlook@1'):
        family = self.workspace/'tasks'/name
        create_family(family, strategy=strategy, snapshot=self.snapshot, event_context=context,
            score_start='2024-11-04', score_end='2024-12-03')
        return family

    def frozen(self, *directories):
        return {p:sha256(p.read_bytes()).hexdigest() for d in directories for p in Path(d).rglob('*') if p.is_file()}

    def unchanged(self, originals):
        for path, expected in originals.items():
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)

    def cli(self, arguments, expected=0):
        with redirect_stdout(io.StringIO()) as output:
            result = main([str(v) for v in arguments])
        self.assertEqual(result, expected, output.getvalue())
        return json.loads(output.getvalue())

    def test_csv_and_existing_snapshot_import_retain_exact_source_identity_without_second_format(self):
        resources = files('hakimi_research').joinpath('resources')
        csv = self.root/'provided.csv';csv.write_bytes(resources.joinpath('trade-demo.csv').read_bytes())
        metadata = self.root/'provided.json';metadata.write_bytes(resources.joinpath('trade-demo-import.json').read_bytes())
        old = self.frozen(self.workspace)
        saved = import_price_csv(csv, metadata, self.workspace)
        self.assertEqual(saved['input_id'], inspect_input(self.snapshot)['input_id'])
        self.assertEqual(saved['source']['raw_sha256'], sha256(csv.read_bytes()).hexdigest())
        copied = import_input(self.snapshot, self.workspace)
        self.assertEqual(Path(copied['path']).read_bytes(), self.snapshot.read_bytes())
        self.assertEqual(import_input(self.snapshot, self.workspace)['path'], copied['path'])
        self.assertEqual(saved['source_authentication'], 'NOT_CRYPTOGRAPHICALLY_AUTHENTICATED')
        self.assertGreaterEqual(len(list_inputs(self.workspace)['items']), 3)
        self.unchanged(old)

    def test_input_check_never_runs_engine_or_commits_files(self):
        context = self.content(approved=True)
        options = dict(strategy='content.reviewed_outlook@1',snapshot=self.snapshot,event_context=context,
            score_start='2024-11-04',score_end='2024-12-03')
        before = self.frozen(self.workspace)
        with patch.object(offline_app, 'run_strategy', side_effect=AssertionError('input check must not simulate')):
            checked = check_inputs(options, location=self.root/'unused/task.json')
        self.assertEqual(checked['status'], 'INPUTS_APPLICABLE_NO_SIMULATION')
        self.assertEqual(checked['new_economic_runs'], 0)
        self.assertFalse((self.root/'unused').exists())
        self.assertEqual(before, self.frozen(self.workspace))

    def test_unapproved_content_holds_and_price_baseline_uses_the_canonical_next_open(self):
        context = self.content()
        active = self.create_content(context)
        baseline = self.create_content(context, name='baseline',strategy='content.price_confirmation@1')
        active_run, baseline_run = run_task(active), run_task(baseline)
        report = verify_run(baseline_run)[1]
        buys = [r for r in report['result']['fills'] if r['action']=='BUY']
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0]['fill_time'], '2024-11-08 14:30:00+00:00')
        blocked = describe_run(active_run)
        self.assertEqual(blocked['fill_count'], 0)
        self.assertEqual(blocked['blocked_new_buys'], 1)
        self.assertEqual(blocked['research_input_outcome']['status'], 'CONTENT_FILTER_CHANGED_PRICE_INTENT')
        self.assertTrue(any(r['reason']=='CONTENT_UNKNOWN_OR_NOT_APPROVED' for r in blocked['research_input_outcome']['reviews']))
        comparison = compare_runs([baseline_run, active_run])
        self.assertEqual(comparison['status'], 'COMPARABLE_CONDITIONS')
        self.assertEqual(comparison['rows'][1]['blocked_new_buys'], 1)
        self.assertEqual(comparison['new_economic_runs'], 0)
        self.assertIn('CONTENT_UNKNOWN_OR_NOT_APPROVED', recover_report(active_run).read_text(encoding='utf-8'))

    def test_approved_existing_condition_with_no_intervention_matches_price_result_bytes(self):
        context = self.content(approved=True)
        active = self.create_content(context)
        baseline = self.create_content(context, name='baseline',strategy='content.price_confirmation@1')
        active_run, baseline_run = run_task(active), run_task(baseline)
        self.assertEqual(canonical_bytes(verify_run(active_run)[1]['result']), canonical_bytes(verify_run(baseline_run)[1]['result']))
        view = describe_run(active_run)
        self.assertEqual(view['research_input_outcome']['status'], 'NO_CONTENT_INTERVENTION')
        self.assertEqual(view['blocked_new_buys'], 0)
        self.assertTrue(replay_run(active_run)['replay_verified'])

    def test_binding_updated_research_creates_version_keeps_pause_old_inputs_and_report(self):
        initial = self.content()
        family = self.create_content(initial)
        original_run = run_task(family)
        change_state(family, 'PAUSED')
        before = describe_task(family)
        original = self.frozen(family, original_run)
        approved = self.content(approved=True)
        updated = bind_inputs(family, event_context=approved)
        self.assertEqual(updated['family_id'], before['family_id'])
        self.assertEqual(updated['state'], 'PAUSED')
        self.assertEqual(len(updated['revisions']), 2)
        self.assertNotEqual(updated['inputs']['research']['input_id'], before['inputs']['research']['input_id'])
        self.unchanged(original)

        early = read_document(self.examples['packet'])
        candidate = early['events'][0]
        candidate.update(first_public_at='2024-10-01T20:15:00Z', version_public_at='2024-10-01T20:15:00Z')
        candidate['candidate_hash'] = content_protocol.digest({k:v for k,v in candidate.items() if k!='candidate_hash'})
        early['packet_hash'] = content_protocol.digest({k:v for k,v in early.items() if k!='packet_hash'})
        with self.assertRaisesRegex(ValueError, 'content_pre_release_price_baseline_missing'):
            self.create_content(self.content(packet=early), name='before-coverage')
        self.assertEqual(describe_run(original_run)['fill_count'], 0)
        with self.assertRaisesRegex(ValueError, 'task_paused'): run_task(family)

    def revised_packet(self, at):
        packet = read_document(self.examples['packet'])
        child = copy.deepcopy(packet['events'][0]); child.pop('candidate_hash')
        child.update(version=2, prior_version_hash=packet['events'][0]['candidate_hash'], version_public_at=at,
            retrieved_at='2025-01-02T00:00:00Z', extraction_completed_at='2025-01-02T00:01:00Z')
        child['candidate_hash'] = content_protocol.digest(child)
        packet['events'].append(child)
        packet['packet_hash'] = content_protocol.digest({k:v for k,v in packet.items() if k!='packet_hash'})
        return packet

    def test_future_revision_does_not_change_earlier_decisions_and_known_unapproved_revision_has_no_fallback(self):
        base = self.create_content(self.content(approved=True), name='base')
        future = self.create_content(self.content(approved=True, packet=self.revised_packet('2025-01-01T00:00:00Z')), name='future')
        base_result = verify_run(run_task(base))[1]['result']
        self.assertEqual(canonical_bytes(base_result), canonical_bytes(verify_run(run_task(future))[1]['result']))
        latest = self.create_content(self.content(approved=True, packet=self.revised_packet('2024-11-07T20:00:00Z')), name='latest')
        view = describe_run(run_task(latest))
        self.assertEqual(view['fill_count'], 0)
        price_review = next(r for r in view['research_input_outcome']['reviews'] if r['price_action']=='BUY')
        self.assertEqual(price_review['known_versions'][0]['version'], 2)
        self.assertEqual(price_review['known_versions'][0]['field_review'], 'NOT_APPROVED')

    def test_security_mismatch_missing_context_and_changed_sealed_bytes_never_commit_binding(self):
        family = self.create_content(self.content())
        change_state(family, 'PAUSED')
        before = read_family(family); old = self.frozen(family)
        with self.assertRaisesRegex(ValueError, 'content_rule_requires_content_context'):
            bind_inputs(family, event_context=self.workspace/'data/event-context.json')
        with self.assertRaisesRegex(ValueError, 'schedule_rule_requires_schedule_context'):
            check_inputs(dict(strategy='event.earnings_schedule@1', snapshot=self.snapshot,
                event_context=self.content(), params=self.price['params']), location=self.root/'wrong-kind/task.json')
        packet = read_document(self.examples['packet'])
        candidate = packet['events'][0]
        candidate['security_id'] = 'SYNTHETIC:OTHER:SECURITY'
        candidate['candidate_hash'] = content_protocol.digest({k:v for k,v in candidate.items() if k!='candidate_hash'})
        packet['packet_hash'] = content_protocol.digest({k:v for k,v in packet.items() if k!='packet_hash'})
        mismatch = self.content(packet=packet)
        with self.assertRaisesRegex(ValueError, 'event_context_security_conflict'):
            bind_inputs(family, event_context=mismatch)
        with self.assertRaisesRegex(ValueError, 'event_strategy_context_required'):
            bind_inputs(family, event_context=None)
        self.assertEqual(read_family(family)['event_hash'], before['event_hash'])
        self.assertEqual(read_family(family)['state'], 'PAUSED')
        self.unchanged(old)
        corrupted = self.document('corrupted-context.json', read_document(mismatch))
        data = read_document(corrupted); data['packet']['events'][0]['facts'][0]['value'] = '999'
        corrupted.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'binding_invalid'): import_input(corrupted, self.workspace)

    def test_new_snapshot_bytes_bind_as_new_version_without_rewriting_old_source_or_run(self):
        create_family(self.family, **self.price)
        run = run_task(self.family); old = self.frozen(self.family, run, self.workspace/'data')
        resources = files('hakimi_research').joinpath('resources')
        csv = self.root/'new-source.csv'; csv.write_bytes(resources.joinpath('trade-demo.csv').read_bytes())
        metadata = json.loads(resources.joinpath('trade-demo-import.json').read_bytes())
        metadata['price_source']['name'] = 'SYNTHETIC_price_v2'
        updated = import_price_csv(csv, self.document('new-metadata.json', metadata), self.workspace)
        view = bind_inputs(self.family, snapshot=Path(updated['path']))
        self.assertEqual(len(view['revisions']), 2)
        self.assertEqual(view['inputs']['snapshot']['input_id'], updated['input_id'])
        self.assertNotEqual(view['inputs']['snapshot']['input_id'], inspect_input(self.snapshot)['input_id'])
        self.unchanged(old)
        self.assertEqual(verify_run(run)[1]['dataset']['snapshot_id'], inspect_input(self.snapshot)['input_id'])

    def test_content_original_missing_and_packet_approval_reuse_stop_with_clear_reasons(self):
        packet = read_document(self.examples['packet'])
        candidate = packet['events'][0]; candidate['raw_sha256'] = '0'*64
        candidate['candidate_hash'] = content_protocol.digest({k:v for k,v in candidate.items() if k!='candidate_hash'})
        packet['packet_hash'] = content_protocol.digest({k:v for k,v in packet.items() if k!='packet_hash'})
        missing = self.content(packet=packet)
        self.assertEqual(inspect_input(missing)['status'], 'BLOCKED')
        with self.assertRaisesRegex(ValueError, 'content_original_source_missing'):
            self.create_content(missing)
        self.content(approved=True)
        original = self.frozen(self.workspace/'data')
        changed = self.document('different-packet.json', packet)
        with self.assertRaisesRegex(ValueError, 'approval_identity'):
            import_content_packet(changed, self.workspace, event_id=self.examples['event_id'],
                texts_dir=self.examples['texts_dir'], originals_dir=self.examples['originals_dir'],
                approval=self.root/'field-review-fixture.json', synthetic=True)
        self.unchanged(original)

    def test_normal_commands_and_reopened_menu_show_catalog_bindings_and_rejections(self):
        saved = self.cli(['input-import','--workspace',self.workspace,'--file',self.workspace/'data/event-context.json'])
        self.assertEqual(saved['status'], 'OFFLINE_INPUT_RETAINED')
        catalog = self.cli(['inputs','--workspace',self.workspace])
        self.assertTrue(any(r['kind']=='SCHEDULE_CONTEXT' for r in catalog['items']))
        self.cli(['task-copy','--from-task',self.workspace/'tasks/event.json','--task',self.family])
        revised = self.cli(['task-bind','--task',self.family,'--event-context',saved['path']])
        self.assertEqual(len(revised['revisions']), 2)
        self.assertEqual(revised['inputs']['research']['input_id'], saved['input_id'])
        stopped = self.cli(['task-bind','--task',self.family,'--clear-event-context'], expected=1)
        self.assertEqual(stopped['status'], 'STOPPED')
        with patch('builtins.input', side_effect=['16','1','0','0']), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wizard(self.workspace), 0)
        self.assertIn('输入中心', output.getvalue())
        self.assertIn('SYNTHETIC:SCHEDULE:Q3', output.getvalue())

    def test_moved_workspace_replays_saved_content_and_retains_external_packet_bytes(self):
        family = self.create_content(self.content(approved=True))
        run = run_task(family); original_report = (run/'report.json').read_bytes()
        moved = self.root/'moved workspace'; shutil.copytree(self.workspace, moved)
        moved_run = moved/run.relative_to(self.workspace)
        moved_family = moved/family.relative_to(self.workspace)
        self.assertEqual(describe_task(moved_family)['task_id'], describe_task(family)['task_id'])
        self.assertEqual((moved_run/'report.json').read_bytes(), original_report)
        self.assertTrue(replay_run(moved_run)['replay_verified'])
        self.assertEqual(recover_report(moved_run).parent, moved_run)
        self.assertEqual((moved_run/'report.json').read_bytes(), original_report)
        context = read_document(Path(describe_task(moved_family)['task_file']).parent/'inputs/event-context.json')
        import base64
        self.assertEqual(base64.b64decode(context['original_inputs']['packet_base64']), (self.root/'candidate-fixture.json').read_bytes())

    def test_price_opportunity_outside_score_is_not_reported_as_content_intervention(self):
        family = self.create_content(self.content())
        from hakimi_research.task_manager import revise_family
        revise_family(family, score_start='2024-11-11')
        run = run_task(family)
        view = describe_run(run)
        self.assertEqual(view['fill_count'], 0)
        self.assertEqual(view['blocked_new_buys'], 0)
        self.assertEqual(view['research_input_outcome']['status'], 'NO_CONTENT_INTERVENTION')
        price = next(r for r in view['research_input_outcome']['reviews'] if r['price_action']=='BUY')
        self.assertEqual(price['applicability'], 'PRICE_OPPORTUNITY_OUTSIDE_SCORE_WINDOW')
        self.assertIn('PRICE_OPPORTUNITY_OUTSIDE_SCORE_WINDOW', recover_report(run).read_text(encoding='utf-8'))
