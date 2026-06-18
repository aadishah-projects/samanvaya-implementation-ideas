import { useState, useEffect } from 'react';
import api from '../api/client';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [volume, setVolume] = useState([]);
  const [anomalyCount, setAnomalyCount] = useState(0);
  const [message, setMessage] = useState('');

  const load = async () => {
    try {
      const [s, v, a] = await Promise.all([
        api.get('/dashboard/summary'),
        api.get('/dashboard/volume'),
        api.get('/dashboard/anomaly-count'),
      ]);
      setSummary(s.data);
      setVolume(v.data.reverse());
      setAnomalyCount(a.data.anomaly_count || 0);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, []);

  if (!summary) return <p className="text-gray-500 mt-8 text-center">Loading...</p>;

  const pieData = [
    { name: 'Success', value: summary.success_count, color: '#16a34a' },
    { name: 'Failed', value: summary.failed_count, color: '#dc2626' },
    { name: 'Pending', value: summary.pending_count, color: '#d97706' },
  ].filter(d => d.value > 0);

  const npr = (v) => 'NPR ' + Number(v).toLocaleString('en-IN');

  const resetDemo = async () => {
    setMessage('Resetting demo...');
    try {
      await api.post('/demo/reset');
      setMessage('Demo reset complete.');
      await load();
    } catch (e) {
      setMessage('Reset failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Financial Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Live payment health for OpenIMIS claim disbursements.</p>
        </div>
        <div className="flex items-center gap-2">
          <a href="http://localhost:8001/ui" target="_blank" rel="noreferrer"
            className="rounded border border-sky-700 bg-sky-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-800">
            Open Mock Bank
          </a>
          <button onClick={resetDemo}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
            Reset Demo
          </button>
        </div>
      </div>

      {message && <div className="bg-sky-50 border border-sky-200 text-sky-900 px-4 py-2 mb-4 text-sm">{message}</div>}

      {anomalyCount > 0 && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 mb-6 flex items-center gap-2">
          <span className="text-lg">&#9888;</span>
          <span className="font-semibold">{anomalyCount} SOSYS Anomalies Detected</span>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Card label="Total Disbursed" value={npr(summary.total_disbursed)} color="text-blue-600" />
        <Card label="Success Rate" value={`${summary.success_rate}%`} color="text-green-600" />
        <Card label="Pending" value={summary.pending_count} color="text-amber-600" />
        <Card label="Failed" value={summary.failed_count} color="text-red-600" />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 p-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Payment Breakdown</h2>
          {pieData.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({name, value}) => `${name}: ${value}`}>
                  {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-center py-12">No transactions yet</p>}
        </div>

        <div className="bg-white border border-slate-200 p-4">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Daily Volume</h2>
          {volume.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={volume}>
                <XAxis dataKey="date" tick={{fontSize: 11}} />
                <YAxis tick={{fontSize: 11}} />
                <Tooltip formatter={(v) => npr(v)} />
                <Bar dataKey="total_amount" fill="#2563eb" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-center py-12">No volume data yet</p>}
        </div>
      </div>
    </div>
  );
}

function Card({ label, value, color }) {
  return (
    <div className="bg-white border border-slate-200 p-4">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 uppercase mt-1">{label}</div>
    </div>
  );
}
