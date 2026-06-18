import { useEffect, useState } from 'react';
import api from '../api/client';

export default function Batches() {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [message, setMessage] = useState('');

  const load = async () => {
    try {
      const res = await api.get('/batches');
      setBatches(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
    const i = setInterval(load, 3000);
    return () => clearInterval(i);
  }, []);

  const openBatch = async (batch) => {
    setSelectedBatch(batch);
    try {
      const res = await api.get(`/batches/${batch.id}/transactions`);
      setTransactions(res.data);
    } catch (e) {
      setMessage('Could not load transactions: ' + (e.response?.data?.detail || e.message));
    }
  };

  const executeBatch = async (batch) => {
    try {
      setMessage(`Executing ${batch.batch_code || batch.id}...`);
      await api.post(`/batches/${batch.id}/execute`);
      setMessage('Batch sent to Mock Bank. Approve or reject payments there.');
      await load();
      await openBatch(batch);
    } catch (e) {
      setMessage('Error: ' + (e.response?.data?.detail || e.message));
    }
  };

  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-slate-900">Batches</h1>
        <p className="mt-1 text-sm text-slate-500">Hospital-specific payout groups ready for gateway execution.</p>
      </div>

      {message && <div className="mb-4 border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">{message}</div>}

      <section className="border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">Batch ID</th>
                <th className="px-3 py-2 text-left">Hospital</th>
                <th className="px-3 py-2 text-right">Amount</th>
                <th className="px-3 py-2 text-center">Claims</th>
                <th className="px-3 py-2 text-center">Status</th>
                <th className="px-3 py-2 text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr key={b.id} className="border-t border-slate-100 hover:bg-sky-50/50">
                  <td className="px-3 py-2 font-mono text-xs font-semibold text-sky-800">{b.batch_code || b.id}</td>
                  <td className="px-3 py-2">{b.health_facility || 'Multiple Facilities'}</td>
                  <td className="px-3 py-2 text-right font-semibold">{npr(b.total_amount)}</td>
                  <td className="px-3 py-2 text-center">{b.claim_count}</td>
                  <td className="px-3 py-2 text-center">{badge(b.status)}</td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => openBatch(b)}
                      className="mr-2 rounded border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                    >
                      View
                    </button>
                    {b.status === 'QUEUED' && (
                      <button
                        onClick={() => executeBatch(b)}
                        className="rounded border border-teal-700 bg-teal-700 px-3 py-1 text-xs font-medium text-white hover:bg-teal-800"
                      >
                        Execute
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {!batches.length && (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">No batches yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {selectedBatch && (
        <section className="mt-5 border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-800">
              {selectedBatch.batch_code || selectedBatch.id} Transactions
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">Claim</th>
                  <th className="px-3 py-2 text-left">Hospital</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                  <th className="px-3 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono text-xs">{tx.claim_code}</td>
                    <td className="px-3 py-2">{tx.health_facility}</td>
                    <td className="px-3 py-2 text-right">{npr(tx.amount)}</td>
                    <td className="px-3 py-2 text-center">{badge(tx.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function badge(status) {
  const colors = {
    QUEUED: 'bg-amber-50 text-amber-800 border-amber-200',
    PENDING: 'bg-amber-50 text-amber-800 border-amber-200',
    EXECUTING: 'bg-sky-50 text-sky-800 border-sky-200',
    PROCESSING: 'bg-sky-50 text-sky-800 border-sky-200',
    DONE: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    SUCCESS: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    PARTIAL: 'bg-orange-50 text-orange-800 border-orange-200',
    FAILED: 'bg-red-50 text-red-800 border-red-200',
  };
  return <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${colors[status] || 'bg-slate-50 text-slate-700 border-slate-200'}`}>{status}</span>;
}
