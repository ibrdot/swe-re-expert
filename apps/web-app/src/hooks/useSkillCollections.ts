import { useCallback, useEffect, useState } from 'react';
import { COLLECTIONS_EVENT, COLLECTIONS_KEY, newCollectionId, parseCollectionFile, serializeCollections, type SkillCollection } from '../utils/skillCollections';

function read(): SkillCollection[] {
  const text = localStorage.getItem(COLLECTIONS_KEY);
  return text === null ? [] : parseCollectionFile(text).collections;
}
function snapshot(): { collections: SkillCollection[]; error: string } {
  try { return { collections: read(), error: '' }; }
  catch { return { collections: [], error: 'Saved collections could not be read. Browser storage may be unavailable or the stored file may be invalid.' }; }
}
export function useSkillCollections() {
  const [state, setState] = useState(snapshot);
  useEffect(() => {
    const refresh = () => setState(snapshot());
    const onStorage = (event: StorageEvent) => { if (event.key === COLLECTIONS_KEY || event.key === null) refresh(); };
    window.addEventListener(COLLECTIONS_EVENT, refresh);
    window.addEventListener('storage', onStorage);
    return () => { window.removeEventListener(COLLECTIONS_EVENT, refresh); window.removeEventListener('storage', onStorage); };
  }, []);
  const update = useCallback((mutate: (current: SkillCollection[]) => SkillCollection[]): boolean => {
    try {
      // Read again so a second mounted view or tab never overwrites a stale snapshot.
      const collections = mutate(read());
      const text = serializeCollections(collections);
      localStorage.setItem(COLLECTIONS_KEY, text);
      setState({ collections, error: '' });
      window.dispatchEvent(new Event(COLLECTIONS_EVENT));
      return true;
    } catch (cause) {
      setState((previous) => ({ ...previous, error: `Collections were not saved. ${cause instanceof Error ? cause.message : 'Browser storage is unavailable.'}` }));
      return false;
    }
  }, []);
  return {
    ...state,
    save: (name: string, ids: string[], version: string) => update((current) => [...current, { id: newCollectionId(), name, note: '', version, ids: [...ids] }]),
    edit: (id: string, name: string, note: string) => update((current) => current.map((item) => item.id === id ? { ...item, name, note } : item)),
    remove: (id: string) => update((current) => current.filter((item) => item.id !== id)),
    importCollections: (incoming: SkillCollection[]) => update((current) => [...current, ...incoming.map((item) => ({ ...item, id: newCollectionId(), ids: [...item.ids] }))]),
  };
}
