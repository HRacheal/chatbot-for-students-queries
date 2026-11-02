import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { extractResults, getErrorMessage, getGuidanceOptions, getRecommendations } from "../lib/api";
import { isOfficialPageUrl } from "../lib/citations";
import { OUTCOME_LABELS } from "../lib/workflow";

const FALLBACK_GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "E"];

const emptyRow = () => ({ subject: "", grade: "" });

// Degree guidance: upload a results slip (or type grades), confirm them, then compare
// them with programme requirements that USIU staff have verified. Guidance only.
function GuidancePanel({ onClose }) {
  const [options, setOptions] = useState(null);
  const [rows, setRows] = useState([emptyRow()]);
  const [meanGrade, setMeanGrade] = useState("");
  const [interests, setInterests] = useState("");
  const [notice, setNotice] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    getGuidanceOptions().then(setOptions).catch(() => setOptions(null));
  }, []);

  const grades = options?.grades || FALLBACK_GRADES;
  const subjects = options?.subjects || [];

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setError("");
    setNotice("");
    setResult(null);
    try {
      const data = await extractResults(file);
      setRows(data.subjects.length ? data.subjects.map((s) => ({ subject: s.subject, grade: s.grade })) : [emptyRow()]);
      setMeanGrade(data.mean_grade || "");
      setWarnings(data.warnings || []);
      setNotice(data.message);
    } catch (err) {
      setError(getErrorMessage(err, "The file could not be read. Please enter your grades manually."));
    } finally {
      setBusy(false);
    }
  };

  const updateRow = (index, field) => (e) =>
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: e.target.value } : row)));

  const handleRecommend = async (e) => {
    e.preventDefault();
    const filled = rows.filter((r) => r.subject && r.grade);
    if (!filled.length) {
      setError("Enter at least one subject and grade.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setResult(await getRecommendations({ subjects: filled, mean_grade: meanGrade || null, interests }));
    } catch (err) {
      setError(getErrorMessage(err, "Guidance is not available right now."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 text-white">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-medium">Degree guidance</h2>
        <button type="button" onClick={onClose} className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600">
          Back to chat
        </button>
      </div>
      <p className="rounded border border-yellow-700 bg-yellow-900/30 p-2 text-sm text-yellow-100">
        {options?.disclaimer ||
          "This is guidance only, not an admission decision. Only USIU-Africa Admissions can confirm eligibility."}
      </p>

      <div className="rounded bg-gray-900 p-3 text-sm">
        <label className="flex flex-col">
          Upload your results slip (PDF or .txt, up to {options?.max_upload_mb || 5} MB), or type your grades below
          <input type="file" accept=".pdf,.txt,application/pdf,text/plain" className="mt-2" onChange={handleFile} disabled={busy} />
        </label>
        <p className="mt-1 text-xs text-gray-400">
          The file is read in memory and not stored. Photos and scans can&apos;t be read yet; enter the grades instead.
        </p>
      </div>

      {notice && <p className="rounded bg-blue-900/50 px-2 py-1 text-sm text-blue-100">{notice}</p>}
      {warnings.map((w) => <p key={w} className="text-sm text-yellow-300">{w}</p>)}
      {error && <p className="rounded bg-red-900/60 px-2 py-1 text-sm text-red-200" role="alert">{error}</p>}

      <form onSubmit={handleRecommend} className="space-y-2 text-sm" aria-label="Confirm your grades">
        <p className="font-medium">Your subjects and grades (please check them)</p>
        {rows.map((row, i) => (
          <div key={i} className="flex gap-2">
            <select aria-label={`Subject ${i + 1}`} className="flex-1 rounded bg-gray-700 p-1.5" value={row.subject} onChange={updateRow(i, "subject")}>
              <option value="">Subject…</option>
              {subjects.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <select aria-label={`Grade ${i + 1}`} className="w-24 rounded bg-gray-700 p-1.5" value={row.grade} onChange={updateRow(i, "grade")}>
              <option value="">Grade</option>
              {grades.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
            <button type="button" aria-label={`Remove subject ${i + 1}`} className="rounded bg-gray-700 px-2 hover:bg-gray-600"
              onClick={() => setRows((prev) => (prev.length > 1 ? prev.filter((_, j) => j !== i) : [emptyRow()]))}>
              ×
            </button>
          </div>
        ))}
        <button type="button" className="rounded bg-gray-700 px-3 py-1 hover:bg-gray-600"
          onClick={() => setRows((prev) => (prev.length < 15 ? [...prev, emptyRow()] : prev))}>
          Add subject
        </button>
        <div className="flex flex-wrap gap-3">
          <label className="flex flex-col">
            Mean grade (as on your certificate)
            <select className="mt-1 w-32 rounded bg-gray-700 p-1.5" value={meanGrade} onChange={(e) => setMeanGrade(e.target.value)}>
              <option value="">Not given</option>
              {grades.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </label>
          <label className="flex flex-1 flex-col">
            Interests (optional, e.g. computing, business)
            <input className="mt-1 rounded bg-gray-700 p-1.5" value={interests} maxLength={300} onChange={(e) => setInterests(e.target.value)} />
          </label>
        </div>
        <button type="submit" disabled={busy} className="rounded bg-blue-600 px-4 py-1.5 font-medium hover:bg-blue-500 disabled:opacity-50">
          {busy ? "Working…" : "Get guidance"}
        </button>
      </form>

      {result && <GuidanceResult result={result} />}
    </div>
  );
}

function GuidanceResult({ result }) {
  return (
    <div className="space-y-3 rounded bg-gray-900 p-3 text-sm" aria-live="polite">
      <p className="font-medium">{result.message}</p>
      {result.mean_grade_note && <p className="text-xs text-gray-400">{result.mean_grade_note}</p>}
      <p className="text-xs text-gray-400">How this works: {result.criteria}</p>
      {result.recommendations?.map((r) => {
        const outcome = OUTCOME_LABELS[r.outcome] || { text: r.outcome, style: "bg-gray-700" };
        return (
          <div key={r.programme} className="rounded border border-gray-700 p-2">
            <div className="flex flex-wrap items-center gap-2">
              {isOfficialPageUrl(r.url) ? (
                <a href={r.url} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-300 underline">{r.programme}</a>
              ) : (
                <span className="font-medium">{r.programme}</span>
              )}
              <span className={`rounded px-2 py-0.5 text-xs ${outcome.style}`}>{outcome.text}</span>
              {r.source_date && <span className="text-xs text-gray-400">requirements dated {r.source_date}</span>}
            </div>
            <ul className="mt-1 list-disc pl-5 text-gray-300">
              {r.reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
            {r.notes && <p className="mt-1 text-xs text-gray-400">{r.notes}</p>}
          </div>
        );
      })}
      {result.places_to_look?.filter((p) => isOfficialPageUrl(p.url)).length > 0 && (
        <ul className="list-disc pl-5">
          {result.places_to_look.filter((p) => isOfficialPageUrl(p.url)).map((p) => (
            <li key={p.url}>
              <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline">{p.title}</a>
              <span className="ml-1 text-xs text-gray-400">(not verified)</span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-yellow-200">{result.disclaimer}</p>
    </div>
  );
}

GuidanceResult.propTypes = {
  result: PropTypes.shape({
    message: PropTypes.string,
    criteria: PropTypes.string,
    disclaimer: PropTypes.string,
    mean_grade_note: PropTypes.string,
    recommendations: PropTypes.arrayOf(PropTypes.shape({
      programme: PropTypes.string,
      url: PropTypes.string,
      outcome: PropTypes.string,
      reasons: PropTypes.arrayOf(PropTypes.string),
      notes: PropTypes.string,
      source_date: PropTypes.string,
    })),
    places_to_look: PropTypes.arrayOf(PropTypes.shape({ title: PropTypes.string, url: PropTypes.string })),
  }).isRequired,
};

GuidancePanel.propTypes = {
  onClose: PropTypes.func.isRequired,
};

export { GuidanceResult };
export default GuidancePanel;
