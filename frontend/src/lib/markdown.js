// Parses a small, safe subset of Markdown into plain data structures.
// The output contains only strings; rendering is done by <SafeMarkdown>, which
// turns every string into a React text node. HTML in the input is therefore
// displayed literally and can never execute.

const INLINE_RE = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g;

// Split a line into inline tokens: { type: "text" | "strong" | "em" | "code", text }.
export function parseInline(text) {
  return String(text ?? "")
    .split(INLINE_RE)
    .filter((part) => part !== "")
    .map((part) => {
      const wrapped = (marker) =>
        part.length > marker.length * 2 && part.startsWith(marker) && part.endsWith(marker);
      if (wrapped("**") || wrapped("__")) return { type: "strong", text: part.slice(2, -2) };
      if (wrapped("`")) return { type: "code", text: part.slice(1, -1) };
      if (wrapped("*") || wrapped("_")) return { type: "em", text: part.slice(1, -1) };
      return { type: "text", text: part };
    });
}

// Split text into blocks: headings, paragraphs (lines), lists and code blocks.
export function parseBlocks(text) {
  const lines = String(text ?? "").replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let list = null;
  let code = null;

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: "p", lines: paragraph });
    paragraph = [];
  };
  const flushList = () => {
    if (list) blocks.push(list);
    list = null;
  };

  for (const raw of lines) {
    if (code) {
      if (raw.trim().startsWith("```")) {
        blocks.push(code);
        code = null;
      } else {
        code.lines.push(raw);
      }
      continue;
    }

    const line = raw.trim();
    if (line.startsWith("```")) {
      flushParagraph();
      flushList();
      code = { type: "pre", lines: [] };
      continue;
    }
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    const bullet = line.match(/^[-*+]\s+(.*)$/);
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);

    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ type: "h", level: heading[1].length, text: heading[2] });
    } else if (bullet || numbered) {
      flushParagraph();
      const type = bullet ? "ul" : "ol";
      if (!list || list.type !== type) {
        flushList();
        list = { type, items: [] };
      }
      list.items.push((bullet || numbered)[1]);
    } else {
      flushList();
      paragraph.push(line);
    }
  }

  if (code) blocks.push(code);
  flushParagraph();
  flushList();
  return blocks;
}
