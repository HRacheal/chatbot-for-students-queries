import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getDashboard, getErrorMessage } from "../lib/api";
import { ENQUIRY_STATUS_LABELS, ENQUIRY_STATUS_STYLES, OPEN_ENQUIRY_STATUSES } from "../lib/workflow";
import { BarList, TrendChart } from "./DashboardCharts";

const formatDate = (value) => (value ? new Date(value).toLocaleString() : "");

function StatCard({ label, value, hint = "", onClick = null, accent = "text-white" }) {
  const body = (
    <>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${accent}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </>
  );
  const cls = "rounded-xl border border-slate-700/70 bg-slate-800/80 p-4 text-left";
  return onClick ? (
    <button type="button" onClick={onClick} className={`${cls} transition hover:border-amber-400/60`}>{body}</button>
  ) : <div className={cls}>{body}</div>;
}

StatCard.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
  hint: PropTypes.string,
  onClick: PropTypes.func,
  accent: PropTypes.string,
};

// Overview of the enquiries the signed-in person may see (all departments for a Super
// Administrator, otherwise their own). Every number comes from the database via the API.
function DashboardOverview({ me, onOpenEnquiries }) {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setError("");
    getDashboard(days)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((err) => { if (!cancelled) setError(getErrorMessage(err, "Could not load the dashboard.")); });
    return () => { cancelled = true; };
  }, [days]);

  if (error) return <p className="rounded-lg bg-red-900/50 p-3 text-red-200" role="alert">{error}</p>;
  if (!data) return <p className="text-slate-400">Loading dashboard…</p>;

  const s = data.stats;
  const open = (filter) => onOpenEnquiries && (() => onOpenEnquiries(filter));
  const departmentRows = Object.entries(data.departments).map(([key, label]) => {
    const counts = s.by_department[key] || {};
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    const openCount = OPEN_ENQUIRY_STATUSES.reduce((n, k) => n + (counts[k] || 0), 0);
    return { key, label, value: total, detail: `${openCount} open · ${(counts.resolved || 0) + (counts.closed || 0)} resolved or closed` };
  }).sort((a, b) => b.value - a.value);
  const statusRows = Object.entries(ENQUIRY_STATUS_LABELS).map(([key, label]) => ({
    key, label, value: s.by_status[key] || 0,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-white">Welcome, {me.name || me.email}</h2>
          <p className="text-sm text-slate-400">
            {me.permissions.view_all_departments ? "All departments" : Object.values(me.department_labels).join(", ")}
            {" · "}{me.role_label}
          </p>
        </div>
        <label className="text-sm text-slate-300">
          Period{" "}
          <select className="ml-1 rounded-lg border border-slate-600 bg-slate-900 p-1.5" value={days}
            onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        <StatCard label="Total enquiries" value={s.total} onClick={open({ status: "" })} />
        <StatCard label="New" value={s.by_status.new || 0} onClick={open({ status: "new" })} accent="text-sky-300" />
        <StatCard label="Pending" value={s.by_status.pending || 0} onClick={open({ status: "pending" })} accent="text-amber-300" />
        <StatCard label="In progress" value={s.by_status.in_progress || 0} onClick={open({ status: "in_progress" })} accent="text-indigo-300" />
        <StatCard label="Awaiting response" value={s.by_status.awaiting_response || 0} onClick={open({ status: "awaiting_response" })} accent="text-fuchsia-300" />
        <StatCard label="Resolved" value={s.by_status.resolved || 0} onClick={open({ status: "resolved" })} accent="text-emerald-300" />
        <StatCard label="Awaiting attention" value={s.awaiting_attention} hint="New + pending"
          onClick={open({ status: "attention" })} accent="text-amber-300" />
        <StatCard label="Unresolved chatbot questions" value={data.unresolved_chatbot_questions}
          hint="Questions USIUBOT could not answer" />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="rounded-xl border border-slate-700/70 bg-slate-800/80 p-4 xl:col-span-2">
          <h3 className="mb-3 font-semibold text-white">Enquiry trend · last {data.days} days</h3>
          <TrendChart data={data.trend} />
        </section>
        <section className="rounded-xl border border-slate-700/70 bg-slate-800/80 p-4">
          <h3 className="mb-3 font-semibold text-white">Enquiries by status</h3>
          <BarList rows={statusRows} emptyText="No enquiries yet." />
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <section className="rounded-xl border border-slate-700/70 bg-slate-800/80 p-4">
          <h3 className="mb-3 font-semibold text-white">Enquiries by department</h3>
          <BarList rows={departmentRows} emptyText="No enquiries yet." />
          <p className="mt-3 text-xs text-slate-400">Hover a department for open / resolved counts.</p>
        </section>
        <section className="rounded-xl border border-slate-700/70 bg-slate-800/80 p-4 xl:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-white">Awaiting departmental attention</h3>
            <span className="text-xs text-slate-400">Assigned to you and open: {data.assigned_to_me_open}</span>
          </div>
          {data.awaiting_attention.length === 0 ? (
            <p className="text-sm text-slate-400">Nothing is waiting. 🎉</p>
          ) : (
            <ul className="divide-y divide-slate-700">
              {data.awaiting_attention.map((e) => (
                <li key={e.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${ENQUIRY_STATUS_STYLES[e.status] || ""}`}>{e.status_label}</span>
                  <span className="font-mono text-xs text-slate-400">{e.reference}</span>
                  <span className="min-w-0 flex-1 truncate text-slate-200">{e.question}</span>
                  <span className="text-xs text-slate-400">{e.department_label} · {formatDate(e.created_at)}</span>
                  {onOpenEnquiries && (
                    <button type="button" className="rounded bg-slate-700 px-2 py-0.5 text-xs text-white hover:bg-slate-600"
                      onClick={() => onOpenEnquiries({ department: e.department, open: e.id })}>Open</button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

DashboardOverview.propTypes = {
  me: PropTypes.object.isRequired,
  onOpenEnquiries: PropTypes.func,
};

export default DashboardOverview;
