"""Regressions consume the actual published examples; all inputs are local/inert."""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def blocks(skill, relative, language):
    text = (ROOT / 'skills' / skill / relative).read_text()
    return re.findall(r'^```' + language + r'\n(.*?)^```\s*$', text, re.M | re.S)


def python_namespace(skill, relative):
    scope = {}
    for code in blocks(skill, relative, 'python'):
        exec(compile(code, str(ROOT / 'skills' / skill / relative), 'exec'), scope)
    return scope


class ReportSkillRepairs(unittest.TestCase):
    def test_schema_helper_never_certifies_missing_unsupported_or_regex_only(self):
        helper = ROOT / 'skills/database-design/scripts/schema_validator.py'
        cases = [None, ('drizzle/schema.ts', 'export const schema = {}'),
                 ('prisma/schema.prisma', 'model User { id Int @id }'),
                 ('prisma/schema.prisma', 'not a schema')]
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                if case:
                    p = Path(directory) / case[0]
                    p.parent.mkdir(parents=True)
                    p.write_text(case[1])
                before = sorted(str(x.relative_to(directory)) for x in Path(directory).rglob('*'))
                result = subprocess.run(['python3', '-B', str(helper), directory], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('"passed": false', result.stdout)
                self.assertIn('"analysis_complete": false', result.stdout)
                self.assertEqual(before, sorted(str(x.relative_to(directory)) for x in Path(directory).rglob('*')))

    def test_billing_unknown_tax_and_invalid_proration_fail_closed(self):
        ns = python_namespace('billing-automation', 'resources/implementation-playbook.md')
        with self.assertRaises(ValueError):
            ns['assessed_tax']('20', None)
        self.assertEqual(str(ns['assessed_tax']('20', '0')), '0')
        key = ns['billing_operation_key']
        self.assertEqual(key('tenant-a', 'invoice-1'), key('tenant-a', 'invoice-1'))
        self.assertNotEqual(key('tenant-a', 'invoice-1'), key('tenant-b', 'invoice-1'))
        self.assertNotEqual(key('tenant-a', 'invoice-1'), key('tenant-a', 'invoice-1', 'refund'))
        from datetime import datetime, timezone
        start, middle, end = [datetime(2026, 2, day, tzinfo=timezone.utc) for day in (1, 15, 28)]
        self.assertEqual(str(ns['linear_proration']('10', '37', start, end, middle)), '13.00')
        with self.assertRaises(ValueError):
            ns['linear_proration']('10', '37', start, start, start)

    def test_memory_cross_identity_and_no_deletion(self):
        ns = python_namespace('agent-memory-systems', 'references/detailed-guide.md')
        plan = ns['plan_consolidation']
        item = {'tenant_id': 'a', 'user_id': 'u', 'id': 'source'}
        self.assertFalse(plan('a', 'u', [item])['delete_originals'])
        with self.assertRaises(PermissionError):
            plan('b', 'u', [item])
        with self.assertRaises(PermissionError):
            plan('a', 'v', [item])
        with self.assertRaises(ValueError):
            ns['memory_namespace']('', 'u', 'semantic')

    def test_frontend_retry_requires_replay_safety_and_classified_error(self):
        text = (ROOT / 'skills/frontend-api-integration-patterns/SKILL.md').read_text()
        code = re.search(r'```js id="8n3zcf"\n(.*?)\n```', text, re.S).group(1)
        checks = """
import assert from 'node:assert/strict';
Math.random = ()=>0;
let attempts = 0;
const transient = async()=>{attempts++; throw Object.assign(new Error('transient'), {status:503})};
await assert.rejects(fetchWithBackoff(transient, 1, 0));
assert.equal(attempts, 1);
attempts=0;
await assert.rejects(fetchWithBackoff(transient, 1, 0, true));
assert.equal(attempts, 2);
attempts=0;
await assert.rejects(fetchWithBackoff(async()=>{attempts++; throw new TypeError('bug')},1,0,true));
assert.equal(attempts,1);
"""
        result = subprocess.run(['node', '--input-type=module', '-e', code + checks], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_requirement_mapping_does_not_certify_counts_or_unknown_risk(self):
        ns = python_namespace('security-requirement-extraction', 'resources/implementation-playbook.md')
        with self.assertRaises(ValueError):
            ns['RequirementExtractor']()._calculate_priority('unknown', 'high')
        req = ns['SecurityRequirement']('a', 'Candidate', 'Protect access',
            ns['RequirementType'].FUNCTIONAL, ns['SecurityDomain'].AUTHENTICATION, ns['Priority'].HIGH)
        req_set = ns['RequirementSet']('test', '1', [req])
        result = ns['ComplianceMapper']().gap_analysis(req_set, ns['ComplianceFramework'].HIPAA)
        self.assertIn('hipaa:164.312(d)', result['assessment_required'])
        self.assertNotIn('weak_coverage', result)

    def test_private_balance_rejects_before_fetch(self):
        code = blocks('native-data-fetching', 'references/expo-router-loaders.md', 'javascript')[0]
        checks = '''
import assert from 'node:assert/strict';
let fetched = 0;
const fetchBalance = async () => { fetched++; return {amount: 5}; };
await assert.rejects(loadPrivateBalance({}, {verifySession: async()=>null, authorizeAccount:async()=>true, fetchBalance}));
await assert.rejects(loadPrivateBalance({}, {verifySession: async()=>({user:'a'}), authorizeAccount:async()=>null, fetchBalance}));
assert.equal(fetched, 0);
assert.deepEqual(await loadPrivateBalance({}, {verifySession:async()=>({user:'a'}), authorizeAccount:async()=>({id:'allowed'}), fetchBalance}), {balance:{amount:5}});
assert.equal(fetched, 1);
'''
        result = subprocess.run(['node', '--input-type=module', '-e', code + checks], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_realpath_rejects_sibling_symlink_escape(self):
        source = next(code for code in blocks('mcp-server-security', 'references/details.md', 'typescript') if '// src/safePath.ts' in code)
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory) / 'workspace'
            sibling = Path(directory) / 'workspace-evil'
            sandbox.mkdir(); sibling.mkdir()
            (sandbox / 'ok.txt').write_text('ok')
            (sibling / 'secret.txt').write_text('secret')
            (sandbox / 'escape').symlink_to(sibling, target_is_directory=True)
            source = source.replace('"/home/mcpuser/workspace"', json.dumps(str(sandbox)))
            source += '''
import assert from 'node:assert/strict';
assert.equal(resolveSafePath('ok.txt'), realpathSync.native(SANDBOX_ROOT + '/ok.txt'));
assert.throws(()=>resolveSafePath('../workspace-evil/secret.txt'));
assert.throws(()=>resolveSafePath('escape/secret.txt'));
'''
            p = Path(directory) / 'check.mts'; p.write_text(source)
            result = subprocess.run(['node', '--experimental-strip-types', str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_fixed_sql_query_does_not_accept_agent_sql(self):
        source = next(code for code in blocks('mcp-server-security', 'references/details.md', 'typescript') if '// Illustrative handler' in code)
        with tempfile.TemporaryDirectory() as directory:
            source += '''
import assert from 'node:assert/strict';
const calls = [];
const db = {query: async(sql, args)=>{calls.push([sql,args]); return []}};
await assert.rejects(handleDatabaseQuery({queryId:'SELECT evil()',itemId:'x'},db));
assert.equal(calls.length, 0);
await handleDatabaseQuery({queryId:'public_item',itemId:"x'; DROP TABLE users; --"},db);
assert.equal(calls[0][0], QUERIES.public_item);
assert.equal(calls[0][1][0], "x'; DROP TABLE users; --");
'''
            p = Path(directory) / 'check.mts'; p.write_text(source)
            result = subprocess.run(['node', '--experimental-strip-types', str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_compliance_evidence_stays_unknown(self):
        text = (ROOT / 'skills/security-compliance-compliance-check/resources/implementation-playbook.md').read_text()
        code = next(c for c in re.findall(r'```python\n(.*?)\n```', text, re.S) if c.startswith('def build_control_register'))
        scope = {}; exec(code, scope)
        self.assertEqual(scope['build_control_register'](['control-a'], {})[0]['status'], 'unknown')
        self.assertEqual(scope['build_control_register'](['control-a'], {'control-a':'evidence'})[0]['assessment'], 'requires_qualified_review')

    def test_mock_fixture_state_isolated_and_unknown_scenarios_rejected(self):
        text = (ROOT / 'skills/api-testing-observability-api-mock/resources/implementation-playbook.md').read_text()
        code = next(c for c in re.findall(r'```python\n(.*?)\n```', text, re.S) if c.startswith('from copy import deepcopy'))
        scope = {}; exec(code, scope)
        resolve = scope['resolve_fixture']
        resolve('GET', '/users/example', 'success')['body']['id'] = 'contaminated'
        self.assertEqual(resolve('GET', '/users/example', 'success')['body']['id'], 'example')
        with self.assertRaises(KeyError):
            resolve('GET', '/users/example', 'undeclared')


if __name__ == '__main__':
    unittest.main()
