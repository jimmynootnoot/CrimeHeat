import { DEMO_MODE } from '../api/client';

/**
 * Demonstration-mode banner.
 *
 * Stays visible on every screen for as long as the system is running on
 * synthetic data. It is deliberately not dismissible: a reader who sees a
 * cluster map without this notice could reasonably mistake it for an official
 * PNP finding.
 */
export function DevModeBanner() {
  if (!DEMO_MODE) return null;

  return (
    <div
      role="status"
      className="w-full bg-amber-400 px-4 py-1.5 text-center text-sm font-semibold text-amber-950"
    >
      DEMONSTRATION MODE — Results are based on synthetic data and must not be interpreted as
      official PNP findings.
    </div>
  );
}
