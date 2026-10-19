/** Only send the public route to analytics, never searches or shared selections. */
export function redactAnalyticsUrl(value: string): string {
  return value.split(/[?#]/, 1)[0];
}
