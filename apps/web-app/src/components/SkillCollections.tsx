import { useEffect, useRef, useState } from 'react';
import { useSkillCollections } from '../hooks/useSkillCollections';
import { MAX_COLLECTION_FILE_BYTES, MAX_COLLECTION_SKILLS, parseCollectionFile, serializeCollections, type SkillCollection } from '../utils/skillCollections';
import { catalogVersion } from '../utils/catalogRelease';

function CollectionEditor({ collection, available, onEdit, onRemove, onAdd }: { collection: SkillCollection; available: Set<string>; onEdit: (id: string, name: string, note: string) => boolean; onRemove: (id: string) => boolean; onAdd: (ids: string[]) => void }) {
  const [name, setName] = useState(collection.name);
  const [note, setNote] = useState(collection.note);
  const [message, setMessage] = useState('');
  const found = collection.ids.filter((id) => available.has(id));
  const missing = collection.ids.filter((id) => !available.has(id));
  return <div className="collection-editor">
    <p>{collection.ids.length} skill {collection.ids.length === 1 ? 'ID' : 'IDs'} · catalog v{collection.version}</p>
    {collection.version !== catalogVersion && <p>Current catalog: v{catalogVersion}. This list pins IDs and a version label, not a snapshot of old skill content.</p>}
    {missing.length > 0 && <p role="status">Unavailable in this catalog: {missing.join(', ')}. These IDs remain in the collection and will not be added to your shortlist.</p>}
    <label>Collection name<input maxLength={80} value={name} onChange={(event) => { setName(event.target.value); setMessage(''); }} /></label>
    <label>Private notes<textarea maxLength={2000} rows={3} value={note} onChange={(event) => { setNote(event.target.value); setMessage(''); }} /></label>
    <div className="platform-actions">
      <button type="button" onClick={() => setMessage(onEdit(collection.id, name, note) ? 'Collection details saved.' : 'Collection details were not saved.')}>Save details</button>
      <button type="button" disabled={!found.length} onClick={() => { onAdd(found); setMessage('Available IDs sent to your shortlist. Check its selected count; your previous selection is preserved.'); }}>Add {found.length} available {found.length === 1 ? 'skill' : 'skills'} to shortlist</button>
      <button type="button" onClick={() => onRemove(collection.id)}>Delete collection</button>
    </div>
    <details><summary>Inspect exact IDs</summary><p className="collection-ids">{collection.ids.join(', ')}</p></details>
    {message && <p role="status">{message}</p>}
  </div>;
}

export function SkillCollections({ shortlistIds, availableIds, onAdd, standalone = false }: { shortlistIds: string[]; availableIds: string[]; onAdd: (ids: string[]) => void; standalone?: boolean }): React.ReactElement {
  const store = useSkillCollections();
  const importAttempt = useRef(0);
  useEffect(() => () => { importAttempt.current += 1; }, []);
  const [name, setName] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [pending, setPending] = useState<SkillCollection[] | null>(null);
  const [importError, setImportError] = useState('');
  const [message, setMessage] = useState('');
  const selected = store.collections.find((item) => item.id === selectedId) || store.collections[0];
  const available = new Set(availableIds);
  const exportAll = () => {
    let url: string | undefined;
    try {
      url = URL.createObjectURL(new Blob([serializeCollections(store.collections)], { type: 'application/json' }));
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'aas-collections.json'; anchor.click();
      setMessage('Export prepared. The file includes collection names and private notes.');
    } catch { setMessage('Export unavailable in this browser. Your saved collections are unchanged.'); }
    finally { if (url) window.setTimeout(() => URL.revokeObjectURL(url!), 1000); }
  };
  return <details className="platform-panel skill-collections" id="skill-collections" open={standalone || undefined}>
    <summary>My collections <span>{store.collections.length} saved on this device</span></summary>
    <div className="platform-panel__body">
      <p>Save multiple selections with names and notes. No account or automatic device sync. Export a backup before clearing site data.</p>
      <form className="collection-save" onSubmit={(event) => { event.preventDefault(); if (store.save(name.trim(), shortlistIds, catalogVersion)) { setName(''); setMessage('Current shortlist saved as a new collection.'); } }}>
        <label>Name for this selection<input value={name} maxLength={80} placeholder="For example: Frontend review" onChange={(event) => setName(event.target.value)} required /></label>
        <button disabled={!shortlistIds.length || shortlistIds.length > MAX_COLLECTION_SKILLS || store.collections.length >= 20} type="submit">Save current shortlist</button>
      </form>
      {shortlistIds.length > MAX_COLLECTION_SKILLS && <p>Collections support up to 200 skills. Reduce your shortlist before saving it.</p>}
      {store.collections.length >= 20 && <p>You have reached the limit of 20 collections. Export a backup before deleting a collection.</p>}
      {store.error && <p role="alert">{store.error}</p>}
      {store.collections.length ? <>
        <label>Open collection<select value={selected?.id || ''} onChange={(event) => setSelectedId(event.target.value)}>{store.collections.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.ids.length})</option>)}</select></label>
        {selected && <CollectionEditor key={JSON.stringify(selected)} collection={selected} available={available} onEdit={(id, updatedName, note) => { const saved = store.edit(id, updatedName, note); setMessage(saved ? 'Collection details saved.' : 'Collection details were not saved.'); return saved; }} onRemove={(id) => { const removed = store.remove(id); setMessage(removed ? 'Collection deleted.' : 'Collection was not deleted.'); return removed; }} onAdd={onAdd} />}
      </> : <p>No collections yet. Select a few skills, then save your shortlist here.</p>}
      <div className="platform-actions"><button type="button" disabled={!store.collections.length} onClick={exportAll}>Export collections</button>
        <label className="collection-import">Import collections<input type="file" accept=".json,application/json" aria-label="Import collections" onChange={async (event) => {
          const attempt = ++importAttempt.current; const file = event.target.files?.[0]; event.target.value = ''; setPending(null); setImportError(''); setMessage(''); if (!file) return;
          try { if (file.size > MAX_COLLECTION_FILE_BYTES) throw new Error('Collection file is too large (maximum 256 KB).'); const data = parseCollectionFile(await file.text()); if (attempt !== importAttempt.current) return; if (!data.collections.length) throw new Error('This file contains no collections.'); setPending(data.collections); }
          catch (cause) { if (attempt !== importAttempt.current) return; setImportError(cause instanceof Error ? cause.message : 'Unable to read this collection file.'); }
        }} /></label>
      </div>
      {importError && <p role="alert">{importError}</p>}
      {pending && <section className="collection-preview" aria-label="Collection import preview"><h3>Review import</h3><p>{pending.length} new {pending.length === 1 ? 'collection' : 'collections'} will be added. Existing collections will be preserved. Imported notes are displayed as plain text.</p><ul>{pending.map((item) => <li key={item.id}>{item.name} · {item.ids.length} {item.ids.length === 1 ? 'ID' : 'IDs'} · v{item.version}{item.ids.some((id) => !available.has(id)) ? ' · includes unavailable IDs' : ''}</li>)}</ul><div className="platform-actions"><button type="button" onClick={() => { if (store.importCollections(pending)) { setPending(null); setMessage('Collections imported. Your existing collections are preserved.'); } }}>Add imported collections</button><button type="button" onClick={() => { importAttempt.current += 1; setPending(null); }}>Cancel import</button></div></section>}
      {message && <p role="status">{message}</p>}
    </div>
  </details>;
}
