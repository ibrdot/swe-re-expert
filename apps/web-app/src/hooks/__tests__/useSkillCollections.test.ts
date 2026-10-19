import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSkillCollections } from '../useSkillCollections';
import { COLLECTIONS_KEY, serializeCollections } from '../../utils/skillCollections';
describe('browser collections persistence', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());
  it('persists snapshots separately from the working shortlist and syncs mounted views', () => {
    localStorage.setItem('aas_skill_shortlist', JSON.stringify(['existing']));
    const a = renderHook(useSkillCollections); const b = renderHook(useSkillCollections);
    act(() => { a.result.current.save('First', ['first'], '19.3.0'); });
    act(() => { b.result.current.save('Second', ['second'], '19.3.0'); });
    expect(a.result.current.collections.map((item) => item.name)).toEqual(['First', 'Second']);
    expect(localStorage.getItem('aas_skill_shortlist')).toBe('["existing"]');
    const id = a.result.current.collections[0].id;
    act(() => { a.result.current.edit(id, 'Renamed', 'my note'); });
    expect(b.result.current.collections[0].note).toBe('my note');
    act(() => { b.result.current.remove(id); });
    expect(a.result.current.collections).toHaveLength(1);
  });
  it('imports as new identities while preserving existing IDs, notes and versions', () => {
    const hook = renderHook(useSkillCollections);
    act(() => { hook.result.current.save('Existing', ['existing'], '19.3.0'); });
    const original = hook.result.current.collections[0];
    act(() => { hook.result.current.importCollections([{ ...original, name: 'Imported', note: 'kept', version: '18.0.0', ids: ['missing'] }]); });
    expect(hook.result.current.collections[0]).toEqual(original);
    expect(hook.result.current.collections[1]).toMatchObject({ name: 'Imported', note: 'kept', version: '18.0.0', ids: ['missing'] });
    expect(hook.result.current.collections[1].id).not.toBe(original.id);
  });
  it('reports quota failures without displaying unsaved collections or destroying existing data', () => {
    const hook = renderHook(useSkillCollections);
    act(() => { hook.result.current.save('Existing', ['ok'], '19.3.0'); });
    const stored = localStorage.getItem(COLLECTIONS_KEY);
    vi.mocked(localStorage.setItem).mockImplementationOnce(() => { throw new DOMException('Quota exceeded'); });
    act(() => { expect(hook.result.current.save('Lost', ['other'], '19.3.0')).toBe(false); });
    expect(hook.result.current.collections).toHaveLength(1);
    expect(hook.result.current.error).toContain('not saved');
    expect(localStorage.getItem(COLLECTIONS_KEY)).toBe(stored);
  });
  it('does not overwrite malformed saved data and handles denied reads', () => {
    localStorage.setItem(COLLECTIONS_KEY, 'broken');
    const hook = renderHook(useSkillCollections);
    act(() => { expect(hook.result.current.save('New', ['ok'], '19.3.0')).toBe(false); });
    expect(localStorage.getItem(COLLECTIONS_KEY)).toBe('broken');
    vi.mocked(localStorage.getItem).mockImplementationOnce(() => { throw new DOMException('Denied'); });
    expect(renderHook(useSkillCollections).result.current.error).toContain('could not be read');
  });
  it('refreshes after an external tab changes or clears the store', () => {
    const hook = renderHook(useSkillCollections);
    localStorage.setItem(COLLECTIONS_KEY, serializeCollections([{ id: 'external', name: 'External', note: '', version: '19.3.0', ids: ['a'] }]));
    act(() => { window.dispatchEvent(new StorageEvent('storage', { key: COLLECTIONS_KEY })); });
    expect(hook.result.current.collections[0].name).toBe('External');
    localStorage.clear(); act(() => { window.dispatchEvent(new StorageEvent('storage', { key: null })); });
    expect(hook.result.current.collections).toEqual([]);
  });
});
