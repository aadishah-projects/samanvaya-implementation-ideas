import { useEffect, useMemo, useState } from 'react';
import api from '../api/client';

export default function ClaimsQueue() {
  const [claims, setClaims] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [detail, setDetail] = useState(null);
  const [msg, setMsg] = useState('');
  const [amountLimit, setAmountLimit] = useState(100000);
  const [mockCount, setMockCount] = useState(60);

  const load = async () => {
    try {
      const res = await api.get('/claims?status=APPROVED');
      setClaims(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    load();
    const i = setInterval(load, 4000);
    return () => clearInterval(i);
  }, []);

  const selectedClaims = useMemo(
    () => claims.filter((claim) => selected.has(claim.id)),
    [claims, selected],
  );
  const selectedClaimed = selectedClaims.reduce((total, claim) => total + Number(claim.claimed_amount || 0), 0);
  const selectedApproved = selectedClaims.reduce((total, claim) => total + Number(claim.approved_amount || 0), 0);

  const toggle = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const openDetail = async (claim) => {
    try {
      const res = await api.get(`/claims/${claim.id}/details`);
      setDetail(res.data);
    } catch (e) {
      setMsg('Could not load claim detail: ' + (e.response?.data?.detail || e.message));
    }
  };

  const processSelected = async () => {
    if (!selected.size) return setMsg('Select at least one claim.');
    try {
      const batch = await api.post('/batches', { claim_ids: [...selected] });
      setMsg(`Created payment batch ${batch.data.batch_code || batch.data.id}.`);
      setSelected(new Set());
      await load();
    } catch (e) {
      setMsg('Error: ' + (e.response?.data?.detail || e.message));
    }
  };

  const reviewDetail = async (status) => {
    if (!detail) return;
    try {
      const res = await api.post(`/claims/${detail.id}/review`, {
        status,
        notes: status === 'APPROVED' ? 'Reviewed from Samanvaya OpenIMIS mock.' : 'Marked during demo review.',
      });
      setDetail(res.data);
      setMsg(`Claim ${status.toLowerCase()} and audit log created.`);
      await load();
    } catch (e) {
      setMsg('Review failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const autoCreateBatches = async () => {
    try {
      const res = await api.post('/batches/auto', { amount_limit: Number(amountLimit) });
      setMsg(`Auto-created ${res.data.created_count} hospital batches (${npr(res.data.total_amount)}).`);
      setSelected(new Set());
      await load();
    } catch (e) {
      setMsg('Auto batching failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  const generateMockData = async () => {
    try {
      const res = await api.post('/demo/mock-data', { claim_count: Number(mockCount), reset: true });
      setDetail(null);
      setSelected(new Set());
      setMsg(`Generated ${res.data.claims} OpenIMIS-style claims.`);
      await load();
    } catch (e) {
      setMsg('Mock data failed: ' + (e.response?.data?.detail || e.message));
    }
  };

  if (detail) {
    return <ClaimDetail claim={detail} onBack={() => setDetail(null)} onReview={reviewDetail} npr={npr} message={msg} />;
  }

  return (
    <div className="mx-auto max-w-[1500px]">
      <section className="bg-white shadow-[0_1px_3px_rgba(0,0,0,0.12)]">
        <div className="border-b border-[#E0E0E0] px-4 py-3">
          <h1 className="text-[20px] font-normal text-[#424242]">{claims.length} Claims Found</h1>
        </div>

        <div className="flex flex-wrap items-center gap-3 border-b border-[#E0E0E0] bg-white px-4 py-3 text-[13px] text-[#757575]">
          <FilterChip text="Random Filter % 5" />
          <FilterChip text="Claimed Amount Above NPR" />
          <FilterChip text="Claimed Amount Above Diagnosis Avg % 10" />
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <label className="text-[12px] uppercase text-[#757575]">
              Amount limit
              <input
                value={amountLimit}
                onChange={(e) => setAmountLimit(e.target.value)}
                type="number"
                className="ml-2 h-9 w-28 rounded border border-[#BDBDBD] px-2 text-[13px] outline-none focus:border-[#00838F]"
              />
            </label>
            <button onClick={autoCreateBatches} className="openimis-button secondary">
              <img src="/icon.png" alt="" className="h-4 w-4" />
              Auto Batch
            </button>
            <input
              value={mockCount}
              onChange={(e) => setMockCount(e.target.value)}
              type="number"
              className="h-9 w-20 rounded border border-[#BDBDBD] px-2 text-[13px] outline-none focus:border-[#00838F]"
            />
            <button onClick={generateMockData} className="openimis-button secondary">
              Generate
            </button>
          </div>
        </div>

        {msg && <div className="border-b border-[#E0E0E0] bg-[#E0F7FA] px-4 py-2 text-[13px] text-[#006064]">{msg}</div>}

        <div className="flex flex-wrap items-center gap-4 border-b border-[#E0E0E0] px-4 py-3">
          <span className="text-[14px] text-[#424242]">Selected {selected.size} claim(s)</span>
          <button onClick={() => setSelected(new Set())} className="openimis-button text-only">CLEAR SELECTION</button>
          <button onClick={processSelected} className="openimis-button primary">
            <img src="/icon.png" alt="" className="h-4 w-4" />
            PROCESS SELECTED
          </button>
          <div className="ml-auto flex gap-8 text-[14px] text-[#424242]">
            <span title="Claimed">{'\u2211'} {npr(selectedClaimed)}</span>
            <span title="Approved">{'\u2211'} {npr(selectedApproved)}</span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px] text-[#424242]">
            <thead className="bg-[#F5F5F5] text-[12px] uppercase text-[#757575]">
              <tr>
                <th className="w-10 border-b border-[#E0E0E0] px-3 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={claims.length > 0 && selected.size === claims.length}
                    onChange={(e) => setSelected(e.target.checked ? new Set(claims.map((claim) => claim.id)) : new Set())}
                  />
                </th>
                {['Claim No.', 'Health Facility', 'Insuree', 'Employer', 'Claimed Date', 'Scheme', 'Review Status', 'Claimed', 'Approved', 'Claim Status'].map((label) => (
                  <SortableTh key={label} label={label} right={['Claimed', 'Approved'].includes(label)} />
                ))}
                <th className="w-12 border-b border-[#E0E0E0] px-3 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.id} className="hover:bg-[#F5F5F5]">
                  <td className="border-b border-[#E0E0E0] px-3 py-3">
                    <input type="checkbox" checked={selected.has(claim.id)} onChange={() => toggle(claim.id)} />
                  </td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">
                    <button onClick={() => openDetail(claim)} className="text-left text-[#1976D2] hover:underline">
                      {claim.claim_code}
                    </button>
                  </td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">{claim.health_facility}</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">{claim.insuree_name}</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">{claim.employer || 'Social Security Fund'}</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">{claim.claimed_date || formatDate(claim.approved_date)}</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">{claim.scheme || 'SSF Health Insurance'}</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">
                    <span className="inline-flex items-center gap-1 text-[#424242]">
                      <span className="material-icons text-[18px] text-[#757575]">person_outline</span>
                      {claim.review_status || 'Reviewed'}
                    </span>
                  </td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3 text-right">{npr(claim.claimed_amount)}</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3 text-right">{npr(claim.approved_amount)}</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3">Recommended</td>
                  <td className="border-b border-[#E0E0E0] px-3 py-3 text-center">
                    <button className="material-icons text-[20px] text-[#757575] hover:text-[#1976D2]" title="Print">print</button>
                  </td>
                </tr>
              ))}
              {!claims.length && (
                <tr>
                  <td colSpan="12" className="px-3 py-10 text-center text-[#757575]">No claims found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function ClaimDetail({ claim, onBack, onReview, npr, message }) {
  return (
    <div className="mx-auto max-w-[1200px]">
      <section className="bg-white p-4 shadow-[0_1px_3px_rgba(0,0,0,0.12)]">
        <div className="mb-4 flex items-center gap-3 border-b border-[#E0E0E0] pb-3">
          <button onClick={onBack} className="material-icons text-[26px] text-[#424242]" title="Back">arrow_back</button>
          <h1 className="text-[20px] font-normal text-[#424242]">Claim {claim.claim_code}</h1>
          <div className="ml-auto flex gap-2">
            <button onClick={() => onReview('PENDING')} className="openimis-button secondary">PENDING</button>
            <button onClick={() => onReview('REJECTED')} className="openimis-button warn">REJECT</button>
            <button onClick={() => onReview('APPROVED')} className="openimis-button primary">APPROVE</button>
          </div>
        </div>

        {message && <div className="mb-4 bg-[#E0F7FA] px-4 py-2 text-[13px] text-[#006064]">{message}</div>}

        <div className="grid gap-x-8 gap-y-3 md:grid-cols-2">
          <Field label="Scheme" value={claim.scheme} />
          <Field label="Health Facility" value={claim.health_facility} />
          <Field label="SSID" value={claim.ssid} />
          <Field label="Name" value={claim.insuree_name} />
          <Field label="Relation" value={claim.relation} />
          <Field label="Main Diagnosis" value={claim.diagnosis} />
          <Field label="Visit Dates" value={`${claim.visit_from || '-'} to ${claim.visit_to || '-'}`} />
          <Field label="Date Claimed" value={claim.claimed_date} />
          <Field label="Visit Type" value={claim.visit_type} />
          <Field label="Claimed Amount" value={npr(claim.claimed_amount)} />
          <Field label="Claim Administrator" value={claim.claim_administrator} />
          <Field label="Issued By" value={claim.issued_by} />
          <label className="flex items-center gap-2 text-[13px] text-[#424242]">
            <input type="checkbox" checked={Boolean(claim.is_reclaim)} readOnly />
            isReclaim
          </label>
        </div>

        <div className="mt-4">
          <label className="mb-1 block text-[12px] uppercase text-[#757575]">Explanation</label>
          <textarea
            readOnly
            value={claim.explanation || ''}
            className="min-h-24 w-full rounded border border-[#BDBDBD] px-3 py-2 text-[13px] text-[#424242] outline-none"
          />
        </div>

        <DetailSection title="Policy Information">
          <p className="text-[13px] text-[#424242]">{claim.policy_information || 'Active policy information not available.'}</p>
        </DetailSection>

        <DetailSection title="Employer Information">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Employer Name" value={claim.employer} />
            <Field label="Employer ESaid" value={claim.employer_esaid} />
          </div>
        </DetailSection>

        <DetailSection title="Hospital Bank Information">
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Bank Name" value={claim.bank_name} />
            <Field label="Branch Name" value={claim.branch_name} />
            <Field label="Account Name" value={claim.account_name} />
            <Field label="Account No" value={claim.account_no} />
          </div>
        </DetailSection>
      </section>
    </div>
  );
}

function FilterChip({ text }) {
  return <span className="rounded border border-[#E0E0E0] bg-[#F5F5F5] px-3 py-1.5">{text}</span>;
}

function SortableTh({ label, right }) {
  return (
    <th className={`border-b border-[#E0E0E0] px-3 py-3 font-medium ${right ? 'text-right' : 'text-left'}`}>
      <span className="inline-flex items-center gap-1">
        {label}
        <span className="material-icons text-[16px]">arrow_drop_down</span>
      </span>
    </th>
  );
}

function Field({ label, value }) {
  return (
    <div>
      <label className="mb-1 block text-[12px] uppercase text-[#757575]">{label}</label>
      <div className="min-h-10 rounded border border-[#BDBDBD] bg-white px-3 py-2 text-[13px] text-[#424242]">
        {value || '-'}
      </div>
    </div>
  );
}

function DetailSection({ title, children }) {
  return (
    <section className="mt-5 border-t border-[#E0E0E0] pt-4">
      <h2 className="mb-3 text-[14px] font-medium text-[#424242]">{title}</h2>
      {children}
    </section>
  );
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString() : '-';
}

function npr(value) {
  return 'NPR ' + Number(value || 0).toLocaleString('en-IN');
}
