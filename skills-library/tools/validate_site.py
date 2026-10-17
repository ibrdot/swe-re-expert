#!/usr/bin/env python3
"""Check catalogue completeness, generated docs, local assets and light-only styling."""
import json,re
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v: self.links.append(v)
def validate():
    data=json.loads((ROOT/'docs/data/skills.json').read_text())
    rows=data['skills']; ids=[s['skill_file'] for s in rows]
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('SKILL.md') if not any(x.startswith('.') for x in p.relative_to(ROOT).parts)}
    assert len(ids)==len(set(ids)), 'Duplicate skill files'
    assert set(ids)==actual, 'Catalogue missing actual skill files'
    assert data['counts']['total']==len(rows)
    assert sum(data['categories'].values())==len(rows)
    assert sum(data['counts'][k] for k in ('builtin','awesome','mattpocock'))==len(rows)
    catalogue=(ROOT/'SKILLS.md').read_text()
    for s in rows:
        assert (ROOT/s['skill_file']).is_file(), s['skill_file']
        assert s['description'].strip(), s['skill_file']
        assert s['skill_file'] in catalogue, s['skill_file']
        assert s['url'].endswith(s['skill_file'])
    for file in (ROOT/'docs').glob('*.html'):
        html=file.read_text(); parser=Links();parser.feed(html)
        assert 'color-scheme' in html
        for link in parser.links:
            if link.startswith(('https:','http:','data:','#','mailto:')): continue
            path=link.split('#')[0].split('?')[0]
            assert (file.parent/path).exists(), f'{file}: missing {link}'
    css=(ROOT/'docs/assets/style.css').read_text()
    assert 'color-scheme:only light' in css
    assert 'prefers-color-scheme:dark' not in css
    assert 'prefers-reduced-motion' in css
    assert (ROOT/'docs/.nojekyll').is_file()
    for file in [ROOT/'README.md',ROOT/'AUTHORS.md',ROOT/'GETTING_STARTED.md',ROOT/'DEPLOYMENT.md',ROOT/'THIRD_PARTY_NOTICES.md']:
        for path in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            if '://' not in path and not path.startswith(('mailto:','#')): assert (file.parent/path.split('#')[0]).exists(), f'{file}: {path}'
    api=json.loads((ROOT/'docs/api/v1/skills.json').read_text())
    assert api['counts']==data['counts']
    assert {r['skill_file'] for r in api['skills']}==actual
    assert len({r['key'] for r in api['skills']})==len(rows)
    for row in api['skills']:
        detail=ROOT/'docs/api/v1/skills'/ (row['key']+'.json')
        assert json.loads(detail.read_text())==row
    print(f'PASS: {len(rows)} unique guide files, category totals, catalogue coverage, local assets, docs links, light-only CSS')
if __name__=='__main__': validate()
