/**
 * Theme Design Token Helper
 * Dynamically resolves CSS Custom Properties (variables) defined in :root.
 * Used primarily for Chart.js canvas rendering and programmatic token queries.
 */
export function getCssToken(name: string, fallback: string): string {
  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (val) return val;
  }
  return fallback;
}
