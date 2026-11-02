import { citationLink, citationLocation, departmentLabel, formatSourceDate } from "../lib/citations";
import PropTypes from "prop-types";

// Warnings (stale, conflicting, external or unconfirmed payment details) and the numbered source
// list under an answer. Titles and URLs come from the backend's source records and are rendered
// as text; a link is only rendered when the URL passes the domain checks in citationLink.
// PDF passages show the file name, page numbers and section heading.
function Citations({ citations = [], warnings = [] }) {
  if (!citations.length && !warnings.length) return null;

  return (
    <div className="mt-3 space-y-2 text-sm">
      {warnings.map((warning, i) => (
        <p
          key={`w-${i}`}
          className={`rounded border px-2 py-1 ${warning.type === "payment" || warning.type === "external"
            ? "border-orange-500 bg-orange-900/40 text-orange-100"
            : "border-yellow-600 bg-yellow-900/40 text-yellow-200"}`}
          role="note"
        >
          {warning.message}
        </p>
      ))}

      {citations.length > 0 && (
        <div>
          <p className="font-medium text-gray-300">Sources</p>
          <ol className="mt-1 space-y-1">
            {citations.map((c) => {
              const sourceDate = formatSourceDate(c.source_date);
              const retrieved = formatSourceDate(c.retrieved_at);
              const collected = formatSourceDate(c.collected_at);
              const link = citationLink(c);
              const location = citationLocation(c);
              const details = [
                c.external ? null : departmentLabel(c.department),
                c.content_type === "pdf" ? "PDF" : null,
                c.content_type === "staff_answer" || c.origin === "staff_answer" ? "answer from USIU staff" : null,
                sourceDate ? `dated ${sourceDate}` : null,
                c.academic_year && c.academic_year !== "Not stated" ? `academic year ${c.academic_year}` : null,
                c.origin === "live" && retrieved ? `retrieved live on ${retrieved}` : null,
                c.origin !== "live" && collected ? `collected ${collected}` : null,
                c.origin !== "live" && !collected && retrieved ? `retrieved ${retrieved}` : null,
                c.content_type === "pdf" && !link ? "no public link" : null,
                c.stale ? "may be out of date" : null,
                c.available === false ? "no longer available" : null,
              ].filter(Boolean).join(" · ");
              return (
                <li key={`${c.number}-${c.source_id}`} className="text-gray-300">
                  <span className="mr-1">[{c.number}]</span>
                  {c.external && (
                    <span className="mr-1 rounded bg-orange-800 px-1.5 py-0.5 text-xs text-orange-100">
                      External: {c.publisher || "not USIU-Africa"}
                    </span>
                  )}
                  {link ? (
                    <a
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-300 underline hover:text-blue-200"
                    >
                      {c.title}
                    </a>
                  ) : (
                    <span>{c.title}</span>
                  )}
                  {location && <span className="block text-xs text-gray-300">{location}</span>}
                  <span className="block text-xs text-gray-400">{details}</span>
                  {c.external && (
                    <span className="block text-xs text-orange-200">
                      Information from an organisation outside USIU-Africa; not USIU-Africa policy.
                    </span>
                  )}
                  {Array.isArray(c.excerpts) && c.excerpts.length > 0 && (
                    <blockquote className="mt-1 whitespace-pre-wrap border-l-2 border-gray-600 pl-2 text-xs text-gray-300">
                      {c.excerpts.join("\n…\n")}
                    </blockquote>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </div>
  );
}

const citationShape = PropTypes.shape({
  number: PropTypes.number,
  origin: PropTypes.string,
  source_id: PropTypes.string,
  title: PropTypes.string,
  url: PropTypes.string,
  department: PropTypes.string,
  content_type: PropTypes.string,
  source_date: PropTypes.string,
  retrieved_at: PropTypes.string,
  stale: PropTypes.bool,
  available: PropTypes.bool,
  external: PropTypes.bool,
  publisher: PropTypes.string,
  document_file: PropTypes.string,
  page_start: PropTypes.number,
  page_end: PropTypes.number,
  section_heading: PropTypes.string,
  collected_at: PropTypes.string,
  academic_year: PropTypes.string,
  excerpts: PropTypes.arrayOf(PropTypes.string),
});

Citations.propTypes = {
  citations: PropTypes.arrayOf(citationShape),
  warnings: PropTypes.arrayOf(PropTypes.shape({ type: PropTypes.string, message: PropTypes.string })),
};

export default Citations;
