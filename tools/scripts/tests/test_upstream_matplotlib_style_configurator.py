"""Regression checks for non-destructive Matplotlib helper outputs."""

from __future__ import annotations

import contextlib
import io
import runpy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "matplotlib"
    / "scripts"
    / "style_configurator.py"
)


def load_helper() -> dict[str, object]:
    """Load the file with lightweight dependency stubs; no plotting is needed."""
    numpy = types.ModuleType("numpy")
    matplotlib = types.ModuleType("matplotlib")
    matplotlib.__path__ = []
    pyplot = types.ModuleType("matplotlib.pyplot")
    gridspec = types.ModuleType("matplotlib.gridspec")
    gridspec.GridSpec = type("GridSpec", (), {})
    matplotlib.pyplot = pyplot
    modules = {
        "numpy": numpy,
        "matplotlib": matplotlib,
        "matplotlib.pyplot": pyplot,
        "matplotlib.gridspec": gridspec,
    }
    with patch.dict(sys.modules, modules):
        return runpy.run_path(str(SCRIPT))


class StyleConfiguratorOutputTests(unittest.TestCase):
    def test_existing_style_is_never_truncated(self) -> None:
        helper = load_helper()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "existing.mplstyle"
            target.write_text("keep this style", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                helper["save_style_file"]({}, str(target))
            self.assertEqual(target.read_text(encoding="utf-8"), "keep this style")

    def test_preview_uses_a_distinct_path_for_non_mplstyle_output(self) -> None:
        helper = load_helper()
        main = helper["main"]
        pyplot = main.__globals__["plt"]
        main.__globals__["create_style_preview"] = lambda _style: object()
        pyplot.savefig = lambda destination, **_kwargs: destination.write(b"preview")
        pyplot.show = lambda: None

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "custom-style"
            old_argv = sys.argv
            sys.argv = [
                str(SCRIPT),
                "--preset",
                "publication",
                "--output",
                str(target),
                "--preview",
            ]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    main()
            finally:
                sys.argv = old_argv

            self.assertIn("Custom matplotlib style", target.read_text(encoding="utf-8"))
            preview = Path(temporary) / "custom-style_preview.png"
            self.assertEqual(preview.read_bytes(), b"preview")


if __name__ == "__main__":
    unittest.main()
