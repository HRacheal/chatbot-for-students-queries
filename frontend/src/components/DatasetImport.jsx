import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getDatasetStatus, getErrorMessage, importDataset, searchDataset } from "../lib/api";
import { CATEGORY_NAMES } from "../lib/citations";
import Citations from "./Citations";

const OUTCOME_LABELS = {
  created: "new drafts",
  unchanged: "unchanged",
  updated: "metadata updated",
  content_updated: "text updated (not approved)",
  returned_to_draft: "approved sources whose text changed, returned to draft",
};

// Admin panel: import or refresh the USIUBOT dataset as DRAFT sources (never approved here),
// see what has been imported/approved per category, and test what the chatbot would retrieve.
function DatasetImport({ onImported = () => {} }) {
  const [status, setStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState(null);

  const loadStatus = async () => {
    try {
      setStatus(await getDatasetStatus());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load the dataset status."));
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const run = async (dryRun) => {
    setBusy(dryRun ? "dry" : "import");
    setError("");
    try {
      const data = await importDataset(dryRun);
      setReport(data.report);
      if (!dryRun) {
        await loadStatus();
        onImported();
      }
    } catch (err) {
      setError(getErrorMessage(err, "The dataset could not be imported."));
    } finally {
      setBusy("");
    }
  };

  const test = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy("search");
    setError("");
    try {
      setSearch(await searchDataset(query.trim(), category));
    } catch (err) {
      setError(getErrorMessage(err, "The search failed."));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="space-y-3 rounded-lg bg-gray-900 p-4 text-sm" aria-label="USIUBOT dataset">
      <div>
        <h3 className="text-lg font-medium">USIUBOT dataset</h3>
        <p className="text-gray-400">
          Imports the sections of the collected dataset (official PDFs, official web pages and labelled
          external sources) as <strong>draft</strong> sources. Nothing is approved automatically: review each
          source (or a selected batch) below and approve it before the chatbot can use it. Importing again after
          the dataset is rebuilt skips unchanged sections, returns changed approved sections to draft, and
          archives sections that were removed.
        </p>
      </div>
      {error && <p className="rounded bg-red-900/60 px-3 py-2 text-red-200">{error}</p>}

      {status && (
        <div className="grid gap-2 md:grid-cols-2">
          <div>
            <p>
              Dataset folder: {status.dataset_available ? "found" : "not found (set DATASET_DIR)"}
              {status.test_dataset && <span className="ml-2 text-yellow-300">TEST dataset</span>}
            </p>
            {status.dataset_validation && (
              <p className="text-gray-400">
                Validated {status.dataset_validation.validated_at}: {status.dataset_validation.blocking_failures} blocking
                failures, {status.dataset_validation.warnings} warning(s)
              </p>
            )}
            <p>
              Imported sections: {status.imported_sections}
              {Object.entries(status.by_status || {}).map(([s, n]) => ` · ${s} ${n}`).join("")}
            </p>
            {status.by_origin?.external > 0 && <p className="text-orange-200">External sources: {status.by_origin.external}</p>}
          </div>
          <table className="text-xs">
            <tbody>
              {Object.entries(status.by_category || {}).map(([cat, counts]) => (
                <tr key={cat}>
                  <td className="pr-2 text-gray-400">{cat} {CATEGORY_NAMES[cat] || ""}</td>
                  <td>{Object.entries(counts).map(([s, n]) => `${s} ${n}`).join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button onClick={() => run(true)} disabled={Boolean(busy)}
          className="rounded bg-gray-700 px-3 py-1 hover:bg-gray-600 disabled:opacity-50">
          {busy === "dry" ? "Checking..." : "Check for changes (dry run)"}
        </button>
        <button onClick={() => run(false)} disabled={Boolean(busy)}
          className="rounded bg-blue-700 px-3 py-1 hover:bg-blue-600 disabled:opacity-50">
          {busy === "import" ? "Importing..." : "Import / refresh as drafts"}
        </button>
      </div>

      {report && (
        <div className="rounded bg-gray-800 p-2 text-xs" aria-label="Import report">
          <p className="font-medium">{report.dry_run ? "Dry run (nothing written)" : "Import finished"}: {report.read?.sections} sections read</p>
          <ul>
            {Object.entries(report.outcomes || {}).map(([k, n]) => <li key={k}>{n} {OUTCOME_LABELS[k] || k}</li>)}
            {report.archived_missing > 0 && <li>{report.archived_missing} archived (no longer in the dataset)</li>}
            {report.refused_count > 0 && <li className="text-red-300">{report.refused_count} refused: {report.refused.map((r) => `${r.section_id} (${r.error})`).join("; ")}</li>}
            {report.read?.duplicate_chunks_skipped > 0 && <li>{report.read.duplicate_chunks_skipped} duplicate passages skipped</li>}
            <li>Approved by the import: {report.approved_by_import}</li>
          </ul>
        </div>
      )}

      <form onSubmit={test} className="flex flex-wrap items-end gap-2">
        <label className="flex flex-1 flex-col">
          Test a question against the approved sources
          <input className="mt-1 rounded bg-gray-700 p-2" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. When does the Fall semester start?" maxLength={500} />
        </label>
        <label className="flex flex-col">
          Category
          <select className="mt-1 rounded bg-gray-700 p-2" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All</option>
            {Object.entries(CATEGORY_NAMES).map(([id, name]) => <option key={id} value={id}>{id} {name}</option>)}
          </select>
        </label>
        <button type="submit" disabled={busy === "search"} className="rounded bg-gray-700 px-3 py-2 hover:bg-gray-600 disabled:opacity-50">
          Search
        </button>
      </form>
      {search && (
        search.results.length === 0
          ? <p className="text-gray-400">No approved source matches. The chatbot would record this question as unresolved.</p>
          : <Citations citations={search.results} warnings={search.warnings} />
      )}
    </div>
  );
}

DatasetImport.propTypes = { onImported: PropTypes.func };

export default DatasetImport;
