#!/usr/bin/env python3
"""Index every actual SKILL.md, once, using only the Python standard library."""
from pathlib import Path
from collections import Counter
import json, re

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/ibrdot/ai-agent-skills'
CATEGORIES = {
 'camoufox-cli':'Browser automation', 'chrome-devtools':'Browser automation',
 'deep-research':'Research', 'planning-with-files':'Planning', 'github':'Engineering',
 'linear':'Productivity','sentry':'Observability','posthog':'Analytics',
 'notion':'Productivity','mcp-hub':'Integrations','pptx':'Documents',
 'pptx-native':'Documents','document-reader':'Documents','remotion':'Media',
 'video-frames':'Media','gifgrep':'Media','weather':'Utilities','airtable':'Data',
 'discord':'Communication','slack-api':'Communication','outlook':'Communication'
}

def frontmatter(text):
    """Read the simple scalar YAML fields used by skill manifests, no execution."""
    match = re.match(r'\A---\s*\n(.*?)\n---(?:\s*\n|$)', text, re.S)
    if not match:
        return {}
    result = {}
    for field in ('name', 'description', 'license', 'category'):
        m = re.search(r'^'+field+r':\s*(.*?)(?=\n[^\s#][\w-]*:|\Z)', match[1], re.M|re.S)
        if m:
            value = m.group(1).strip()
            if value.startswith(('>', '|')):
                value = re.sub(r'^[>|][-+]?\s*', '', value)
            result[field] = ' '.join(value.strip('\"\'').split())
    return result

def build():
    skills = []
    for file in sorted(ROOT.rglob('SKILL.md')):
        rel = file.relative_to(ROOT)
        if any(p.startswith('.') for p in rel.parts):
            continue
        meta = frontmatter(file.read_text(encoding='utf-8', errors='replace'))
        top = rel.parts[0]
        collection, label = 'builtin', 'Suite skills'
        category = meta.get('category') or CATEGORIES.get(top, 'Utilities')
        if top.startswith('gws-') or top.startswith('google_'):
            category = 'Google Workspace'
        if rel.parts[:2] == ('vendor', 'awesome-claude-skills'):
            collection, label = 'awesome', 'Community collection'
            category = 'Integrations' if 'composio-skills' in rel.parts else 'Creative & workflow'
            if 'document-skills' in rel.parts: category = 'Documents'
        elif rel.parts[:2] == ('vendor', 'mattpocock-skills'):
            collection, label = 'mattpocock', 'Engineering collection'
            category = {'engineering':'Engineering', 'productivity':'Productivity',
                        'misc':'Utilities', 'in-progress':'Experimental', 'deprecated':'Deprecated'}.get(rel.parts[3] if len(rel.parts)>3 else '', 'Engineering')
        source_license = meta.get('license')
        if not source_license:
            if collection == 'mattpocock': source_license = 'MIT'
            elif collection == 'awesome': source_license = 'See upstream and per-skill terms'
            elif top == 'chrome-devtools': source_license = 'Apache-2.0 (suite license)'
            else: source_license = 'Not specified; verify before redistribution'
        path = rel.parent.as_posix()+'/'
        skills.append(dict(id=rel.as_posix(), name=meta.get('name') or file.parent.name,
                           collection=collection, collection_label=label, category=category,
                           path=path, skill_file=rel.as_posix(),
                           url=REPO+'/blob/main/'+rel.as_posix(),
                           description=meta.get('description') or 'Read this skill guide for its workflow and setup.',
                           mode='Guide', license=source_license))
    counts = {'total':len(skills), **{c:sum(s['collection']==c for s in skills) for c in ('builtin','awesome','mattpocock')}}
    output = dict(schema_version=2, counts=counts, categories=dict(sorted(Counter(s['category'] for s in skills).items())), skills=skills)
    out = ROOT/'docs/data/skills.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')
    print(json.dumps(counts))

if __name__ == '__main__': build()
