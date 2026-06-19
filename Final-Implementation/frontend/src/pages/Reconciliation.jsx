import { useEffect, useState } from 'react';
import api from '../api/client';

export default function Reconciliation() {
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const [tab, setTab] = useState('ALL');
  const [message, setMessage] = useState('');
  const [review, setReview] = useState(null);

  const load = async () => {
    try {
      const [r, s] = await Promise.all([
        api.get('/reconciliation/results'),
        api.get('/reconciliation/summary'),
      ]);
      setResults(r.data);
      setSummary(s.data);
    } catch (e) {
      setMessage('Could not load reconciliation results: ' + (e.response?.data?.detail || e.message));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runComparison = async () => {
    setMessage('Running OpenIMIS vs Bank comparison...');
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
      setMessage('Resolve failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const filtered = results.filter((r) => tab === 'ALL' || r.match_status === tab || r.issue_type === tab);
  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Reconciliation Console</h1>
          <p className="mt-1 text-sm text-slate-500">Comparing the OpenIMIS ledger against the Bank ledger.</p>
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
          <Insight label="Matched" value={summary.matched} tone="emerald" note="Fully reconciled" />
          <Insight label="Flagged" value={summary.flagged} tone="red" note="Review needed" />
          <Insight label="Ghost Payments" value={summary.ghost_payments} tone="rose" note="Bank only" />
          <Insight label="Missing Payments" value={summary.missing_payments ?? summary.missing_in_sosys} tone="amber" note="OpenIMIS only" />
          <Insight label="Differences" value={summary.amount_mismatches} tone="orange" note="Claimed vs paid" />
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {[
          ['ALL', 'All'],
          ['MATCHED', 'Matched'],
          ['UNMATCHED', 'Unmatched'],
          ['FLAGGED', 'Flagged'],
          ['FINANCIAL_SCREENING_REQUIRED', 'Screening Required'],
          ['CLAIMED_PAID_MISMATCH', 'Claimed vs Paid'],
          ['GHOST_PAYMENT', 'Ghost'],
          ['MISSING_PAYMENT', 'Missing'],
          ['STATUS_MISMATCH', 'Status'],
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
          <h2 className="text-sm font-semibold text-slate-800">OpenIMIS vs Bank ({filtered.length})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">TXN ID</th>
                <th className="px-3 py-2 text-left">Claim</th>
                <th className="px-3 py-2 text-left">Hospital</th>
                <th className="px-3 py-2 text-right">Claimed</th>
                <th className="px-3 py-2 text-right">Approved</th>
                <th className="px-3 py-2 text-right">Paid</th>
                <th className="px-3 py-2 text-right">Clinical</th>
                <th className="px-3 py-2 text-right">Financial</th>
                <th className="px-3 py-2 text-right">Total Flag</th>
                <th className="px-3 py-2 text-center">Status</th>
                <th className="px-3 py-2 text-left">Review</th>
                <th className="px-3 py-2 text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id} className={`border-t border-slate-100 ${rowTone(r)}`}>
                  <td className="px-3 py-2 font-mono text-xs text-slate-500">{r.gateway_ref_id || r.id}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.claim_code}</td>
                  <td className="px-3 py-2">{r.health_facility}</td>
                  <td className="px-3 py-2 text-right">{npr(r.claimed_amount)}</td>
                  <td className="px-3 py-2 text-right">{npr(r.approved_amount ?? r.amount)}</td>
                  <td className="px-3 py-2 text-right font-medium">{npr(r.paid_amount)}</td>
                  <td className="px-3 py-2 text-right">{npr(r.clinical_difference)}</td>
                  <td className="px-3 py-2 text-right">{npr(r.financial_difference)}</td>
                  <td className="px-3 py-2 text-right font-semibold">{npr(r.total_difference)}</td>
                  <td className="px-3 py-2 text-center">{badge(r.match_status)}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {needsFinancialReview(r) && (
                        <button
                          onClick={() => setReview(r)}
                          className="rounded border border-sky-700 bg-sky-700 px-2 py-1 text-xs font-medium text-white hover:bg-sky-800"
                        >
                          Financial
                        </button>
                      )}
                      <span className="text-xs font-semibold text-slate-700">{formatIssue(r.issue_type)}</span>
                    </div>
                  </td>
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
                  <td colSpan="12" className="py-8 text-center text-slate-400">No reconciliation rows yet. Run a comparison after paying a batch.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {review && <FinancialReview row={review} onClose={() => setReview(null)} />}
    </div>
  );
}

function FinancialReview({ row, onClose }) {
  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="mx-4 w-full max-w-lg bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Financial Screening Review</h2>
            <p className="mt-1 font-mono text-xs text-slate-500">{row.gateway_ref_id || row.id}</p>
          </div>
          <button onClick={onClose} className="text-2xl leading-none text-slate-400 hover:text-slate-700">&times;</button>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
          <Metric label="Approved" value={npr(row.approved_amount ?? row.amount)} />
          <Metric label="Paid" value={npr(row.paid_amount)} />
          <Metric label="Difference" value={npr(row.financial_difference)} />
        </div>

        <dl className="mt-4 space-y-2 text-sm">
          <Row label="Reason" value={row.financial_reason || (row.financial_screening_completed ? 'Recorded with no settlement difference' : 'Financial screening required')} />
          <Row label="Notes" value={row.financial_notes || '-'} />
          <Row label="Final Flag" value={row.notes || '-'} />
        </dl>
      </div>
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

function Metric({ label, value }) {
  return (
    <div className="border border-slate-200 bg-slate-50 p-3">
      <div className="text-[11px] font-semibold uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-slate-900">{value}</div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex gap-3">
      <dt className="w-24 shrink-0 text-slate-500">{label}</dt>
      <dd className="text-slate-800">{value}</dd>
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

function needsFinancialReview(row) {
  return (
    Math.abs(Number(row.financial_difference || 0)) > 0.01 ||
    row.financial_reason ||
    row.financial_notes ||
    row.issue_type === 'FINANCIAL_SCREENING_REQUIRED'
  );
}

function rowTone(row) {
  if (row.match_status === 'MATCHED') return '';
  if (row.issue_type === 'GHOST_PAYMENT') return 'bg-red-50/70';
  if (row.issue_type === 'MISSING_IN_SOSYS' || row.issue_type === 'MISSING_PAYMENT') return 'bg-amber-50/70';
  if (row.issue_type === 'FINANCIAL_SCREENING_REQUIRED') return 'bg-sky-50/70';
  return 'bg-orange-50/70';
}
