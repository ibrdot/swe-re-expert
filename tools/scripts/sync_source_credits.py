#!/usr/bin/env python3
"""Generate README source attribution without dropping the reviewed legacy credits."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from check_readme_credits import extract_credit_repos, normalize_repo_slug, parse_frontmatter, classify_source
from _project_paths import find_repo_root

TITLES = {"official": "Official Sources", "community": "Community Contributors"}
def load_ledger(text):
    ledger = json.loads(text)
    if ledger.get("schemaVersion") != 1 or set(ledger.get("sections", {})) != set(TITLES):
        raise ValueError("Invalid source credit ledger")
    for key, value in ledger["sections"].items():
        if isinstance(value, list) and all(isinstance(line, str) for line in value):
            ledger["sections"][key] = "\n".join(value)
    if any(not isinstance(value, str) for value in ledger["sections"].values()):
        raise ValueError("Source credit sections must be text")
    return ledger

def render_sections(ledger, skills):
    sections = dict(ledger["sections"])
    known = extract_credit_repos("\n".join("### " + TITLES[k] + "\n" + v for k,v in sections.items()))
    additions = {key: {} for key in TITLES}
    for skill_id, metadata in sorted(skills):
        raw = metadata.get("source_repo")
        if raw is None or classify_source(metadata) == "self":
            continue
        repo = normalize_repo_slug(raw)
        if not repo or classify_source(metadata) is None:
            raise ValueError(f"{skill_id}: invalid source provenance")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*", skill_id):
            raise ValueError("Invalid canonical skill ID")
        bucket = "official" if classify_source(metadata) == "official" else "community"
        if repo not in known[bucket]:
            additions[bucket].setdefault(repo, []).append(skill_id)
    for bucket in TITLES:
        rows = [f"- **[{repo}](https://github.com/{repo})**: Source for " + ", ".join(f"`{sid}`" for sid in ids) + "."
                for repo,ids in sorted(additions[bucket].items())]
        if rows:
            sections[bucket] = sections[bucket].rstrip() + "\n\n" + "\n".join(rows)
    return sections

def update_readme(text, sections):
    for bucket,title in TITLES.items():
        marker = "### " + title + "\n"
        if text.count(marker) != 1:
            raise ValueError(f"Expected one {title} heading")
        start = text.index(marker) + len(marker)
        end = text.index("</details>", start)
        text = text[:start] + "\n" + sections[bucket].strip("\n") + "\n\n" + text[end:]
    return text

def generate(root):
    ledger = load_ledger((root / "data/source-credits.json").read_text())
    skills = []
    for path in sorted((root / "skills").rglob("SKILL.md")):
        if path.is_symlink():
            raise ValueError("Linked skill metadata is not a credit source")
        skills.append((path.parent.relative_to(root / "skills").as_posix(), parse_frontmatter(path.read_text())))
    return update_readme((root / "README.md").read_text(), render_sections(ledger, skills))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = find_repo_root(__file__)
    output = generate(root)
    readme = root / "README.md"
    if args.check and output != readme.read_text():
        raise SystemExit("README source credits need sync:source-credits")
    if not args.check:
        readme.write_text(output)
    print("[source-credits] checked" if args.check else "[source-credits] synchronized")
if __name__ == "__main__":
    main()
