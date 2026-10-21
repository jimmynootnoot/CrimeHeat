import { useAuth } from '../context/AuthContext';

export function ViewerBanner() {
  const { isViewer } = useAuth();
  if (!isViewer) return null;

  return (
    <div className="border-b border-sky-200 bg-sky-50 px-4 py-2 text-center text-sm text-sky-900">
      <span className="font-semibold">Viewer mode — read only.</span>{' '}
      You can explore maps, records, summaries, and export reports. Upload, analysis, deletion, and user management are disabled.
    </div>
  );
}
