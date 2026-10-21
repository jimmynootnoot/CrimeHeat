import { useState } from 'react';
import axios from 'axios';
import { downloadCsvText, runTemporalSplitEvaluation, type TemporalSplitResult } from '../api/endpoints';
import { CRIME_TYPES, PPALMA_MUNICIPALITIES } from '../types';

export function TemporalSplitEvaluation() {
  const [cutoffDate, setCutoffDate] = useState('');
  const [municipality, setMunicipality] = useState('');
  const [crimeType, setCrimeType] = useState('');
  const [epsKm, setEpsKm] = useState('1.0');
  const [minSamples, setMinSamples] = useState('4');
  const [cellKm, setCellKm] = useState('1.0');
  const [result, setResult] = useState<TemporalSplitResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const data = await runTemporalSplitEvaluation({
        cutoff_date: cutoffDate,
        municipality: municipality || undefined,
        crime_type: crimeType || undefined,
        eps_km: Number(epsKm),
        min_samples: Number(minSamples),
        cell_km: Number(cellKm),
      });
      setResult(data);
    } catch (err) {
      let message = 'Could not run the temporal split. Check the cutoff date and filters.';
      if (axios.isAxiosError(err) && typeof err.response?.data?.detail === 'string') {
        message = err.response.data.detail;
      }
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="bg-white rounded-lg shadow border border-slate-200 p-4 space-y-3">
      <h2 className="font-semibold text-slate-900">Temporal split evaluation (real-data alternative)</h2>
      <p className="text-sm text-slate-600">
        Detects hotspots using only incidents before the cutoff date, then checks whether incidents
        actually occurred in the same grid cells on or after it. The test-window incidents are the
        reference label — an independent, non-circular check built entirely from incident data already
        covered by the PNP data request, with no separate hotspot-validation dataset required.
      </p>
      <label className="block text-sm">Cutoff date (training window ends before this date)
        <input type="date" value={cutoffDate} onChange={e => setCutoffDate(e.target.value)}
          className="block w-full border rounded p-2" />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className="block text-sm">Municipality
          <select value={municipality} onChange={e => setMunicipality(e.target.value)} className="block w-full border rounded p-2">
            <option value="">All municipalities</option>
            {PPALMA_MUNICIPALITIES.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>
        <label className="block text-sm">Crime type
          <select value={crimeType} onChange={e => setCrimeType(e.target.value)} className="block w-full border rounded p-2">
            <option value="">All crime types</option>
            {CRIME_TYPES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <label className="block text-sm">Eps (km)
          <input type="number" step="0.1" min="0.1" value={epsKm} onChange={e => setEpsKm(e.target.value)}
            className="block w-full border rounded p-2" />
        </label>
        <label className="block text-sm">Min samples
          <input type="number" step="1" min="2" value={minSamples} onChange={e => setMinSamples(e.target.value)}
            className="block w-full border rounded p-2" />
        </label>
        <label className="block text-sm">Grid cell (km)
          <input type="number" step="0.1" min="0.1" value={cellKm} onChange={e => setCellKm(e.target.value)}
            className="block w-full border rounded p-2" />
        </label>
      </div>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button onClick={run} disabled={busy || !cutoffDate}
        className="bg-slate-900 text-white rounded px-4 py-2 text-sm font-semibold disabled:opacity-50">
        {busy ? 'Running…' : 'Run temporal split evaluation'}
      </button>

      {result && (
        <div className="border-t border-slate-200 pt-3 space-y-3">
          <p className="text-xs text-slate-500">{result.methodology}</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-slate-50 rounded p-2">
              <div className="font-semibold text-slate-700">Training window</div>
              <div>{result.train_period.start} – {result.train_period.end}</div>
              <div>{result.train_period.incident_count} incidents · {result.train_cluster_count} clusters detected</div>
            </div>
            <div className="bg-slate-50 rounded p-2">
              <div className="font-semibold text-slate-700">Test window (held out)</div>
              <div>{result.test_period.start} – {result.test_period.end}</div>
              <div>{result.test_period.incident_count} incidents</div>
            </div>
          </div>

          <table className="text-sm border-collapse w-full">
            <thead>
              <tr>
                <th className="border p-1"></th>
                <th className="border p-1">Actually recurred</th>
                <th className="border p-1">Did not recur</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border p-1 font-semibold">Predicted hotspot</td>
                <td className="border p-1 text-center bg-green-50">{result.true_positives} (TP)</td>
                <td className="border p-1 text-center bg-red-50">{result.false_positives} (FP)</td>
              </tr>
              <tr>
                <td className="border p-1 font-semibold">Not predicted</td>
                <td className="border p-1 text-center bg-red-50">{result.false_negatives} (FN)</td>
                <td className="border p-1 text-center bg-green-50">{result.true_negatives} (TN)</td>
              </tr>
            </tbody>
          </table>

          <div className="grid grid-cols-3 gap-3 text-center text-sm">
            <div className="bg-slate-50 rounded p-2">
              <div className="text-xs text-slate-500">Precision</div>
              <div className="font-semibold text-slate-900">{result.precision_percent.toFixed(1)}%</div>
            </div>
            <div className="bg-slate-50 rounded p-2">
              <div className="text-xs text-slate-500">Recall</div>
              <div className="font-semibold text-slate-900">{result.recall_percent.toFixed(1)}%</div>
            </div>
            <div className="bg-slate-900 text-white rounded p-2">
              <div className="text-xs text-slate-300">F1 (algorithmic score)</div>
              <div className="font-semibold">{result.f1_score_percent.toFixed(1)}%</div>
            </div>
          </div>

          <div className="flex gap-3">
            <button onClick={() => downloadCsvText(result.predictions_csv, 'temporal_split_predictions.csv')}
              className="border border-slate-300 rounded px-3 py-1.5 text-xs font-semibold">
              Download predictions.csv
            </button>
            <button onClick={() => downloadCsvText(result.reference_csv, 'temporal_split_reference.csv')}
              className="border border-slate-300 rounded px-3 py-1.5 text-xs font-semibold">
              Download reference.csv
            </button>
          </div>
          <p className="text-xs text-slate-500">
            These two files use the same unit_id/predicted_label/reference_label format as the evaluation
            export above — pair them with a real functional_tests_csv there for the full 90/10 workbook.
          </p>
        </div>
      )}
    </section>
  );
}
