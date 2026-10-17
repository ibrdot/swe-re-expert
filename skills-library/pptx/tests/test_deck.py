import json
import os
import tempfile
import unittest
from pathlib import Path

from ppt_skill.deck import Deck


class DeckSourceUrlTest(unittest.TestCase):
    def test_source_url_for_slot_prefers_prompt_companion_over_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deck = Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.slide_path(4).write_bytes(b"current")
            os.utime(deck.slide_path(4), ns=(1_000, 1_000))
            deck.prompt_path(4).parent.mkdir(parents=True)
            deck.prompt_path(4).write_text(
                "\n".join(
                    [
                        "# Slide 04",
                        "",
                        "## Metadata",
                        "",
                        "- **source_url**: https://fal.media/files/current-slot.png",
                    ]
                ),
                encoding="utf-8",
            )
            os.utime(deck.prompt_path(4), ns=(2_000, 2_000))
            deck.meta_path.write_text(
                json.dumps(
                    {
                        "history": [
                            {
                                "slot": 4,
                                "source_url": "https://fal.media/files/original-slot.png",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                deck.source_url_for_slot(4),
                "https://fal.media/files/current-slot.png",
            )

    def test_source_url_for_slot_ignores_prompt_when_slide_is_newer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deck = Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.prompt_path(1).parent.mkdir(parents=True)
            deck.prompt_path(1).write_text(
                "- **source_url**: https://fal.media/files/stale.png",
                encoding="utf-8",
            )
            os.utime(deck.prompt_path(1), ns=(1_000, 1_000))
            deck.slide_path(1).write_bytes(b"manual replacement")
            os.utime(deck.slide_path(1), ns=(2_000, 2_000))

            self.assertIsNone(deck.source_url_for_slot(1))

    def test_source_url_for_slot_does_not_use_history_when_prompt_has_no_url(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deck = Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.slide_path(1).write_bytes(b"current")
            os.utime(deck.slide_path(1), ns=(1_000, 1_000))
            deck.prompt_path(1).parent.mkdir(parents=True)
            deck.prompt_path(1).write_text("# Slide 01\n", encoding="utf-8")
            os.utime(deck.prompt_path(1), ns=(2_000, 2_000))
            deck.meta_path.write_text(
                json.dumps(
                    {
                        "history": [
                            {
                                "slot": 1,
                                "source_url": "https://fal.media/files/stale.png",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertIsNone(deck.source_url_for_slot(1))

    def test_source_url_for_slot_returns_newest_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deck = Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.meta_path.write_text(
                json.dumps(
                    {
                        "history": [
                            {
                                "slot": 1,
                                "source_url": "https://fal.media/files/old.png",
                            },
                            {
                                "slot": 2,
                                "source_url": "https://fal.media/files/other.png",
                            },
                            {
                                "slot": 1,
                                "source_url": "https://fal.media/files/new.png",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                deck.source_url_for_slot(1),
                "https://fal.media/files/new.png",
            )

    def test_source_url_for_slot_ignores_missing_or_non_url_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deck = Deck("demo", root=Path(tmp))
            deck.root.mkdir(parents=True)
            deck.meta_path.write_text(
                json.dumps(
                    {
                        "history": [
                            {"slot": 1, "source_url": "/local/slide-01.png"},
                            {"slot": 1},
                            {"slot": 2, "source_url": "https://fal.media/files/other.png"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertIsNone(deck.source_url_for_slot(1))


if __name__ == "__main__":
    unittest.main()
