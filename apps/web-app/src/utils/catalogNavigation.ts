interface CatalogLocation {
  pathname: string;
  search: string;
  state: unknown;
}

export function catalogReturnTo(state: unknown): string {
  const candidate = state && typeof state === 'object' && 'catalogReturnTo' in state
    ? state.catalogReturnTo : undefined;
  return typeof candidate === 'string' && /^\/core\/?(?:\?[^#]*)?$/.test(candidate)
    ? candidate : '/core';
}

export function catalogNavigationState(location: CatalogLocation): { catalogReturnTo: string } {
  return { catalogReturnTo: /^\/core\/?$/.test(location.pathname)
    ? `${location.pathname}${location.search}` : catalogReturnTo(location.state) };
}
