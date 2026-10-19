import { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router';
import { ShortlistReview } from '../components/ShortlistReview';
import { useSkills } from '../context/SkillContext';
import { usePageMeta } from '../hooks/usePageMeta';
import { useSkillShortlist } from '../hooks/useSkillShortlist';
import { catalogVersion } from '../utils/catalogRelease';
import { parseSharedShortlist, type SharedShortlist } from '../utils/sharedShortlist';
import './SharedSelection.css';

function Selection({ selection }: { selection: SharedShortlist }): React.ReactElement {
  const { skills, loading, error } = useSkills();
  const [selectionIds, setSelectionIds] = useState(selection.ids);
  const [saveAttempted, setSaveAttempted] = useState(false);
  const { ids: savedIds, addMany } = useSkillShortlist();
  const byId = useMemo(() => new Map(skills.map((skill) => [skill.id, skill])), [skills]);
  const found = selectionIds.flatMap((id) => { const skill = byId.get(id); return skill ? [skill] : []; });
  const missing = selectionIds.filter((id) => !byId.has(id));
  const saved = found.length > 0 && found.every((skill) => savedIds.includes(skill.id));

  if (loading) return <p role="status">Loading the catalog…</p>;
  if (error) return <p role="alert">The catalog could not be loaded. Reload this page to try again.</p>;

  return <>
    <p>Shared from catalog v{selection.version}. This is a selection to inspect, not a validated stack.</p>
    {selection.version !== catalogVersion ? <p role="status">You are viewing catalog v{catalogVersion}. Skill content may have changed since this link was created.</p> : null}
    {missing.length ? <p role="alert">Unavailable in this catalog: {missing.join(', ')}. These IDs will not be added.</p> : null}
    <ShortlistReview shared skills={found} onRemove={(id) => setSelectionIds((current) => current.filter((item) => item !== id))} onClear={() => setSelectionIds([])} />
    <div className="shared-selection__actions">
      <button type="button" disabled={!found.length || saved} onClick={() => { addMany(found.map((skill) => skill.id)); setSaveAttempted(true); }}>
        {saved ? 'Already in your shortlist' : 'Add to my shortlist'}
      </button>
      <Link to="/core/?scope=shortlist">Open my shortlist →</Link>
    </div>
    {saveAttempted ? <p role="status">{saved ? 'Added to your shortlist. Your previous selection is preserved.' : 'Unable to save in this browser. You can still inspect this selection and copy its IDs or brief.'}</p> : null}
  </>;
}

export function SharedSelection(): React.ReactElement {
  const { hash } = useLocation();
  const selection = useMemo(() => parseSharedShortlist(hash), [hash]);
  usePageMeta({ title: 'Shared skill selection | Agentic Awesome Skills', description: 'Inspect a shared skill selection and prepare a brief for your coding agent.', canonicalPath: '/share/', robots: 'noindex, follow' });

  return <div className="shared-selection">
    <Link to="/core/">← Browse all skills</Link>
    <h1>A shortlist worth sharing.</h1>
    <p>No account needed. Opening a link does not change your saved shortlist.</p>
    {selection ? <Selection key={hash} selection={selection} /> : <p role="alert">This selection link is missing or invalid. Create a new link with “Share selection” in the catalog.</p>}
  </div>;
}

export default SharedSelection;
