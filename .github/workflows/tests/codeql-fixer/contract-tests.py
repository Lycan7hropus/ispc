"""Run actual workflow Bash against API fixtures and real local Git repositories."""
import copy, json, os, shutil, subprocess, tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
SUBJECT = yaml.load((ROOT / 'subject.yml').read_text(), Loader=yaml.BaseLoader)
SHA = 'a' * 40
BRANCH = 'b' * 40
PASSED = []

def actual_script(job, name):
    return next(s['run'] for s in SUBJECT['jobs'][job]['steps'] if s.get('name') == name)

SCRIPTS = dict(select=actual_script('select-alerts', 'Select the alerts to investigate'), collect=actual_script('collect-results', 'Validate each result'), outcomes=actual_script('apply-outcomes', 'Apply the outcomes'))

def alert(n):
    return dict(number=n, state='open', rule={'id': 'test/rule'}, most_recent_instance={'ref': 'refs/heads/main', 'commit_sha': SHA, 'location': {'path': f'src/fixture-{n}.cpp', 'start_line': 10}})

def matrix(n):
    return [dict(number=i, analyzed_sha=SHA, rule='test/rule', path=f'src/fixture-{i}.cpp', line=10) for i in range(1, n+1)]

def report(n, verdict):
    return dict(alert_number=n, analyzed_sha=SHA, verdict=verdict, evidence='Fixture evidence', counterexample_checks=['Fixture check'], unresolved_fact='Fixture question' if verdict == 'unsure' else None, validation=[dict(command='fixture-only', passed=True, summary='Fixture check')] if verdict == 'bug' else [], fix_available=verdict == 'bug', execution_status='complete', error=None)

def issue(ids, state='open', legacy=False):
    return dict(number=900, title=f'[codeql-alert #{ids[0]}] legacy' if legacy else 'Grouped fixture issue', body='' if legacy else '<!-- codeql-unsure-alerts: '+json.dumps(ids,separators=(',',':'))+' -->\nFixture', state=state, user={'login': 'github-actions[bot]'})

def run(kind, state=None, selected=None, reports=None, patches=(), requested='', expect=0):
    state = copy.deepcopy(state or {'base_sha': SHA, 'alerts': []})
    with tempfile.TemporaryDirectory(prefix='fixer-contract-') as tmp:
        root = Path(tmp)
        (root / 'state.json').write_text(json.dumps(state))
        bindir = root / 'bin'; bindir.mkdir()
        gh = bindir / 'gh'; shutil.copyfile(ROOT / 'fake-gh.py', gh); gh.chmod(0o755)
        (root / 'batch').mkdir()
        if kind == 'collect':
            for r in reports or []:
                dest=root / 'results' / str(r['alert_number']); dest.mkdir(parents=True,exist_ok=True)
                (dest/'result.json').write_text(json.dumps(r))
                if r['alert_number'] in patches: (dest/'fix.patch').write_text('fixture patch\n')
        elif kind == 'outcomes':
            merged=[{**r,'alert': next(a for a in selected if a['number']==r['alert_number'])} for r in reports or []]
            (root/'batch/results.json').write_text(json.dumps(merged))
        env={**os.environ,'PATH':str(bindir)+os.pathsep+os.environ['PATH'],'FIXTURE_STATE':str(root/'state.json'),'GH_REPO':'fixture/ispc','GH_TOKEN':'fixture-token','GITHUB_SERVER_URL':'https://github.com','GITHUB_OUTPUT':str(root/'outputs'),'GITHUB_STEP_SUMMARY':str(root/'summary'),'RUN_URL':'https://github.com/fixture/ispc/actions/runs/1','REQUESTED_ALERT':requested,'MATRIX':json.dumps(selected or [])}
        result=subprocess.run(['bash','-c',SCRIPTS[kind]],cwd=root,env=env,text=True,capture_output=True)
        assert (result.returncode == 0) == (expect == 0), (kind,result.returncode,result.stdout,result.stderr)
        outputs=dict(line.split('=',1) for line in (root/'outputs').read_text().splitlines()) if (root/'outputs').exists() else {}
        batch=json.loads((root/'batch/results.json').read_text()) if (root/'batch/results.json').exists() else None
        return outputs,json.loads((root/'state.json').read_text()),batch

def check(name, fn):
    fn(); PASSED.append(name); print('PASS:',name,flush=True)

def selection_counts():
    for n in [1,6,20,50]:
        out,_,_=run('select',{'base_sha':SHA,'alerts':[alert(i) for i in range(1,n+1)]})
        assert len(json.loads(out['matrix']))==n
    run('select',{'base_sha':SHA,'alerts':[alert(i) for i in range(1,258)]},expect=1)

def selection_decisions():
    state={'base_sha':SHA,'alerts':[alert(1),alert(2)],'issues':[issue([1])]}
    out,_,_=run('select',state); assert [x['number'] for x in json.loads(out['matrix'])]==[2]
    out,_,_=run('select',state,requested='1'); assert [x['number'] for x in json.loads(out['matrix'])]==[1]
    state['issues'][0]['state']='closed'
    out,_,_=run('select',state); assert len(json.loads(out['matrix']))==2
    state['alerts'][0]['state']='dismissed'
    out,_,_=run('select',state); assert [x['number'] for x in json.loads(out['matrix'])]==[2]
    state['alerts']=[alert(1),alert(2)]; state['issues']=[issue([1],legacy=True)]
    out,_,_=run('select',state); assert [x['number'] for x in json.loads(out['matrix'])]==[2]
    state['issues']=[dict(issue([1]),title='Unrelated empty issue',body='')]
    out,_,_=run('select',state); assert len(json.loads(out['matrix']))==2
    run('select',state,requested='1; touch bad',expect=1)

def branch_selection():
    pull={'number':1,'state':'open','draft':True,'merged_at':None,'head':{'sha':BRANCH,'repo':{'full_name':'fixture/ispc'}}}
    state={'base_sha':SHA,'alerts':[alert(1),alert(2)],'branch_sha':BRANCH,'pulls':[pull]}
    for requested in ['', '1']:
        out,_,_=run('select',state,requested=requested); assert out['matrix']=='[]'
    pull['state']='closed'
    state['commit_messages']=['Fix one\n\nCodeQL-Alert: 1']
    out,_,_=run('select',state); assert [x['number'] for x in json.loads(out['matrix'])]==[2]
    out,_,_=run('select',state,requested='1'); assert out['matrix']=='[]'
    pull['merged_at']='2026-01-01T00:00:00Z'
    out,_,_=run('select',state); assert out['matrix']=='[]'
    state['branch_sha']='c'*40
    out,_,_=run('select',state); assert [x['number'] for x in json.loads(out['matrix'])]==[2]
    state.pop('branch_sha');state['pulls'][0]['merged_at']=None
    out,_,_=run('select',state); assert len(json.loads(out['matrix']))==2

def collector():
    m=matrix(10); rs=[report(i,'bug' if i<=5 else 'unsure' if i<=8 else 'false-positive') for i in range(1,11)]
    rs[4]['validation'][0]['passed']=False
    out,_,batch=run('collect',selected=m,reports=rs,patches=range(1,6))
    assert out['has_fixes']=='true' and len(batch)==10 and all(x['execution_status']=='complete' for x in batch)
    out,_,batch=run('collect',selected=m,reports=rs[:-1],patches=range(1,6))
    assert out['has_fixes']=='true' and sum(x['execution_status']=='incomplete' for x in batch)==1
    out,_,batch=run('collect',selected=m,reports=[]); assert out['has_fixes']=='false' and all(x['execution_status']=='incomplete' for x in batch)
    for mutate in [lambda r:r.update(analyzed_sha='c'*40),lambda r:r.update(extra=True),lambda r:r.update(execution_status='incomplete',error='timeout'),lambda r:r.update(validation=[])]:
        r=report(1,'bug');mutate(r)
        out,_,batch=run('collect',selected=matrix(1),reports=[r],patches=[1]);assert out['has_fixes']=='false' and batch[0]['execution_status']=='incomplete'
    out,_,batch=run('collect',selected=matrix(1),reports=[report(1,'bug')]);assert out['has_fixes']=='false'

def mixed_outcomes():
    m=matrix(10);rs=[report(i,'bug' if i<=5 else 'unsure' if i<=8 else 'false-positive') for i in range(1,11)]
    state={'base_sha':SHA,'alerts':[alert(i) for i in range(1,11)]}
    _,state,_=run('outcomes',state,selected=m,reports=rs)
    assert len(state['issues'])==1 and state['issues'][0]['body'].splitlines()[0]=='<!-- codeql-unsure-alerts: [6,7,8] -->'
    assert [a['number'] for a in state['alerts'] if a['state']=='dismissed']==[9,10]
    _,again,_=run('outcomes',state,selected=m,reports=rs)
    assert len(again['issues'])==1
    state={'base_sha':SHA,'alerts':[alert(i) for i in range(1,8)]}
    _,state,_=run('outcomes',state,selected=matrix(7),reports=[report(i,'unsure') for i in range(1,8)])
    assert len(state['issues'])==1 and '[1,2,3,4,5,6,7]' in state['issues'][0]['body'].splitlines()[0]

def dismissal_guards():
    for change in ['file','rule','sha','ref','line','limit']:
        state={'base_sha':SHA,'alerts':[alert(1)]}
        if change=='file':state['changed_files']=['src/fixture-1.cpp']
        if change=='rule':state['alerts'][0]['rule']['id']='other/rule'
        if change=='sha':state['alerts'][0]['most_recent_instance']['commit_sha']='c'*40
        if change=='ref':state['alerts'][0]['most_recent_instance']['ref']='refs/heads/other'
        if change=='line':state['alerts'][0]['most_recent_instance']['location']['start_line']=11
        if change=='limit':state['changed_files']=[f'x{i}' for i in range(300)]
        _,after,_=run('outcomes',state,selected=matrix(1),reports=[report(1,'false-positive')])
        assert after['alerts'][0]['state']=='open' and not after.get('issues')
    state={'base_sha':SHA,'alerts':[alert(1)],'ignore_patch':True}
    run('outcomes',state,selected=matrix(1),reports=[report(1,'false-positive')],expect=1)

def incomplete_outcomes():
    r=report(1,'unsure');r.update(execution_status='incomplete',error='timeout')
    empty_issue=dict(issue([1]),title='Unrelated empty issue',body='')
    _,after,_=run('outcomes',{'base_sha':SHA,'alerts':[alert(1)],'issues':[empty_issue]},selected=matrix(1),reports=[r])
    assert after['issues']==[empty_issue] and after['alerts'][0]['state']=='open'

def leases():
    with tempfile.TemporaryDirectory(prefix='fixer-git-') as tmp:
        p=Path(tmp)
        def git(*args,cwd=None,ok=True):
            r=subprocess.run(['git',*args],cwd=cwd or p,text=True,capture_output=True)
            assert (r.returncode==0)==ok,(args,r.stdout,r.stderr)
            return r.stdout.strip()
        git('init','--bare','remote.git');git('init','local')
        local=p/'local';git('config','user.name','Fixture',cwd=local);git('config','user.email','fixture@example.invalid',cwd=local)
        (local/'base').write_text('base\n');git('add','base',cwd=local);git('commit','-m','Base',cwd=local)
        git('remote','add','origin',str(p/'remote.git'),cwd=local)
        git('checkout','-b','codeql/fixes',cwd=local)
        (local/'one').write_text('one\n');git('add','one',cwd=local);git('commit','-m','Fix one\n\nCodeQL-Alert: 1',cwd=local)
        first=git('rev-parse','HEAD',cwd=local)
        git('push','--force-with-lease=refs/heads/codeql/fixes:','origin','HEAD:refs/heads/codeql/fixes',cwd=local)
        (local/'two').write_text('two\n');git('add','two',cwd=local);git('commit','-m','Fix two\n\nCodeQL-Alert: 2',cwd=local)
        second=git('rev-parse','HEAD',cwd=local)
        git('merge-base','--is-ancestor',first,second,cwd=local)
        git('push','--force-with-lease=refs/heads/codeql/fixes:'+first,'origin','HEAD:refs/heads/codeql/fixes',cwd=local)
        (local/'three').write_text('three\n');git('add','three',cwd=local);git('commit','-m','Concurrent fixture',cwd=local)
        git('push','--force-with-lease=refs/heads/codeql/fixes:'+first,'origin','HEAD:refs/heads/codeql/fixes',cwd=local,ok=False)
        assert git('--git-dir='+str(p/'remote.git'),'rev-parse','codeql/fixes')==second
        assert (local/'one').exists() and (local/'two').exists()

for name,fn in [('all alerts selected at 1/6/20/50; 257 rejected as a whole',selection_counts),('open/closed issues, human dismissals, manual override and legacy index',selection_decisions),('draft PR freezes; append skips pending IDs; merge cleanup and rejected PR retry',branch_selection),('collector accepts real failed-test reports; rejects missing/malformed/incomplete artifacts',collector),('10 mixed reports => one issue, two dismissals; repeat creates no duplicate; seven unsure => one issue',mixed_outcomes),('changed alert/file and unconfirmed dismissal cause no false dismissal',dismissal_guards),('timeout does not create an issue or dismiss an alert',incomplete_outcomes),('real Git: create, append with preserved ancestry, reject stale explicit lease',leases)]:
    check(name,fn)

summary=f'{len(PASSED)} contract groups passed. GitHub API and model outputs were fixtures; Git lease tests used real local repositories.'
print(summary)
if os.environ.get('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
        f.write('## Controlled contract tests\n\n'+''.join('- PASS: '+n+'\n' for n in PASSED)+'\n'+summary+'\n')
