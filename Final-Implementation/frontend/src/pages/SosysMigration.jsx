import { useEffect, useState } from 'react';
import api from '../api/client';

export default function SosysMigration() {
  const [rows, setRows] = useState([]);
  const [message, setMessage] = useState('');

  const load = async () => {
    try {
      const res = await api.get('/reconciliation/sosys-ledger');
      setRows(res.data);
      setMessage('');
    } catch (e) {
      setMessage('Could not load SOSYS mirror: ' + (e.response?.data?.detail || e.message));
    }
  };

  useEffect(() => {
    load();
    const i = setInterval(load, 3000);
    return () => clearInterval(i);
  }, []);

  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">SOSYS Mirror</h1>
          <p className="mt-1 text-sm text-slate-500">Read-only reflection of the OpenIMIS payment ledger.</p>
        </div>
        <button
          onClick={load}
          className="rounded border border-sky-700 bg-sky-700 px-4 py-2 text-sm font-medium text-white hover:bg-sky-800"
        >
          Refresh
        </button>
      </div>

      {message && <div className="mb-4 border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">{message}</div>}

      <section className="border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">OpenIMIS Ledger Rows ({rows.length})</h2>
          <span className="text-xs text-slate-500">Source: OpenIMIS internal ledger</span>
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
                <th className="px-3 py-2 text-left">Batch</th>
                <th className="px-3 py-2 text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs text-slate-500">{row.gateway_ref_id || row.id}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.claim_code}</td>
                  <td className="px-3 py-2">{row.health_facility}</td>
                  <td className="px-3 py-2 text-right">{npr(row.claimed_amount)}</td>
                  <td className="px-3 py-2 text-right">{npr(row.approved_amount ?? row.amount)}</td>
                  <td className="px-3 py-2 text-right font-medium">{npr(row.paid_amount)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.batch_code || '-'}</td>
                  <td className="px-3 py-2">{row.sosys_status || 'OPENIMIS_MIRROR'}</td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-slate-400">No OpenIMIS ledger rows yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
