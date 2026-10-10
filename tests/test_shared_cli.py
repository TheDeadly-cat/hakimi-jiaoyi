"""User entries, explicit receipt lookup and movable account identity."""
from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from hakimi_research.trade_cli import main,wizard


class SharedCliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def call(self,*args,expected=0):
        out=io.StringIO()
        with redirect_stdout(out):status=main(list(map(str,args)))
        value=json.loads(out.getvalue());self.assertEqual(status,expected,value);return value
    def test_cold_commands_share_tasks_lookup_cancel_and_refuse_retry(self):
        demo=self.call('shared-demo','--directory',self.root/'demo');account=demo['account'];at=demo['at']
        r=self.call('shared-step','--account',account,'--operation-id','first','--at',at,'--task',demo['tasks'][0],'--task',demo['tasks'][1])
        self.assertEqual([d['status'] for d in r['outcome']['decisions']],['RESERVED','REJECTED'])
        self.assertEqual(self.call('shared-receipt','--account',account,'--operation-id','first')['receipt'],r)
        self.assertEqual(self.call('shared-receipt','--account',account,'--operation-id','absent')['status'],'NOT_RECORDED')
        intent=r['outcome']['decisions'][0]['intent_id']
        self.call('shared-cancel','--account',account,'--operation-id','cancel','--at',at,'--intent-id',intent,'--reason','offline operator cancelled')
        r=self.call('shared-step','--account',account,'--operation-id','later','--at',at,'--task',demo['tasks'][0],'--task',demo['tasks'][1])
        self.assertEqual([d['status'] for d in r['outcome']['decisions']],['DUPLICATE_SIGNAL','DUPLICATE_SIGNAL'])
        self.assertEqual(self.call('shared-show','--account',account)['reserved_cash'],'0')
    def test_menu_create_reserve_exit_reopen_and_whole_directory_copy(self):
        workspace=self.root/'user';out=io.StringIO()
        with patch('builtins.input',side_effect=['17','1','example','4','cohort','','','0','0']),redirect_stdout(out):
            self.assertEqual(wizard(workspace),0)
        text=out.getvalue();self.assertNotIn('操作停止',text);self.assertIn('预留 8000.00；可用 2000.00',text)
        account=workspace/'shared-accounts/example/account'
        before={p.relative_to(account):sha256(p.read_bytes()).hexdigest() for p in account.rglob('*') if p.is_file()}
        copy=self.root/'copied';shutil.copytree(workspace,copy)
        original=self.call('shared-show','--account',account);moved=self.call('shared-show','--account',copy/'shared-accounts/example/account')
        self.assertEqual(original,moved)
        self.assertEqual(before,{p.relative_to(account):sha256(p.read_bytes()).hexdigest() for p in account.rglob('*') if p.is_file()})
        out=io.StringIO()
        with patch('builtins.input',side_effect=['17','2','1','3','12','cohort','0','0']),redirect_stdout(out):wizard(copy)
        self.assertNotIn('操作停止',out.getvalue());self.assertIn('已提交：',out.getvalue())
    def test_global_pause_resume_checks_and_stale_head_visible_in_cli(self):
        account=self.root/'account';v=self.call('shared-init','--account',account,'--demo');at=v['state']['current_at']
        self.call('shared-pause','--account',account,'--operation-id','pause','--at',at,'--reason','review')
        failed=self.call('shared-resume','--account',account,'--operation-id','resume','--at',at,'--expected-head',v['receipt_head'],expected=1)
        self.assertIn('current_receipt_head',failed['error'])
        head=self.call('shared-show','--account',account)['receipt_head']
        self.call('shared-resume','--account',account,'--operation-id','resume','--at',at,'--expected-head',head)
        self.assertFalse(self.call('shared-show','--account',account)['state']['paused'])


if __name__=='__main__':unittest.main()
