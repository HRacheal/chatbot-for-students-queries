import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import Citations from "./Citations";
import UnverifiedHelp from "./UnverifiedHelp";
import EnquiryForm from "./EnquiryForm";
import { GuidanceResult } from "./GuidancePanel";
import { EnquiryStatus } from "./TrackEnquiry";
import EnquiryManagement from "./EnquiryManagement";
import OfficialLinks from "./OfficialLinks";
import SourceManagement from "./SourceManagement";
import { formatRules, parseRules } from "../lib/workflow";
import { isOfficialPageUrl, isSiteSearchUrl } from "../lib/citations";

const SEARCH = "https://www.google.com/search?q=site%3Awww.usiu.ac.ke+gym";

describe("official page and search link checks", () => {
  it("accepts only exact trusted hosts for pages", () => {
    expect(isOfficialPageUrl("https://www.usiu.ac.ke/how-to-apply/")).toBe(true);
    expect(isOfficialPageUrl("https://cx.usiu.ac.ke/ics/")).toBe(false);
    expect(isOfficialPageUrl("https://usiu.ac.ke/")).toBe(false);
    expect(isOfficialPageUrl("http://www.usiu.ac.ke/")).toBe(false);
    expect(isOfficialPageUrl("javascript:alert(1)")).toBe(false);
  });

  it("accepts only a site-restricted search link", () => {
    expect(isSiteSearchUrl(SEARCH)).toBe(true);
    expect(isSiteSearchUrl("https://www.google.com/search?q=gym")).toBe(false);
    expect(isSiteSearchUrl("https://evil.example/search?q=site%3Awww.usiu.ac.ke+gym")).toBe(false);
    expect(isSiteSearchUrl("https://www.google.com/search?q=site%3Awww.usiu.ac.ke.evil.example+x")).toBe(false);
  });
});

describe("UnverifiedHelp", () => {
  const render = (props) => renderToStaticMarkup(<UnverifiedHelp question="Is there a gym?" {...props} />);

  it("offers a follow-up for the uncovered part of a partly answered question", () => {
    const enquiry = { available: true, query_id: "q2", suggested_department: "admissions",
      suggested_department_label: "Admissions" };
    const partial = render({ partial: true, enquiry });
    expect(partial).toContain("parts of this question that the verified sources do not cover");
    expect(partial).toContain("Admissions");
    expect(partial).toContain("Ask USIU staff to follow up");
    expect(partial).not.toContain("recorded as unresolved");
    expect(render({ enquiry })).toContain("recorded as unresolved");
  });

  it("does not offer a staff follow-up when no staff member reviews questions", () => {
    const enquiry = { available: false, staff_review: false, suggested_department: "registrar",
      suggested_department_label: "Registrar" };
    const html = render({ enquiry });
    expect(html).toContain("recorded as unresolved");
    expect(html).toContain("No USIU staff member reviews USIUBOT questions yet");
    expect(html).not.toContain("Ask USIU staff to follow up");
  });

  it("labels places to look and the search link as unverified", () => {
    const html = render({
      placesToLook: [{ title: "TEST FIXTURE: Campus Life", url: "https://www.usiu.ac.ke/test-fixture/campus/",
        reason: "Official Marketing page whose title, address or keywords match: campus" }],
      siteSearchUrl: SEARCH,
      enquiry: { available: true, query_id: "q1", suggested_department: "marketing" },
    });
    expect(html).toContain("Suggested official pages (not verified by USIUBOT)");
    expect(html).toContain("keywords match: campus");
    expect(html).toContain("USIUBOT has not read this page");
    expect(html).toContain('href="https://www.usiu.ac.ke/test-fixture/campus/"');
    expect(html).toContain("Unverified search of www.usiu.ac.ke");
    expect(html).toContain("Ask USIU staff to follow up");
  });

  it("drops untrusted links", () => {
    const html = render({
      placesToLook: [{ title: "Portal", url: "https://cx.usiu.ac.ke/ics/" }],
      siteSearchUrl: "https://evil.example/?q=site:www.usiu.ac.ke",
    });
    expect(html).not.toContain("cx.usiu.ac.ke");
    expect(html).not.toContain("evil.example");
    expect(html).not.toContain("Suggested official pages");
  });

  it("shows the enquiry form with consent when opened", () => {
    const html = render({ enquiry: { available: true, suggested_department: "registrar" }, initiallyOpen: true });
    expect(html).toContain("Send enquiry");
    expect(html).toContain("I agree that USIU-Africa staff may use the contact details");
    expect(html).toContain('value="registrar" selected=""');
  });
});

describe("EnquiryForm", () => {
  it("asks only for the minimum contact details", () => {
    const html = renderToStaticMarkup(<EnquiryForm question="How do I get a transcript?" />);
    expect(html).toContain("Name");
    expect(html).toContain("Email");
    expect(html).toContain("Phone (optional)");
    expect(html).toContain('type="checkbox"');
    expect(html).not.toContain("Student ID");
  });
});

describe("Citations origin labels", () => {
  it("labels live pages and staff answers", () => {
    const html = renderToStaticMarkup(<Citations citations={[
      { number: 1, origin: "live", source_id: "live:x", title: "TEST FIXTURE page", url: "https://www.usiu.ac.ke/test-fixture/",
        department: "admissions", content_type: "html", retrieved_at: "2026-10-20T08:00:00+00:00" },
      { number: 2, origin: "staff_answer", source_id: "s2", title: "Staff answer", url: null,
        department: "registrar", content_type: "staff_answer" },
    ]} />);
    expect(html).toContain("retrieved live on 2026-10-20");
    expect(html).toContain("answer from USIU staff");
  });
});

describe("GuidanceResult", () => {
  it("shows outcomes, reasons and the disclaimer", () => {
    const html = renderToStaticMarkup(<GuidanceResult result={{
      message: "Programmes compared",
      criteria: "Synthetic criteria",
      disclaimer: "This is guidance only, not an admission decision.",
      recommendations: [{ programme: "TEST FIXTURE Programme", url: "https://www.usiu.ac.ke/test-fixture/p/",
        outcome: "meets_listed_requirements", reasons: ["Mathematics B meets the listed minimum of C+."] }],
    }} />);
    expect(html).toContain("Meets the listed requirements");
    expect(html).toContain("Mathematics B meets the listed minimum of C+.");
    expect(html).toContain("not an admission decision");
  });

  it("shows the no-verified-data state with unverified pages", () => {
    const html = renderToStaticMarkup(<GuidanceResult result={{
      message: "USIUBOT does not yet have verified programme entry requirements",
      disclaimer: "guidance only", recommendations: [],
      places_to_look: [{ title: "TEST FIXTURE Programmes", url: "https://www.usiu.ac.ke/test-fixture/programmes/" }],
    }} />);
    expect(html).toContain("does not yet have verified");
    expect(html).toContain("(not verified)");
  });
});

describe("EnquiryStatus", () => {
  it("shows status and staff reply without contact details", () => {
    const html = renderToStaticMarkup(<EnquiryStatus enquiry={{
      reference: "ENQ-TEST0001", department_label: "Registrar", question: "Transcript?",
      status_label: "Resolved", created_at: "2026-10-20T08:00:00", staff_response: "Synthetic reply",
    }} />);
    expect(html).toContain("ENQ-TEST0001");
    expect(html).toContain("Resolved");
    expect(html).toContain("Reply from USIU staff: Synthetic reply");
  });
});

describe("programme requirement rules", () => {
  it("round-trips the rule text format", () => {
    const rules = parseRules("Mathematics:C+; Physics|Chemistry:C");
    expect(rules).toEqual([
      { subjects: ["Mathematics"], min_grade: "C+" },
      { subjects: ["Physics", "Chemistry"], min_grade: "C" },
    ]);
    expect(formatRules(rules)).toBe("Mathematics:C+; Physics|Chemistry:C");
  });
});

describe("admin screens", () => {
  it("enquiries can be filtered by all five departments, lifecycle status and date", () => {
    const html = renderToStaticMarkup(<EnquiryManagement />);
    for (const label of ["Admissions", "Registrar", "Marketing", "Academic Programmes", "General University Information"]) {
      expect(html).toContain(label);
    }
    for (const label of ["New", "Pending", "In Progress", "Awaiting Response", "Resolved", "Closed"]) {
      expect(html).toContain(label);
    }
    expect(html).toContain("Search");
    expect(html.match(/type="date"/g)).toHaveLength(2);
  });

  it("official links can be previewed, added, reviewed and hidden", () => {
    const html = renderToStaticMarkup(<OfficialLinks />);
    expect(html).toContain("Check which pages a question would get");
    expect(html).toContain("only https pages on the official website");
    expect(html).toContain("never as evidence");
  });

  it("sources can be filtered as rejected and the index rebuilt", () => {
    const html = renderToStaticMarkup(<SourceManagement />);
    expect(html).toContain('value="rejected"');
    expect(html).toContain("Rebuild search index");
  });
});
