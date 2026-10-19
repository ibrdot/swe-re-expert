"""Exercise review boundary cases using canonical example code and inert fixtures."""
import ast
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

class BoundaryExamples(unittest.TestCase):
    def test_missing_metrics_cannot_pass_and_latency_direction_is_respected(self):
        text = (ROOT/'skills/llm-evaluation/SKILL.md').read_text()
        code = next(c for c in re.findall(r'```python\n(.*?)\n```', text, re.S) if c.startswith('class RegressionDetector'))
        scope = {}; exec(code, scope)
        cls = scope['RegressionDetector']
        incomplete = cls({'accuracy': 1}).check_for_regression({})
        self.assertIsNone(incomplete['has_regression'])
        self.assertFalse(incomplete['analysis_complete'])
        self.assertTrue(cls({'latency':100}, directions={'latency':'lower'}).check_for_regression({'latency':120})['has_regression'])
        self.assertFalse(cls({'latency':100}, directions={'latency':'lower'}).check_for_regression({'latency':80})['has_regression'])
        with self.assertRaises(ValueError): cls({'accuracy':1}).check_for_regression({'accuracy':float('nan')})
        with self.assertRaises(ValueError): cls({})
        with self.assertRaises(ValueError): cls({'accuracy':1}, threshold=-0.1)
        with self.assertRaises(ValueError): cls({'score':-1}).check_for_regression({'score':-2})

    def test_benchmark_rejects_empty_missing_and_duplicate_metrics(self):
        import math
        import statistics
        from types import SimpleNamespace
        text = (ROOT/'skills/llm-evaluation/references/benchmarking.md').read_text()
        code = re.search(r'```python\n(.*?)\n```', text, re.S).group(1)
        nodes = [n for n in ast.parse(code).body if isinstance(n, ast.ClassDef)]
        scope = {'math':math, 'np':SimpleNamespace(mean=statistics.mean, std=statistics.pstdev)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-benchmark-example>', 'exec'), scope)
        cls = scope['BenchmarkRunner']
        with self.assertRaises(ValueError): cls([])
        with self.assertRaises(ValueError): cls([{}, {}], max_examples=1)
        data = [{'input':'inert', 'reference':'fixture'}]
        runner = cls(data)
        model = SimpleNamespace(predict=lambda value: value)
        metric = SimpleNamespace(name='test', calculate=lambda **kwargs: 1)
        self.assertEqual(runner.run_benchmark(model, [metric])['test']['mean'], 1)
        with self.assertRaises(ValueError): runner.run_benchmark(model, [])
        with self.assertRaises(ValueError): runner.run_benchmark(model, [metric, metric])
        missing = SimpleNamespace(name='test', calculate=lambda **kwargs: None)
        with self.assertRaises(ValueError): runner.run_benchmark(model, [missing])

    def test_unknown_privacy_values_survive_sql_and_schema(self):
        text = (ROOT/'skills/data-privacy-controls/SKILL.md').read_text()
        ddl = re.search(r'```sql\n(.*?)\n```', text, re.S).group(1)
        # Translate only PostgreSQL NOW() syntax for the local nullable-field fixture.
        db = sqlite3.connect(':memory:'); self.addCleanup(db.close)
        db.executescript(ddl.replace("DEFAULT NOW()", "DEFAULT CURRENT_TIMESTAMP"))
        table = re.search(r'CREATE TABLE (\w+)', ddl, re.I).group(1)
        info = {row[1]:row for row in db.execute('PRAGMA table_info('+table+')')}
        self.assertEqual(info['consent_required'][3],0)
        self.assertEqual(info['last_reviewed'][3],0)
        schema = json.loads(re.search(r'```json\n(.*?)\n```', text, re.S).group(1))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'schema.json'; path.write_text(json.dumps(schema))
            script = "const Ajv=require('ajv/dist/2020'); const s=require(process.argv[1]); delete s.properties['Last Reviewed'].format; const v=new Ajv().compile(s); if(!v({'Data Category':'Personal',Status:'Draft','Consent Required':null,'Last Reviewed':null})) throw Error(JSON.stringify(v.errors)); if(v({'Data Category':'Personal',Status:'Draft','Consent Required':'unknown'})) throw Error('bad type accepted');"
            result=subprocess.run(['node','-e',script,str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_accessibility_report_escapes_finding_content(self):
        text=(ROOT/'skills/accessibility-compliance-accessibility-audit/resources/implementation-playbook.md').read_text()
        code=next(c for c in re.findall(r'```javascript\n(.*?)\n```',text,re.S) if 'function escapeReportText' in c)
        script=code+"\nconst assert=require('node:assert/strict'); const html=renderFindings([{help:'<script>alert(1)</script>',description:'<img onerror=x>',impact:'\\\"&'}]); assert(!html.includes('<script>')); assert(!html.includes('<img')); assert(html.includes('&lt;script&gt;'));"
        result=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_wait_helpers_reject_invalid_bounds_and_getter_failures(self):
        text=(ROOT/'skills/systematic-debugging/condition-based-waiting-example.ts').read_text()
        text=re.sub(r'^import type .*;\n','',text,flags=re.M)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.mts'
            path.write_text(text+"\nimport assert from 'node:assert/strict'; const broken={getEvents(){throw new Error('getter failed')}}; await assert.rejects(waitForEvent(broken,'t','done'),/getter failed/); await assert.rejects(waitForEvent(broken,'t','done',NaN),/Invalid timeout/); await assert.rejects(waitForEventCount(broken,'t','done',0),/Invalid count/); const ready={getEvents:()=>[{type:'done'}]}; assert.equal((await waitForEvent(ready,'t','done',0)).type,'done'); await assert.rejects(waitForEvent({getEvents:()=>[]},'t','done',0),/Timeout/);")
            result=subprocess.run(['node','--experimental-strip-types',str(path)],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('swiftc'), 'Swift compiler is unavailable; runtime fixture remains a separate local check')
    def test_cancelled_load_does_not_publish_late_result(self):
        text=(ROOT/'skills/swiftui-ui-patterns/references/async-state.md').read_text()
        method=re.search(r'  private func load\(\) async \{(.*?)\n  \}\n\}',text,re.S).group(1)
        source='''import Foundation
actor Client {
 var continuation: CheckedContinuation<String, Never>?
 func fetch(id: String) async throws -> String { await withCheckedContinuation { continuation = $0 } }
 func waiting() -> Bool { continuation != nil }
 func release() { continuation?.resume(returning: "late"); continuation = nil }
}
enum LoadState { case idle, loading, loaded(String), failed(Error) }
@MainActor final class Model {
 let id = "fixture"
 let client: Client
 var state: LoadState = .idle
 init(_ client: Client) { self.client = client }
 func load() async {'''+method+'''
 }
}
@main struct Check {
 @MainActor static func main() async {
  let client = Client(); let model = Model(client)
  let job = Task { await model.load() }
  while !(await client.waiting()) { await Task.yield() }
  job.cancel(); await client.release(); await job.value
  if case .loaded = model.state { fatalError("cancelled result published") }
 }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'main.swift'; p.write_text(source); binary=Path(directory)/'check'
            # A fresh private module cache compiles Foundation on Linux CI hosts.
            # Keep compilation bounded separately from the 10-second execution check.
            compiled=subprocess.run(['swiftc','-module-cache-path',str(Path(directory)/'module-cache'),'-parse-as-library',str(p),'-o',str(binary)],capture_output=True,text=True,timeout=180)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result=subprocess.run([str(binary)],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__ == '__main__': unittest.main()
