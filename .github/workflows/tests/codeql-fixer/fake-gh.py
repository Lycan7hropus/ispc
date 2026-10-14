#!/usr/bin/env python3
"""Local GitHub API fixture. Never connects to GitHub."""
import json, os, subprocess, sys
from pathlib import Path

args = sys.argv[1:]
if not args or args.pop(0) != 'api':
    raise SystemExit('Only fixture gh api is supported')
endpoint = next(a for a in args if a.startswith('repos/'))
method = args[args.index('-X') + 1] if '-X' in args else 'GET'
state_path = Path(os.environ['FIXTURE_STATE'])
state = json.loads(state_path.read_text())
route = endpoint.split('/', 3)[3].split('?')[0]
body = json.load(sys.stdin) if '--input' in args else {}
fields = {}
for i, a in enumerate(args):
    if a == '-f':
        k, v = args[i + 1].split('=', 1)
        fields[k] = v
state.setdefault('calls', []).append([method, route])
status = 0
if route == 'pulls':
    data = state.get('pulls', [])
elif route.startswith('git/matching-refs'):
    data = [{'ref': 'refs/heads/codeql/fixes', 'object': {'sha': state['branch_sha']}}] if state.get('branch_sha') else []
elif route == 'commits/main':
    data = {'sha': state['base_sha']}
elif route.startswith('compare/'):
    data = {'files': [{'filename': p} for p in state.get('changed_files', [])]} if route.endswith('...main') else {'commits': [{'commit': {'message': m}} for m in state.get('commit_messages', [])]}
elif route == 'issues' and method == 'GET':
    data = [i for i in state.get('issues', []) if i['state'] == 'open' and i['user']['login'] == 'github-actions[bot]']
elif route == 'issues' and method == 'POST':
    data = {**body, 'number': 1000 + len(state.get('issues', [])), 'state': 'open', 'user': {'login': 'github-actions[bot]'}}
    state.setdefault('issues', []).append(data)
elif route == 'labels/codeql-unsure':
    data = {}
    status = 0 if state.get('label_exists') else 1
elif route == 'labels' and method == 'POST':
    state['label_exists'] = True
    data = fields
elif route == 'code-scanning/alerts':
    data = [a for a in state['alerts'] if a['state'] == 'open']
elif route.startswith('code-scanning/alerts/'):
    number = int(route.rsplit('/', 1)[1])
    data = next(a for a in state['alerts'] if a['number'] == number)
    if method == 'PATCH':
        if state.get('patch_error'):
            status = 1
        elif not state.get('ignore_patch'):
            data.update(body)
else:
    raise SystemExit('Unsupported fixture route: ' + endpoint)
state_path.write_text(json.dumps(state))
if status:
    print('Fixture API refused the request', file=sys.stderr)
    raise SystemExit(status)
if '--jq' in args:
    result = subprocess.run(['jq', '-r', args[args.index('--jq') + 1]], input=json.dumps(data), text=True, capture_output=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)
print(json.dumps(data))
