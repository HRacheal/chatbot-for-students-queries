import { useEffect, useState } from "react";
import {
  createProgrammeRequirement, deleteProgrammeRequirement, fetchProgrammeRequirements, getErrorMessage,
  getGuidanceOptions, updateProgrammeRequirement,
} from "../lib/api";
import { isOfficialPageUrl } from "../lib/citations";
import { formatRules, parseRules } from "../lib/workflow";

const GRADES = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "E"];
const EMPTY = { programme: "", level: "undergraduate", url: "", source_date: "", min_mean_grade: "", rules: "",
  notes: "", keywords: "", verified: false };

// Admin page for programme entry requirements used by degree guidance. Only records
// marked verified (checked against the linked official page) are used for guidance.
function ProgrammeRequirements() {
  const [items, setItems] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = async () => {
    try {
      setItems((await fetchProgrammeRequirements()).requirements || []);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load programme requirements."));
    }
  };

  useEffect(() => {
    load();
    getGuidanceOptions().then((o) => setSubjects(o.subjects || [])).catch(() => setSubjects([]));
  }, []);

  const update = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setNotice("");
    const payload = {
      programme: form.programme, level: form.level, url: form.url.trim(), source_date: form.source_date.trim(),
      min_mean_grade: form.min_mean_grade || null, subject_requirements: parseRules(form.rules),
      notes: form.notes, keywords: form.keywords.split(",").map((k) => k.trim()).filter(Boolean),
      verified: form.verified,
    };
    try {
      if (editing) await updateProgrammeRequirement(editing, payload);
      else await createProgrammeRequirement(payload);
      setNotice(`"${form.programme}" saved${form.verified ? " as verified" : " (not verified: not used for guidance yet)"}.`);
      setForm(EMPTY);
      setEditing(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not save the requirement."));
    }
  };

  const edit = (item) => {
    setEditing(item.id);
    setForm({
      programme: item.programme, level: item.level, url: item.url, source_date: item.source_date || "",
      min_mean_grade: item.min_mean_grade || "", rules: formatRules(item.subject_requirements), notes: item.notes || "",
      keywords: (item.keywords || []).join(", "), verified: item.verified,
    });
  };

  const remove = async (item) => {
    if (!window.confirm(`Delete the requirements for "${item.programme}"?`)) return;
    try {
      await deleteProgrammeRequirement(item.id);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Could not delete the requirement."));
    }
  };

  return (
    <div className="space-y-5 text-white">
      <div>
        <h2 className="text-2xl font-bold">Programme Requirements</h2>
        <p className="mt-1 text-sm text-gray-400">
          Entry requirements used for degree guidance. Copy them from the official programme page, link that page,
          and tick &quot;verified&quot; only after checking them. USIUBOT never invents requirements: without verified
          records it recommends no programmes.
        </p>
      </div>
      {error && <p className="rounded bg-red-900/60 px-3 py-2 text-red-200" role="alert">{error}</p>}
      {notice && <p className="rounded bg-green-900/60 px-3 py-2 text-green-200">{notice}</p>}

      <form onSubmit={submit} className="grid gap-3 rounded-lg bg-gray-900 p-4 text-sm md:grid-cols-2">
        <label className="flex flex-col">Programme
          <input required className="mt-1 rounded bg-gray-700 p-2" value={form.programme} onChange={update("programme")} />
        </label>
        <label className="flex flex-col">Level
          <select className="mt-1 rounded bg-gray-700 p-2" value={form.level} onChange={update("level")}>
            <option value="undergraduate">Undergraduate</option>
            <option value="postgraduate">Postgraduate</option>
            <option value="diploma">Diploma</option>
          </select>
        </label>
        <label className="flex flex-col">Official page (https://www.usiu.ac.ke/...)
          <input required className="mt-1 rounded bg-gray-700 p-2" value={form.url} onChange={update("url")} />
        </label>
        <label className="flex flex-col">Date shown on the page (optional)
          <input className="mt-1 rounded bg-gray-700 p-2" value={form.source_date} onChange={update("source_date")} placeholder="YYYY-MM" />
        </label>
        <label className="flex flex-col">Minimum mean grade
          <select className="mt-1 rounded bg-gray-700 p-2" value={form.min_mean_grade} onChange={update("min_mean_grade")}>
            <option value="">None listed</option>
            {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </label>
        <label className="flex flex-col">Subject requirements
          <input className="mt-1 rounded bg-gray-700 p-2" value={form.rules} onChange={update("rules")}
            placeholder="Mathematics:C+; Physics|Chemistry:C" />
          <span className="mt-1 text-xs text-gray-400">
            Separate rules with ;  alternatives with |. Subjects: {subjects.slice(0, 8).join(", ")}…
          </span>
        </label>
        <label className="flex flex-col">Keywords for interests (comma-separated)
          <input className="mt-1 rounded bg-gray-700 p-2" value={form.keywords} onChange={update("keywords")} />
        </label>
        <label className="flex flex-col">Notes shown to users (optional)
          <input className="mt-1 rounded bg-gray-700 p-2" value={form.notes} onChange={update("notes")} />
        </label>
        <label className="flex items-center gap-2 md:col-span-2">
          <input type="checkbox" checked={form.verified} onChange={update("verified")} />
          I checked these requirements against the official page (verified)
        </label>
        <div className="flex gap-2 md:col-span-2">
          <button type="submit" className="rounded bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500">
            {editing ? "Save changes" : "Add programme"}
          </button>
          {editing && (
            <button type="button" className="rounded bg-gray-700 px-4 py-2 hover:bg-gray-600" onClick={() => { setEditing(null); setForm(EMPTY); }}>
              Cancel
            </button>
          )}
        </div>
      </form>

      {items.length === 0 ? (
        <p className="text-gray-400">No programme requirements recorded yet, so degree guidance cannot recommend programmes.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead className="text-gray-400">
            <tr><th className="p-2">Programme</th><th className="p-2">Requirements</th><th className="p-2">Status</th><th className="p-2"></th></tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-gray-700 align-top">
                <td className="p-2">
                  {isOfficialPageUrl(item.url)
                    ? <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline">{item.programme}</a>
                    : item.programme}
                  <span className="block text-xs text-gray-400">{item.level}{item.source_date && ` · dated ${item.source_date}`}</span>
                </td>
                <td className="p-2 text-xs text-gray-300">
                  {item.min_mean_grade && <div>Mean grade {item.min_mean_grade}</div>}
                  {formatRules(item.subject_requirements)}
                </td>
                <td className="p-2">
                  <span className={`rounded px-2 py-0.5 text-xs ${item.verified ? "bg-green-700" : "bg-gray-600"}`}>
                    {item.verified ? "verified" : "not verified"}
                  </span>
                </td>
                <td className="space-x-2 whitespace-nowrap p-2">
                  <button type="button" onClick={() => edit(item)} className="rounded bg-gray-700 px-2 py-1 text-xs hover:bg-gray-600">Edit</button>
                  <button type="button" onClick={() => remove(item)} className="rounded bg-red-800 px-2 py-1 text-xs hover:bg-red-700">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default ProgrammeRequirements;
