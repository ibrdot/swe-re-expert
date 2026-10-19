import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import bundles from '../../../../../data/editorial-bundles.json';
import { specializedPlugins } from '../../data/specializedPlugins';
import { catalogVersion } from '../../utils/catalogRelease';
import { Plugins } from '../Plugins';
import { renderWithRouter } from '../../utils/testUtils';

describe('Plugins', () => {
  it(
    'renders the specialized plugin catalog and sets metadata',
    () => {
      renderWithRouter(<Plugins />, { route: '/plugins', path: '/plugins', useProvider: false });

      expect(screen.getByRole('heading', { name: /Choose the focused AAS plugin/i })).toBeInTheDocument();
      expect(screen.getByText('AAS Web App Builder')).toBeInTheDocument();
      expect(screen.getByText('AAS Security Engineer')).toBeInTheDocument();
      expect(screen.getByText('AAS Marketing, SEO & Growth')).toBeInTheDocument();
      expect(screen.getByText(/distributions of the full skill library/i)).toBeInTheDocument();
      expect(screen.queryByText(/1,550\+/i)).not.toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Install one skill with GitHub CLI/i })).toHaveAttribute(
        'href',
        '/docs/getting-started/',
      );
      expect(screen.getByText(/Plugins, bundles, and workflows serve different decisions/i)).toBeInTheDocument();
      expect(screen.getAllByRole('link', { name: '@frontend-developer' })[0]).toHaveAttribute(
        'href',
        '/skill/frontend-developer/',
      );
      expect(document.title).toContain('AAS Specialized Plugins');
      expect(document.querySelector('meta[name="description"]')).toHaveAttribute(
        'content',
        expect.stringContaining('specialized plugin'),
      );
    },
    20_000,
  );
});

describe('canonical specialized plugin definitions', () => {
  it('shows every source plugin with exactly its installable composition and current copy', () => {
    expect(specializedPlugins.map((plugin) => plugin.id)).toEqual(bundles.bundles.map((plugin) => plugin.id));
    for (const plugin of specializedPlugins) {
      const bundle = bundles.bundles.find((entry) => entry.id === plugin.id)!;
      expect(plugin.skills).toEqual(bundle.skills.map((skill) => skill.id));
      expect(plugin.why).toBe(bundle.description);
      expect(plugin.defaultPrompts).toEqual(bundle.defaultPrompts);
      expect(plugin.notFor).toEqual(bundle.notFor);
    }
  });

  it('offers one replacement for retired packs and includes the remaining distinct jobs', () => {
    expect(specializedPlugins).toHaveLength(bundles.bundles.length);
    const ids = new Set(specializedPlugins.map((plugin) => plugin.id));
    for (const migration of bundles.migrations) {
      expect(ids.has(migration.from)).toBe(false);
      expect(ids.has(migration.to)).toBe(true);
    }
    expect(ids.has('odoo-erp')).toBe(true);
    expect(ids.has('oss-maintainer')).toBe(true);
  });

  it('finds the one current pack when searching for a retired ID', () => {
    renderWithRouter(<Plugins />, { route: '/plugins', path: '/plugins', useProvider: false });
    fireEvent.change(screen.getByLabelText('Filter plugins'), { target: { value: 'web-wizard' } });
    expect(screen.getByRole('status')).toHaveTextContent('1 plugin');
    expect(screen.getByRole('heading', { name: 'AAS Web App Builder' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Web Wizard' })).not.toBeInTheDocument();
  });

  it('filters by exact included skill and exposes the full list and scope', () => {
    renderWithRouter(<Plugins />, { route: '/plugins', path: '/plugins', useProvider: false });
    expect(screen.getByRole('status')).toHaveTextContent(`${specializedPlugins.length} plugins`);
    fireEvent.change(screen.getByLabelText('Filter plugins'), { target: { value: 'web-app' } });
    expect(screen.getByRole('status')).toHaveTextContent('1 plugin');
    const row = screen.getByText('AAS Web App Builder').closest('[role="row"]')! as HTMLElement;
    const plugin = specializedPlugins.find((entry) => entry.id === 'web-app')!;
    fireEvent.click(within(row).getByText(`Show all ${plugin.skills.length} skills`));
    expect(within(row).getByRole('link', { name: '@browser-automation' })).toBeVisible();
    expect(within(row).getByRole('link', { name: '@nextjs-best-practices' })).toBeVisible();
    fireEvent.click(within(row).getByText('Scope and starting prompt'));
    expect(within(row).getByText(/report checks actually run/)).toBeVisible();
    expect(within(row).getByRole('link', { name: 'View plugin' })).toHaveAttribute('href', expect.stringContaining(`/tree/v${catalogVersion}/plugins/`));
    fireEvent.change(screen.getByLabelText('Filter plugins'), { target: { value: 'no-such-plugin-unique' } });
    expect(screen.getByText(/No plugins match/)).toBeVisible();
  });

  it.each(specializedPlugins)('exposes every expanded member in $name', (plugin) => {
    renderWithRouter(<Plugins />, { route: '/plugins', path: '/plugins', useProvider: false });
    fireEvent.change(screen.getByLabelText('Filter plugins'), { target: { value: plugin.id } });
    const row = screen.getByText(plugin.name).closest('[role="row"]')! as HTMLElement;
    const expanded = within(row).getByText(`Show all ${plugin.skills.length} skills`);
    fireEvent.click(expanded);
    for (const id of plugin.skills) {
      expect(within(row).getByRole('link', { name: `@${id}` })).toBeVisible();
    }
    if (plugin.skills.length !== 10) expect(within(row).queryByText('Show all 10 skills')).not.toBeInTheDocument();
  });
});
