import { useState, useEffect } from 'react';
import api from '../api/client';

export default function ClaimsQueue() {
  const [claims, setClaims] = useState([]);
  const [batches, setBatches] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [msg, setMsg] = useState('');
  const [batchTx, setBatchTx] = useState(null);
  const [amountLimit, setAmountLimit] = useState(100000);
  const [mockCount, setMockCount] = useState(60);

  const load = async () => {
    try {
      const [c, b] = await Promise.all([
        api.get('/claims?status=APPROVED'),
        api.get('/batches'),
      ]);
      setClaims(c.data);
      setBatches(b.data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    load();
    const i = setInterval(load, 3000);
    return () => clearInterval(i);
  }, []);

  useEffect(() => {
    if (!batchTx?.batchId) return;
    const refreshBatch = async () => {
      try {
        const txRes = await api.get(`/batches/${batchTx.batchId}/transactions`);
        setBatchTx(current => current ? { ...current, txs: txRes.data } : current);
      } catch (e) { console.error(e); }
    };
    const i = setInterval(refreshBatch, 3000);
    return () => clearInterval(i);
  }, [batchTx?.batchId]);

  const toggle = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const createBatch = async () => {
    if (!selected.size) return setMsg('Select at least one claim.');
    try {
      const res = await api.post('/batches', { claim_ids: [...selected] });
      setMsg(`Batch created: ${res.data.id.slice(0,8)}... (${res.data.claim_count} claims)`);
      setSelected(new Set());
      load();
    } catch (e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const autoCreateBatches = async () => {
    try {
      const limit = Number(amountLimit);
      if (!limit || limit <= 0) return setMsg('Enter a valid amount limit.');
      const res = await api.post('/batches/auto', { amount_limit: limit });
      const overLimit = res.data.over_limit_claims?.length
        ? ` Over-limit claims isolated: ${res.data.over_limit_claims.join(', ')}.`
        : '';
      setMsg(`Auto-created ${res.data.created_count} batches for ${res.data.total_claims} claims (${npr(res.data.total_amount)}).${overLimit}`);
      setSelected(new Set());
      await load();
    } catch (e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const generateMockData = async () => {
    try {
      const count = Number(mockCount);
      if (!count || count < 5) return setMsg('Generate at least 5 claims.');
      setMsg('Generating mock claim data...');
      const res = await api.post('/demo/mock-data', { claim_count: count, reset: true });
      setBatchTx(null);
      setSelected(new Set());
      setMsg(`Generated ${res.data.claims} claims: ${res.data.approved} approved, ${res.data.processed} historical processed.`);
      await load();
    } catch (e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const executeBatch = async (batchId) => {
    try {
      setMsg('Executing batch...');
      await api.post(`/batches/${batchId}/execute`);
      setMsg('Batch executed! Check Mock Bank UI to approve/reject.');
      load();
      // Load transactions
      const txRes = await api.get(`/batches/${batchId}/transactions`);
      setBatchTx({ batchId, label: batchId.slice(0,8), txs: txRes.data });
    } catch (e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const npr = (v) => 'NPR ' + Number(v).toLocaleString('en-IN');
  const badge = (s) => {
    const colors = {
      QUEUED: 'bg-amber-100 text-amber-800',
      PENDING: 'bg-amber-100 text-amber-800',
      EXECUTING: 'bg-blue-100 text-blue-800',
      PROCESSING: 'bg-blue-100 text-blue-800',
      DONE: 'bg-green-100 text-green-800',
      SUCCESS: 'bg-green-100 text-green-800',
      PARTIAL: 'bg-orange-100 text-orange-800',
      FAILED: 'bg-red-100 text-red-800',
    };
    return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${colors[s] || 'bg-gray-100'}`}>{s}</span>;
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Claims Queue</h1>
      {msg && <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-2 rounded mb-4 text-sm">{msg}</div>}

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="px-4 py-3 border-b">
          <h2 className="font-semibold text-gray-700">Batch Automation</h2>
        </div>
        <div className="p-4 grid gap-4 md:grid-cols-2">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm text-gray-600">
              Amount limit
              <input type="number" min="1" step="1000" value={amountLimit}
                onChange={e => setAmountLimit(e.target.value)}
                className="block mt-1 border rounded px-3 py-1.5 text-sm w-40" />
            </label>
            <button onClick={autoCreateBatches}
              className="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-indigo-700">
              Auto Create Batches
            </button>
          </div>
          <div className="flex flex-wrap items-end gap-3 md:justify-end">
            <label className="text-sm text-gray-600">
              Mock claims
              <input type="number" min="5" max="250" value={mockCount}
                onChange={e => setMockCount(e.target.value)}
                className="block mt-1 border rounded px-3 py-1.5 text-sm w-32" />
            </label>
            <button onClick={generateMockData}
              className="bg-slate-700 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-slate-800">
              Generate Mock Data
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-700">Approved Claims ({claims.length})</h2>
          <button onClick={createBatch} disabled={!selected.size}
            className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium disabled:opacity-40 hover:bg-blue-700">
            Create Batch ({selected.size})
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
              <tr><th className="px-3 py-2 w-8"><input type="checkbox" onChange={e => { e.target.checked ? setSelected(new Set(claims.map(c=>c.id))) : setSelected(new Set()); }} /></th>
              <th className="px-3 py-2 text-left">Code</th><th className="px-3 py-2 text-left">Hospital</th>
              <th className="px-3 py-2 text-left">Insuree</th><th className="px-3 py-2 text-right">Approved</th></tr>
            </thead>
            <tbody>
              {claims.map(c => (
                <tr key={c.id} className="border-t hover:bg-gray-50">
                  <td className="px-3 py-2"><input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)} /></td>
                  <td className="px-3 py-2 font-mono text-xs">{c.claim_code}</td>
                  <td className="px-3 py-2">{c.health_facility}</td>
                  <td className="px-3 py-2">{c.insuree_name}</td>
                  <td className="px-3 py-2 text-right font-medium">{npr(c.approved_amount)}</td>
                </tr>
              ))}
              {!claims.length && <tr><td colSpan="5" className="text-center text-gray-400 py-8">No approved claims</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-700">Batches ({batches.length})</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
              <tr><th className="px-3 py-2 text-left">Batch</th><th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2 text-center">Claims</th><th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2 text-center">Action</th></tr>
            </thead>
            <tbody>
              {batches.map(b => (
                <tr key={b.id} className="border-t hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{b.id.slice(0,8)}...</td>
                  <td className="px-3 py-2 text-right font-medium">{npr(b.total_amount)}</td>
                  <td className="px-3 py-2 text-center">{b.claim_count}</td>
                  <td className="px-3 py-2 text-center">{badge(b.status)}</td>
                  <td className="px-3 py-2 text-center">
                    {b.status === 'QUEUED' && (
                      <button onClick={() => executeBatch(b.id)}
                        className="bg-green-600 text-white px-3 py-1 rounded text-xs font-medium hover:bg-green-700">
                        Execute
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {batchTx && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-4 py-3 border-b"><h2 className="font-semibold text-gray-700">Batch {batchTx.label}... Transactions</h2></div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr><th className="px-3 py-2 text-left">Claim</th><th className="px-3 py-2 text-left">Hospital</th>
                <th className="px-3 py-2 text-right">Amount</th><th className="px-3 py-2 text-center">Status</th></tr>
              </thead>
              <tbody>
                {batchTx.txs.map(tx => (
                  <tr key={tx.id} className="border-t">
                    <td className="px-3 py-2 font-mono text-xs">{tx.claim_code}</td>
                    <td className="px-3 py-2">{tx.health_facility}</td>
                    <td className="px-3 py-2 text-right">{npr(tx.amount)}</td>
                    <td className="px-3 py-2 text-center">{badge(tx.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
