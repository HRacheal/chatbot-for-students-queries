import { useState } from "react";
import PropTypes from "prop-types";
import { isOfficialPageUrl, isSiteSearchUrl } from "../lib/citations";
import EnquiryForm from "./EnquiryForm";

// Shown under a reply that could not be verified. Nothing here is presented as an
// answer: official pages that *may* help (not checked), an optional unverified
// site search, and a way to ask USIU staff to follow up.
// With ``partial``, the answer above is verified but does not cover every part of the question.
function UnverifiedHelp({ question, placesToLook = [], siteSearchUrl = null, enquiry = null, initiallyOpen = false,
  partial = false }) {
  const [showForm, setShowForm] = useState(initiallyOpen);
  const pages = placesToLook.filter((p) => isOfficialPageUrl(p.url));
  const search = isSiteSearchUrl(siteSearchUrl) ? siteSearchUrl : null;
  // Contacts are sent only after an administrator has published them for the department.
  const contacts = Array.isArray(enquiry?.contacts) ? enquiry.contacts.filter((c) => c && c.value) : [];

  return (
    <div className="mt-3 space-y-2 text-sm">
      {pages.length > 0 && (
        <div>
          <p className="font-medium text-gray-300">Suggested official pages (not verified by USIUBOT)</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {pages.map((p) => (
              <li key={p.url}>
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline hover:text-blue-200">
                  {p.title}
                </a>
                <span className="block text-xs text-gray-400">
                  {p.reason ? `${p.reason}. ` : ""}USIUBOT has not read this page; open it for the complete, current information.
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {enquiry?.suggested_department_label && (
        <div aria-label="Suggested office">
          <p className="text-gray-300">
            {partial ? "The parts of this question that the verified sources do not cover have been recorded for the "
              : "This question has been recorded as unresolved for the "}
            <span className="font-medium">{enquiry.suggested_department_label}</span> office.
            {enquiry.staff_review === false && (
              " No USIU staff member reviews USIUBOT questions yet, so please contact the office directly."
            )}
          </p>
          {contacts.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-xs text-gray-300">
              {contacts.map((c, i) => (
                <li key={`${c.type}-${i}`}>
                  {c.office ? `${c.office}: ` : ""}{c.type !== "other" ? `${c.type} ` : ""}{c.value}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {search && (
        <p>
          <a href={search} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline hover:text-blue-200">
            Unverified search of www.usiu.ac.ke
          </a>
          <span className="block text-xs text-gray-400">
            Opens a Google search in your browser. The results are not official USIU-Africa answers and are not
            checked by USIUBOT.
          </span>
        </p>
      )}
      {enquiry?.available && (
        showForm ? (
          <EnquiryForm question={question} queryId={enquiry.query_id || null}
            suggestedDepartment={enquiry.suggested_department || null} />
        ) : (
          <button type="button" onClick={() => setShowForm(true)}
            className="rounded border border-blue-500 px-3 py-1 text-blue-300 hover:bg-blue-800 hover:text-white">
            Ask USIU staff to follow up
          </button>
        )
      )}
    </div>
  );
}

UnverifiedHelp.propTypes = {
  question: PropTypes.string.isRequired,
  placesToLook: PropTypes.arrayOf(PropTypes.shape({ title: PropTypes.string, url: PropTypes.string, reason: PropTypes.string })),
  siteSearchUrl: PropTypes.string,
  enquiry: PropTypes.shape({
    available: PropTypes.bool,
    staff_review: PropTypes.bool,
    query_id: PropTypes.string,
    suggested_department: PropTypes.string,
    suggested_department_label: PropTypes.string,
    contacts: PropTypes.arrayOf(PropTypes.shape({ type: PropTypes.string, value: PropTypes.string, office: PropTypes.string })),
  }),
  initiallyOpen: PropTypes.bool,
  partial: PropTypes.bool,
};

export default UnverifiedHelp;
