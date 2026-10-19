import React from "react";
import { parseBlocks, parseInline } from "../lib/markdown";

// Renders assistant answers safely. Never use dangerouslySetInnerHTML for
// chatbot or user-supplied text: answers can contain text from documents or
// from users, and HTML in them must not run in the browser.
function Inline({ text }) {
  return parseInline(text).map((token, i) => {
    switch (token.type) {
      case "strong":
        return <strong key={i}>{token.text}</strong>;
      case "em":
        return <em key={i}>{token.text}</em>;
      case "code":
        return <code key={i}>{token.text}</code>;
      default:
        return <React.Fragment key={i}>{token.text}</React.Fragment>;
    }
  });
}

const HEADINGS = { 1: "h1", 2: "h2", 3: "h3" };

function SafeMarkdown({ text, className = "", as: Wrapper = "div" }) {
  const blocks = parseBlocks(text);
  return (
    <Wrapper className={className}>
      {blocks.map((block, i) => {
        if (block.type === "h") {
          const Heading = HEADINGS[block.level];
          return (
            <Heading key={i}>
              <Inline text={block.text} />
            </Heading>
          );
        }
        if (block.type === "ul" || block.type === "ol") {
          const List = block.type;
          return (
            <List key={i} className={block.type === "ul" ? "list-disc" : "list-decimal"}>
              {block.items.map((item, j) => (
                <li key={j}>
                  <Inline text={item} />
                </li>
              ))}
            </List>
          );
        }
        if (block.type === "pre") {
          return (
            <pre key={i}>
              <code>{block.lines.join("\n")}</code>
            </pre>
          );
        }
        return (
          <p key={i}>
            {block.lines.map((line, j) => (
              <React.Fragment key={j}>
                {j > 0 && <br />}
                <Inline text={line} />
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </Wrapper>
  );
}

export default SafeMarkdown;
