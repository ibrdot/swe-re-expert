import { describe, expect, it } from 'vitest';
import { redactAnalyticsUrl } from '../analyticsPrivacy';

describe('analytics URL privacy', () => {
  it('removes searches and shared fragments while preserving the public route', () => {
    expect(redactAnalyticsUrl('https://github.com/ibrdot/swe-re-expert/core/?q=private+project#selection=secret')).toBe('https://github.com/ibrdot/swe-re-expert/core/');
    expect(redactAnalyticsUrl('https://github.com/ibrdot/swe-re-expert/share/#selection=secret')).toBe('https://github.com/ibrdot/swe-re-expert/share/');
    expect(redactAnalyticsUrl('/teams/')).toBe('/teams/');
  });
});
