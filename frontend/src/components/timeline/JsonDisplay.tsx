"use client";

import { useTheme } from "next-themes";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter/dist/esm/prism-light";
import { vscDarkPlus, vs } from "react-syntax-highlighter/dist/esm/styles/prism";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";

SyntaxHighlighter.registerLanguage("json", json);

interface Props {
  label: string;
  json: string | null | undefined;
}

export function JsonDisplay({ label, json: rawJson }: Props) {
  const { resolvedTheme } = useTheme();

  if (!rawJson) return null;

  let formatted = rawJson;
  try {
    formatted = JSON.stringify(JSON.parse(rawJson), null, 2);
  } catch {
    // render as raw string
  }

  return (
    <details className="mb-2" open>
      <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground">
        {label}
      </summary>
      <div className="mt-1 max-h-[300px] overflow-y-auto rounded border border-border text-xs">
        <SyntaxHighlighter
          language="json"
          style={resolvedTheme === "dark" ? vscDarkPlus : vs}
          customStyle={{ margin: 0, padding: "8px", fontSize: "11px", background: "transparent" }}
          wrapLongLines
        >
          {formatted}
        </SyntaxHighlighter>
      </div>
    </details>
  );
}
