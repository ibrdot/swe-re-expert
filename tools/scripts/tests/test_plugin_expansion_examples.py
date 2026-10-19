"""Execute pure published examples with inert inputs; no provider calls or writes."""
import ast
import hashlib
import hmac
import json
from pathlib import Path
import re
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def read(skill, file='SKILL.md'):
    return (ROOT / 'skills' / skill / file).read_text()


def python_block(skill, marker, file='SKILL.md'):
    return next(c for c in re.findall(r'```python\n(.*?)```', read(skill, file), re.S) if marker in c)


class ExpansionExamples(unittest.TestCase):
    def test_signature_rejection_survives_python_optimization(self):
        code = python_block('api-integration', '# webhook-signature-example')
        expected = 'sha256=' + hmac.new(b'fixture-secret', b'fixture-payload', hashlib.sha256).hexdigest()
        for signature, success in [(expected, True), ('sha256=invalid', False), ('', False)]:
            fixture = f"from types import SimpleNamespace\nsecret='fixture-secret'\npayload_bytes=b'fixture-payload'\nrequest=SimpleNamespace(headers={{'X-Webhook-Signature':{signature!r}}})\n" + code
            result = subprocess.run([sys.executable, '-O', '-c', fixture], capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, success, result.stderr)

    def test_supplied_email_fixtures_match_published_predicate(self):
        code = python_block('python-testing-patterns', 'def is_valid_email', 'resources/implementation-playbook.md')
        tree = ast.parse(code)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'is_valid_email')
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'published-predicate', 'exec'), namespace)
        examples = next(ast.literal_eval(n.decorator_list[0].args[1]) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'test_email_validation')
        for email, expected in examples:
            self.assertEqual(namespace['is_valid_email'](email), expected, email)

    def test_python_retries_respect_wait_budget_and_terminal_status(self):
        code = python_block('api-rate-limit-handler', 'def fetch_with_retry')
        clock = [0]
        waits, calls, closed = [], [], []
        states = []
        def request(*args, **kwargs):
            calls.append(args)
            status, headers = states[min(len(calls)-1, len(states)-1)]
            def fail():
                raise ValueError(f'status {status}')
            return types.SimpleNamespace(is_success=status == 200, status_code=status, headers=headers,
                raise_for_status=fail, close=lambda: closed.append(status))
        fake = types.ModuleType('httpx'); fake.request = request; fake.Response = object
        namespace = {}
        with patch.dict(sys.modules, {'httpx': fake}):
            exec(compile(code, 'published-python-retry', 'exec'), namespace)
        def sleep(delay):
            waits.append(delay); clock[0] += delay
        with patch('time.monotonic', lambda: clock[0]), patch('time.sleep', sleep), patch.object(namespace['random'], 'uniform', lambda a,b: .5):
            retry = namespace['fetch_with_retry']
            states[:] = [(429, {'retry-after': '3600'})]
            with self.assertRaises(TimeoutError): retry('fixture')
            self.assertEqual(len(calls), 1); self.assertEqual(waits, []); self.assertEqual(closed, [429])
            for state in [(405, {}), (429, {'retry-after': '0'}), (503, {})]:
                calls.clear(); waits.clear(); closed.clear(); clock[0] = 0; states[:] = [state]
                with self.assertRaises(ValueError): retry('fixture', max_retries=2)
                self.assertEqual(len(calls), 1 if state[0] == 405 else 3)
                if state[1]: self.assertEqual(waits, [0, 0])
            calls.clear(); waits.clear(); states[:] = [(503, {}), (200,{})]
            self.assertTrue(retry('fixture').is_success)
            self.assertEqual(waits, [1.5])

    def test_published_scoring_and_savings(self):
        strategy = read('content-strategy')
        for row in re.findall(r'\| Topic [AB] \|([^\n]+)', strategy):
            values = [float(x.strip()) for x in row.strip(' |').split('|')]
            self.assertAlmostEqual(sum(v*w for v,w in zip(values[:4], [.4,.3,.2,.1])), values[4])
        pricing = read('usage-based-pricing', 'references/detailed-guide.md')
        developers, hours, rate = [int(re.search(pattern, pricing).group(1)) for pattern in [r'Developers: \[(\d+)\]', r'Hours/week on auth per developer: \[(\d+)\]', r'Fully-loaded cost/hour: \[\$(\d+)\]']]
        annual = developers * hours * rate * 52
        self.assertIn(f'${annual:,}/year', pricing)
        self.assertIn(f'= ${annual-3000-12000:,}', pricing)

    def test_published_contrast_before_and_after(self):
        css = read('wcag-audit-patterns', 'resources/implementation-playbook.md').split('### Fix: Insufficient Color Contrast')[1].split('```')[1]
        colors = re.findall(r'color: #(\w{6});', css)[:2]
        def contrast(color):
            channels = [int(color[i:i+2],16)/255 for i in (0,2,4)]
            linear = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in channels]
            luminance = sum(c*w for c,w in zip(linear,[.2126,.7152,.0722]))
            return 1.05/(luminance+.05)
        self.assertLess(contrast(colors[0]), 4.5); self.assertGreaterEqual(contrast(colors[1]), 7)

    def test_published_market_matrix_and_cost_units(self):
        text = read('data-storytelling')
        rows = re.findall(r'\| (?:Market Size|Growth|Competition|Ease)\s*\| (\d+)%\s*\| (\d+)\s*\| (\d+)\s*\|', text)
        self.assertEqual(len(rows), 4)
        totals = re.search(r'\| \*\*Total\*\*.*?\*\*([\d.]+)\*\*.*?\*\*([\d.]+)\*\*', text).groups()
        for index in [1, 2]:
            self.assertAlmostEqual(sum(int(row[0])/100*int(row[index]) for row in rows), float(totals[index-1]))
        alert = read('ai-sre-incident-response').split('- alert: TokenCostExplosion')[1].split('for:')[0]
        self.assertIn('60 * sum(rate(llm_token_cost_dollars[5m]))', alert)
        # A synthetic $0.01/second cost must exceed a $0.50/minute threshold.
        self.assertGreater(60 * .01, .50)

    def test_accessibility_cli_uses_existing_project_tools(self):
        guide = read('wcag-audit-patterns', 'resources/implementation-playbook.md')
        self.assertNotIn('npx @axe-core/cli', guide)
        self.assertNotIn('npx pa11y', guide)
        self.assertIn('./node_modules/.bin/axe http://localhost:3000', guide)
        self.assertIn('do not download or install a moving package', guide)

    def test_evaluation_json_is_machine_readable(self):
        for block in re.findall(r'```json\n(.*?)```', read('advanced-evaluation'), re.S):
            self.assertIsInstance(json.loads(block), dict)


if __name__ == '__main__':
    unittest.main()
