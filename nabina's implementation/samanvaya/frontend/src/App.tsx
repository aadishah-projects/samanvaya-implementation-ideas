import { useEffect, useMemo, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, AreaChart, Area } from 'recharts';
import { api, ClaimDetail, ClaimRow, DashboardResponse, HospitalSummary, HospitalDetail, HospitalClaim } from './lib/api';

type StatusFilter = 'all' | 'green' | 'yellow' | 'red' | 'anomalies';

const statusConfig = {
  fully_matched: { label: 'Fully Matched', pill: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30', dot: 'bg-[#2fd27b]' },
  partial_match: { label: 'Partial Match', pill: 'bg-amber-500/15 text-amber-300 border-amber-500/30', dot: 'bg-[#f7c948]' },
  failed: { label: 'Unmatched', pill: 'bg-rose-500/15 text-rose-300 border-rose-500/30', dot: 'bg-[#ef4d4d]' },
  anomaly: { label: 'Anomaly', pill: 'bg-rose-500/15 text-rose-300 border-rose-500/30', dot: 'bg-[#ef4d4d]' },
} as const;

const trafficLights = [
  { key: 'Green', description: 'Fully matched and clean', color: '#2fd27b' },
  { key: 'Yellow', description: 'Partial or fuzzy match', color: '#f7c948' },
  { key: 'Red', description: 'Failed or anomalous', color: '#ef4d4d' },
];

const initialMessage = 'Upload OpenIMIS and SOSYS files or generate synthetic records to start reconciliation.';

export default function App() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [claims, setClaims] = useState<ClaimRow[]>([]);
  const [selectedClaim, setSelectedClaim] = useState<ClaimDetail | null>(null);
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [message, setMessage] = useState(initialMessage);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [hospitals, setHospitals] = useState<HospitalSummary[]>([]);
  const [selectedHospital, setSelectedHospital] = useState<HospitalDetail | null>(null);
  const [hospitalFilter, setHospitalFilter] = useState<'all' | 'issues' | 'anomalies'>('all');
  const [hospitalSearch, setHospitalSearch] = useState('');

  const loadHospitals = async () => {
    try {
      const result = await api.getHospitals();
      setHospitals(result.items);
    } catch {
      // silently fail, hospitals section will show empty
    }
  };

  const openHospital = async (hospitalName: string) => {
    setBusy(true);
    try {
      const detail = await api.getHospitalDetail(hospitalName);
      setSelectedHospital(detail);
      setHospitalFilter('all');
      setHospitalSearch('');
    } finally {
      setBusy(false);
    }
  };

  const filteredHospitalClaims = useMemo(() => {
    if (!selectedHospital) return [];
    let items = selectedHospital.claims;
    if (hospitalFilter === 'issues') {
      items = items.filter((c) => c.status === 'failed' || c.status === 'anomaly');
    } else if (hospitalFilter === 'anomalies') {
      items = items.filter((c) => c.status === 'anomaly');
    }
    if (hospitalSearch.trim()) {
      const q = hospitalSearch.toLowerCase();
      items = items.filter(
        (c) =>
          c.claim_id.toLowerCase().includes(q) ||
          c.patient_id.toLowerCase().includes(q) ||
          (c.anomaly_reason ?? '').toLowerCase().includes(q) ||
          c.diagnosis.toLowerCase().includes(q)
      );
    }
    return items;
  }, [selectedHospital, hospitalFilter, hospitalSearch]);

  const loadDashboard = async () => {
    setRefreshing(true);
    try {
      const [dashboardResult, claimsResult] = await Promise.all([api.getDashboard(), api.getClaims()]);
      setDashboard(dashboardResult);
      setClaims(claimsResult.items);
      await loadHospitals();
      if (!selectedClaim && claimsResult.items[0]) {
        const detail = await api.getClaimDetail(claimsResult.items[0].claim_id);
        setSelectedClaim(detail);
      }
      setMessage('Dashboard refreshed with the latest reconciliation state.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to load dashboard.');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const filteredClaims = useMemo(() => {
    if (filter === 'all') return claims;
    if (filter === 'green') return claims.filter((item) => item.status === 'fully_matched');
    if (filter === 'yellow') return claims.filter((item) => item.status === 'partial_match');
    if (filter === 'anomalies') return claims.filter((item) => item.status === 'anomaly');
    return claims.filter((item) => item.status === 'failed' || item.status === 'anomaly');
  }, [claims, filter]);

  const openDetail = async (claimId: string) => {
    setBusy(true);
    try {
      const detail = await api.getClaimDetail(claimId);
      setSelectedClaim(detail);
    } finally {
      setBusy(false);
    }
  };

  const uploadHandler = async (file: File | null, kind: 'openimis' | 'sosys') => {
    if (!file) return;
    setBusy(true);
    try {
      const result = kind === 'openimis' ? await api.uploadOpenImis(file) : await api.uploadSosys(file);
      setMessage(`Uploaded ${file.name}. ${JSON.stringify(result)}`);
      await loadDashboard();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Upload failed.');
    } finally {
      setBusy(false);
    }
  };

  const runSynthetic = async () => {
    setBusy(true);
    try {
      const result = await api.generateSynthetic(500);
      setMessage(`Synthetic dataset generated: ${JSON.stringify(result)}`);
      await loadDashboard();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Synthetic generation failed.');
    } finally {
      setBusy(false);
    }
  };

  const runReconcile = async () => {
    setBusy(true);
    try {
      const result = await api.runReconciliation();
      setMessage(`Reconciliation complete: ${JSON.stringify(result)}`);
      await loadDashboard();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Reconciliation failed.');
    } finally {
      setBusy(false);
    }
  };

  const sendSms = async () => {
    if (!selectedClaim) return;
    setBusy(true);
    try {
      const result = await api.sendSms(selectedClaim.claim.claim_id as string);
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'SMS could not be sent.');
    } finally {
      setBusy(false);
    }
  };

  const trendData = dashboard?.trend ?? [];
  const pieData = dashboard?.statusBreakdown ?? [];

  return (
    <div className="min-h-screen bg-dashboard text-ink">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 lg:px-6">
        <header className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-glow backdrop-blur-xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.3em] text-accent">Nepal Health Insurance</div>
              <h1 className="mt-2 text-4xl font-semibold tracking-tight">Samanvaya</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                Financial reconciliation dashboard for OpenIMIS claims and SOSYS payments with exact, fuzzy, and anomaly detection.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={runSynthetic}
                className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm font-medium text-emerald-200 transition hover:bg-emerald-400/20 disabled:opacity-50"
                disabled={busy}
              >
                Generate 500 Synthetic Records
              </button>
              <button
                onClick={runReconcile}
                className="rounded-2xl border border-sky-400/30 bg-sky-400/10 px-4 py-2 text-sm font-medium text-sky-200 transition hover:bg-sky-400/20 disabled:opacity-50"
                disabled={busy}
              >
                Run Reconciliation
              </button>
              <button
                onClick={loadDashboard}
                className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10 disabled:opacity-50"
                disabled={busy || refreshing}
              >
                Refresh
              </button>
            </div>
          </div>
          <p className="mt-4 rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">{message}</p>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard title="Total Claims" value={dashboard?.metrics.totalClaims ?? 0} accent="text-sky-300" />
          <MetricCard title="Fully Matched" value={dashboard?.metrics.fullyMatched ?? 0} accent="text-emerald-300" />
          <MetricCard title="Partial Matches" value={dashboard?.metrics.partialMatches ?? 0} accent="text-amber-300" />
          <MetricCard title="Failed / Unmatched" value={dashboard?.metrics.failed ?? 0} accent="text-rose-300" />
          <MetricCard title="Anomalies Detected" value={dashboard?.metrics.anomalies ?? 0} accent="text-red-300" />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="grid gap-6">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Traffic Light Status</h2>
                  <p className="text-sm text-slate-400">Green, yellow, and red indicators for operational control.</p>
                </div>
                <div className="rounded-full border border-white/10 bg-slate-950/50 px-3 py-1 text-xs text-slate-300">
                  Match rate {dashboard?.metrics.matchRate ?? 0}%
                </div>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                {trafficLights.map((light) => (
                  <div key={light.key} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="flex items-center gap-3">
                      <span className="h-4 w-4 rounded-full" style={{ backgroundColor: light.color }} />
                      <h3 className="font-medium">{light.key}</h3>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">{light.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
                <h2 className="text-lg font-semibold">Reconciliation Breakdown</h2>
                <div className="mt-4 h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={3}>
                        {pieData.map((entry) => (
                          <Cell key={entry.name} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid rgba(255,255,255,0.08)' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
                <h2 className="text-lg font-semibold">Trend Chart</h2>
                <div className="mt-4 h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData}>
                      <defs>
                        <linearGradient id="matched" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2fd27b" stopOpacity={0.45} />
                          <stop offset="95%" stopColor="#2fd27b" stopOpacity={0.02} />
                        </linearGradient>
                        <linearGradient id="yellow" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f7c948" stopOpacity={0.45} />
                          <stop offset="95%" stopColor="#f7c948" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                      <XAxis dataKey="day" stroke="#8fa3c4" tick={{ fill: '#8fa3c4', fontSize: 12 }} />
                      <YAxis stroke="#8fa3c4" tick={{ fill: '#8fa3c4', fontSize: 12 }} />
                      <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid rgba(255,255,255,0.08)' }} />
                      <Area type="monotone" dataKey="fully_matched" stroke="#2fd27b" fill="url(#matched)" />
                      <Area type="monotone" dataKey="partial_matches" stroke="#f7c948" fill="url(#yellow)" />
                      <Line type="monotone" dataKey="failed" stroke="#ef4d4d" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
            <h2 className="text-lg font-semibold">Data Upload</h2>
            <p className="mt-1 text-sm text-slate-400">Upload OpenIMIS FHIR Claim Bundle JSON and SOSYS payment CSV or JSON.</p>
            <UploadBox label="Upload OpenIMIS Bundle JSON" accept="application/json" onFile={(file) => uploadHandler(file, 'openimis')} />
            <UploadBox label="Upload SOSYS Payment CSV/JSON" accept=".csv,application/json" onFile={(file) => uploadHandler(file, 'sosys')} />

            <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/70 p-4">
              <h3 className="font-medium">Upload Status</h3>
              <div className="mt-3 space-y-3 text-sm text-slate-300">
                {(dashboard?.uploads ?? []).slice(0, 5).map((upload) => (
                  <div key={`${upload.filename}-${upload.created_at}`} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/5 px-3 py-2">
                    <div>
                      <div className="font-medium capitalize">{upload.source_type}</div>
                      <div className="text-xs text-slate-400">{upload.filename}</div>
                    </div>
                    <div className="text-right">
                      <div>{upload.record_count} records</div>
                      <div className="text-xs text-emerald-300">{upload.status}</div>
                    </div>
                  </div>
                ))}
                {!(dashboard?.uploads?.length) && <div className="text-slate-500">No uploads yet.</div>}
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Claims Table</h2>
                <p className="text-sm text-slate-400">Click a claim to inspect the source record and matched payment.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {(['all', 'green', 'yellow', 'red', 'anomalies'] as StatusFilter[]).map((item) => (
                  <button
                    key={item}
                    onClick={() => setFilter(item)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${filter === item ? 'border-accent bg-accent/15 text-white' : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'}`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-4 overflow-hidden rounded-2xl border border-white/10">
              <table className="min-w-full divide-y divide-white/10 text-sm">
                <thead className="bg-slate-950/80 text-slate-400">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Claim ID</th>
                    <th className="px-4 py-3 text-left font-medium">Provider</th>
                    <th className="px-4 py-3 text-left font-medium">Claim Amount</th>
                    <th className="px-4 py-3 text-left font-medium">Paid Amount</th>
                    <th className="px-4 py-3 text-left font-medium">Match Score</th>
                    <th className="px-4 py-3 text-left font-medium">Status</th>
                    <th className="px-4 py-3 text-left font-medium">Anomaly Reason</th>
                    <th className="px-4 py-3 text-left font-medium">Payment Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 bg-slate-950/40">
                  {filteredClaims.map((row) => {
                    const config = statusConfig[row.status];
                    return (
                      <tr key={row.claim_id} onClick={() => openDetail(row.claim_id)} className="cursor-pointer transition hover:bg-white/5">
                        <td className="px-4 py-3 font-medium text-white">{row.claim_id}</td>
                        <td className="px-4 py-3 text-slate-300">{row.provider}</td>
                        <td className="px-4 py-3">NPR {row.claim_amount.toLocaleString()}</td>
                        <td className="px-4 py-3">{row.paid_amount ? `NPR ${row.paid_amount.toLocaleString()}` : '-'}</td>
                        <td className="px-4 py-3">{row.match_score.toFixed(1)}</td>
                        <td className="px-4 py-3"><span className={`inline-flex rounded-full border px-2.5 py-1 text-xs ${config.pill}`}>{config.label}</span></td>
                        <td className="px-4 py-3 text-slate-300">{row.anomaly_reason ?? '-'}</td>
                        <td className="px-4 py-3 text-slate-300">{row.payment_date ?? '-'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
              <h2 className="text-lg font-semibold">Detail Page</h2>
              {selectedClaim ? (
                <div className="mt-4 space-y-4 text-sm text-slate-300">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
                    <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Original OpenIMIS Record</div>
                    <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-200">{JSON.stringify(selectedClaim.claim, null, 2)}</pre>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
                    <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Matched SOSYS Record</div>
                    <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs leading-6 text-slate-200">{JSON.stringify(selectedClaim.payment ?? {}, null, 2)}</pre>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <InfoCard label="Match Score" value={selectedClaim.reconciliation?.match_score.toFixed(2) ?? '0.00'} />
                    <InfoCard label="Traffic Status" value={selectedClaim.reconciliation?.status ?? 'pending'} />
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
                    <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Reconciliation Explanation</div>
                    <p className="mt-2 text-slate-200">{selectedClaim.reconciliation?.explanation ?? 'No reconciliation record found.'}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
                    <div className="text-xs uppercase tracking-[0.25em] text-slate-500">Anomaly Explanation</div>
                    <p className="mt-2 text-slate-200">{selectedClaim.reconciliation?.anomaly_reason ?? 'No anomaly detected.'}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
                    <div className="text-xs uppercase tracking-[0.25em] text-slate-500">SMS Alert Mock</div>
                    <p className="mt-2 text-slate-200">{selectedClaim.smsMessage}</p>
                    <button onClick={sendSms} className="mt-4 rounded-xl border border-accent/30 bg-accent/15 px-4 py-2 text-sm font-medium text-accent transition hover:bg-accent/25">Send SMS</button>
                  </div>
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-dashed border-white/10 bg-slate-950/40 p-6 text-sm text-slate-400">
                  Select a claim to view the original OpenIMIS record, matched SOSYS entry, and audit explanation.
                </div>
              )}
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
              <h2 className="text-lg font-semibold">Recent Anomalies</h2>
              <div className="mt-4 space-y-3">
                {(dashboard?.recentAnomalies ?? []).slice(0, 5).map((item) => (
                  <div key={item.claim_id} className="rounded-2xl border border-white/10 bg-slate-950/70 p-3 text-sm text-slate-300">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-white">{item.claim_id}</span>
                      <span className="text-rose-300">{item.anomaly_reason}</span>
                    </div>
                    <div className="mt-1 text-slate-400">{item.explanation}</div>
                  </div>
                ))}
                {!(dashboard?.recentAnomalies?.length) && <div className="text-sm text-slate-500">No anomalies detected yet.</div>}
              </div>
            </div>
          </div>
        </section>

        {/* Hospital Inspection Section */}
        <section className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold">Hospital Inspection</h2>
              <p className="text-sm text-slate-400">
                Drill into each hospital to inspect individual patients, anomaly reasons, and resolution steps.
              </p>
            </div>
          </div>

          {!selectedHospital ? (
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {hospitals.map((h) => (
                <button
                  key={h.provider}
                  onClick={() => openHospital(h.provider)}
                  disabled={busy}
                  className="group rounded-2xl border border-white/10 bg-slate-950/60 p-4 text-left transition hover:border-accent/40 hover:bg-white/5 disabled:opacity-50"
                >
                  <h3 className="font-semibold text-white group-hover:text-accent">{h.provider}</h3>
                  <div className="mt-3 space-y-1 text-xs text-slate-400">
                    <div className="flex justify-between"><span>Total Claims</span><span className="text-white">{h.total_claims}</span></div>
                    <div className="flex justify-between"><span>Fully Matched</span><span className="text-emerald-300">{h.fully_matched}</span></div>
                    <div className="flex justify-between"><span>Partial</span><span className="text-amber-300">{h.partial_matches}</span></div>
                    <div className="flex justify-between"><span>Failed</span><span className="text-rose-300">{h.failed}</span></div>
                    <div className="flex justify-between"><span>Anomalies</span><span className="text-red-300">{h.anomalies}</span></div>
                  </div>
                  <div className="mt-3 flex items-center justify-between border-t border-white/10 pt-3 text-xs">
                    <span className="text-slate-500">Match Rate</span>
                    <span className={`font-semibold ${h.match_rate >= 80 ? 'text-emerald-300' : h.match_rate >= 50 ? 'text-amber-300' : 'text-rose-300'}`}>
                      {h.match_rate}%
                    </span>
                  </div>
                  {h.unresolved_issues > 0 && (
                    <div className="mt-2 rounded-lg bg-rose-500/10 px-2 py-1 text-center text-xs font-medium text-rose-300">
                      {h.unresolved_issues} unresolved issue{h.unresolved_issues > 1 ? 's' : ''}
                    </div>
                  )}
                </button>
              ))}
              {hospitals.length === 0 && (
                <div className="col-span-full rounded-2xl border border-dashed border-white/10 bg-slate-950/40 p-6 text-center text-sm text-slate-500">
                  No hospital data yet. Generate synthetic records or upload files to populate hospitals.
                </div>
              )}
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <button
                  onClick={() => setSelectedHospital(null)}
                  className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-200 transition hover:bg-white/10"
                >
                  <span className="text-base">&larr;</span> Back to all hospitals
                </button>
                <h3 className="text-xl font-semibold text-accent">{selectedHospital.hospital}</h3>
              </div>

              {/* Hospital summary metrics */}
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <MiniMetric label="Total Claims" value={selectedHospital.summary.total_claims} color="text-sky-300" />
                <MiniMetric label="Fully Matched" value={selectedHospital.summary.fully_matched} color="text-emerald-300" />
                <MiniMetric label="Partial Matches" value={selectedHospital.summary.partial_matches} color="text-amber-300" />
                <MiniMetric label="Failed" value={selectedHospital.summary.failed} color="text-rose-300" />
                <MiniMetric label="Anomalies" value={selectedHospital.summary.anomalies} color="text-red-300" />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
                  <h4 className="font-medium text-white">Financial Summary</h4>
                  <div className="mt-3 space-y-2 text-sm text-slate-300">
                    <div className="flex justify-between"><span>Total Claimed</span><span className="font-medium text-white">NPR {selectedHospital.summary.total_claimed.toLocaleString()}</span></div>
                    <div className="flex justify-between"><span>Total Paid</span><span className="font-medium text-emerald-300">NPR {selectedHospital.summary.total_paid.toLocaleString()}</span></div>
                    <div className="flex justify-between"><span>Match Rate</span><span className="font-medium text-white">{selectedHospital.summary.match_rate}%</span></div>
                    <div className="flex justify-between"><span>Unresolved Issues</span><span className="font-medium text-rose-300">{selectedHospital.summary.unresolved_issues}</span></div>
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
                  <h4 className="font-medium text-white">Anomaly Breakdown</h4>
                  <div className="mt-3 space-y-2 text-sm text-slate-300">
                    {selectedHospital.anomaly_breakdown.length === 0 && <div className="text-slate-500">No anomalies found.</div>}
                    {selectedHospital.anomaly_breakdown.map((a) => (
                      <div key={a.reason} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/5 px-3 py-2">
                        <span>{a.reason}</span>
                        <span className="rounded-full bg-rose-500/15 px-2 py-0.5 text-xs font-medium text-rose-300">{a.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Hospital claims filter */}
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap gap-2">
                  {(['all', 'issues', 'anomalies'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setHospitalFilter(f)}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${hospitalFilter === f ? 'border-accent bg-accent/15 text-white' : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'}`}
                    >
                      {f === 'all' ? 'All Claims' : f === 'issues' ? 'Failed + Anomalies' : 'Anomalies Only'}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Search by claim ID, patient ID, diagnosis..."
                  value={hospitalSearch}
                  onChange={(e) => setHospitalSearch(e.target.value)}
                  className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-1.5 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-accent/40 sm:w-72"
                />
              </div>

              {/* Hospital claims table */}
              <div className="overflow-hidden rounded-2xl border border-white/10">
                <div className="max-h-[520px] overflow-auto">
                  <table className="min-w-full divide-y divide-white/10 text-sm">
                    <thead className="sticky top-0 z-10 bg-slate-950/90 text-slate-400 backdrop-blur">
                      <tr>
                        <th className="px-3 py-2.5 text-left font-medium">Claim ID</th>
                        <th className="px-3 py-2.5 text-left font-medium">Patient ID</th>
                        <th className="px-3 py-2.5 text-left font-medium">Diagnosis</th>
                        <th className="px-3 py-2.5 text-left font-medium">Claim Amt</th>
                        <th className="px-3 py-2.5 text-left font-medium">Paid Amt</th>
                        <th className="px-3 py-2.5 text-left font-medium">Status</th>
                        <th className="px-3 py-2.5 text-left font-medium">Reason</th>
                        <th className="px-3 py-2.5 text-left font-medium min-w-[260px]">Resolution</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 bg-slate-950/40">
                      {filteredHospitalClaims.map((row) => {
                        const cfg = statusConfig[row.status];
                        return (
                          <tr key={row.claim_id} className="transition hover:bg-white/5">
                            <td className="px-3 py-2.5 font-medium text-white">{row.claim_id}</td>
                            <td className="px-3 py-2.5 text-slate-300">{row.patient_id}</td>
                            <td className="px-3 py-2.5 text-slate-300">{row.diagnosis}</td>
                            <td className="px-3 py-2.5">NPR {row.claim_amount.toLocaleString()}</td>
                            <td className="px-3 py-2.5">{row.paid_amount ? `NPR ${row.paid_amount.toLocaleString()}` : '-'}</td>
                            <td className="px-3 py-2.5"><span className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${cfg.pill}`}>{cfg.label}</span></td>
                            <td className="px-3 py-2.5 text-rose-300">{row.anomaly_reason ?? '-'}</td>
                            <td className="px-3 py-2.5 text-xs leading-5 text-slate-400">{row.resolution}</td>
                          </tr>
                        );
                      })}
                      {filteredHospitalClaims.length === 0 && (
                        <tr><td colSpan={8} className="px-4 py-6 text-center text-slate-500">No claims match the current filter.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function MetricCard({ title, value, accent }: { title: string; value: number; accent: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur-xl">
      <div className="text-sm text-slate-400">{title}</div>
      <div className={`mt-2 text-3xl font-semibold ${accent}`}>{value.toLocaleString()}</div>
    </div>
  );
}

function UploadBox({ label, accept, onFile }: { label: string; accept: string; onFile: (file: File | null) => void }) {
  return (
    <label className="mt-4 block rounded-2xl border border-dashed border-white/15 bg-slate-950/60 p-4 text-sm text-slate-300 transition hover:border-accent/40 hover:bg-white/5">
      <div className="font-medium text-white">{label}</div>
      <div className="mt-1 text-slate-400">Drop or choose a file to upload.</div>
      <input type="file" accept={accept} className="mt-3 block w-full text-sm text-slate-400 file:mr-4 file:rounded-xl file:border-0 file:bg-accent/15 file:px-4 file:py-2 file:text-accent file:transition hover:file:bg-accent/25" onChange={(event) => onFile(event.target.files?.[0] ?? null)} />
    </label>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/70 p-4">
      <div className="text-xs uppercase tracking-[0.25em] text-slate-500">{label}</div>
      <div className="mt-2 text-lg font-semibold text-white">{value}</div>
    </div>
  );
}

function MiniMetric({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${color}`}>{value.toLocaleString()}</div>
    </div>
  );
}
