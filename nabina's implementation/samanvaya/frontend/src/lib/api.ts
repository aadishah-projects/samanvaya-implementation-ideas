export type DashboardResponse = {
  metrics: {
    totalClaims: number;
    fullyMatched: number;
    partialMatches: number;
    failed: number;
    anomalies: number;
    matchRate: number;
  };
  statusBreakdown: Array<{ name: string; value: number; color: string }>;
  trend: Array<{ day: string; fully_matched: number; partial_matches: number; failed: number; anomalies: number }>;
  uploads: Array<{ source_type: string; filename: string; record_count: number; status: string; created_at: string }>;
  recentClaims: ClaimRow[];
  recentAnomalies: ClaimRow[];
};

export type ClaimRow = {
  claim_id: string;
  payment_ref?: string | null;
  provider: string;
  claim_amount: number;
  paid_amount?: number | null;
  match_score: number;
  status: 'fully_matched' | 'partial_match' | 'failed' | 'anomaly';
  anomaly_reason?: string | null;
  explanation: string;
  payment_date?: string | null;
  claim_json: string;
  payment_json?: string | null;
  updated_at: string;
};

export type ClaimDetail = {
  claim: Record<string, unknown>;
  reconciliation: ClaimRow | null;
  payment: Record<string, unknown> | null;
  smsMessage: string;
};

export type SmsResponse = {
  claim_id: string;
  message: string;
  status: string;
};

export type HospitalSummary = {
  provider: string;
  total_claims: number;
  fully_matched: number;
  partial_matches: number;
  failed: number;
  anomalies: number;
  total_claimed: number;
  total_paid: number;
  match_rate: number;
  unresolved_issues: number;
};

export type HospitalClaim = {
  claim_id: string;
  payment_ref?: string | null;
  provider: string;
  claim_amount: number;
  paid_amount?: number | null;
  match_score: number;
  status: 'fully_matched' | 'partial_match' | 'failed' | 'anomaly';
  anomaly_reason?: string | null;
  explanation: string;
  payment_date?: string | null;
  claim_json: string;
  payment_json?: string | null;
  updated_at: string;
  patient_id: string;
  diagnosis: string;
  resolution: string;
};

export type HospitalDetail = {
  hospital: string;
  summary: {
    total_claims: number;
    fully_matched: number;
    partial_matches: number;
    failed: number;
    anomalies: number;
    total_claimed: number;
    total_paid: number;
    match_rate: number;
    unresolved_issues: number;
  };
  anomaly_breakdown: Array<{ reason: string; count: number }>;
  claims: HospitalClaim[];
};

const apiBase = '';

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export const api = {
  getDashboard: () => requestJson<DashboardResponse>('/api/dashboard'),
  getClaims: (status?: string, search?: string) => {
    const query = new URLSearchParams();
    if (status) query.set('status', status);
    if (search) query.set('search', search);
    return requestJson<{ items: ClaimRow[]; total: number }>(`/api/claims?${query.toString()}`);
  },
  getClaimDetail: (claimId: string) => requestJson<ClaimDetail>(`/api/claims/${encodeURIComponent(claimId)}`),
  uploadOpenImis: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return requestJson('/api/upload/openimis', { method: 'POST', body: form });
  },
  uploadSosys: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return requestJson('/api/upload/sosys', { method: 'POST', body: form });
  },
  runReconciliation: () => requestJson('/api/reconcile/run', { method: 'POST' }),
  generateSynthetic: (count = 500) => requestJson(`/api/synthetic/generate?count=${count}`, { method: 'POST' }),
  sendSms: (claimId: string) => requestJson<SmsResponse>(`/api/claims/${encodeURIComponent(claimId)}/sms`, { method: 'POST' }),
  getHospitals: () => requestJson<{ items: HospitalSummary[]; total: number }>('/api/hospitals'),
  getHospitalDetail: (hospitalName: string) =>
    requestJson<HospitalDetail>(`/api/hospitals/${encodeURIComponent(hospitalName)}`),
};