import {
  PERSISTENCE_CATEGORY_DESCRIPTIONS,
  PERSISTENCE_CATEGORY_LABELS,
  type PersistenceFeatureProperties,
} from '../../types';
import { DetailDrawer } from './DetailDrawer';

export function PersistenceDetailPanel({
  record,
  onClose,
}: {
  record: PersistenceFeatureProperties;
  onClose: () => void;
}) {
  return (
    <DetailDrawer
      title={record.municipality}
      subtitle={PERSISTENCE_CATEGORY_LABELS[record.category]}
      onClose={onClose}
    >
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded bg-slate-50 p-3">
          <div className="text-2xl font-bold text-slate-900">
            {Math.round(record.persistence_score * 100)}%
          </div>
          <div className="text-xs text-slate-500">
            Persistence score ({record.period_count}/{record.total_periods_analyzed} periods)
          </div>
        </div>
        <div className="rounded bg-slate-50 p-3">
          <div className="text-lg font-bold text-slate-900">
            {record.first_year}–{record.latest_year}
          </div>
          <div className="text-xs text-slate-500">First → latest recurring year</div>
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-semibold text-slate-800">Recurring years</h3>
        <ul className="flex flex-wrap gap-1.5">
          {record.periods_present.map((y) => (
            <li key={y} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
              {y}
            </li>
          ))}
        </ul>
      </div>

      {record.crime_type && (
        <p className="text-xs text-slate-500">Filtered to crime type: {record.crime_type}</p>
      )}

      <p className="text-xs text-slate-400">{PERSISTENCE_CATEGORY_DESCRIPTIONS[record.category]}</p>

      <p className="text-xs text-slate-400">
        This describes where historical, already-reported incidents recurred — it is not a
        forecast of future crime.
      </p>
    </DetailDrawer>
  );
}
