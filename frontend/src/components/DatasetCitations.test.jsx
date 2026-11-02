import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import Citations from "./Citations";
import UnverifiedHelp from "./UnverifiedHelp";
import { citationLink, citationLocation, DEPARTMENT_LABELS } from "../lib/citations";
import { ENQUIRY_DEPARTMENTS } from "../lib/workflow";

// Synthetic citations for tests only; not real USIU-Africa information.
const pdf = {
  number: 1, source_id: "a", title: "TEST FIXTURE Student Handbook — 9.1 Parking", url: null,
  department: "general_university", content_type: "pdf", document_file: "TEST-FIXTURE-Handbook.pdf",
  page_start: 54, page_end: 55, section_heading: "Zorblat Parking Permits", collected_at: "2026-11-01",
  external: false, stale: false,
};
const web = {
  number: 2, source_id: "b", title: "TEST FIXTURE Fees page — Quibble Tuition",
  url: "https://www.usiu.ac.ke/test-fixture/quibble-fees/", department: "finance", content_type: "html",
  section_heading: "Quibble Tuition", collected_at: "2026-11-01", external: false, stale: false,
};
const external = {
  number: 3, source_id: "c", title: "TEST FIXTURE Cut-off points", url: "https://kuccps.net/test-fixture/cut-off/",
  department: "admissions", content_type: "html", external: true, publisher: "TEST FIXTURE Placement Service",
  stale: false,
};

const render = (el) => renderToStaticMarkup(el);

describe("dataset citations", () => {
  it("shows the PDF file, page range and section, without a link", () => {
    const html = render(<Citations citations={[pdf]} />);
    expect(html).toContain("TEST-FIXTURE-Handbook.pdf, pages 54-55, section &quot;Zorblat Parking Permits&quot;");
    expect(html).toContain("no public link");
    expect(html).toContain("collected 2026-11-01");
    expect(html).not.toContain("href=");
  });

  it("links official web pages and shows the department", () => {
    const html = render(<Citations citations={[web]} />);
    expect(html).toContain('href="https://www.usiu.ac.ke/test-fixture/quibble-fees/"');
    expect(html).toContain("Finance");
    expect(html).not.toContain("section &quot;Quibble Tuition&quot;"); // already in the title
  });

  it("labels external sources and links them only on listed external domains", () => {
    const html = render(<Citations citations={[external]} />);
    expect(html).toContain("External: TEST FIXTURE Placement Service");
    expect(html).toContain("not USIU-Africa policy");
    expect(html).toContain('href="https://kuccps.net/test-fixture/cut-off/"');
    expect(citationLink({ ...external, url: "https://evil.example/cut-off" })).toBeNull();
    // An official-looking URL is not trusted as "external", nor an external one as official.
    expect(citationLink({ ...web, url: "https://kuccps.net/x" })).toBeNull();
  });

  it("shows approved passages in a sources-only reply as text", () => {
    const html = render(<Citations citations={[{ ...web, excerpts: ["<b>TEST FIXTURE passage</b>"] }]} />);
    expect(html).toContain("&lt;b&gt;TEST FIXTURE passage&lt;/b&gt;");
  });

  it("highlights payment and external warnings", () => {
    const html = render(<Citations citations={[web]} warnings={[
      { type: "payment", message: "Confirm the account details with the USIU-Africa Finance Office first." },
    ]} />);
    expect(html).toContain("Finance Office");
    expect(html).toContain("border-orange-500");
  });

  it("formats a single page", () => {
    expect(citationLocation({ document_file: "x.pdf", page_start: 4, page_end: 4 })).toBe("x.pdf, page 4");
    expect(citationLocation({})).toBeNull();
  });
});

describe("routing", () => {
  it("lists Finance separately and all nine departments", () => {
    const keys = ["admissions", "registrar", "finance", "academic_programmes", "marketing", "student_affairs",
      "ict", "library", "general_university"];
    expect(Object.keys(ENQUIRY_DEPARTMENTS)).toEqual(keys);
    expect(Object.keys(DEPARTMENT_LABELS)).toEqual(keys);
  });

  it("names the office an unresolved question was routed to and only published contacts", () => {
    const html = render(<UnverifiedHelp question="TEST question" enquiry={{
      available: true, query_id: "q1", suggested_department: "finance", suggested_department_label: "Finance",
      contacts: [{ type: "email", value: "finance-fixture@example.test", office: "TEST FIXTURE Finance" }],
    }} />);
    expect(html).toContain("recorded as unresolved");
    expect(html).toContain("Finance");
    expect(html).toContain("TEST FIXTURE Finance: email finance-fixture@example.test");
    expect(html).not.toContain("mailto:");
  });

  it("shows no contacts when none are published", () => {
    const html = render(<UnverifiedHelp question="TEST question" enquiry={{
      available: true, suggested_department: "ict", suggested_department_label: "ICT", contacts: [],
    }} />);
    expect(html).toContain("ICT");
    expect(html).not.toContain("@");
  });
});
