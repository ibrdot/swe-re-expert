import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO_ROOT / "skills" / "typescript-expert"


def load_diagnostic():
    path = SKILL_DIR / "scripts" / "ts_diagnostic.py"
    spec = importlib.util.spec_from_file_location("ts_diagnostic", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TypeScriptExpertDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.diag = load_diagnostic()

    def type_check_output(self, returncode, output):
        self.diag.run_cmd = lambda args: (returncode, output)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.diag.check_type_errors()
        return buffer.getvalue()

    def test_type_check_does_not_pass_when_tsc_did_not_run(self):
        for returncode, output in [
            (None, "[Errno 2] No such file or directory: 'npx'"),
            (1, "npm error npx canceled due to missing packages"),
            (1, "This is not the tsc command you are looking for"),
        ]:
            report = self.type_check_output(returncode, output)
            self.assertNotIn("No type errors", report)
            self.assertIn("did not run", report)

    def test_type_check_reports_errors_and_clean_runs(self):
        failing = self.type_check_output(2, "src/a.ts(1,7): error TS2322: Type 'string' is not assignable")
        self.assertIn("type errors found", failing)
        self.assertIn("No type errors", self.type_check_output(0, ""))

    def test_tsc_is_never_downloaded(self):
        self.assertEqual(self.diag.TSC, ["npx", "--no-install", "tsc"])

    def test_strip_jsonc_parses_bundled_strict_tsconfig(self):
        text = (SKILL_DIR / "references" / "tsconfig-strict.json").read_text(encoding="utf-8")
        config = json.loads(self.diag.strip_jsonc(text))
        self.assertTrue(config["compilerOptions"]["strict"])

    def test_strip_jsonc_keeps_comment_markers_inside_strings(self):
        text = """{
          // line comment
          "paths": { "@/*": ["src/*"] }, /* block */
          "url": "https://example.com/a,]",
          "quote": "say \\"hi\\" // not a comment",
          "list": [1, 2, // trailing comma
          ],
        }"""
        self.assertEqual(
            json.loads(self.diag.strip_jsonc(text)),
            {
                "paths": {"@/*": ["src/*"]},
                "url": "https://example.com/a,]",
                "quote": 'say "hi" // not a comment',
                "list": [1, 2],
            },
        )


if __name__ == "__main__":
    unittest.main()
