import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SkillCollections } from '../SkillCollections';
import { COLLECTIONS_KEY, serializeCollections } from '../../utils/skillCollections';

const seed = { id: 'old-list', name: 'Old selection', note: '<script>private note</script>', version: '18.0.0', ids: ['available', 'missing'] };
describe('collections user flow', () => {
  beforeEach(() => localStorage.clear());
  it('saves a named snapshot and retains private notes across reloads', () => {
    const props = { shortlistIds: ['available'], availableIds: ['available'], onAdd: vi.fn() };
    const view = render(<SkillCollections {...props} />);
    fireEvent.click(screen.getByText('My collections'));
    fireEvent.change(screen.getByLabelText('Name for this selection'), { target: { value: 'My project' } });
    fireEvent.submit(screen.getByRole('button', { name: 'Save current shortlist' }).closest('form')!);
    fireEvent.change(screen.getByLabelText('Private notes'), { target: { value: 'Review this with my team' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save details' }));
    expect(screen.getByText('Collection details saved.')).toBeInTheDocument();
    view.unmount(); render(<SkillCollections {...props} />);
    expect(screen.getByLabelText('Private notes')).toHaveValue('Review this with my team');
    expect(JSON.parse(localStorage.getItem(COLLECTIONS_KEY)!).collections[0].ids).toEqual(['available']);
  });
  it('shows catalog drift and unavailable IDs, and only adds available IDs explicitly', () => {
    localStorage.setItem(COLLECTIONS_KEY, serializeCollections([seed]));
    const add = vi.fn(); render(<SkillCollections shortlistIds={[]} availableIds={['available']} onAdd={add} />);
    fireEvent.click(screen.getByText('My collections'));
    expect(add).not.toHaveBeenCalled();
    expect(screen.getByRole('status')).toHaveTextContent('Unavailable in this catalog: missing');
    expect(screen.getByText(/not a snapshot of old skill content/)).toBeInTheDocument();
    expect(screen.getByLabelText('Private notes')).toHaveValue(seed.note);
    expect(document.querySelector('script')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Add 1 available skill to shortlist' }));
    expect(add).toHaveBeenCalledWith(['available']);
  });
  it('previews imports without overwriting saved collections and supports cancellation', async () => {
    localStorage.setItem(COLLECTIONS_KEY, serializeCollections([seed]));
    render(<SkillCollections shortlistIds={[]} availableIds={['available']} onAdd={vi.fn()} />);
    fireEvent.click(screen.getByText('My collections'));
    const file = { size: 200, text: async () => serializeCollections([{ ...seed, name: 'Imported' }]) };
    fireEvent.change(screen.getByLabelText('Import collections'), { target: { files: [file] } });
    await screen.findByRole('region', { name: 'Collection import preview' });
    expect(JSON.parse(localStorage.getItem(COLLECTIONS_KEY)!).collections).toHaveLength(1);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel import' }));
    expect(screen.queryByRole('region', { name: 'Collection import preview' })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Import collections'), { target: { files: [file] } });
    await screen.findByRole('region', { name: 'Collection import preview' });
    fireEvent.click(screen.getByRole('button', { name: 'Add imported collections' }));
    expect(JSON.parse(localStorage.getItem(COLLECTIONS_KEY)!).collections.map((item: { name: string }) => item.name)).toEqual(['Old selection', 'Imported']);
  });
  it('rejects oversized files before reading them and ignores superseded asynchronous reads', async () => {
    render(<SkillCollections shortlistIds={[]} availableIds={[]} onAdd={vi.fn()} />);
    const text = vi.fn();
    fireEvent.change(screen.getByLabelText('Import collections'), { target: { files: [{ size: 300000, text }] } });
    expect(text).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('too large');
    let resolve!: (text: string) => void;
    fireEvent.change(screen.getByLabelText('Import collections'), { target: { files: [{ size: 100, text: () => new Promise<string>((done) => { resolve = done; }) }] } });
    fireEvent.change(screen.getByLabelText('Import collections'), { target: { files: [{ size: 10, text: async () => 'broken' }] } });
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('valid AAS collections'));
    resolve(serializeCollections([seed]));
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Collection import preview' })).not.toBeInTheDocument());
  });
});
