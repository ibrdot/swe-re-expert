import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def load_session_catchup_module():
    script_path = Path(__file__).with_name("session-catchup.py")
    spec = spec_from_file_location("session_catchup", script_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


session_catchup = load_session_catchup_module()


class SessionCatchupPathTests(unittest.TestCase):
    def test_sanitize_project_path_preserves_underscores(self) -> None:
        underscored = session_catchup.sanitize_project_path("/Users/example/foo_bar")
        dashed = session_catchup.sanitize_project_path("/Users/example/foo-bar")

        self.assertNotEqual(underscored, dashed)
        self.assertEqual(underscored, "Users-example-foo_bar")
        self.assertEqual(dashed, "Users-example-foo-bar")

    def test_normalize_path_converts_git_bash_drive_prefix(self) -> None:
        normalized = session_catchup.normalize_path("/c/Users/example/project")
        self.assertEqual(normalized, "C:/Users/example/project")

    def test_detect_session_source_prefers_explicit_env(self) -> None:
        with patch.dict(session_catchup.os.environ, {"PLANNING_SESSION_SOURCE": "none"}, clear=False):
            self.assertEqual(session_catchup.detect_session_source(), "none")

    def test_detect_session_source_uses_codex_runtime_markers(self) -> None:
        with patch.dict(session_catchup.os.environ, {"CODEX_THREAD_ID": "thread-123"}, clear=True):
            self.assertEqual(session_catchup.detect_session_source(), "codex")

    def test_get_project_dir_skips_codex_without_scanning_claude_projects(self) -> None:
        with TemporaryDirectory() as temp_home:
            with (
                patch.dict(session_catchup.os.environ, {"CODEX_THREAD_ID": "thread-123"}, clear=True),
                patch.object(session_catchup.Path, "home", return_value=Path(temp_home)),
            ):
                project_dir, skip_reason = session_catchup.get_project_dir("/Users/example/foo_bar")

        self.assertIsNone(project_dir)
        assert skip_reason is not None
        self.assertIn("Codex runtime detected", skip_reason)

    def test_get_project_dir_uses_claude_projects_for_claude_runtime(self) -> None:
        with TemporaryDirectory() as temp_home:
            with (
                patch.dict(session_catchup.os.environ, {"CLAUDE_PLUGIN_ROOT": "/tmp/skill"}, clear=True),
                patch.object(session_catchup.Path, "home", return_value=Path(temp_home)),
            ):
                project_dir, skip_reason = session_catchup.get_project_dir("/Users/example/foo_bar")

        self.assertEqual(project_dir, Path(temp_home) / ".claude" / "projects" / "Users-example-foo_bar")
        self.assertIsNone(skip_reason)


if __name__ == "__main__":
    unittest.main()
