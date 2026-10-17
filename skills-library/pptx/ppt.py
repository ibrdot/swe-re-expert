#!/usr/bin/env python3
"""
GPT Image 2 PPT — deck-oriented CLI.

Usage:
  ppt gen  <deck> <prompt> [--size WxH] [--quality Q] [--model M] [--slot N]
  ppt edit <deck> <prompt> --ref <N|PATH|URL>... [--slot N] [--size WxH] [--quality Q] [--model M] [--mask M]
  ppt pack <deck> [--title T]
  ppt info <deck>

A deck is a directory under outputs/. Slides auto-number (slide-01.png, slide-02.png...).
`--ref N` refers to slot N of the current deck; `--ref` also accepts local paths or URLs.
Deck defaults (size / quality) are cached in outputs/<deck>/deck.json after the first gen,
so subsequent commands inherit them automatically. CLI flags always override.
"""

import argparse
import sys
from pathlib import Path

from ppt_skill.env import load_env
from ppt_skill.deck import Deck
from ppt_skill import api, pack


def _resolve_slot(deck: Deck, requested: int | None) -> int:
    return requested if requested is not None else deck.next_slot()


def _resolve_ref(deck: Deck, val: str) -> str:
    """`--ref N` → slot path; else treat as URL or local path."""
    if val.isdigit():
        slot = int(val)
        p = deck.slide_path(slot)
        if not p.exists():
            sys.exit(f"Error: deck '{deck.name}' has no slide {slot} (looked for {p})")
        source_url = deck.source_url_for_slot(slot)
        if source_url:
            return source_url
        return str(p)
    if val.startswith(("http://", "https://")):
        return val
    if Path(val).exists():
        return val
    sys.exit(f"Error: --ref {val!r} is not a slot number, URL, or existing file")


# ------------------------------------------------------------------- commands

def cmd_gen(args: argparse.Namespace) -> None:
    deck = Deck(args.deck)
    meta = deck.ensure_meta(size=args.size, quality=args.quality)
    slot = _resolve_slot(deck, args.slot)
    out = deck.slide_path(slot)

    effective_size = meta.get("size")
    effective_quality = meta.get("quality") or "high"

    print(f"[gen] deck={deck.name} slot={slot:02d}", flush=True)
    url = api.gen_image(
        prompt=args.prompt,
        out_path=out,
        size=effective_size,
        quality=effective_quality,
        model=args.model,
        queue_state_path=deck.queue_job_path(slot),
    )
    deck.append_history({
        "cmd": "gen", "slot": slot, "model": args.model,
        "prompt": args.prompt, "source_url": url,
    })
    deck.write_prompt_md(
        slot,
        cmd="gen",
        prompt=args.prompt,
        size=effective_size,
        quality=effective_quality,
        model=args.model,
        source_url=url,
    )


def cmd_edit(args: argparse.Namespace) -> None:
    deck = Deck(args.deck)
    meta = deck.ensure_meta(size=args.size, quality=args.quality)
    slot = _resolve_slot(deck, args.slot)
    out = deck.slide_path(slot)

    refs = [_resolve_ref(deck, r) for r in args.ref]
    effective_quality = meta.get("quality") or "high"

    print(f"[edit] deck={deck.name} slot={slot:02d} refs={args.ref}", flush=True)
    url = api.edit_image(
        prompt=args.prompt,
        refs=refs,
        out_path=out,
        size=args.size,  # edit default is 'auto' upstream; don't inherit deck size here
        quality=effective_quality,
        mask=args.mask,
        model=args.model,
        queue_state_path=deck.queue_job_path(slot),
    )
    deck.append_history({
        "cmd": "edit", "slot": slot, "model": args.model, "refs": args.ref,
        "prompt": args.prompt, "source_url": url,
    })
    deck.write_prompt_md(
        slot,
        cmd="edit",
        prompt=args.prompt,
        refs=args.ref,
        size=args.size,
        quality=effective_quality,
        model=args.model,
        source_url=url,
    )


def cmd_pack(args: argparse.Namespace) -> None:
    deck = Deck(args.deck)
    images = deck.slide_files()
    if not images:
        sys.exit(f"Error: deck '{deck.name}' has no slides (looked in {deck.root})")
    title = args.title or deck.name
    notes = deck.load_slot_notes()

    pack.to_pptx(images, deck.pptx_path(), notes=notes)
    pack.to_html(images, deck.html_path(), title=title)


def cmd_info(args: argparse.Namespace) -> None:
    deck = Deck(args.deck)
    meta = deck.load_meta()
    slots = deck.existing_slots()
    print(f"deck: {deck.name}")
    print(f"  path: {deck.root}")
    print(f"  slides: {len(slots)} ({', '.join(f'{s:02d}' for s in slots) or '—'})")
    if meta:
        print(f"  size: {meta.get('size')}")
        print(f"  quality: {meta.get('quality')}")
        print(f"  history entries: {len(meta.get('history') or [])}")


# ---------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ppt",
        description="GPT Image 2 PPT — deck-oriented slide generation and packaging",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="Text-to-image; appends a new slide to the deck")
    g.add_argument("deck", help="Deck name (directory under outputs/)")
    g.add_argument("prompt", help="Image generation prompt")
    g.add_argument("--size", help="WxH (e.g. 2048x1152) or preset. First gen sets deck default.")
    g.add_argument("--quality", choices=["low", "medium", "high"], help="Default: high (stored in deck.json)")
    g.add_argument("--model", default=api.DEFAULT_GEN_MODEL,
                   help=f"Default: {api.DEFAULT_GEN_MODEL}")
    g.add_argument("--slot", type=int, help="Override auto-numbering; overwrites that slot")
    g.set_defaults(func=cmd_gen)

    e = sub.add_parser("edit", help="Image-to-image; appends a new slide to the deck")
    e.add_argument("deck", help="Deck name")
    e.add_argument("prompt", help="Edit instruction")
    e.add_argument("--ref", required=True, nargs="+",
                   help="One or more refs: slot number (e.g. 1), local path, or URL")
    e.add_argument("--slot", type=int, help="Override auto-numbering; overwrites that slot")
    e.add_argument("--size", help="Override size (default: auto)")
    e.add_argument("--quality", choices=["low", "medium", "high"])
    e.add_argument("--model", default=api.DEFAULT_EDIT_MODEL,
                   help=f"Default: {api.DEFAULT_EDIT_MODEL}")
    e.add_argument("--mask", help="Optional mask image (local path or URL)")
    e.set_defaults(func=cmd_edit)

    k = sub.add_parser("pack", help="Assemble the deck into deck.pptx + index.html")
    k.add_argument("deck", help="Deck name")
    k.add_argument("--title", help="HTML title (default: deck name)")
    k.set_defaults(func=cmd_pack)

    i = sub.add_parser("info", help="Show deck contents and metadata")
    i.add_argument("deck", help="Deck name")
    i.set_defaults(func=cmd_info)

    return p


def main() -> None:
    load_env()
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
