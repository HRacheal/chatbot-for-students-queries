import { useMemo, useState } from "react";
import PropTypes from "prop-types";

// Small SVG charts for the staff dashboard (no chart library).
// Colours: validated pair for the dark dashboard surface (#1e293b): blue = received,
// orange = resolved (dataviz validator: all checks pass). Text always uses text colours,
// identity is given by the legend, and every chart has a table view.
const SERIES = { received: "#3987e5", resolved: "#d95926" };
const GRID = "#334155";
const AXIS_TEXT = "#94a3b8";

const shortDate = (iso) => {
  const [, m, d] = iso.split("-");
  return `${Number(d)}/${Number(m)}`;
};

function niceMax(value) {
  if (value <= 4) return 4;
  const pow = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * pow * 4 >= value) * pow;
  return step * 4;
}

// Enquiries received and resolved per day.
export function TrendChart({ data }) {
  const [hover, setHover] = useState(null);
  const [showTable, setShowTable] = useState(false);
  const width = 720;
  const height = 240;
  const pad = { top: 16, right: 16, bottom: 28, left: 36 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const max = useMemo(() => niceMax(Math.max(1, ...data.map((d) => Math.max(d.received, d.resolved)))), [data]);
  const x = (i) => pad.left + (data.length <= 1 ? innerW / 2 : (i * innerW) / (data.length - 1));
  const y = (v) => pad.top + innerH - (v / max) * innerH;
  const path = (key) => data.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(" ");
  const ticks = [0, max / 4, max / 2, (3 * max) / 4, max];
  const labelEvery = Math.max(1, Math.ceil(data.length / 8));
  const totals = data.reduce((t, d) => ({ received: t.received + d.received, resolved: t.resolved + d.resolved }),
    { received: 0, resolved: 0 });

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * width;
    const i = Math.round(((px - pad.left) / innerW) * (data.length - 1));
    setHover(Math.max(0, Math.min(data.length - 1, i)));
  };

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-4 text-xs text-slate-300">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5 rounded" style={{ background: SERIES.received }} aria-hidden="true" />
          Received ({totals.received})
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5 rounded" style={{ background: SERIES.resolved }} aria-hidden="true" />
          Resolved ({totals.resolved})
        </span>
        <button type="button" className="ml-auto text-slate-400 underline hover:text-white"
          onClick={() => setShowTable((v) => !v)}>
          {showTable ? "Show chart" : "Show table"}
        </button>
      </div>
      {showTable ? (
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="text-slate-400"><tr><th className="p-1">Date</th><th className="p-1">Received</th><th className="p-1">Resolved</th></tr></thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.date} className="border-t border-slate-700">
                  <td className="p-1">{d.date}</td><td className="p-1">{d.received}</td><td className="p-1">{d.resolved}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative">
          <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img"
            aria-label={`Enquiries received (${totals.received}) and resolved (${totals.resolved}) per day`}
            onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            {ticks.map((t) => (
              <g key={t}>
                <line x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth="1"
                  strokeDasharray={t === 0 ? "" : "2 4"} />
                <text x={pad.left - 6} y={y(t) + 3} textAnchor="end" fontSize="10" fill={AXIS_TEXT}>
                  {Number.isInteger(t) ? t : t.toFixed(1)}
                </text>
              </g>
            ))}
            {data.map((d, i) => (i % labelEvery === 0 || i === data.length - 1) && (
              <text key={d.date} x={x(i)} y={height - 8} textAnchor="middle" fontSize="10" fill={AXIS_TEXT}>
                {shortDate(d.date)}
              </text>
            ))}
            <path d={path("received")} fill="none" stroke={SERIES.received} strokeWidth="2" strokeLinejoin="round" />
            <path d={path("resolved")} fill="none" stroke={SERIES.resolved} strokeWidth="2" strokeLinejoin="round" />
            {hover !== null && (
              <g>
                <line x1={x(hover)} x2={x(hover)} y1={pad.top} y2={pad.top + innerH} stroke={AXIS_TEXT} strokeWidth="1" />
                {["received", "resolved"].map((k) => (
                  <circle key={k} cx={x(hover)} cy={y(data[hover][k])} r="4.5" fill={SERIES[k]}
                    stroke="#1e293b" strokeWidth="2" />
                ))}
              </g>
            )}
          </svg>
          {hover !== null && (
            <div className="pointer-events-none absolute top-1 rounded-md border border-slate-600 bg-slate-950/95 px-2 py-1 text-xs text-slate-200 shadow"
              style={{ left: `${Math.min(80, (x(hover) / width) * 100)}%` }}>
              <p className="font-medium">{data[hover].date}</p>
              <p>Received: {data[hover].received}</p>
              <p>Resolved: {data[hover].resolved}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

TrendChart.propTypes = {
  data: PropTypes.arrayOf(PropTypes.shape({
    date: PropTypes.string.isRequired, received: PropTypes.number.isRequired, resolved: PropTypes.number.isRequired,
  })).isRequired,
};

// Horizontal bars for one measure (single hue), with value labels and a hover detail line.
export function BarList({ rows, color = SERIES.received, emptyText = "No data yet." }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (!rows.length || rows.every((r) => r.value === 0)) {
    return <p className="text-sm text-slate-400">{emptyText}</p>;
  }
  return (
    <ul className="space-y-2">
      {rows.map((r) => (
        <li key={r.key} className="text-sm" onMouseEnter={() => setHover(r.key)} onMouseLeave={() => setHover(null)}>
          <div className="flex justify-between gap-2 text-slate-300">
            <span className="truncate">{r.label}</span>
            <span className="font-medium text-slate-100">{r.value}</span>
          </div>
          <div className="mt-1 h-2.5 w-full rounded-sm bg-slate-700/40">
            <div className="h-2.5 rounded-r" style={{ width: `${(r.value / max) * 100}%`, background: color,
              minWidth: r.value ? 4 : 0 }} />
          </div>
          {hover === r.key && r.detail && <p className="mt-0.5 text-xs text-slate-400">{r.detail}</p>}
        </li>
      ))}
    </ul>
  );
}

BarList.propTypes = {
  rows: PropTypes.arrayOf(PropTypes.shape({
    key: PropTypes.string.isRequired, label: PropTypes.string.isRequired, value: PropTypes.number.isRequired,
    detail: PropTypes.string,
  })).isRequired,
  color: PropTypes.string,
  emptyText: PropTypes.string,
};
