import { useState, useRef, useEffect } from 'react';
import api from '../api/client';

export default function Reconciliation() {
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const [tab, setTab] = useState('ALL');
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState('');
  const [scenario, setScenario] = useState('mixed');
  const fileRef = useRef();

  const load = async () => {
    try {
      const [r, s] = await Promise.all([
        api.get('/reconciliation/results'),
        api.get('/reconciliation/summary'),
      ]);
      setResults(r.data);
      setSummary(s.data);
    } catch (e) { console.error(e); }
  };

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setMsg('');
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/reconciliation/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setMsg(`Uploaded ${res.data.uploaded} rows. Matched: ${res.data.reconciliation.matched}, Flagged: ${res.data.reconciliation.flagged}, Unmatched: ${res.data.reconciliation.unmatched}`);
      await load();
    } catch (e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
    setUploading(false);
  };

  const downloadGeneratedCsv = async () => {
    try {
      const res = await api.get('/reconciliation/generate-csv', {
        params: { scenario },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `sosys_${scenario}_export.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setMsg('Generated SOSYS CSV downloaded.');
    } catch (e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const runGeneratedReconciliation = async () => {
    setUploading(true);
    setMsg('Generating SOSYS data and running reconciliation...');
    try {
      const res = await api.post('/reconciliation/generate-demo', null, { params: { scenario } });
      const summary = res.data.reconciliation;
      setMsg(`Generated ${res.data.generated} SOSYS rows. Matched: ${summary.matched}, Flagged: ${summary.flagged}, Unmatched: ${summary.unmatched}`);
      await load();
    } catch (e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
    setUploading(false);
  };

  const resolve = async (id) => {
    try {
      await api.post(`/reconciliation/${id}/resolve`);
      load();
    } catch (e) { console.error(e); }
  };

  const filtered = results.filter(r => tab === 'ALL' || r.match_status === tab);
  const badge = (s) => {
    const c = { MATCHED: 'bg-green-100 text-green-800', UNMATCHED: 'bg-orange-100 text-orange-800', FLAGGED: 'bg-red-100 text-red-800' };
    return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${c[s] || 'bg-gray-100'}`}>{s}</span>;
  };
  const npr = (v) => 'NPR ' + Number(v).toLocaleString('en-IN');

  useEffect(() => { load(); }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Reconciliation Console</h1>

      <div className="bg-white rounded-lg shadow p-4 mb-6 flex flex-wrap items-center gap-3">
        <label className="bg-slate-700 text-white px-4 py-2 rounded text-sm font-medium cursor-pointer hover:bg-slate-800">
          {uploading ? 'Uploading...' : 'Upload SOSYS CSV'}
          <input ref={fileRef} type="file" accept=".csv" onChange={upload} className="hidden" />
        </label>
        <select value={scenario} onChange={e => setScenario(e.target.value)}
          className="border rounded px-3 py-2 text-sm bg-white">
          <option value="mixed">Mixed Anomalies</option>
          <option value="clean">Clean Export</option>
        </select>
        <button onClick={downloadGeneratedCsv}
          className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50">
          Generate SOSYS CSV
        </button>
        <button onClick={runGeneratedReconciliation} disabled={uploading}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          Run Generated Reconciliation
        </button>
        {msg && <span className="text-sm text-gray-600">{msg}</span>}
      </div>

      {summary && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-3 text-center">
            <div className="text-xl font-bold text-gray-800">{summary.total}</div>
            <div className="text-xs text-gray-500">Total</div>
          </div>
          <div className="bg-white rounded-lg shadow p-3 text-center">
            <div className="text-xl font-bold text-green-600">{summary.matched}</div>
            <div className="text-xs text-gray-500">Matched</div>
          </div>
          <div className="bg-white rounded-lg shadow p-3 text-center">
            <div className="text-xl font-bold text-orange-600">{summary.unmatched}</div>
            <div className="text-xs text-gray-500">Unmatched</div>
          </div>
          <div className="bg-white rounded-lg shadow p-3 text-center">
            <div className="text-xl font-bold text-red-600">{summary.flagged}</div>
            <div className="text-xs text-gray-500">Flagged</div>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="flex gap-2 mb-4">
            {['ALL', 'MATCHED', 'UNMATCHED', 'FLAGGED'].map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-3 py-1.5 rounded text-sm font-medium ${tab === t ? 'bg-slate-700 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}>
                {t}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr>
                  <th className="px-3 py-2 text-left">Claim Code</th>
                  <th className="px-3 py-2 text-left">Hospital</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                  <th className="px-3 py-2 text-center">Match</th>
                  <th className="px-3 py-2 text-left">Notes</th>
                  <th className="px-3 py-2 text-center">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(r => (
                  <tr key={r.id} className={`border-t ${r.match_status === 'FLAGGED' ? 'bg-red-50' : r.match_status === 'UNMATCHED' ? 'bg-orange-50' : ''}`}>
                    <td className="px-3 py-2 font-mono text-xs">{r.claim_code}</td>
                    <td className="px-3 py-2">{r.health_facility}</td>
                    <td className="px-3 py-2 text-right">{npr(r.amount)}</td>
                    <td className="px-3 py-2 text-center">{badge(r.match_status)}</td>
                    <td className="px-3 py-2 text-xs text-gray-600 max-w-xs">{r.notes || '-'}</td>
                    <td className="px-3 py-2 text-center">
                      {r.match_status !== 'MATCHED' && !r.resolved && (
                        <button onClick={() => resolve(r.id)}
                          className="bg-blue-600 text-white px-2 py-0.5 rounded text-xs hover:bg-blue-700">
                          Resolve
                        </button>
                      )}
                      {r.resolved && <span className="text-green-600 text-xs font-semibold">Resolved</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
