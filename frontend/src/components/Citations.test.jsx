import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import Citations from "./Citations";
import { formatSourceDate, isSafeSourceUrl } from "../lib/citations";

const citation = {
  number: 1,
  source_id: "abc",
  title: "TEST FIXTURE: How to Apply",
  url: "https://www.usiu.ac.ke/test-fixture/how-to-apply/",
  department: "admissions",
  content_type: "html",
  source_date: "2026-01",
  retrieved_at: "2026-10-19T08:00:00+00:00",
  stale: false,
};

const render = (props) => renderToStaticMarkup(<Citations {...props} />);

describe("Citations", () => {
  it("renders a clickable source link that opens safely in a new tab", () => {
    const html = render({ citations: [citation] });
    expect(html).toContain('href="https://www.usiu.ac.ke/test-fixture/how-to-apply/"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("TEST FIXTURE: How to Apply");
    expect(html).toContain("Admissions");
    expect(html).toContain("dated 2026-01");
    expect(html).toContain("retrieved 2026-10-19");
  });

  it.each([
    "javascript:alert(1)",
    "http://www.usiu.ac.ke/page",
    "https://evil.example.com/page",
    "https://usiu.ac.ke.evil.com/",
    "https://user:pw@www.usiu.ac.ke/",
    "data:text/html,<script>alert(1)</script>",
    "not a url",
  ])("does not render a link for unsafe URL %s", (url) => {
    const html = render({ citations: [{ ...citation, url }] });
    expect(html).not.toContain("href=");
    expect(html).toContain("TEST FIXTURE: How to Apply");
  });

  it("escapes HTML in titles", () => {
    const html = render({ citations: [{ ...citation, title: "<img src=x onerror=alert(1)>" }] });
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });

  it("shows stale and conflict warnings", () => {
    const html = render({
      citations: [{ ...citation, stale: true }],
      warnings: [
        { type: "stale", message: "Some of this information may be out of date." },
        { type: "conflict", message: "The approved sources disagree on this point." },
      ],
    });
    expect(html).toContain("may be out of date");
    expect(html).toContain("The approved sources disagree");
  });

  it("shows a staff answer as plain text without a link", () => {
    const html = render({ citations: [{ ...citation, url: null, content_type: "staff_answer", title: "Staff answer: When?" }] });
    expect(html).not.toContain("href=");
    expect(html).toContain("answer from USIU staff");
  });

  it("does not link a citation that is no longer available, even with a valid URL", () => {
    const html = render({ citations: [{ ...citation, available: false }] });
    expect(html).not.toContain("href=");
    expect(html).toContain("no longer available");
  });

  it("renders nothing without citations or warnings", () => {
    expect(render({})).toBe("");
  });
});

describe("citation helpers", () => {
  it("accepts subdomains of the approved domain only", () => {
    expect(isSafeSourceUrl("https://cx.usiu.ac.ke/x")).toBe(true);
    expect(isSafeSourceUrl("https://notusiu.ac.ke/x")).toBe(false);
  });

  it("formats dates", () => {
    expect(formatSourceDate("2025")).toBe("2025");
    expect(formatSourceDate("2026-10-19T08:00:00+00:00")).toBe("2026-10-19");
    expect(formatSourceDate(null)).toBe(null);
  });
});
