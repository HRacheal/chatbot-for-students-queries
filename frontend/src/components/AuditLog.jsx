import { useEffect, useState } from "react";
import { fetchAuditLog, getErrorMessage } from "../lib/api";

const field = "mt-1 rounded-lg border border-slate-600 bg-slate-900 p-1.5 text-sm text-white";
const PAGE = 100;

// Super Administrators: who did what and when (sign-ins, account changes, enquiry updates,
// source reviews, routing and dataset changes). Entries never contain passwords or contact details.
function AuditLog() {
  const [filter, setFilter] = useState({ action: "", actor: "" });
  const [skip, setSkip] = useState(0);
  const [data, setData] = useState({ total: 0, entries: [] });
  const [error, setError] = useState("");

  const load = async (offset = skip) => {
    setError("");
    try {
      const params = { limit: PAGE, skip: offset };
      if (filter.action) params.action = filter.action;
      if (filter.actor) params.actor = filter.actor;
      setData(await fetchAuditLog(params));
    } catch (err) {
      setError(getErrorMessage(err, "Could not load the audit log."));
    }
  };

  useEffect(() => {
    load(skip);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip]);

  return (
    <div className="space-y-4 text-white">
      <div>
        <h2 className="text-2xl font-bold">System activity</h2>
        <p className="mt-1 text-sm text-slate-400">Audit log of staff actions. Passwords, tokens and enquirers&apos; contact details are never recorded.</p>
      </div>
      <form className="flex flex-wrap items-end gap-3 text-sm" onSubmit={(e) => { e.preventDefault(); setSkip(0); load(0); }}>
        <label className="flex flex-col">Action starts with
          <select className={field} value={filter.action} onChange={(e) => setFilter({ ...filter, action: e.target.value })}>
            <option value="">Any</option>
            <option value="auth">Sign-in / sign-out</option>
            <option value="staff">Staff accounts</option>
            <option value="enquiry">Enquiries</option>
            <option value="sources">Knowledge sources</option>
            <option value="dataset">Dataset and routing</option>
            <option value="official_links">Official links</option>
            <option value="guidance">Programme requirements</option>
          </select>
        </label>
        <label className="flex flex-col">Staff email contains
          <input className={field} value={filter.actor} maxLength={100} onChange={(e) => setFilter({ ...filter, actor: e.target.value })} />
        </label>
        <button type="submit" className="rounded-lg bg-slate-700 px-3 py-1.5 hover:bg-slate-600">Filter</button>
      </form>
      {error && <p className="rounded-lg bg-red-900/50 px-3 py-2 text-red-200" role="alert">{error}</p>}
      <div className="overflow-x-auto rounded-xl border border-slate-700">
        <table className="w-full min-w-[720px] text-left text-xs">
          <thead className="bg-slate-800 uppercase tracking-wide text-slate-400">
            <tr><th className="p-2">When</th><th className="p-2">Who</th><th className="p-2">Action</th><th className="p-2">Target</th><th className="p-2">Details</th><th className="p-2">Result</th></tr>
          </thead>
          <tbody>
            {data.entries.map((e) => (
              <tr key={e.id} className="border-t border-slate-700 align-top text-slate-300">
                <td className="p-2 whitespace-nowrap">{e.at ? new Date(e.at).toLocaleString() : ""}</td>
                <td className="p-2">{e.actor_email || "—"}{e.actor_role && <span className="block text-slate-500">{e.actor_role}</span>}</td>
                <td className="p-2 font-mono">{e.action}</td>
                <td className="p-2">{[e.target_type, e.target_id].filter(Boolean).join(" ")}</td>
                <td className="p-2">{Object.entries(e.details || {}).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" · ")}</td>
                <td className={`p-2 ${e.outcome === "failed" ? "text-red-300" : ""}`}>{e.outcome}</td>
              </tr>
            ))}
            {!data.entries.length && <tr><td colSpan={6} className="p-3 text-slate-400">No activity recorded.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3 text-sm text-slate-300">
        <button type="button" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - PAGE))}
          className="rounded-lg bg-slate-700 px-3 py-1 disabled:opacity-40">Newer</button>
        <span>{data.total ? `${skip + 1}–${Math.min(skip + PAGE, data.total)} of ${data.total}` : "0 entries"}</span>
        <button type="button" disabled={skip + PAGE >= data.total} onClick={() => setSkip(skip + PAGE)}
          className="rounded-lg bg-slate-700 px-3 py-1 disabled:opacity-40">Older</button>
      </div>
    </div>
  );
}

export default AuditLog;
