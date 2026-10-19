"""Exercise the actual inline local scanner with synthetic data; never probe a target."""
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]

class ReferenceExampleTests(unittest.TestCase):
    def test_redaction_and_incomplete_reads(self):
        text = (ROOT / 'skills/offensive-osint/references/helpers-and-automation.md').read_text()
        code = next(block for block in re.findall(r'```python\n(.*?)\n```', text, re.S) if 'def scan_text(' in block)
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            script = base / 'example.py'
            script.write_text(code)
            token = 'ghp_' + 'A' * 36
            result = subprocess.run([sys.executable, str(script)], input=token.encode(), capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'[REDACTED]', result.stdout)
            self.assertNotIn(token.encode(), result.stdout)
            oversized = base / 'large.txt'
            oversized.write_bytes(b'a' * (1024 * 1024 + 1))
            result = subprocess.run([sys.executable, str(script), str(oversized)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'incomplete', result.stderr)
            if getattr(os, 'O_NOFOLLOW', 0):
                fixture = base / 'fixture.txt'
                fixture.write_text(token)
                linked = base / 'linked.txt'
                linked.symlink_to(fixture)
                result = subprocess.run([sys.executable, str(script), str(linked)], capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn(token.encode(), result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
