import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { SharedSelection } from '../SharedSelection';
import { renderWithRouter } from '../../utils/testUtils';
import { createMockSkill } from '../../factories/skill';
import { useSkills } from '../../context/SkillContext';
import { buildSharedShortlistUrl } from '../../utils/sharedShortlist';
import { catalogVersion } from '../../utils/catalogRelease';

vi.mock('../../context/SkillContext', async (original) => ({ ...await original<typeof import('../../context/SkillContext')>(), useSkills: vi.fn() }));
const skills = [createMockSkill({ id: 'review' }), createMockSkill({ id: 'testing' })];
function open(ids = ['review'], version = catalogVersion) {
  const url = new URL(buildSharedShortlistUrl(ids, version, 'https://github.com/ibrdot/swe-re-expert', '/'));
  return renderWithRouter(<SharedSelection />, { route: url.pathname + url.hash, useProvider: false });
}

describe('shared selection import', () => {
  beforeEach(() => {
    vi.mocked(useSkills).mockReturnValue({ skills, stars: {}, loading: false, error: null, refreshSkills: vi.fn() });
    localStorage.clear();
    vi.mocked(localStorage.setItem).mockClear();
  });

  it('inspects before saving and merges without replacing an existing shortlist', async () => {
    localStorage.setItem('aas_skill_shortlist', JSON.stringify(['testing']));
    vi.mocked(localStorage.setItem).mockClear();
    open();
    expect(localStorage.setItem).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Add to my shortlist' }));
    await waitFor(() => expect(JSON.parse(localStorage.getItem('aas_skill_shortlist')!)).toEqual(['testing', 'review']));
    expect(screen.getByRole('button', { name: 'Already in your shortlist' })).toBeDisabled();
    expect(document.querySelector('meta[name="robots"]')).toHaveAttribute('content', 'noindex, follow');
  });

  it('reports version drift and missing IDs without silently saving them', async () => {
    open(['review', 'removed-skill'], '1.0.0');
    expect(screen.getByText(/Skill content may have changed/)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('removed-skill');
    fireEvent.click(screen.getByRole('button', { name: 'Add to my shortlist' }));
    await waitFor(() => expect(JSON.parse(localStorage.getItem('aas_skill_shortlist')!)).toEqual(['review']));
  });

  it('keeps storage unchanged for invalid links and edits to the shared selection', () => {
    const { unmount } = renderWithRouter(<SharedSelection />, { route: '/share/#selection=%ZZ', useProvider: false });
    expect(screen.getByRole('alert')).toHaveTextContent('invalid');
    unmount();
    open();
    fireEvent.click(screen.getByText('Compare 1 selected skill and prepare an agent brief'));
    fireEvent.click(screen.getByRole('button', { name: 'Remove review' }));
    expect(localStorage.setItem).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Add to my shortlist' })).toBeDisabled();
  });

  it('reports a rejected storage write instead of claiming success', async () => {
    open();
    vi.mocked(localStorage.setItem).mockImplementationOnce(() => { throw new Error('Denied'); });
    fireEvent.click(screen.getByRole('button', { name: 'Add to my shortlist' }));
    await waitFor(() => expect(screen.getByText(/Unable to save in this browser/)).toBeInTheDocument());
    expect(localStorage.getItem('aas_skill_shortlist')).toBeNull();
  });
});
