import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export default function TransactionLedger() {
  const [txs, setTxs] = useState([]);
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState(null);
  const [clinical, setClinical] = useState(null);
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    try {
      const params = {};
      if (filter) params.status = filter;
      if (search) params.health_facility = search;
      const res = await api.get('/transactions', { params });
      setTxs(res.data);
    } catch (e) { console.error(e); }
  }, [filter, search]);

  useEffect(() => { load(); const i = setInterval(load, 3000); return () => clearInterval(i); }, [load]);

  const showDetail = async (id) => {
    try {
      const res = await api.get(`/transactions/${id}`);
      setDetail(res.data);
    } catch (e) { console.error(e); }
  };

  const retry = async (id) => {
    try {
      await api.post(`/transactions/${id}/retry`);
      load();
    } catch (e) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const exportCsv = async () => {
    try {
      const res = await api.get('/transactions/export-csv', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'samanvaya_ledger_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setMessage('Ledger CSV exported.');
    } catch (e) {
      setMessage('Export failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const clearLedger = async () => {
    const ok = window.confirm(
      'Clear the full payment ledger, batches, and reconciliation rows? Affected claims will return to APPROVED for a fresh demo.'
    );
    if (!ok) return;

    try {
      const res = await api.delete('/transactions/ledger');
      setDetail(null);
      setClinical(null);
      setMessage(
        `Cleared ${res.data.deleted_transactions} transactions, ${res.data.deleted_batches} batches, and reset ${res.data.reset_claims} claims.`
      );
      await load();
    } catch (e) {
      setMessage('Clear failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Transaction Ledger</h1>
          <p className="mt-1 text-sm text-slate-500">Complete OpenIMIS payment history with claimed, approved, and paid amounts.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={exportCsv} className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">Export CSV</button>
          <button onClick={clearLedger} className="rounded border border-red-700 bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-800">Clear Ledger</button>
        </div>
      </div>

      {message && <div className="mb-4 border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">{message}</div>}

      <div className="mb-4 flex gap-3">
        <select value={filter} onChange={e => setFilter(e.target.value)} className="border border-slate-300 bg-white px-3 py-1.5 text-sm">
          <option value="">All Statuses</option>
          <option value="SUCCESS">Success</option>
          <option value="FAILED">Failed</option>
          <option value="PROCESSING">Processing</option>
          <option value="PENDING">Pending</option>
        </select>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search hospital..." className="flex-1 border border-slate-300 px-3 py-1.5 text-sm" />
      </div>

      <div className="overflow-x-auto border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">Claim</th>
              <th className="px-3 py-2 text-left">Hospital</th>
              <th className="px-3 py-2 text-right">Claimed</th>
              <th className="px-3 py-2 text-right">Approved</th>
              <th className="px-3 py-2 text-right">Paid</th>
              <th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2 text-left">TXN ID</th>
              <th className="px-3 py-2 text-center">Review</th>
            </tr>
          </thead>
          <tbody>
            {txs.map(tx => {
              const approved = Number(tx.approved_amount ?? tx.amount ?? 0);
              const claimed = Number(tx.claimed_amount ?? approved);
              const hasClinicalDifference = approved < claimed;
              return (
                <tr key={tx.id} className="border-t hover:bg-gray-50">
                  <td onClick={() => showDetail(tx.id)} className="cursor-pointer px-3 py-2 font-mono text-xs">{tx.claim_code || '-'}</td>
                  <td onClick={() => showDetail(tx.id)} className="cursor-pointer px-3 py-2">{tx.health_facility || '-'}</td>
                  <td onClick={() => showDetail(tx.id)} className="cursor-pointer px-3 py-2 text-right">{npr(claimed)}</td>
                  <td onClick={() => showDetail(tx.id)} className="cursor-pointer px-3 py-2 text-right">{npr(approved)}</td>
                  <td onClick={() => showDetail(tx.id)} className="cursor-pointer px-3 py-2 text-right font-medium">{npr(tx.paid_amount)}</td>
                  <td onClick={() => showDetail(tx.id)} className="cursor-pointer px-3 py-2 text-center">{badge(tx.status)}</td>
                  <td onClick={() => showDetail(tx.id)} className="cursor-pointer px-3 py-2 font-mono text-xs text-gray-500">{tx.gateway_ref_id || tx.id}</td>
                  <td className="px-3 py-2 text-center">
                    {hasClinicalDifference && (
                      <button onClick={() => setClinical(tx)} className="rounded border border-sky-700 bg-sky-700 px-2 py-1 text-xs font-medium text-white hover:bg-sky-800">Review</button>
                    )}
                    {tx.status === 'FAILED' && (
                      <button onClick={() => retry(tx.id)} className="ml-1 rounded border border-amber-600 bg-amber-600 px-2 py-1 text-xs font-medium text-white hover:bg-amber-700">Retry</button>
                    )}
                  </td>
                </tr>
              );
            })}
            {!txs.length && <tr><td colSpan="8" className="py-8 text-center text-gray-400">No transactions yet</td></tr>}
          </tbody>
        </table>
      </div>

      {clinical && (
        <ClinicalModal tx={clinical} onClose={() => setClinical(null)} />
      )}

      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDetail(null)}>
          <div className="mx-4 w-full max-w-xl bg-white p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">Transaction Detail</h2>
              <button onClick={() => setDetail(null)} className="text-xl text-gray-400 hover:text-gray-600">&times;</button>
            </div>
            <dl className="space-y-2 text-sm">
              <Row label="TXN ID" value={detail.id} mono />
              <Row label="Status" value={badge(detail.status)} />
              <Row label="Claimed" value={npr(detail.claimed_amount)} />
              <Row label="Approved" value={npr(detail.approved_amount ?? detail.amount)} />
              <Row label="Paid" value={npr(detail.paid_amount)} />
              <Row label="Hospital" value={detail.health_facility} />
              <Row label="Financial" value={detail.financial_screening_completed ? (detail.financial_screening_reason || 'Recorded') : 'Required'} />
            </dl>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <h3 className="mb-1 text-xs font-semibold text-gray-500">Request Log</h3>
                <pre className="max-h-32 overflow-auto bg-gray-50 p-2 text-xs">{JSON.stringify(detail.raw_request_log, null, 2)}</pre>
              </div>
              <div>
                <h3 className="mb-1 text-xs font-semibold text-gray-500">Response Log</h3>
                <pre className="max-h-32 overflow-auto bg-gray-50 p-2 text-xs">{JSON.stringify(detail.raw_response_log, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ClinicalModal({ tx, onClose }) {
  const reasons = tx.clinical_screening_reasons?.length ? tx.clinical_screening_reasons : ['Clinical tariff adjustment'];
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="mx-4 w-full max-w-md bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Clinical Screening Review</h2>
            <p className="mt-1 font-mono text-xs text-slate-500">{tx.claim_code}</p>
          </div>
          <button onClick={onClose} className="text-2xl leading-none text-slate-400 hover:text-slate-700">&times;</button>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <Metric label="Claimed" value={'NPR ' + Number(tx.claimed_amount || 0).toLocaleString('en-IN')} />
          <Metric label="Approved" value={'NPR ' + Number(tx.approved_amount || tx.amount || 0).toLocaleString('en-IN')} />
        </div>
        <ul className="mt-4 space-y-2">
          {reasons.map((reason) => (
            <li key={reason} className="border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">{reason}</li>
          ))}
        </ul>
      </div>
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

function Row({ label, value, mono }) {
  return (
    <div className="flex"><dt className="w-36 shrink-0 text-gray-500">{label}</dt><dd className={mono ? 'break-all font-mono text-xs' : ''}>{value}</dd></div>
  );
}

function badge(status) {
  const colors = {
    SUCCESS: 'border-green-200 bg-green-50 text-green-800',
    FAILED: 'border-red-200 bg-red-50 text-red-800',
    PENDING: 'border-amber-200 bg-amber-50 text-amber-800',
    PROCESSING: 'border-blue-200 bg-blue-50 text-blue-800',
    PARTIAL: 'border-orange-200 bg-orange-50 text-orange-800',
  };
  return <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${colors[status] || 'border-gray-200 bg-gray-50 text-gray-700'}`}>{status}</span>;
}
