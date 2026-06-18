import { useEffect, useState } from 'react';
import api from '../api/client';

export default function Reconciliation() {
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const [tab, setTab] = useState('ALL');
  const [message, setMessage] = useState('');

  const load = async () => {
    try {
      const [r, s] = await Promise.all([
        api.get('/reconciliation/results'),
        api.get('/reconciliation/summary'),
      ]);
      setResults(r.data);
      setSummary(s.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runComparison = async () => {
    setMessage('Running ledger comparison...');
    try {
      const res = await api.post('/reconciliation/run');
      setSummary(res.data);
      setMessage('Comparison refreshed.');
      await load();
    } catch (e) {
      setMessage('Comparison failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const resolve = async (id) => {
    try {
      await api.post(`/reconciliation/${id}/resolve`);
      await load();
    } catch (e) {
      console.error(e);
    }
  };

  const filtered = results.filter((r) => tab === 'ALL' || r.match_status === tab || r.issue_type === tab);
  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Reconciliation Console</h1>
          <p className="mt-1 text-sm text-slate-500">Comparing Samanvaya Ledger vs. Legacy SOSYS/Bank Ledger.</p>
        </div>
        <button
          onClick={runComparison}
          className="rounded border border-sky-700 bg-sky-700 px-4 py-2 text-sm font-medium text-white hover:bg-sky-800"
        >
          Refresh Comparison
        </button>
      </div>

      {message && <div className="mb-4 border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">{message}</div>}

      {summary && (
        <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Insight label="Matched" value={summary.matched} tone="emerald" note="Perfect match" />
          <Insight label="Ghost Payments" value={summary.ghost_payments} tone="red" note="In SOSYS only" />
          <Insight label="Missing in SOSYS" value={summary.missing_in_sosys} tone="amber" note="Samanvaya success only" />
          <Insight label="Amount Mismatches" value={summary.amount_mismatches} tone="orange" note="Amounts differ" />
          <Insight label="Duplicates" value={summary.duplicates} tone="rose" note="Repeated legacy rows" />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {[
          ['ALL', 'All'],
          ['MATCHED', 'Matched'],
          ['UNMATCHED', 'Unmatched'],
          ['FLAGGED', 'Flagged'],
          ['GHOST_PAYMENT', 'Ghost'],
          ['MISSING_IN_SOSYS', 'Missing'],
          ['AMOUNT_MISMATCH', 'Mismatch'],
          ['DUPLICATE', 'Duplicate'],
        ].map(([value, label]) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`rounded border px-3 py-1.5 text-sm font-medium ${
              tab === value
                ? 'border-sky-700 bg-sky-700 text-white'
                : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <section className="border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Line-by-Line Comparison ({filtered.length})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">Claim Code</th>
                <th className="px-3 py-2 text-left">Hospital</th>
                <th className="px-3 py-2 text-right">Legacy Amount</th>
                <th className="px-3 py-2 text-center">Flag</th>
                <th className="px-3 py-2 text-left">Insight</th>
                <th className="px-3 py-2 text-left">Notes</th>
                <th className="px-3 py-2 text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id} className={`border-t border-slate-100 ${rowTone(r)}`}>
                  <td className="px-3 py-2 font-mono text-xs">{r.claim_code}</td>
                  <td className="px-3 py-2">{r.health_facility}</td>
                  <td className="px-3 py-2 text-right">{npr(r.amount)}</td>
                  <td className="px-3 py-2 text-center">{badge(r.match_status)}</td>
                  <td className="px-3 py-2 text-xs font-semibold text-slate-700">{formatIssue(r.issue_type)}</td>
                  <td className="max-w-md px-3 py-2 text-xs text-slate-600">{r.notes || '-'}</td>
                  <td className="px-3 py-2 text-center">
                    {r.match_status !== 'MATCHED' && !r.resolved && (
                      <button
                        onClick={() => resolve(r.id)}
                        className="rounded border border-sky-700 bg-sky-700 px-2 py-1 text-xs font-medium text-white hover:bg-sky-800"
                      >
                        Resolve
                      </button>
                    )}
                    {r.resolved && <span className="text-xs font-semibold text-emerald-700">Resolved</span>}
                  </td>
                </tr>
              ))}
              {!filtered.length && (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-slate-400">No comparison rows yet. Load SOSYS data first.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Insight({ label, value, note, tone }) {
  const tones = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    red: 'border-red-200 bg-red-50 text-red-800',
    amber: 'border-amber-200 bg-amber-50 text-amber-800',
    orange: 'border-orange-200 bg-orange-50 text-orange-800',
    rose: 'border-rose-200 bg-rose-50 text-rose-800',
  };
  return (
    <div className={`border p-4 ${tones[tone] || tones.emerald}`}>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="mt-1 text-sm font-semibold">{label}</div>
      <div className="mt-1 text-xs opacity-80">{note}</div>
    </div>
  );
}

function badge(status) {
  const colors = {
    MATCHED: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    UNMATCHED: 'border-amber-200 bg-amber-50 text-amber-800',
    FLAGGED: 'border-red-200 bg-red-50 text-red-800',
  };
  return <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${colors[status] || 'border-slate-200 bg-slate-50 text-slate-700'}`}>{status}</span>;
}

function formatIssue(issue) {
  if (!issue) return '-';
  return issue.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function rowTone(row) {
  if (row.match_status === 'MATCHED') return '';
  if (row.issue_type === 'GHOST_PAYMENT') return 'bg-red-50/70';
  if (row.issue_type === 'MISSING_IN_SOSYS') return 'bg-amber-50/70';
  if (row.issue_type === 'DUPLICATE') return 'bg-rose-50/70';
  return 'bg-orange-50/70';
}
