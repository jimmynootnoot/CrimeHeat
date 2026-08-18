import { PPALMA_MUNICIPALITIES } from '../types';

/**
 * Municipality-name canonicalization for the frontend.
 *
 * Mirrors `normalize_municipality` in backend/app/core/taxonomy.py. It is
 * needed here because the boundary GeoJSON is loaded directly by the browser
 * from /data/, bypassing the API — and that file is the PSGC source, which
 * spells one municipality "Pigkawayan" while this study displays "Pigcawayan".
 *
 * Without this, boundary features and API responses key on different strings,
 * so per-municipality statistics silently fail to join.
 */
const ALIASES: Record<string, string> = {
  alamada: 'Alamada',
  aleosan: 'Aleosan',
  libungan: 'Libungan',
  midsayap: 'Midsayap',
  pigcawayan: 'Pigcawayan',
  pigkawayan: 'Pigcawayan',
  pikit: 'Pikit',
};

export function canonicalMunicipality(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const key = String(value).trim().toLowerCase().replace(/\s+/g, ' ');
  return ALIASES[key] ?? null;
}

/** Canonical name when recognized, otherwise the original text unchanged —
 * so an unexpected value stays visible rather than silently disappearing. */
export function displayMunicipality(value: unknown, fallback = 'Unknown'): string {
  if (value === null || value === undefined) return fallback;
  return canonicalMunicipality(value) ?? String(value);
}

export const MUNICIPALITY_LIST: readonly string[] = PPALMA_MUNICIPALITIES;
