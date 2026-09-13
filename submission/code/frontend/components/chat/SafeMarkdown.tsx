import type { ElementType, ReactNode } from "react";

type InlineToken = {
  text: string;
  kind: "text" | "code" | "strong" | "em" | "strike" | "link";
  href?: string;
};

function safeHref(raw: string): string | null {
  const value = raw.trim();
  if (!value || /[\u0000-\u001f\u007f]/.test(value)) return null;
  const protocolRelative = value.startsWith("//");
  const normalizedValue = protocolRelative ? `https:${value}` : value;
  try {
    const parsed = new URL(normalizedValue, "https://openportfo.invalid");
    if (!["http:", "https:", "mailto:"].includes(parsed.protocol)) return null;
    // Relative links are kept local; absolute links are restricted to safe
    // protocols and open in a separate tab with a safe referrer policy.
    return parsed.origin === "https://openportfo.invalid" && !/^[a-z][a-z0-9+.-]*:/i.test(value)
      ? `${parsed.pathname}${parsed.search}${parsed.hash}`
      : normalizedValue;
  } catch {
    return null;
  }
}

function inlineTokens(text: string): InlineToken[] {
  const pattern = /(`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|~~[^~\n]+~~|\*[^*\n]+\*|_[^_\n]+_|\[[^\]\n]+\]\([^\)\n]+\))/g;
  const output: InlineToken[] = [];
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? cursor;
    if (index > cursor) output.push({ text: text.slice(cursor, index), kind: "text" });
    const token = match[0];
    if (token.startsWith("`") && token.endsWith("`")) {
      output.push({ text: token.slice(1, -1), kind: "code" });
    } else if (token.startsWith("**") || token.startsWith("__")) {
      output.push({ text: token.slice(2, -2), kind: "strong" });
    } else if (token.startsWith("~~")) {
      output.push({ text: token.slice(2, -2), kind: "strike" });
    } else if (token.startsWith("*") || token.startsWith("_")) {
      output.push({ text: token.slice(1, -1), kind: "em" });
    } else {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const href = link ? safeHref(link[2]) : null;
      if (link && href) output.push({ text: link[1], kind: "link", href });
      else output.push({ text: token, kind: "text" });
    }
    cursor = index + token.length;
  }
  if (cursor < text.length) output.push({ text: text.slice(cursor), kind: "text" });
  return output;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  inlineTokens(text).forEach((token, index) => {
    const key = `${keyPrefix}-${index}`;
    if (token.kind === "code") {
      nodes.push(<code key={key} className="rounded bg-gray-900 px-1.5 py-0.5 font-mono text-[0.86em] text-teal-300">{token.text}</code>);
    } else if (token.kind === "strong") {
      nodes.push(<strong key={key} className="font-semibold text-gray-100">{token.text}</strong>);
    } else if (token.kind === "em") {
      nodes.push(<em key={key}>{token.text}</em>);
    } else if (token.kind === "strike") {
      nodes.push(<del key={key} className="text-gray-500">{token.text}</del>);
    } else if (token.kind === "link" && token.href) {
      const external = /^https?:/i.test(token.href);
      nodes.push(
        <a
          key={key}
          href={token.href}
          className="text-teal-300 underline decoration-teal-500/50 underline-offset-2 hover:text-teal-200"
          {...(external ? { target: "_blank", rel: "noreferrer noopener" } : {})}
        >
          {token.text}
        </a>,
      );
    } else {
      nodes.push(<span key={key}>{token.text}</span>);
    }
  });
  return nodes;
}

function renderTextWithBreaks(text: string, keyPrefix: string): ReactNode[] {
  const lines = text.split("\n");
  return lines.flatMap((line, index) => [
    ...(index ? [<br key={`${keyPrefix}-br-${index}`} />] : []),
    ...renderInline(line, `${keyPrefix}-${index}`),
  ]);
}

function tableCells(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim().replace(/\\\|/g, "|"));
}

function isTableDivider(line: string): boolean {
  const cells = tableCells(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function isUnordered(line: string): boolean {
  return /^\s*[-*+]\s+/.test(line);
}

function isOrdered(line: string): boolean {
  return /^\s*\d+[.)]\s+/.test(line);
}

function isBlockStart(line: string): boolean {
  return Boolean(
    /^\s*#{1,6}\s+/.test(line) ||
      /^\s*```/.test(line) ||
      /^\s*>/.test(line) ||
      /^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line) ||
      isUnordered(line) ||
      isOrdered(line),
  );
}

export default function SafeMarkdown({ content }: { content: string }) {
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let code: { language: string; lines: string[] } | null = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const text = paragraph.join("\n").trim();
    if (text) {
      blocks.push(
        <p key={`p-${blocks.length}`} className="whitespace-normal leading-6">
          {renderTextWithBreaks(text, `p-${blocks.length}`)}
        </p>,
      );
    }
    paragraph = [];
  };

  const flushList = () => {
    if (!list) return;
    const Tag = list.ordered ? "ol" : "ul";
    blocks.push(
      <Tag key={`list-${blocks.length}`} className={list.ordered ? "list-decimal space-y-1 pl-5" : "list-disc space-y-1 pl-5"}>
        {list.items.map((item, index) => {
          const task = /^\[([ xX])\]\s+/.exec(item);
          const value = task ? item.slice(task[0].length) : item;
          return (
            <li key={index}>
              {task ? <span aria-label={task[1].toLowerCase() === "x" ? "completed" : "not completed"}>{task[1].toLowerCase() === "x" ? "☑ " : "☐ "}</span> : null}
              {renderInline(value, `li-${blocks.length}-${index}`)}
            </li>
          );
        })}
      </Tag>,
    );
    list = null;
  };

  const flushCode = () => {
    if (!code) return;
    blocks.push(
      <pre key={`code-${blocks.length}`} className="max-w-full overflow-x-auto rounded-lg border border-gray-700 bg-gray-950 p-3 text-xs leading-5 text-gray-300">
        <code data-language={code.language || undefined}>{code.lines.join("\n")}</code>
      </pre>,
    );
    code = null;
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index] || "";
    if (code) {
      if (/^\s*```/.test(line)) flushCode();
      else code.lines.push(line);
      continue;
    }
    const fence = /^\s*```\s*([\w+-]*)\s*$/.exec(line);
    if (fence) {
      flushParagraph();
      flushList();
      code = { language: fence[1] || "", lines: [] };
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = /^\s*(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      const headingTags = ["h1", "h2", "h3", "h4", "h5", "h6"] as const;
      const Tag: ElementType = headingTags[level - 1] || "h6";
      blocks.push(<Tag key={`h-${blocks.length}`} className="font-semibold text-gray-100">{renderInline(heading[2], `h-${blocks.length}`)}</Tag>);
      continue;
    }
    if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) {
      flushParagraph();
      flushList();
      blocks.push(<hr key={`hr-${blocks.length}`} className="border-gray-700" />);
      continue;
    }
    if (index + 1 < lines.length && line.includes("|") && isTableDivider(lines[index + 1] || "")) {
      flushParagraph();
      flushList();
      const headers = tableCells(line);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && (lines[index] || "").includes("|") && (lines[index] || "").trim()) {
        rows.push(tableCells(lines[index] || ""));
        index += 1;
      }
      index -= 1;
      blocks.push(
        <div
          key={`table-${blocks.length}`}
          className="table-scroll min-w-0"
          role="region"
          aria-label="Scrollable data table"
          tabIndex={0}
        >
          <table className="w-max min-w-full border-collapse text-left text-sm">
            <thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex} className="max-w-64 whitespace-normal break-words border-b border-gray-600 px-2 py-1.5 font-semibold text-gray-200">{renderInline(cell, `th-${blocks.length}-${cellIndex}`)}</th>)}</tr></thead>
            <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex} className="max-w-64 whitespace-normal break-words border-b border-gray-800 px-2 py-1.5 align-top">{renderInline(row[cellIndex] || "", `td-${blocks.length}-${rowIndex}-${cellIndex}`)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    const quote = /^\s*>\s?(.*)$/.exec(line);
    if (quote) {
      flushParagraph();
      flushList();
      blocks.push(<blockquote key={`quote-${blocks.length}`} className="border-l-2 border-teal-500/60 pl-3 text-gray-400">{renderInline(quote[1], `quote-${blocks.length}`)}</blockquote>);
      continue;
    }
    const unordered = /^\s*[-*+]\s+(.+)$/.exec(line);
    const ordered = /^\s*\d+[.)]\s+(.+)$/.exec(line);
    if (unordered || ordered) {
      flushParagraph();
      const orderedFlag = Boolean(ordered);
      if (!list || list.ordered !== orderedFlag) {
        flushList();
        list = { ordered: orderedFlag, items: [] };
      }
      list.items.push((ordered || unordered)![1]);
      continue;
    }
    if (list && !isBlockStart(line)) {
      // Continuation lines are part of the latest list item.
      list.items[list.items.length - 1] = `${list.items[list.items.length - 1]}\n${line.trim()}`;
      continue;
    }
    paragraph.push(line);
  }
  flushCode();
  flushParagraph();
  flushList();

  return <div className="min-w-0 max-w-full space-y-3 break-words">{blocks.length ? blocks : <span className="text-gray-500">No response.</span>}</div>;
}

export { safeHref, inlineTokens };
