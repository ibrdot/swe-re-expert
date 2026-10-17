import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from argparse import Namespace
from pathlib import Path


def _load_ppt_module():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.modules.setdefault(
        "dotenv",
        types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
    )
    fake_httpx = types.ModuleType("httpx")
    fake_httpx.HTTPStatusError = RuntimeError
    sys.modules.setdefault("httpx", fake_httpx)

    spec = importlib.util.spec_from_file_location("ppt_cli_test", root / "ppt.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResolveRefTest(unittest.TestCase):
    def test_cmd_edit_passes_recorded_url_to_api_for_numeric_ref(self) -> None:
        ppt = _load_ppt_module()

        with tempfile.TemporaryDirectory() as tmp:
            deck = ppt.Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.slide_path(1).write_bytes(b"local image")
            os.utime(deck.slide_path(1), ns=(1_000, 1_000))
            deck.prompt_path(1).parent.mkdir(parents=True)
            deck.prompt_path(1).write_text(
                "- **source_url**: https://fal.media/files/slide.png",
                encoding="utf-8",
            )
            os.utime(deck.prompt_path(1), ns=(2_000, 2_000))

            captured_refs = []

            def fake_edit_image(**kwargs):
                captured_refs.extend(kwargs["refs"])
                kwargs["out_path"].write_bytes(b"edited image")
                return "https://fal.media/files/edited.png"

            original_deck = ppt.Deck
            original_edit_image = ppt.api.edit_image
            try:
                ppt.Deck = lambda _: deck
                ppt.api.edit_image = fake_edit_image
                ppt.cmd_edit(
                    Namespace(
                        deck="demo",
                        prompt="keep style",
                        ref=["1"],
                        slot=2,
                        size=None,
                        quality=None,
                        mask=None,
                        model=ppt.api.DEFAULT_EDIT_MODEL,
                    )
                )
            finally:
                ppt.Deck = original_deck
                ppt.api.edit_image = original_edit_image

            self.assertEqual(captured_refs, ["https://fal.media/files/slide.png"])

    def test_slot_ref_prefers_recorded_source_url(self) -> None:
        ppt = _load_ppt_module()

        with tempfile.TemporaryDirectory() as tmp:
            deck = ppt.Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.slide_path(1).write_bytes(b"local image")
            deck.meta_path.write_text(
                json.dumps(
                    {
                        "history": [
                            {
                                "slot": 1,
                                "source_url": "https://fal.media/files/slide.png",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                ppt._resolve_ref(deck, "1"),
                "https://fal.media/files/slide.png",
            )

    def test_slot_ref_keeps_local_path_when_source_url_missing(self) -> None:
        ppt = _load_ppt_module()

        with tempfile.TemporaryDirectory() as tmp:
            deck = ppt.Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            slide_path = deck.slide_path(1)
            slide_path.write_bytes(b"local image")

            self.assertEqual(ppt._resolve_ref(deck, "1"), str(slide_path))

    def test_slot_ref_errors_when_slide_file_is_missing_even_if_history_has_url(
        self,
    ) -> None:
        ppt = _load_ppt_module()

        with tempfile.TemporaryDirectory() as tmp:
            deck = ppt.Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.meta_path.write_text(
                json.dumps(
                    {
                        "history": [
                            {
                                "slot": 1,
                                "source_url": "https://fal.media/files/slide.png",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                ppt._resolve_ref(deck, "1")


if __name__ == "__main__":
    unittest.main()
