import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import SafeMarkdown from "./SafeMarkdown";
import { parseBlocks, parseInline } from "../lib/markdown";

const render = (text) => renderToStaticMarkup(<SafeMarkdown text={text} />);

describe("SafeMarkdown XSS protection", () => {
  const attacks = [
    '<img src=x onerror="alert(1)">',
    "<script>alert('xss')</script>",
    '<a href="javascript:alert(1)">click</a>',
    "**<svg onload=alert(1)>**",
    "- <iframe src=//evil.example></iframe>",
    "# <b onmouseover=alert(1)>title</b>",
    "`<script>alert(1)</script>`",
  ];

  it.each(attacks)("renders %s as text, not HTML", (attack) => {
    const html = render(attack);
    expect(html).not.toMatch(/<(img|script|a|svg|iframe|b)[\s>]/i);
    expect(html).toContain("&lt;");
  });
});

describe("SafeMarkdown formatting", () => {
  it("renders bold, italic and inline code", () => {
    const html = render("**Fees** are *due* in `June`");
    expect(html).toContain("<strong>Fees</strong>");
    expect(html).toContain("<em>due</em>");
    expect(html).toContain("<code>June</code>");
  });

  it("renders headings and lists", () => {
    const html = render("## Requirements\n- KCSE C+\n- Two references\n\n1. Apply\n2. Pay");
    expect(html).toContain("<h2>Requirements</h2>");
    expect(html).toMatch(/<ul[^>]*><li>KCSE C\+<\/li><li>Two references<\/li><\/ul>/);
    expect(html).toMatch(/<ol[^>]*><li>Apply<\/li><li>Pay<\/li><\/ol>/);
  });

  it("handles empty and missing text", () => {
    expect(render("")).toBe("<div class=\"\"></div>");
    expect(parseBlocks(undefined)).toEqual([]);
  });

  it("does not treat lone asterisks as emphasis", () => {
    expect(parseInline("2 * 3 = 6").map((t) => t.type)).toEqual(["text"]);
  });
});
