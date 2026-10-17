#!/usr/bin/env python3
"""Generate complete human-readable indexes from the canonical JSON catalogue."""
import json
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parents[1]

def esc(text): return str(text).replace('|', '\\|').replace('\n', ' ')

def build():
    data = json.loads((ROOT/'docs/data/skills.json').read_text())
    rows = data['skills']
    lines = ['# Complete skill catalogue', '', f"**{len(rows)} actual SKILL.md guides**, indexed once by file path.", '',
             'Every entry includes its name, exact file, category, purpose, and license guidance.', '',
             'A skill is an instruction guide, not an installed tool. Read its SKILL.md and prerequisites before use.', '',
             'Third-party notices are preserved in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).', '',
             '## Collections', '', '| Collection | Guides |', '| --- | ---: |']
    labels = {'builtin':'Suite skills','awesome':'Community collection','mattpocock':'Engineering collection'}
    for key,label in labels.items(): lines.append(f"| {label} | {data['counts'][key]} |")
    for key,label in labels.items():
        lines += ['', '## '+label, '']
        groups=defaultdict(list)
        for s in rows:
            if s['collection']==key: groups[s['category']].append(s)
        for category, items in sorted(groups.items()):
            lines += ['### '+category, '', '| Name and guide | Folder path | What it does / when to use | License |', '| --- | --- | --- | --- |']
            for s in items:
                lines.append(f"| [{esc(s['name'])}]({s['skill_file']}) | `{s['path']}` | {esc(s['description'])} | {esc(s['license'])} |")
            lines += ['']
    lines += ['## Regenerate', '', '```sh', 'python3 tools/build_skills_index.py', 'python3 tools/build_skill_docs.py', 'python3 tools/validate_site.py', '```', '']
    (ROOT/'SKILLS.md').write_text('\n'.join(lines))
    vendor = ['# Third-party skill file index', '', 'Generated from actual SKILL.md files. See [notices](../THIRD_PARTY_NOTICES.md) for source and license details.', '']
    for s in rows:
        if s['collection']!='builtin': vendor.append(f"- [{s['name']}]({s['skill_file'].removeprefix('vendor/')}) - `{s['path']}` - {esc(s['description'])}")
    (ROOT/'vendor').mkdir(exist_ok=True)
    (ROOT/'vendor/SKILL_INDEX.md').write_text('\n'.join(vendor)+'\n')
    # Static pages get their totals from the same index, including no-JavaScript content.
    import re
    for name in ('index.html','skills.html'):
        path=ROOT/'docs'/name
        if path.exists():
            text=path.read_text()
            for key,value in [('total',data['counts']['total']),('categories',len(data['categories'])),('builtin',data['counts']['builtin']),('community',data['counts']['awesome']+data['counts']['mattpocock'])]:
                text=re.sub(r'(?<=data-stat="'+key+r'">)[^<]*', str(value), text)
            path.write_text(text)
    # Keep prose/table totals in maintained landing docs synchronized as well.
    readme=ROOT/'README.md'
    if readme.exists():
        text=readme.read_text()
        text=re.sub(r'\*\*\d+ actual `SKILL.md` guides:\*\* \d+ suite guides, \d+ community guides, and \d+\s+engineering guides\.',f"**{len(rows)} actual `SKILL.md` guides:** {data['counts']['builtin']} suite guides, {data['counts']['awesome']} community guides, and {data['counts']['mattpocock']} engineering guides.",text)
        readme.write_text(text)
    vendor_readme=ROOT/'vendor/README.md'
    if vendor_readme.exists():
        text=vendor_readme.read_text()
        for folder,key in [('awesome-claude-skills','awesome'),('mattpocock-skills','mattpocock')]:
            text=re.sub(r'(`'+folder+r'/` \| )\d+( \|)',lambda m:m.group(1)+str(data['counts'][key])+m.group(2),text)
        vendor_readme.write_text(text)
    print(f'Generated documentation for {len(rows)} guides')

if __name__=='__main__': build()
