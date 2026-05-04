import { useEffect, useState } from "react";
import { domainApi } from "../lib/api";
import Spinner from "../components/Spinner";

const emptyCost = {
  transport_type: "cab",
  origin: "",
  destination: "",
  distance_km: "",
  amount: "",
  currency: "INR",
  receipt_url: "",
};

export default function Expenses() {
  const [reports, setReports] = useState([]);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    employee_name: "",
    report_number: `EXP-${Date.now().toString().slice(-6)}`,
    status: "DRAFT",
    currency: "INR",
    source_file_url: "",
    transportation_costs: [emptyCost],
  });
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadResult, setDownloadResult] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const [appInfo, list] = await Promise.all([domainApi.appInfo(), domainApi.listReports()]);
      setInfo(appInfo.data);
      setReports(list.data || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function updateCost(index, key, value) {
    setForm(prev => ({
      ...prev,
      transportation_costs: prev.transportation_costs.map((c, i) => i === index ? { ...c, [key]: value } : c),
    }));
  }

  async function submit(e) {
    e.preventDefault();
    const payload = {
      ...form,
      transportation_costs: form.transportation_costs.map(c => ({
        ...c,
        distance_km: c.distance_km === "" ? null : Number(c.distance_km),
        amount: Number(c.amount || 0),
        receipt_url: c.receipt_url || null,
      })),
    };
    await domainApi.createReport(payload);
    setForm(prev => ({ ...prev, report_number: `EXP-${Date.now().toString().slice(-6)}`, transportation_costs: [emptyCost] }));
    load();
  }

  async function testDownload() {
    const result = await domainApi.downloadFile(downloadUrl);
    setDownloadResult(result.data);
  }

  return (
    <div className="max-w-6xl mx-auto animate-slide-up space-y-5">
      <div className="card p-6">
        <p className="eyebrow">Expenses</p>
        <h1 className="h-page mt-2">Transportation reimbursement workspace</h1>
        <p className="lead mt-2">{info?.domain || "Expense application workspace"}{info?.target && <span className="ml-2 text-xs text-[var(--muted)] font-mono">{info.target}</span>}</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-[430px_1fr] items-start">
        <form onSubmit={submit} className="card p-5 space-y-4">
          <div>
            <p className="eyebrow">Form</p>
            <h2 className="h-section mt-1">Transportation reimbursement</h2>
          </div>
          <input className="input" placeholder="Employee name" value={form.employee_name} onChange={e => setForm({ ...form, employee_name: e.target.value })} required />
          <input className="input" placeholder="Report number" value={form.report_number} onChange={e => setForm({ ...form, report_number: e.target.value })} required />
          <input className="input" placeholder="Source file URL" value={form.source_file_url} onChange={e => setForm({ ...form, source_file_url: e.target.value })} />

          {form.transportation_costs.map((cost, index) => (
            <div key={index} className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-3 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input className="input" placeholder="Type" value={cost.transport_type} onChange={e => updateCost(index, "transport_type", e.target.value)} />
                <input className="input" placeholder="Amount" type="number" value={cost.amount} onChange={e => updateCost(index, "amount", e.target.value)} required />
                <input className="input" placeholder="Origin" value={cost.origin} onChange={e => updateCost(index, "origin", e.target.value)} />
                <input className="input" placeholder="Destination" value={cost.destination} onChange={e => updateCost(index, "destination", e.target.value)} />
                <input className="input" placeholder="Distance km" type="number" value={cost.distance_km} onChange={e => updateCost(index, "distance_km", e.target.value)} />
                <input className="input" placeholder="Currency" value={cost.currency} onChange={e => updateCost(index, "currency", e.target.value)} />
              </div>
              <input className="input" placeholder="Receipt URL" value={cost.receipt_url} onChange={e => updateCost(index, "receipt_url", e.target.value)} />
            </div>
          ))}

          <button type="button" className="btn btn-secondary w-full" onClick={() => setForm(prev => ({ ...prev, transportation_costs: [...prev.transportation_costs, { ...emptyCost }] }))}>
            Add Transportation Cost
          </button>
          <button className="btn btn-primary w-full">Save Expense Report</button>
        </form>

        <div className="space-y-5">
          <div className="card p-5 space-y-3">
            <div>
              <p className="eyebrow">Target REST File Download</p>
              <h2 className="h-section mt-1">Test a remote file URL</h2>
            </div>
            <div className="flex gap-2">
              <input className="input flex-1" placeholder="http://localhost:8000/testing/mcp_hub_accuracy_improvements.md" value={downloadUrl} onChange={e => setDownloadUrl(e.target.value)} />
              <button className="btn btn-secondary" onClick={testDownload} disabled={!downloadUrl}>Test</button>
            </div>
            {downloadResult && (
              <pre className="code-block mt-3">{JSON.stringify(downloadResult, null, 2)}</pre>
            )}
          </div>

          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-[var(--line)]">
              <p className="eyebrow">Normalized Reports</p>
            </div>
            {loading ? <div className="p-8 flex justify-center"><Spinner size={20} /></div> : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--line)] text-[var(--muted-2)]">
                    <th className="text-left px-5 py-3 font-semibold text-[10px] uppercase tracking-[0.18em]">Report</th>
                    <th className="text-left px-5 py-3 font-semibold text-[10px] uppercase tracking-[0.18em]">Employee</th>
                    <th className="text-left px-5 py-3 font-semibold text-[10px] uppercase tracking-[0.18em]">Status</th>
                    <th className="text-left px-5 py-3 font-semibold text-[10px] uppercase tracking-[0.18em]">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {reports.map(report => (
                    <tr key={report.id} className="hover:bg-[var(--hover)]">
                      <td className="px-5 py-3 text-sm font-medium">{report.report_number}</td>
                      <td className="px-5 py-3 text-sm text-[var(--muted)]">{report.employee_name}</td>
                      <td className="px-5 py-3 text-sm">{report.status}</td>
                      <td className="px-5 py-3 text-sm font-medium">{report.currency} {report.total_amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
