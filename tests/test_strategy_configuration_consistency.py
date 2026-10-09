"""Configuration admission and legacy semantics, independent of BUY occurrence."""
import csv
import base64
import io
import json
from copy import deepcopy
from contextlib import redirect_stdout
from importlib.resources import files
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research import offline_app
from hakimi_research.documents import read_document
from hakimi_research.equity_dataset import build_equity_snapshot,save_equity_snapshot
from hakimi_research.offline_app import check_task,run_task,verify_run
from hakimi_research.task_manager import create_family,revise_family,read_family,change_state,version_options,describe_task
from hakimi_research.trade_cli import (initialize_demo,create_task,configuration_form,configuration_view,
    validate_configuration,default_risk,main,wizard)


class StrategyConfigurationConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hakimi-config-consistency-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.workspace=self.root/'workspace'
        initialize_demo(self.workspace)

    def options(self,key='price'):
        options=version_options(self.workspace/'tasks'/(key+'.json'))
        options['params']=dict(options['params']);options['params'].pop('take_profit_pct')
        return options

    def form(self,options,answers=None):
        with patch('builtins.input',side_effect=answers,return_value=''),redirect_stdout(io.StringIO()):
            return configuration_form(options)

    def cli(self,args,status=0):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(args),status,output.getvalue())
        return json.loads(output.getvalue())

    def test_legacy_blank_copy_preserves_omission_and_effective_defaults_for_both_adapters(self):
        for key in ['price','event']:
            with self.subTest(key=key):
                options=self.options(key)
                legacy=self.workspace/'tasks'/('partial-'+key+'.json')
                create_task(legacy,**options);original=legacy.read_bytes()
                effective=describe_task(legacy)['configuration']['effective']
                self.assertEqual(effective['take_profit_pct'],.08)
                unchanged=self.form(version_options(legacy))
                self.assertEqual(unchanged['params'],options['params'])
                copied=self.workspace/'tasks'/('copied-'+key)
                create_family(copied,**unchanged)
                self.assertEqual(describe_task(copied)['configuration']['effective'],effective)
                self.assertEqual(legacy.read_bytes(),original)

    def test_blank_managed_edit_and_cash_only_revision_keep_rules_and_old_report(self):
        for key in ['price','event']:
            with self.subTest(key=key):
                family=self.workspace/'tasks'/('managed-'+key)
                options=self.options(key);create_family(family,**options)
                first=check_task(family);task_bytes=first['task_path'].read_bytes()
                folder=run_task(family);report_bytes=(folder/'report.json').read_bytes()
                if key=='price':
                    buys=[r for r in verify_run(folder)[1]['result']['signals'] if r['action']=='BUY']
                    self.assertTrue(buys);self.assertTrue(all(r['requested_take_profit_pct']==.08 for r in buys))
                revise_family(family,**self.form(version_options(family)))
                self.assertEqual(check_task(family)['semantics']['experiment']['strategy'],first['semantics']['experiment']['strategy'])
                form=['']*15;form[10]='12000'
                if key=='event':form.append('')
                revised=self.form(version_options(family),form)
                revise_family(family,**revised)
                after=check_task(family)['semantics']['experiment']
                before=first['semantics']['experiment']
                self.assertEqual({k:v for k,v in after.items() if k!='initial_cash'},
                    {k:v for k,v in before.items() if k!='initial_cash'})
                self.assertEqual(after['initial_cash'],12000)
                self.assertEqual(describe_task(family)['configuration']['effective']['take_profit_pct'],.08)
                self.assertEqual(first['task_path'].read_bytes(),task_bytes)
                self.assertEqual((folder/'report.json').read_bytes(),report_bytes)

    def test_explicit_protection_edit_and_explicit_eight_percent_survive_new_template_six(self):
        for key in ['price','event']:
            options=self.options(key)
            explicit=deepcopy(options);explicit['params']['take_profit_pct']=.08
            self.assertEqual(self.form(explicit)['params']['take_profit_pct'],.08)
            answers=['']*15;answers[5]='.09'
            if key=='event':answers.append('')
            changed=self.form(options,answers)
            self.assertEqual(changed['params']['take_profit_pct'],.09)
            self.assertEqual({k:v for k,v in changed['params'].items() if k!='take_profit_pct'},options['params'])
        new=self.form(dict(snapshot=self.options()['snapshot']))
        self.assertEqual(new['params']['take_profit_pct'],.06)

    def test_illegal_signal_numbers_and_types_are_rejected_before_creation(self):
        invalid=[0,-.1,1.1,float('nan'),float('inf'),float('-inf'),'0.03',True,None]
        for key in ['price','event']:
            options=version_options(self.workspace/'tasks'/(key+'.json'))
            for parameter in ['stop_loss_pct','take_profit_pct','position_pct']:
                for value in invalid:
                    if parameter=='position_pct' and value==0 and type(value) is int:continue
                    with self.subTest(adapter=key,parameter=parameter,value=value):
                        params=dict(options['params'],**{parameter:value})
                        destination=self.root/'invalid-task.json'
                        with patch.object(offline_app,'run_strategy',side_effect=AssertionError('must not simulate')):
                            with self.assertRaises((ValueError,TypeError)):create_task(destination,**dict(options,params=params))
                        self.assertFalse(destination.exists())

    def test_risk_snapshot_strict_bounds_reject_before_managed_version_commit(self):
        options=self.options()
        for i,parameter in enumerate(['max_position_pct','max_single_loss_pct','max_daily_loss_pct']):
            for j,value in enumerate([0,-.1,1.1,float('nan'),float('inf'),'0.1',True,None]):
                family=self.workspace/'tasks'/f'valid-{i}-{j}';create_family(family,**options)
                change_state(family,'PAUSED');before=read_family(family)
                with self.subTest(parameter=parameter,value=value):
                    risk=dict(options['risk'],**{parameter:value})
                    with patch.object(offline_app,'run_strategy',side_effect=AssertionError('must not simulate')):
                        with self.assertRaises((ValueError,TypeError)):revise_family(family,risk=risk)
                    view=read_family(family)
                    self.assertEqual(view['event_hash'],before['event_hash']);self.assertEqual(view['state'],'PAUSED')
                    self.assertEqual(view['selected_revision'],before['selected_revision']);self.assertEqual(len(view['revisions']),1)

    def test_legal_model_boundaries_and_zero_allocation_are_not_replaced_or_rejected(self):
        options=self.options()
        for position in [0,1]:
            params=dict(options['params'],position_pct=position,stop_loss_pct=1,take_profit_pct=1)
            risk=dict(options['risk'],max_position_pct=1,max_single_loss_pct=1,max_daily_loss_pct=1,min_cash_pct=0)
            task=self.root/('boundary-'+str(position)+'.json')
            create_task(task,**dict(options,params=params,risk=risk))
            view=check_task(task)
            self.assertEqual(view['semantics']['experiment']['strategy']['params'],params)
            self.assertEqual(view['semantics']['experiment']['risk'],risk)
        tiny=dict(options['params'],position_pct=0,stop_loss_pct=1e-10,take_profit_pct=1e-10)
        risk=dict(options['risk'],max_position_pct=1e-10,max_single_loss_pct=1e-10,max_daily_loss_pct=1e-10,min_cash_pct=1)
        create_task(self.root/'tiny.json',**dict(options,params=tiny,risk=risk))

    def test_previous_hash_valid_managed_inputs_cannot_bypass_new_numeric_check(self):
        # Reproduce the former producer's missing admission gate in a new
        # synthetic fixture; no historical report or approved record is edited.
        options=self.options()
        for name,changes in [('bad-stop',dict(params=dict(options['params'],stop_loss_pct=0))),
                ('bad-target',dict(params=dict(options['params'],take_profit_pct=1.1))),
                ('bad-position',dict(params=dict(options['params'],position_pct=-.1))),
                ('bad-daily',dict(risk=dict(options['risk'],max_daily_loss_pct=0)))]:
            family=self.workspace/'tasks'/name
            with patch('hakimi_research.trade_cli.validate_configuration',return_value=None):
                # On the repaired code, patch its input-only helper as well.
                with patch('hakimi_research.trade_cli.validate_runtime_configuration',return_value=None,create=True):
                    create_family(family,**dict(options,**changes))
            before=read_family(family)['event_hash']
            with patch.object(offline_app,'run_strategy',side_effect=AssertionError('must not simulate')):
                with self.assertRaises(ValueError):check_task(family)
            self.assertEqual(read_family(family)['event_hash'],before)

    def test_no_signal_and_signal_snapshots_share_early_validation_without_a_backtest(self):
        resources=files('hakimi_research').joinpath('resources')
        parsed=list(csv.DictReader(io.StringIO(resources.joinpath('trade-demo.csv').read_text(encoding='utf-8'))))
        for row in parsed:
            for field in ['open','high','low','close']:row[field]='100'
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(parsed[0]));writer.writeheader();writer.writerows(parsed)
        raw=stream.getvalue().encode()
        metadata=json.loads(resources.joinpath('trade-demo-import.json').read_bytes())
        metadata['price_source'].update(reference='urn:synthetic:configuration:constant-price',raw_base64=base64.b64encode(raw).decode())
        snapshot=build_equity_snapshot(raw,metadata)
        no_signal=save_equity_snapshot(snapshot,self.workspace/'data/constant')
        options=self.options()
        valid=self.root/'constant-valid.json';create_task(valid,**dict(options,snapshot=no_signal))
        result=verify_run(run_task(valid))[1]['result']
        self.assertEqual(result['fill_count'],0);self.assertTrue(all(r['action']=='HOLD' for r in result['signals']))
        for source in [options['snapshot'],no_signal]:
            for parameter,value in [('stop_loss_pct',0),('take_profit_pct',0),('position_pct',-.1)]:
                with self.subTest(snapshot=str(source),parameter=parameter):
                    destination=self.root/'bad-signal-independent.json'
                    with patch.object(offline_app,'run_strategy',side_effect=AssertionError('must not simulate')):
                        with self.assertRaises(ValueError):create_task(destination,**dict(options,snapshot=source,params=dict(options['params'],**{parameter:value})))
                    self.assertFalse(destination.exists())

    def test_cli_partial_copy_cash_revision_and_numeric_rejection_preserve_old_selection(self):
        options=self.options();legacy=self.workspace/'tasks/legacy-partial.json';create_task(legacy,**options)
        family=self.workspace/'tasks/cli-managed'
        self.cli(['task-copy','--from-task',str(legacy),'--task',str(family)])
        self.cli(['task-revise','--task',str(family),'--initial-cash','14000'])
        self.assertEqual(describe_task(family)['configuration']['effective']['take_profit_pct'],.08)
        before=read_family(family)
        bad=self.root/'bad-params.json';bad.write_text(json.dumps(dict(options['params'],take_profit_pct=0)),encoding='utf-8')
        self.cli(['task-revise','--task',str(family),'--parameters',str(bad)],1)
        self.cli(['task-copy','--from-task',str(legacy),'--task',str(self.workspace/'tasks/bad-copy'),'--parameters',str(bad)],1)
        self.assertEqual(read_family(family)['event_hash'],before['event_hash'])
        self.assertFalse((self.workspace/'tasks/bad-copy').exists())

    def test_wizard_legacy_copy_blank_edit_and_cash_only_edit_preserve_eight_percent(self):
        for key,event in [('price',False),('event',True)]:
            self.workspace=self.root/('wizard-'+key);initialize_demo(self.workspace)
            with self.subTest(adapter=key):
                options=self.options(key);legacy=self.workspace/'tasks/partial.json';create_task(legacy,**options)
                # Sorted event, partial, price; use the partial task in both cases.
                inputs=['13','2','3']+['']*(16 if event else 15)+['wizard-copy','13','4','2']
                form=['']*(16 if event else 15);form[10]='15000'
                inputs+=form+['0']
                with patch('builtins.input',side_effect=inputs),redirect_stdout(io.StringIO()) as stream:
                    self.assertEqual(wizard(self.workspace),0)
                family=self.workspace/'tasks/wizard-copy'
                self.assertEqual(len(read_family(family)['revisions']),2)
                effective=describe_task(family)['configuration']['effective']
                self.assertEqual(effective['initial_cash'],15000);self.assertEqual(effective['take_profit_pct'],.08)

    def test_complete_configuration_check_uses_runtime_bounds_before_any_signal(self):
        spec=read_document(self.workspace/'tasks/price.json')['experiment']
        for field,value in [('stop_loss_pct',0),('take_profit_pct',0),('position_pct',-.1),('max_daily_loss_pct',0)]:
            altered=deepcopy(spec)
            (altered['risk'] if field.startswith('max_') else altered['strategy']['params'])[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_configuration(altered)


if __name__=='__main__':unittest.main()
