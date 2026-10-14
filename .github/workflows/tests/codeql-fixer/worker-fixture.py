"""Generate explicit fixture reports, without invoking a model or running tests."""
import json, os
from pathlib import Path

n = int(os.environ['ALERT_NUMBER'])
sha = os.environ['ANALYZED_SHA']
verdict = 'bug' if n <= 5 else 'unsure' if n <= 8 else 'false-positive'
root = Path(os.environ['RUNNER_TEMP']) / 'codeql-result' / str(n)
root.mkdir(parents=True, exist_ok=True)
report = dict(alert_number=n, analyzed_sha=sha, verdict=verdict, evidence='CONTROLLED TEST FIXTURE, not an agent conclusion.', counterexample_checks=['Fixture only'], unresolved_fact='Fixture question' if verdict == 'unsure' else None, validation=[dict(command='fixture-only', passed=n != 5, summary='Synthetic validation result')] if verdict == 'bug' else [], fix_available=verdict == 'bug', execution_status='complete', error=None)
(root / 'result.json').write_text(json.dumps(report, separators=(',', ':')))
if verdict == 'bug':
    (root / 'fix.patch').write_text(f'diff --git a/tests/fixer-fixture-{n}.txt b/tests/fixer-fixture-{n}.txt\nnew file mode 100644\n--- /dev/null\n+++ b/tests/fixer-fixture-{n}.txt\n@@ -0,0 +1 @@\n+CONTROLLED TEST FIXTURE\n')
