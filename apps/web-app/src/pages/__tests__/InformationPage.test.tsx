import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import InformationPage from '../InformationPage';

describe('team and transparency pages', () => {
  it('provides actionable team entry points without fetching the catalog', () => {
    render(<MemoryRouter initialEntries={['/teams/']}><InformationPage /></MemoryRouter>);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('shared starting point');
    expect(screen.getByRole('link', { name: /Compare domain packs/ })).toHaveAttribute('href', '/plugins/');
    expect(screen.getByRole('link', { name: /Core workflow and boundaries/ })).toHaveAttribute('href', '/docs/aas-core/');
    expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute('href', `${window.location.origin}/teams/`);
  });
  it('links controlling license files and private reporting rather than making certifications', () => {
    render(<MemoryRouter initialEntries={['/trust']}><InformationPage /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /Content license/ })).toHaveAttribute('href', expect.stringContaining('/LICENSE-CONTENT'));
    expect(screen.getByRole('link', { name: /Private security report/ })).toHaveAttribute('href', expect.stringContaining('/security/advisories/new'));
    expect(screen.getByText(/do not certify security/)).toBeInTheDocument();
  });
});
