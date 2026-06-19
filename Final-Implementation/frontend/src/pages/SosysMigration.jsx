import { useEffect, useRef, useState } from 'react';
import api from '../api/client';

export default function SosysMigration() {
  const [rows, setRows] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const fileRef = useRef();

  const load = async () => {
    try {
      const res = await api.get('/reconciliation/sosys-ledger');
      setRows(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true);
    setMessage('');
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/reconciliation/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      const summary = res.data.reconciliation;
      setMessage(`Uploaded ${res.data.uploaded} SOSYS rows. Matched ${summary.matched}, flagged ${summary.flagged}, unmatched ${summary.unmatched}.`);
      await load();
    } catch (e) {
      setMessage('Upload failed: ' + (e.response?.data?.detail || e.message));
    }
    setBusy(false);
    if (fileRef.current) fileRef.current.value = '';
  };

  const npr = (v) => 'NPR ' + Number(v || 0).toLocaleString('en-IN');

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-slate-900">Legacy SOSYS Migration</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload real legacy SOSYS files, or review audit rows automatically reflected after Mock Bank batch approval.
        </p>
      </div>

      <section className="mb-5 border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">Legacy File Controls</h2>
        </div>
        <div className="flex flex-wrap items-center gap-3 p-4">
          <label className="rounded border border-slate-700 bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
            {busy ? 'Working...' : 'Upload SOSYS CSV'}
            <input ref={fileRef} type="file" accept=".csv" onChange={upload} className="hidden" />
          </label>
          <span className="text-sm text-slate-500">Expected columns: claim_code, health_facility, amount, payment_date, status</span>
        </div>
      </section>

      {message && <div className="mb-4 border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">{message}</div>}

      <section className="border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">SOSYS Audit Ledger ({rows.length})</h2>
          <span className="text-xs text-slate-500">Uploaded rows and auto-reflected approved batches</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">Claim Code</th>
                <th className="px-3 py-2 text-left">Hospital</th>
                <th className="px-3 py-2 text-right">Amount</th>
                <th className="px-3 py-2 text-left">Payment Date</th>
                <th className="px-3 py-2 text-left">Batch</th>
                <th className="px-3 py-2 text-left">Source</th>
                <th className="px-3 py-2 text-left">SOSYS Status</th>
                <th className="px-3 py-2 text-left">Latest Comparison</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{row.claim_code}</td>
                  <td className="px-3 py-2">{row.health_facility}</td>
                  <td className="px-3 py-2 text-right">{npr(row.amount)}</td>
                  <td className="px-3 py-2">{row.payment_date || '-'}</td>
                  <td className="px-3 py-2 font-mono text-xs">{row.batch_code || '-'}</td>
                  <td className="px-3 py-2">{row.source || '-'}</td>
                  <td className="px-3 py-2">{row.sosys_status || '-'}</td>
                  <td className="px-3 py-2 text-xs text-slate-600">{row.issue_type || row.match_status}</td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-slate-400">No SOSYS audit rows loaded</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
