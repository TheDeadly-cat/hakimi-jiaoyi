"""Local graphical entry over the existing offline research kernel.

Only loopback HTTP is exposed. A per-process secret is carried in the browser
fragment, never in access logs; every API request needs the corresponding header.
Economic operations run once in a serial worker, with a durable request first.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sys
from threading import RLock, Thread
from urllib.parse import unquote, urlsplit
import webbrowser

MAX_REQUEST = 24 * 1024 * 1024
REQUEST_ID = re.compile(r'[A-Za-z0-9_-]{16,80}\Z')


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')


def atomic_json(path, value):
    """UI control state only; never used to overwrite task/report/ledger files."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '-' + secrets.token_hex(8))
    with temporary.open('xb') as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def control_directory(workspace):
    workspace = Path(workspace).resolve()
    key = sha256(str(workspace).encode('utf-8')).hexdigest()[:20]
    return workspace.parent / '.hakimi-ui' / key


def error_view(error):
    detail = str(error)
    translations = {
        'warmup': '行情长度不足以完成策略预热。请增加数据，或明确调整参数。',
        'paused': '任务已暂停。请先启用任务再运行。',
        'source': '来源或版本校验未通过，请查看详细原因。',
        'calendar': '交易日历未通过校验。请核对缺失交易日和休市说明。',
        'outside': '所选文件不在当前工作区中。请通过导入数据操作添加文件。',
        'not_found': '记录不存在。请刷新列表后重新选择。',
        'permission': '无法访问文件。请检查目录权限，并保留现有数据。',
    }
    message = next((value for key, value in translations.items() if key in detail.lower()),
        '操作未完成，请核对输入和下方具体原因。')
    return {'code': type(error).__name__, 'message': message, 'detail': detail[:4000]}


class Jobs:
    def __init__(self, service, directory):
        self.service = service
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='hakimi-offline')
        self.lock = RLock()
        self.live = set()

    def submit(self, action, payload, request_id):
        if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
            raise ValueError('invalid_request_id')
        if not isinstance(action, str) or not re.fullmatch(r'[a-z_]{2,40}', action):
            raise ValueError('invalid_action')
        if not isinstance(payload, dict):
            raise ValueError('payload_must_be_object')
        fingerprint = sha256(encode({'action':action,'payload':payload})).hexdigest()
        path = self.directory / (request_id + '.json')
        with self.lock:
            if path.exists():
                try:
                    previous = json.loads(path.read_bytes())
                    previous_fingerprint = previous['request_sha256']
                except (OSError,ValueError,KeyError,TypeError) as error:
                    raise ValueError('operation_record_unreadable_no_retry:原操作记录不完整，已保留；请查看结果，不要重新提交。') from error
                if previous_fingerprint != fingerprint:
                    raise ValueError('request_id_conflict:请保留原操作编号，不要用它提交不同内容')
                return self.get(request_id)
            record = {'job_id':request_id,'action':action,'request_sha256':fingerprint,
                'status':'queued','created_at':now(),'updated_at':now(),
                'message':'等待执行','automatic_retry':False}
            # Request payload is retained before dispatch, including imported bytes.
            with path.open('xb') as stream:
                stream.write(encode({**record,'request':payload}))
                stream.flush()
                os.fsync(stream.fileno())
            self.live.add(request_id)
            self.executor.submit(self._run, request_id, action, payload)
            return record

    def _run(self, request_id, action, payload):
        path = self.directory / (request_id + '.json')
        record = None
        dispatched = False
        try:
            with self.lock:
                candidate = json.loads(path.read_bytes())
            if (not isinstance(candidate, dict) or candidate.get('job_id') != request_id
                    or candidate.get('action') != action or candidate.get('status') != 'queued'
                    or candidate.get('automatic_retry') is not False
                    or candidate.get('request_sha256') != sha256(encode({'action':action,'payload':payload})).hexdigest()
                    or 'request' not in candidate or encode(candidate['request']) != encode(payload)):
                raise ValueError('queued_job_record_invalid_no_dispatch')
            # Only a validated record may be updated. Unreadable or changed
            # request bytes remain intact for review, even before dispatch.
            record = candidate
            record.update(status='running',message='正在处理，请勿重复提交',updated_at=now())
            with self.lock:
                atomic_json(path, record)
            dispatched = True
            result = self.service.mutate(action, payload)
            record.update(status='succeeded',message='已完成',result=result,updated_at=now())
            with self.lock:
                atomic_json(path, record)
        except Exception as error:
            logging.exception('Offline action failed: %s', action)
            if record is None:
                return
            record.update(status='unknown' if dispatched else 'failed',
                message='执行结果需要核对。请先查看任务和结果记录，不要重复提交。' if dispatched else '尚未执行，无法记录操作请求。',
                error=error_view(error),updated_at=now())
            try:
                with self.lock:
                    atomic_json(path, record)
            except OSError:
                # A result which could not be recorded stays unknown, not retried.
                logging.exception('Cannot publish job result; retain request for review')
        finally:
            with self.lock:
                self.live.discard(request_id)

    def get(self, request_id):
        with self.lock:
            return self._get_locked(request_id)

    def _get_locked(self, request_id):
        if not REQUEST_ID.fullmatch(request_id):
            raise ValueError('invalid_job_id')
        path = self.directory / (request_id + '.json')
        if not path.is_file():
            raise FileNotFoundError('job_not_found')
        try:
            record = json.loads(path.read_bytes())
            if not isinstance(record,dict) or record.get('job_id') != request_id or record.get('status') not in {
                    'queued','running','succeeded','failed','unknown'}:
                raise ValueError('invalid_job_record')
        except (OSError,ValueError,TypeError):
            return {'job_id':request_id,'status':'unknown','action':'unknown',
                'message':'原操作记录不完整，文件已保留。请先检查任务和结果，系统不会自动重试。',
                'automatic_retry':False,'record_readable':False}
        record.pop('request', None)
        if record['status'] in {'queued','running'} and request_id not in self.live:
            record.update(status='unknown',message='上次操作未留下完整结果。请先查看任务和结果记录；系统不会自动重试。')
        return record

    def list(self):
        paths = sorted(self.directory.glob('*.json'), key=lambda path:path.stat().st_mtime, reverse=True)
        return {'items':[self.get(path.stem) for path in paths[:30]]}

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=False)


class DesktopServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, workspace, *, port=0, service=None, token=None, control=None):
        if service is None:
            from .desktop_service import DesktopService
            service = DesktopService(workspace)
        self.workspace = Path(workspace).resolve()
        self.control = Path(control) if control else control_directory(self.workspace)
        self.token = token or secrets.token_urlsafe(32)
        self.instance_id = secrets.token_hex(16)
        from .source_identity import package_content_identity
        self.source_sha256 = package_content_identity(Path(__file__).parent)['content_sha256']
        self.service = service
        self.jobs = Jobs(service, self.control/'jobs')
        super().__init__(('127.0.0.1',port), DesktopHandler)

    @property
    def origin(self):
        return 'http://127.0.0.1:' + str(self.server_port)

    @property
    def launch_url(self):
        return self.origin + '/#token=' + self.token

    def server_close(self):
        super().server_close()
        self.jobs.close()


class DesktopHandler(BaseHTTPRequestHandler):
    server_version = 'HakimiOffline'

    def log_message(self, format, *args):
        # Do not record query strings, tokens or upload contents.
        logging.info('Local HTTP %s', getattr(self,'command',''))

    def send(self, code, body, content_type='application/json; charset=utf-8', *, nonce=None):
        self.send_response(code)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy', "default-src 'none'; connect-src 'self'; img-src 'self' data:; "
            "style-src 'unsafe-inline'; script-src " + ("'nonce-"+nonce+"'" if nonce else "'none'")
            + "; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def answer(self, value, code=200):
        self.send(code,encode({'ok':True,'data':value}))

    def fail(self, error, code=400):
        self.send(code,encode({'ok':False,'error':error_view(error)}))

    def boundary(self, authenticated=True):
        if self.headers.get_all('Host',[]) != [self.server.origin.removeprefix('http://')]:
            raise PermissionError('host_not_allowed')
        origins = self.headers.get_all('Origin', [])
        if origins and origins != [self.server.origin]:
            raise PermissionError('origin_not_allowed')
        if self.headers.get('Sec-Fetch-Site','') not in {'','none','same-origin'}:
            raise PermissionError('cross_site_request_rejected')
        if authenticated:
            tokens = self.headers.get_all('X-Hakimi-Token',[])
            if len(tokens) != 1 or not secrets.compare_digest(tokens[0], self.server.token):
                raise PermissionError('session_token_required:请从桌面入口重新打开窗口')

    def do_GET(self):
        try:
            path = urlsplit(self.path).path
            self.boundary(authenticated=path not in {'/','/health','/favicon.ico'})
            if path == '/':
                nonce = secrets.token_urlsafe(20)
                html = files('hakimi_terminal_research').joinpath('resources/desktop.html').read_bytes()
                html = html.replace(b'<script>',('<script nonce="'+nonce+'">').encode('ascii'))
                self.send(200,html,'text/html; charset=utf-8',nonce=nonce)
            elif path == '/health':
                self.answer({'status':'ready','instance_id':self.server.instance_id,
                    'source_sha256':self.server.source_sha256})
            elif path == '/favicon.ico':
                self.send(204,b'','image/x-icon')
            elif path == '/api/jobs':
                self.answer(self.server.jobs.list())
            elif path.startswith('/api/jobs/'):
                self.answer(self.server.jobs.get(unquote(path.removeprefix('/api/jobs/'))))
            elif path.startswith('/api/'):
                resource, _, identity = path.removeprefix('/api/').partition('/')
                result = self.server.service.read(resource, unquote(identity) if identity else None)
                if resource == 'status' and isinstance(result,dict):
                    result.update(log_path=str(self.server.control/'desktop.log'),
                        session={'instance_id':self.server.instance_id,'offline':True})
                self.answer(result)
            else:
                self.fail(ValueError('route_not_found'),404)
        except PermissionError as error:
            self.fail(error,403)
        except FileNotFoundError as error:
            self.fail(error,404)
        except (ValueError,TypeError,KeyError,OSError) as error:
            self.fail(error)
        except Exception as error:
            logging.exception('Local read failed')
            self.fail(error,500)

    def do_POST(self):
        try:
            self.boundary()
            path = urlsplit(self.path).path
            if self.headers.get_all('Origin',[]) != [self.server.origin]:
                raise PermissionError('exact_origin_required')
            if path == '/api/shutdown':
                if self.server.jobs.live:
                    self.fail(ValueError('operations_in_progress:请等待当前操作结束后退出'),409)
                    return
                self.answer({'status':'closing'})
                Thread(target=self.server.shutdown,daemon=True).start()
                return
            if not path.startswith('/api/actions/'):
                self.fail(ValueError('route_not_found'),404)
                return
            if self.headers.get('Content-Type','').split(';')[0].strip() != 'application/json':
                raise ValueError('json_content_type_required')
            lengths = self.headers.get_all('Content-Length',[])
            if len(lengths) != 1 or not lengths[0].isdigit() or self.headers.get('Transfer-Encoding'):
                raise ValueError('valid_content_length_required')
            length = int(lengths[0])
            if not 0 < length <= MAX_REQUEST:
                self.fail(ValueError('request_too_large:上传文件请控制在16MB以内'),413)
                return
            self.connection.settimeout(20)
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError('incomplete_request')
            payload = json.loads(body, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('finite_json_required')))
            if not isinstance(payload,dict):
                raise ValueError('request_object_required')
            job = self.server.jobs.submit(path.removeprefix('/api/actions/'),payload.get('payload',{}),payload.get('request_id'))
            self.answer(job,202)
        except PermissionError as error:
            self.fail(error,403)
        except (ValueError,TypeError,KeyError,OSError) as error:
            self.fail(error)
        except Exception as error:
            logging.exception('Local submission failed')
            self.fail(error,500)


class InstanceLock:
    def __init__(self,path):
        self.stream = Path(path).open('a+b')
        if self.stream.tell() == 0:
            self.stream.write(b'0'); self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise RuntimeError('workspace_already_open:这个工作区已有图形服务运行，请使用现有窗口。')

    def close(self):
        self.stream.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='哈基米离线量化图形界面')
    parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--ready-file',type=Path)
    parser.add_argument('--launch-id',default=None)
    args = parser.parse_args(argv)
    control = control_directory(args.workspace)
    control.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=control/'desktop.log',encoding='utf-8',level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s')
    instance_lock = InstanceLock(control/'server.lock')
    server = DesktopServer(args.workspace,port=args.port,control=control)
    record = {'schema_version':'hakimi-desktop-session-v1','pid':os.getpid(),'created_at':now(),
        'origin':server.origin,'url':server.launch_url,'instance_id':server.instance_id,
        'source_sha256':server.source_sha256,
        'launch_id':args.launch_id,
        'workspace':str(server.workspace),'log':str(control/'desktop.log')}
    ready_file = args.ready_file or control/'session.json'
    atomic_json(ready_file,record)
    if not args.no_browser:
        Thread(target=lambda:webbrowser.open(server.launch_url),daemon=True).start()
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        instance_lock.close()


if __name__ == '__main__':
    main()
