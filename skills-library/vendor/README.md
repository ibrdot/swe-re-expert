# Community skill collections

Two collections are already included in separate namespaces. They are not newly
created by the maintainers and are not renamed to imply different authorship.

| Website label | Folder | Actual guides | Source |
| --- | --- | ---: | --- |
| Community collection | `awesome-claude-skills/` | 864 | [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) |
| Engineering collection | `mattpocock-skills/` | 38 | [mattpocock/skills](https://github.com/mattpocock/skills) |

Read [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for pinned revisions and
licensing. Per-skill terms take precedence over collection summaries. Original
collection README files and license notices remain in place.

- [Complete name, path, and purpose catalogue](../SKILLS.md)
- [Third-party file index](SKILL_INDEX.md)

## Safe updates

1. Clone upstream into a separate temporary directory, never over the working tree.
2. Record the resolved commit and compare its files against the existing collection.
3. Review removals, local adaptations, license changes, and new dependencies.
4. Copy reviewed changes without nested `.git` directories.
5. Update the pinned revisions and regenerate both catalogues.
6. Run `python3 tools/validate_site.py` before committing.

Do not execute upstream install hooks merely to update a collection of guide files.
