"""HTTP privacy and validation regression gate for three-resident V7 telemetry.

The host is imported only after LOCALAPPDATA points at this test's owned temp
directory. No native observer, live connection, credentials, or player is used.
The existing host/auth/range gate is also run unchanged in an isolated child.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--report', type=Path)
args = parser.parse_args()
started = time.monotonic()
cases = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    cases.append(name)


def run():
    with tempfile.TemporaryDirectory(prefix='resort-v7-host-') as temporary:
        owned = Path(temporary).resolve()
        original_local = os.environ.get('LOCALAPPDATA')
        os.environ['LOCALAPPDATA'] = str(owned / 'local')
        try:
            spec = importlib.util.spec_from_file_location('resort_v7_test_host', ROOT / 'wallpaper/server.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            if original_local is None:
                os.environ.pop('LOCALAPPDATA', None)
            else:
                os.environ['LOCALAPPDATA'] = original_local
        check('host data isolated before import', module.DATA.is_relative_to(owned))
        check('test did not create a connection credential', not (module.DATA / 'connection.json').exists())

        server = module.ThreadingHTTPServer(('127.0.0.1', 0), module.Handler)
        server.token = 'synthetic-v7-test-only'
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'

        def request(path, payload=None, *, body=None, origin=True, headers=None, method=None):
            if payload is not None:
                body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
            head = dict(headers or {})
            if origin is True:
                head['Origin'] = base
            elif isinstance(origin, str):
                head['Origin'] = origin
            req = urllib.request.Request(base + path, data=body, headers=head, method=method)
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as response:
                return response.code, response.read()

        def recorded():
            code, body = request('/bench-metrics', origin=False)
            check('sanitized telemetry GET succeeds', code == 200)
            return json.loads(body)

        good = {
            'format': 'video', 'state': 'idle', 'position': [-1.42, -1.865, .66],
            'transition': {'kind': 'lie', 'elapsed': .5},
            'actors': [
                {'key': 'claude', 'state': 'idle', 'position': [-1.42, -1.865, .66], 'activity': 'sit'},
                {'key': 'codex', 'state': 'done', 'position': [0, -1.865, .7034], 'activity': 'scratch'},
                {'key': 'apps', 'state': 'working', 'position': [1.2, -1.1, .43], 'activity': 'work'},
            ],
        }
        try:
            status, _ = request('/bench-metrics', good)
            check('three unique enum actors accepted', status == 200)
            check('three actors and lie transition retained exactly', recorded() == good)

            for activity in ('sit', 'stand', 'walk', 'work', 'wait', 'lie', 'rise', 'scratch', 'tea'):
                value = copy.deepcopy(good)
                for actor in value['actors']:
                    actor['activity'] = activity
                status, _ = request('/bench-metrics', value)
                check(f'enum activity {activity} accepted', status == 200)
                check(f'enum activity {activity} recorded', recorded()['actors'] == value['actors'])

            for state in sorted(module.STATES):
                value = copy.deepcopy(good)
                for actor in value['actors']:
                    actor['state'] = state
                check(f'enum actor state {state} accepted', request('/bench-metrics', value)[0] == 200)
                check(f'enum actor state {state} recorded', recorded()['actors'] == value['actors'])

            for transition in ('sit', 'stand', 'lie', 'rise'):
                for elapsed in (0, 10):
                    value = copy.deepcopy(good)
                    value['transition'] = {'kind': transition, 'elapsed': elapsed}
                    check(f'{transition} transition at {elapsed} accepted', request('/bench-metrics', value)[0] == 200)
                    check(f'{transition} transition at {elapsed} retained', recorded()['transition'] == value['transition'])
            value = copy.deepcopy(good)
            value['transition'] = None
            check('null transition accepted', request('/bench-metrics', value)[0] == 200)
            check('null transition retained', recorded()['transition'] is None)

            private = copy.deepcopy(good)
            private['privateText'] = 'synthetic conversation that must not be retained'
            private['filePath'] = 'synthetic-private-path'
            private['transition']['privateText'] = 'synthetic transition detail'
            for actor in private['actors']:
                actor.update(title='synthetic app title', command='synthetic command', token='synthetic token')
            check('unrecognized private fields do not reject valid metrics', request('/bench-metrics', private)[0] == 200)
            check('top-level, actor and transition private fields discarded', recorded() == good)

            value = copy.deepcopy(good)
            value['actors'][0]['position'] = [-100, 100, 0]
            check('bounded actor coordinates at limits accepted', request('/bench-metrics', value)[0] == 200)
            check('coordinate limits retained', recorded()['actors'][0]['position'] == [-100, 100, 0])

            # Every rejection must preserve the last accepted snapshot. This
            # also catches partially updated BENCH state on a later actor error.
            baseline = recorded()

            def rejected(name, payload=None, **kwargs):
                code, _ = request('/bench-metrics', payload, **kwargs)
                check(name + ' returns 400', code == 400)
                check(name + ' does not mutate accepted metrics', recorded() == baseline)

            malformed_actors = [None, {}, 'synthetic private text', [], good['actors'][:2], good['actors'] + [good['actors'][0]]]
            for index, actors in enumerate(malformed_actors):
                value = copy.deepcopy(good)
                value['actors'] = actors
                rejected(f'malformed actor collection {index}', value)
            for bad in (None, [], 3, 'synthetic private actor'):
                value = copy.deepcopy(good)
                value['actors'][2] = bad
                rejected(f'malformed actor object {type(bad).__name__}', value)
            value = copy.deepcopy(good)
            value['actors'][2]['key'] = 'claude'
            rejected('duplicate actor key', value)
            for field, bad in [('key', 'unknown-app'), ('key', 'synthetic-private-title'),
                               ('state', 'synthetic-private-command'), ('activity', 'synthetic-private-command'),
                               ('activity', None), ('activity', {}), ('activity', 1)]:
                value = copy.deepcopy(good)
                value['actors'][2][field] = bad
                rejected(f'invalid actor {field} {type(bad).__name__} {str(bad)[:20]}', value)
            for field in ('key', 'state', 'position', 'activity'):
                value = copy.deepcopy(good)
                del value['actors'][2][field]
                rejected(f'missing actor {field}', value)
            for index, position in enumerate(([], [1, 2], [1, 2, 3, 4], None, {},
                                               ['1', 2, 3], [101, 0, 0], [0, -101, 0],
                                               [0, 0, float('nan')], [float('inf'), 0, 0],
                                               [0, float('-inf'), 0], [1e100, 0, 0])):
                value = copy.deepcopy(good)
                value['actors'][2]['position'] = position
                rejected(f'invalid actor position {index}', value)
            for transition in ('private text', [], {'kind': 'unknown', 'elapsed': 0},
                               {'kind': 'lie'}, {'kind': 'rise', 'elapsed': -.01},
                               {'kind': 'lie', 'elapsed': 10.01},
                               {'kind': 'rise', 'elapsed': float('nan')},
                               {'kind': 'lie', 'elapsed': float('inf')}):
                value = copy.deepcopy(good)
                value['transition'] = transition
                rejected(f'invalid transition {len(cases)}', value)
            for body in (b'{broken', b'[]', b'null', b'42', b'"private text"'):
                rejected(f'malformed JSON {body[:12]!r}', body=body)
            for length in ('-1', 'not-a-number', '2049', '1000000000'):
                rejected(f'invalid Content-Length {length}', body=b'{}', headers={'Content-Length': length})
            rejected('missing request body', method='POST')

            # Boundary request is exactly 2048 bytes. Unknown padding is
            # discarded; 2049 bytes is rejected before parsing or recording.
            boundary = copy.deepcopy(good)
            boundary['padding'] = ''
            encoded = json.dumps(boundary, separators=(',', ':')).encode()
            boundary['padding'] = 'x' * (2048-len(encoded))
            encoded = json.dumps(boundary, separators=(',', ':')).encode()
            check('body-boundary fixture is exactly 2048 bytes', len(encoded) == 2048)
            check('2048-byte valid telemetry accepted', request('/bench-metrics', body=encoded)[0] == 200)
            baseline = recorded()
            check('boundary padding discarded', baseline == good)
            rejected('2049-byte telemetry', body=encoded+b' ')

            for origin in (False, 'http://localhost:'+str(server.server_port),
                           'https://127.0.0.1:'+str(server.server_port),
                           'http://127.0.0.1:'+str(server.server_port+1),
                           'https://synthetic.invalid', 'null'):
                code, _ = request('/bench-metrics', good, origin=origin)
                check(f'foreign or missing Origin {origin} rejected', code == 403)
                check(f'foreign or missing Origin {origin} preserves snapshot', recorded() == baseline)
            check('host data remains credential-free', not (module.DATA/'connection.json').exists())
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)
        check('in-process host thread exited', not worker.is_alive())

        child_env = os.environ.copy()
        child_env['LOCALAPPDATA'] = str(owned/'legacy-local')
        legacy = subprocess.run([sys.executable, str(ROOT/'tests/check_resort_host.py')],
                                env=child_env, capture_output=True, text=True, timeout=45)
        check('unchanged baseline host/auth/range gate passes', legacy.returncode == 0)
        check('unchanged baseline gate reports PASS', 'PASS loopback host' in legacy.stdout)
        return {'status': 'PASS', 'checks': len(cases), 'checksDetail': cases,
                'isolatedData': True, 'nativeObserverStarted': False,
                'legacyGate': {'exitCode': legacy.returncode, 'output': legacy.stdout.strip()},
                'hostSha256': hashlib.sha256((ROOT/'wallpaper/server.py').read_bytes()).hexdigest(),
                'seconds': round(time.monotonic()-started, 3)}


try:
    report = run()
except Exception as error:
    report = {'status': 'FAIL', 'checksCompleted': len(cases), 'checksDetail': cases,
              'failure': f'{type(error).__name__}: {error}',
              'seconds': round(time.monotonic()-started, 3)}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    raise
if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(f"PASS V7 host telemetry/privacy/origin/bounds: {report['checks']} checks; legacy host/auth/range gate unchanged")
