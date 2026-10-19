import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CategoryRail, categoryGroups } from '../CategoryRail';

describe('category navigation', () => {
  it('preserves every canonical category exactly once, including unfamiliar categories', () => {
    const categories = ['all', 'frontend', 'security', 'ai-ml', 'rare-domain', 'uncategorized'];
    const grouped = categoryGroups(categories).flatMap((group) => group.categories);
    expect(new Set(grouped).size).toBe(categories.length - 1);
    expect([...grouped].sort()).toEqual(categories.slice(1).sort());
  });
  it('searches labels and keeps the full catalog reachable when no category matches', () => {
    const select = vi.fn();
    render(<CategoryRail categories={['all', 'rare-domain', 'security']} stats={{ 'rare-domain': 2, security: 3 }} total={5} selected="security" onSelect={select} />);
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'rare domain' } });
    fireEvent.click(screen.getByRole('button', { name: 'Rare Domain, 2 skills' }));
    expect(select).toHaveBeenCalledWith('rare-domain');
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'absent' } });
    expect(screen.getByRole('status')).toHaveTextContent('0 matching categories');
    fireEvent.click(screen.getByRole('button', { name: 'All categories, 5 skills' }));
    expect(select).toHaveBeenCalledWith('all');
  });
});
