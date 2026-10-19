import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { GuidedDiscovery } from '../GuidedDiscovery';
import { specializedPlugins } from '../../data/specializedPlugins';
import { workflows } from '../../data/workflows';

describe('editorial guided paths', () => {
  it('links the chosen agent and real editorial packs without selecting any skills', () => {
    const focus = vi.fn();
    render(<MemoryRouter><GuidedDiscovery onWorkflow={focus} /></MemoryRouter>);
    fireEvent.click(screen.getByText('Help me get started'));
    fireEvent.change(screen.getByLabelText('My coding agent'), { target: { value: 'cursor-skills' } });
    fireEvent.submit(screen.getByRole('button', { name: 'Show my starting points' }).closest('form')!);
    let result = screen.getByRole('region', { name: 'Your starting points' });
    expect(within(result).getByRole('link', { name: /Read the Cursor setup guide/ })).toHaveAttribute('href', '/docs/cursor-skills/');
    fireEvent.click(within(result).getByRole('button', { name: 'Ship a SaaS MVP' }));
    expect(focus).toHaveBeenCalledWith('ship-saas-mvp');
    for (const goal of ['security', 'qa', 'agents', 'automation', 'web']) {
      fireEvent.change(screen.getByLabelText('I want to'), { target: { value: goal } });
      expect(screen.queryByRole('region', { name: 'Your starting points' })).not.toBeInTheDocument();
      fireEvent.submit(screen.getByRole('button', { name: 'Show my starting points' }).closest('form')!);
      result = screen.getByRole('region', { name: 'Your starting points' });
      const pack = within(result).getAllByRole('link').find((link) => link.getAttribute('href')?.startsWith('/plugins/#'))!;
      expect(specializedPlugins.some((item) => `/plugins/#${item.id}` === pack.getAttribute('href'))).toBe(true);
      for (const button of within(result).queryAllByRole('button')) expect(workflows.some((item) => item.name === button.textContent)).toBe(true);
    }
    expect(localStorage.getItem('aas_skill_shortlist')).toBeNull();
  });
});
