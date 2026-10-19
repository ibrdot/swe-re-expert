"""Exercise the actual reviewed AI-register examples, without calling models/tools."""
import ast
import json
import hashlib
import tempfile
from unittest.mock import patch
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]
# Updating a documented executable example requires direct review of its bytes.
# Ordinary Markdown changes cannot silently inject code into this test process.
REVIEWED_EXAMPLE_DIGESTS = {
    'ai-code-generation-guardrails': '05693aeb03c7fb621a5e19d07e85b4f1a4aff68161e8893e21700fefb020df0c',
    'ai-prompt-regression-testing': '524eef49099a2708e629b3915ad9c2bfd12b565726adff9631742f7a9888b49b',
}


def load_example(skill):
    content = (ROOT / 'skills' / skill / 'SKILL.md').read_text()
    code = re.search(r'```python\n(.*?)```', content, re.S).group(1)
    if hashlib.sha256(code.encode()).hexdigest() != REVIEWED_EXAMPLE_DIGESTS[skill]:
        raise AssertionError("Example bytes changed: direct review required before execution")
    parsed = ast.parse(code)
    # Only the reviewed helper and stdlib imports; demonstration print calls omitted.
    statements = [node for node in parsed.body if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
    namespace = {}
    exec(compile(ast.Module(body=statements, type_ignores=[]), str(skill), 'exec'), namespace)
    return namespace


class RegisterExamples(unittest.TestCase):
    def test_changed_markdown_example_is_rejected_before_executing_definition(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'skills/ai-code-generation-guardrails/SKILL.md'
            target.parent.mkdir(parents=True)
            target.write_text('```python\ndef altered(value=1/0):\n    return value\n```\n')
            with patch.dict(load_example.__globals__, ROOT=root):
                with self.assertRaisesRegex(AssertionError, 'direct review required'):
                    load_example('ai-code-generation-guardrails')

    def test_router_schema_rejects_wrong_types_extra_tenant_and_missing_id(self):
        content = (ROOT / 'skills/ai-agent-tool-routing/SKILL.md').read_text()
        record = json.loads(re.search(r'```json\n(.*?)```', content, re.S).group(1))
        script = '''const Ajv = require('ajv/dist/2020');
const validate = new Ajv().compile(JSON.parse(process.argv[1]));
const cases = [{document_id:'DOC-1'}, {}, {document_id:''},
 {document_id:1}, {document_id:'DOC-1',tenant_id:'other'}, {document_id:'x'.repeat(81)}];
process.stdout.write(JSON.stringify(cases.map(value=>validate(value))));'''
        run = subprocess.run(['node', '-e', script, json.dumps(record['parameter_schema'])],
                             cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(run.stdout), [True, False, False, False, False, False])
        self.assertEqual(record['status'], 'draft')
        self.assertEqual(record['evidence'], [])

    def test_ast_findings_are_inert_and_do_not_approve_clean_or_alias_code(self):
        inspect = load_example('ai-code-generation-guardrails')['inspect_generated_python']
        self.assertEqual(inspect('import subprocess\n')['status'], 'blocked')
        self.assertEqual(inspect('from os.path import join\n')['status'], 'blocked')
        self.assertEqual(inspect("eval('1+1')\n")['status'], 'blocked')
        self.assertEqual(inspect('answer = 1 + 1\n')['status'], 'review-required')
        self.assertEqual(inspect('alias = eval\nalias(user_input)\n')['status'], 'review-required')

    def test_unparseable_oversized_or_nontext_ast_inputs_remain_incomplete(self):
        inspect = load_example('ai-code-generation-guardrails')['inspect_generated_python']
        for value in [None, [], 'if', 'x' * 65537, '\ud800']:
            with self.subTest(value_type=type(value).__name__):
                self.assertEqual(inspect(value)['status'], 'incomplete')

    def test_empty_missing_duplicate_or_unknown_results_never_pass(self):
        summarize = load_example('ai-prompt-regression-testing')['summarize_regression']
        cases = [([], []), ([], ['A']), ([{'case_id':'A','result':'pass'}], ['A','B']),
                 ([{'case_id':'A','result':'pass'}] * 2, ['A']),
                 ([{'case_id':'X','result':'pass'}], ['A']),
                 ([{'case_id':'A','result':'maybe'}], ['A']),
                 ([{'case_id':'A','result':[]}], ['A']), ([], ['A','A'])]
        for results, expected in cases:
            with self.subTest(results=results, expected=expected):
                self.assertEqual(summarize(results, expected)['status'], 'incomplete')

    def test_known_failure_stays_visible_when_another_case_is_missing(self):
        summarize = load_example('ai-prompt-regression-testing')['summarize_regression']
        result = summarize([{'case_id':'A','result':'fail'}], ['A','B'])
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['failed_cases'], ['A'])
        self.assertEqual(result['evaluated'], 1)

    def test_complete_recorded_checks_are_not_general_quality_certificate(self):
        summarize = load_example('ai-prompt-regression-testing')['summarize_regression']
        self.assertEqual(summarize([{'case_id':'A','result':'pass'}], ['A'])['status'], 'checks-passed')
        self.assertEqual(summarize([{'case_id':'A','result':'fail'}], ['A'])['status'], 'regression')
        self.assertEqual(summarize([{'case_id':'A','result':'incomplete'}], ['A'])['status'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
