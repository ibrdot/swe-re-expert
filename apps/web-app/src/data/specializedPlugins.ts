import bundleManifest from '../../../../data/editorial-bundles.json';

export interface SpecializedPlugin {
  id: string;
  name: string;
  audience: string;
  why: string;
  skills: string[];
  aliases: string[];
  notFor: string[];
  defaultPrompts: string[];
}

// One offer: every editorial pack appears once, matching the installable composition.
export const specializedPlugins: SpecializedPlugin[] = bundleManifest.bundles.map((bundle) => ({
  id: bundle.id,
  name: bundle.name,
  audience: bundle.audience,
  why: bundle.description,
  skills: bundle.skills.map((skill) => skill.id),
  aliases: bundle.aliases ?? [],
  notFor: bundle.notFor ?? [],
  defaultPrompts: bundle.defaultPrompts ?? [],
}));
