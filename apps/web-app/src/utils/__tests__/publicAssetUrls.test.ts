import { describe, expect, it } from 'vitest';

import {
  getAbsolutePublicAssetUrl,
  getSkillMarkdownCandidateUrls,
  getSkillsIndexCandidateUrls,
  normalizeBasePath,
} from '../publicAssetUrls';

describe('public asset URL helpers', () => {
  it('resolves hosted assets at the custom-domain root', () => {
    expect(
      getSkillsIndexCandidateUrls({
        baseUrl: '/',
        origin: 'https://swe-re-expert.vercel.app',
        pathname: '/skill/some-id',
        documentBaseUrl: 'https://swe-re-expert.vercel.app/',
      }),
    ).toEqual([
      'https://swe-re-expert.vercel.app/skills.json',
      'https://swe-re-expert.vercel.app/skills.json.backup',
      'https://swe-re-expert.vercel.app/skill/skills.json',
      'https://swe-re-expert.vercel.app/skill/skills.json.backup',
      'https://swe-re-expert.vercel.app/skill/some-id/skills.json',
      'https://swe-re-expert.vercel.app/skill/some-id/skills.json.backup',
    ]);
  });

  it('normalizes dot-relative BASE_URL values', () => {
    expect(normalizeBasePath('./')).toBe('/');
    expect(normalizeBasePath('/agentic-awesome-skills/')).toBe('/agentic-awesome-skills/');
  });

  it('builds stable skills index candidates for gh-pages routes', () => {
    expect(
      getSkillsIndexCandidateUrls({
        baseUrl: '/agentic-awesome-skills/',
        origin: 'https://ibrdot.github.io',
        pathname: '/agentic-awesome-skills/skill/some-id',
        documentBaseUrl: 'https://ibrdot.github.io/agentic-awesome-skills/',
      }),
    ).toEqual([
      'https://ibrdot.github.io/agentic-awesome-skills/skills.json',
      'https://ibrdot.github.io/agentic-awesome-skills/skills.json.backup',
      'https://ibrdot.github.io/skills.json',
      'https://ibrdot.github.io/skills.json.backup',
      'https://ibrdot.github.io/agentic-awesome-skills/skill/skills.json',
      'https://ibrdot.github.io/agentic-awesome-skills/skill/skills.json.backup',
      'https://ibrdot.github.io/agentic-awesome-skills/skill/some-id/skills.json',
      'https://ibrdot.github.io/agentic-awesome-skills/skill/some-id/skills.json.backup',
    ]);
  });

  it('builds stable markdown candidates for gh-pages routes', () => {
    expect(
      getSkillMarkdownCandidateUrls({
        baseUrl: '/agentic-awesome-skills/',
        origin: 'https://ibrdot.github.io',
        pathname: '/agentic-awesome-skills/skill/react-patterns',
        documentBaseUrl: 'https://ibrdot.github.io/agentic-awesome-skills/',
        skillPath: 'skills/react-patterns',
      }),
    ).toEqual([
      'https://ibrdot.github.io/agentic-awesome-skills/skills/react-patterns/SKILL.md',
      'https://ibrdot.github.io/skills/react-patterns/SKILL.md',
      'https://ibrdot.github.io/agentic-awesome-skills/skill/skills/react-patterns/SKILL.md',
      'https://ibrdot.github.io/agentic-awesome-skills/skill/react-patterns/skills/react-patterns/SKILL.md',
    ]);
  });

  it('rejects markdown asset paths that escape the skills tree', () => {
    const input = {
      baseUrl: '/agentic-awesome-skills/',
      origin: 'https://ibrdot.github.io',
      pathname: '/agentic-awesome-skills/skill/react-patterns',
      documentBaseUrl: 'https://ibrdot.github.io/agentic-awesome-skills/',
    };

    expect(getSkillMarkdownCandidateUrls({ ...input, skillPath: 'skills/../../manifest.webmanifest' })).toEqual([]);
    expect(getSkillMarkdownCandidateUrls({ ...input, skillPath: 'skills/%2e%2e/%2e%2e/manifest.webmanifest' })).toEqual([]);
    expect(getSkillMarkdownCandidateUrls({ ...input, skillPath: 'https://evil.example/skills/demo' })).toEqual([]);
  });

  it('resolves absolute public asset URLs from the shared base path logic', () => {
    expect(
      getAbsolutePublicAssetUrl('/skill/react-patterns', {
        baseUrl: '/agentic-awesome-skills/',
        origin: 'https://ibrdot.github.io',
      }),
    ).toBe('https://ibrdot.github.io/agentic-awesome-skills/skill/react-patterns');
  });
});
