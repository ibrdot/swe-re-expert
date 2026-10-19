import { describe, expect, it } from 'vitest';
import { catalogNavigationState, catalogReturnTo } from '../catalogNavigation';

describe('catalog return navigation', () => {
  it.each([undefined, null, {}, { catalogReturnTo: 'https://example.com/core' },
    { catalogReturnTo: '//example.com/core' }, { catalogReturnTo: '/core/../workbench' },
    { catalogReturnTo: '/workbench' }, { catalogReturnTo: '/core#fragment' }])('falls back for an invalid state %j', (state) => {
    expect(catalogReturnTo(state)).toBe('/core');
  });
  it('carries catalog filters through subsequent skill navigation', () => {
    const state = catalogNavigationState({ pathname: '/core/', search: '?q=react&risk=safe', state: null });
    expect(catalogNavigationState({ pathname: '/skill/first/', search: '', state })).toEqual(state);
    expect(catalogReturnTo(state)).toBe('/core/?q=react&risk=safe');
  });
});
