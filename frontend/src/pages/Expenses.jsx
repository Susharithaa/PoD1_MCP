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
    <div className="max-w-6xl animate-slide-up">
      <div className="mb-6">
        <h1 className="page-title">Expense Reports</h1>
        {info && <p className="text-sm text-zinc-500 mt-1">{info.domain}</p>}
      </div>

      <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
        <form onSubmit={submit} className="card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-100">Transportation Reimbursement</h2>
          <input className="input w-full" placeholder="Employee name" value={form.employee_name} onChange={e => setForm({ ...form, employee_name: e.target.value })} required />
          <input className="input w-full" placeholder="Report number" value={form.report_number} onChange={e => setForm({ ...form, report_number: e.target.value })} required />
          <input className="input w-full" placeholder="Source file URL" value={form.source_file_url} onChange={e => setForm({ ...form, source_file_url: e.target.value })} />

          {form.transportation_costs.map((cost, index) => (
            <div key={index} className="rounded border border-zinc-800 p-3 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input className="input" placeholder="Type" value={cost.transport_type} onChange={e => updateCost(index, "transport_type", e.target.value)} />
                <input className="input" placeholder="Amount" type="number" value={cost.amount} onChange={e => updateCost(index, "amount", e.target.value)} required />
                <input className="input" placeholder="Origin" value={cost.origin} onChange={e => updateCost(index, "origin", e.target.value)} />
                <input className="input" placeholder="Destination" value={cost.destination} onChange={e => updateCost(index, "destination", e.target.value)} />
                <input className="input" placeholder="Distance km" type="number" value={cost.distance_km} onChange={e => updateCost(index, "distance_km", e.target.value)} />
                <input className="input" placeholder="Currency" value={cost.currency} onChange={e => updateCost(index, "currency", e.target.value)} />
              </div>
              <input className="input w-full" placeholder="Receipt URL" value={cost.receipt_url} onChange={e => updateCost(index, "receipt_url", e.target.value)} />
            </div>
          ))}

          <button type="button" className="btn-secondary w-full" onClick={() => setForm(prev => ({ ...prev, transportation_costs: [...prev.transportation_costs, emptyCost] }))}>
            Add Transportation Cost
          </button>
          <button className="btn-primary w-full">Save Expense Report</button>
        </form>

        <div className="space-y-4">
          <div className="card p-4">
            <h2 className="text-sm font-semibold text-zinc-100 mb-3">Target REST File Download</h2>
            <div className="flex gap-2">
              <input className="input flex-1" placeholder="https://example.com/file.txt" value={downloadUrl} onChange={e => setDownloadUrl(e.target.value)} />
              <button className="btn-secondary" onClick={testDownload} disabled={!downloadUrl}>Test</button>
            </div>
            {downloadResult && (
              <pre className="mt-3 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-3 overflow-auto">
                {JSON.stringify(downloadResult, null, 2)}
              </pre>
            )}
          </div>

          <div className="card overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800 text-sm font-semibold text-zinc-100">Normalized Reports</div>
            {loading ? <div className="p-8 flex justify-center"><Spinner size={20} /></div> : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-500">
                    <th className="text-left px-4 py-3">Report</th>
                    <th className="text-left px-4 py-3">Employee</th>
                    <th className="text-left px-4 py-3">Status</th>
                    <th className="text-left px-4 py-3">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map(report => (
                    <tr key={report.id} className="border-b border-zinc-800/60">
                      <td className="px-4 py-3 text-zinc-200">{report.report_number}</td>
                      <td className="px-4 py-3 text-zinc-400">{report.employee_name}</td>
                      <td className="px-4 py-3 text-zinc-500">{report.status}</td>
                      <td className="px-4 py-3 text-zinc-200">{report.currency} {report.total_amount}</td>
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
