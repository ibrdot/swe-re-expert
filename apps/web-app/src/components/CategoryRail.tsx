import { useState } from 'react';

const groups = [
  { name: 'Build & test', categories: ['development', 'web-development', 'frontend', 'backend', 'code', 'coding', 'code-quality', 'testing', 'test-automation', 'architecture', 'framework', 'api-integration', 'database', 'mobile', 'game-development', 'browser-automation', 'developer-tools', 'app-builder', 'core-dev'] },
  { name: 'AI & data', categories: ['ai-ml', 'ai-agents', 'ai', 'agent-orchestration', 'agent-tooling', 'agent-evaluation', 'agent-persona', 'agent-behavior', 'agent-squad', 'mcp', 'data', 'data-ai', 'data-science', 'data-engineering', 'data-engineering-platform', 'memory', 'knowledge-management', 'reasoning', 'context-optimization'] },
  { name: 'Security & operations', categories: ['security', 'devops', 'cloud', 'reliability', 'operations', 'observability', 'pentest-tools'] },
  { name: 'Design & content', categories: ['design', 'design-it', 'creative', 'content', 'writing', 'media', 'graphics-processing', 'document-processing', 'document-verification', 'presentation-processing', 'spreadsheet-processing', 'media-processing', 'video', 'voice-agents', 'localization'] },
  { name: 'Business & workflows', categories: ['business', 'business-strategy', 'marketing', 'growth', 'seo', 'finance', 'legal', 'consulting', 'product', 'product-management', 'project-management', 'planning', 'productivity', 'workflow', 'workflow-bundle', 'granular-workflow-bundle', 'automation', 'research', 'education', 'engineering', 'science', 'health', 'personal-development'] },
] as const;
export function categoryGroups(categories: string[]): { name: string; categories: string[] }[] {
  const assigned = new Set<string>();
  const result: { name: string; categories: string[] }[] = groups.map((group) => ({ name: group.name, categories: categories.filter((category) => {
    if (!(group.categories as readonly string[]).includes(category) || assigned.has(category)) return false;
    assigned.add(category); return true;
  }) })).filter((group) => group.categories.length);
  const other = categories.filter((category) => category !== 'all' && !assigned.has(category));
  if (other.length) result.push({ name: 'More categories', categories: other });
  return result;
}
export function categoryLabel(category: string): string { return category === 'all' ? 'All categories' : category.replace(/[-_]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()); }

export function CategoryRail({ categories, stats, total, selected, onSelect }: { categories: string[]; stats: Record<string, number>; total: number; selected: string; onSelect: (category: string) => void }): React.ReactElement {
  const [query, setQuery] = useState('');
  const visible = categories.filter((category) => category !== 'all' && categoryLabel(category).toLowerCase().includes(query.trim().toLowerCase()));
  const button = (category: string) => <button key={category} type="button" className={selected === category ? 'is-active' : ''} aria-pressed={selected === category} aria-label={`${categoryLabel(category)}, ${category === 'all' ? total : stats[category] || 0} skills`} onClick={() => onSelect(category)}><span>{categoryLabel(category)}</span><span>{category === 'all' ? total : stats[category] || 0}</span></button>;
  return <>
    <p className="catalog-rail__label">Browse categories</p>
    <label className="category-search">Find a category<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={100} placeholder="Search categories" /></label>
    <nav aria-label="Categories">
      {button('all')}
      {selected !== 'all' && <p className="category-selected">Selected: {categoryLabel(selected)}</p>}
      {query.trim() ? <><p role="status">{visible.length} matching categories</p>{visible.map(button)}</> : categoryGroups(categories).map((group) => <details key={group.name} open={group.categories.includes(selected) || undefined}><summary>{group.name}<span>{group.categories.length}</span></summary>{group.categories.map(button)}</details>)}
    </nav>
  </>;
}
