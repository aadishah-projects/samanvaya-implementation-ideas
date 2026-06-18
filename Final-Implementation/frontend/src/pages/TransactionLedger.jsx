import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';

export default function TransactionLedger() {
  const [txs, setTxs] = useState([]);
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState(null);
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

  const verify = async (id) => {
    try {
      await api.post(`/transactions/${id}/verify`);
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
      setMessage(
        `Cleared ${res.data.deleted_transactions} transactions, ${res.data.deleted_batches} batches, and reset ${res.data.reset_claims} claims.`
      );
      await load();
    } catch (e) {
      setMessage('Clear failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const npr = (v) => 'NPR ' + Number(v).toLocaleString('en-IN');
  const badge = (s) => {
    const c = { SUCCESS: 'bg-green-100 text-green-800', FAILED: 'bg-red-100 text-red-800', PENDING: 'bg-amber-100 text-amber-800', PROCESSING: 'bg-blue-100 text-blue-800', PARTIAL: 'bg-orange-100 text-orange-800' };
    return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${c[s] || 'bg-gray-100'}`}>{s}</span>;
  };

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h1 className="text-2xl font-bold text-gray-800">Transaction Ledger</h1>
        <div className="flex items-center gap-2">
          <button onClick={exportCsv}
            className="bg-white border border-gray-300 text-gray-700 px-3 py-1.5 rounded text-sm font-medium hover:bg-gray-50">
            Export CSV
          </button>
          <button onClick={clearLedger}
            className="bg-red-600 text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-red-700">
            Clear Ledger
          </button>
        </div>
      </div>

      {message && <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-2 rounded mb-4 text-sm">{message}</div>}

      <div className="flex gap-3 mb-4">
        <select value={filter} onChange={e => setFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm bg-white">
          <option value="">All Statuses</option>
          <option value="SUCCESS">Success</option>
          <option value="FAILED">Failed</option>
          <option value="PROCESSING">Processing</option>
          <option value="PENDING">Pending</option>
        </select>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search hospital..."
          className="border rounded px-3 py-1.5 text-sm flex-1" />
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
            <tr>
              <th className="px-3 py-2 text-left">Claim</th>
              <th className="px-3 py-2 text-left">Hospital</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2 text-left">Gateway Ref</th>
              <th className="px-3 py-2 text-left">Time</th>
              <th className="px-3 py-2 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {txs.map(tx => (
              <tr key={tx.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => showDetail(tx.id)}>
                <td className="px-3 py-2 font-mono text-xs">{tx.claim_code || '-'}</td>
                <td className="px-3 py-2">{tx.health_facility || '-'}</td>
                <td className="px-3 py-2 text-right font-medium">{npr(tx.amount)}</td>
                <td className="px-3 py-2 text-center">{badge(tx.status)}</td>
                <td className="px-3 py-2 font-mono text-xs text-gray-500">{tx.gateway_ref_id ? tx.gateway_ref_id.slice(0,12)+'...' : '-'}</td>
                <td className="px-3 py-2 text-xs text-gray-500">{new Date(tx.created_at).toLocaleString()}</td>
                <td className="px-3 py-2 text-center">
                  {tx.status === 'FAILED' && (
                    <button onClick={e => { e.stopPropagation(); retry(tx.id); }}
                      className="bg-amber-500 text-white px-2 py-0.5 rounded text-xs hover:bg-amber-600 mr-1">
                      Retry
                    </button>
                  )}
                  {tx.status === 'PROCESSING' && tx.gateway_ref_id && (
                    <button onClick={e => { e.stopPropagation(); verify(tx.id); }}
                      className="bg-blue-600 text-white px-2 py-0.5 rounded text-xs hover:bg-blue-700">
                      Verify
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!txs.length && <tr><td colSpan="7" className="text-center text-gray-400 py-8">No transactions yet</td></tr>}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setDetail(null)}>
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Transaction Detail</h2>
              <button onClick={() => setDetail(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <dl className="text-sm space-y-2">
              <Row label="ID" value={detail.id} />
              <Row label="Status" value={badge(detail.status)} />
              <Row label="Amount" value={npr(detail.amount)} />
              <Row label="Hospital" value={detail.health_facility} />
              <Row label="Idempotency Key" value={detail.idempotency_key} mono />
              <Row label="Gateway Ref" value={detail.gateway_ref_id || '-'} mono />
              <Row label="Retries" value={detail.retry_count} />
              <Row label="Webhook At" value={detail.webhook_received_at ? new Date(detail.webhook_received_at).toLocaleString() : '-'} />
            </dl>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <h3 className="text-xs font-semibold text-gray-500 mb-1">Request Log</h3>
                <pre className="bg-gray-50 rounded p-2 text-xs overflow-auto max-h-32">{JSON.stringify(detail.raw_request_log, null, 2)}</pre>
              </div>
              <div>
                <h3 className="text-xs font-semibold text-gray-500 mb-1">Response Log</h3>
                <pre className="bg-gray-50 rounded p-2 text-xs overflow-auto max-h-32">{JSON.stringify(detail.raw_response_log, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, mono }) {
  return (
    <div className="flex"><dt className="w-36 text-gray-500 shrink-0">{label}</dt><dd className={mono ? 'font-mono text-xs break-all' : ''}>{value}</dd></div>
  );
}
