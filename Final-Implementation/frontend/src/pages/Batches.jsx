import { useEffect, useMemo, useState } from 'react';
import api from '../api/client';

const FINANCIAL_REASONS = [
  'Bank processing fee',
  'Partial settlement due to insufficient funds',
  'System truncation',
  'Manual treasury adjustment',
];

export default function Batches() {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [message, setMessage] = useState('');
  const [screening, setScreening] = useState(null);
  const [reason, setReason] = useState(FINANCIAL_REASONS[0]);
  const [notes, setNotes] = useState('');

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
    try {
      const res = await api.get(`/batches/${batch.id}`);
      setSelectedBatch(res.data);
    } catch (e) {
      setMessage('Could not load batch details: ' + (e.response?.data?.detail || e.message));
    }
  };

  const runBatchAction = async (batch, action, successText) => {
    try {
      setMessage(`${successText.pending} ${batch.batch_code || batch.id}...`);
      await api.post(`/batches/${batch.id}/${action}`);
      setMessage(successText.done);
      await load();
      await openBatch(batch);
    } catch (e) {
      setMessage('Error: ' + (e.response?.data?.detail || e.message));
    }
  };

  const openScreening = (batch) => {
    setScreening(batch);
    setReason(FINANCIAL_REASONS[0]);
    setNotes('');
  };

  const submitScreening = async () => {
    if (!screening) return;
    const hasDifference = hasFinancialDifference(screening);
    if (hasDifference && !reason) {
      setMessage('Select a financial screening reason for the Approved vs Paid difference.');
      return;
    }
    try {
      await api.post(`/batches/${screening.id}/financial-screening`, {
        reason: hasDifference ? reason : null,
        notes,
      });
      setMessage('Financial screening recorded.');
      setScreening(null);
      await load();
      await openBatch(screening);
    } catch (e) {
      setMessage('Financial screening failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-slate-900">Batches</h1>
        <p className="mt-1 text-sm text-slate-500">OpenIMIS-approved claim groups ready for payment and settlement screening.</p>
      </div>

      {message && <div className="mb-4 border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">{message}</div>}

      <section className="border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">Batch ID</th>
                <th className="px-3 py-2 text-left">Hospital</th>
                <th className="px-3 py-2 text-right">Approved</th>
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
                        onClick={() => runBatchAction(b, 'pay', { pending: 'Paying', done: 'Payment recorded in OpenIMIS and Bank ledgers.' })}
                        className="rounded border border-teal-700 bg-teal-700 px-3 py-1 text-xs font-medium text-white hover:bg-teal-800"
                      >
                        Pay
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
        <div className="fixed inset-0 z-50 bg-black/30" onClick={() => setSelectedBatch(null)}>
          <aside
            className="ml-auto flex h-full w-full max-w-5xl flex-col bg-white shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-slate-200 px-5 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{selectedBatch.batch_code || selectedBatch.id}</h2>
                  <p className="mt-1 text-sm text-slate-500">{selectedBatch.health_facility || 'Multiple Facilities'}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {selectedBatch.status === 'QUEUED' && (
                    <>
                      <button onClick={() => runBatchAction(selectedBatch, 'pay', { pending: 'Paying', done: 'Payment recorded in both ledgers.' })} className="rounded border border-teal-700 bg-teal-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-800">Pay</button>
                      <button onClick={() => runBatchAction(selectedBatch, 'pay-less', { pending: 'Paying less for', done: 'Partial settlement anomaly recorded in the Bank ledger.' })} className="rounded border border-orange-700 bg-orange-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-800">Pay Less</button>
                    </>
                  )}
                  <button onClick={() => runBatchAction(selectedBatch, 'ghost-payment', { pending: 'Injecting ghost payment for', done: 'Ghost payment injected into the Bank ledger.' })} className="rounded border border-rose-700 bg-rose-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-800">Ghost Payment</button>
                  <button onClick={() => openScreening(selectedBatch)} className="rounded border border-sky-700 bg-sky-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-800">Run Financial Screening</button>
                  <button onClick={() => setSelectedBatch(null)} className="text-2xl leading-none text-slate-400 hover:text-slate-700">&times;</button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-4">
                <Metric label="Status" value={selectedBatch.status} />
                <Metric label="Claims" value={selectedBatch.claim_count} />
                <Metric label="Approved" value={npr(selectedBatch.total_amount)} />
                <Metric label="Screening" value={screeningState(selectedBatch)} />
              </div>
            </div>

            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2 text-left">Claim</th>
                    <th className="px-3 py-2 text-left">Insuree</th>
                    <th className="px-3 py-2 text-right">Claimed</th>
                    <th className="px-3 py-2 text-right">Approved</th>
                    <th className="px-3 py-2 text-right">Paid</th>
                    <th className="px-3 py-2 text-center">Status</th>
                    <th className="px-3 py-2 text-left">TXN ID</th>
                    <th className="px-3 py-2 text-left">Financial</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedBatch.transactions.map((tx) => (
                    <tr key={tx.id} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-mono text-xs">{tx.claim_code}</td>
                      <td className="px-3 py-2">{tx.insuree_name || '-'}</td>
                      <td className="px-3 py-2 text-right">{npr(tx.claimed_amount)}</td>
                      <td className="px-3 py-2 text-right">{npr(tx.approved_amount ?? tx.amount)}</td>
                      <td className="px-3 py-2 text-right">{npr(tx.paid_amount)}</td>
                      <td className="px-3 py-2 text-center">{badge(tx.status)}</td>
                      <td className="px-3 py-2 font-mono text-xs text-slate-500">{tx.gateway_ref_id || tx.id}</td>
                      <td className="px-3 py-2 text-xs">{tx.financial_screening_completed ? (tx.financial_screening_reason || 'Recorded') : 'Required'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </aside>
        </div>
      )}

      {screening && (
        <FinancialScreeningModal
          batch={screening}
          reason={reason}
          setReason={setReason}
          notes={notes}
          setNotes={setNotes}
          onClose={() => setScreening(null)}
          onSubmit={submitScreening}
        />
      )}
    </div>
  );
}

function FinancialScreeningModal({ batch, reason, setReason, notes, setNotes, onClose, onSubmit }) {
  const hasDifference = useMemo(() => hasFinancialDifference(batch), [batch]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="w-full max-w-lg bg-white p-5 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Financial Screening</h2>
            <p className="mt-1 text-sm text-slate-500">{batch.batch_code || batch.id}</p>
          </div>
          <button onClick={onClose} className="text-2xl leading-none text-slate-400 hover:text-slate-700">&times;</button>
        </div>

        <div className="mt-4 border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          {hasDifference
            ? 'Approved and Paid amounts differ. Select the financial reason that explains the settlement difference.'
            : 'No Approved vs Paid difference is present. Recording this step marks the batch financially screened.'}
        </div>

        {hasDifference && (
          <label className="mt-4 block text-sm">
            <span className="font-medium text-slate-700">Reason</span>
            <select value={reason} onChange={(e) => setReason(e.target.value)} className="mt-1 w-full border border-slate-300 bg-white px-3 py-2">
              {FINANCIAL_REASONS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        )}

        <label className="mt-4 block text-sm">
          <span className="font-medium text-slate-700">Notes</span>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows="3" className="mt-1 w-full border border-slate-300 px-3 py-2" />
        </label>

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">Cancel</button>
          <button onClick={onSubmit} className="rounded border border-sky-700 bg-sky-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-800">Record Screening</button>
        </div>
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

function hasFinancialDifference(batch) {
  return (batch.transactions || []).some((tx) => Math.abs(Number(tx.approved_amount ?? tx.amount ?? 0) - Number(tx.paid_amount || 0)) > 0.01);
}

function screeningState(batch) {
  const txs = batch.transactions || [];
  if (!txs.length) return 'No transactions';
  return txs.every((tx) => tx.financial_screening_completed) ? 'Recorded' : 'Required';
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
