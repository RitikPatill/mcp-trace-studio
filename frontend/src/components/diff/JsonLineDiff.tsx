"use client";

import { diffLines } from "diff";

interface Props {
  before: string;
  after: string;
}

function prettyJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

export function JsonLineDiff({ before, after }: Props) {
  const changes = diffLines(prettyJson(before), prettyJson(after));

  return (
    <pre className="overflow-auto max-h-64 rounded-md border bg-muted/30 p-2 text-xs font-mono leading-5">
      {changes.map((change, i) => {
        const lines = change.value.split("\n").filter((_, idx, arr) => idx < arr.length - 1 || change.value.endsWith("\n") || idx < arr.length - 1);
        const prefix = change.added ? "+" : change.removed ? "−" : " ";
        const bg = change.added
          ? "bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200"
          : change.removed
          ? "bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200"
          : "text-muted-foreground";

        return change.value.split("\n").slice(0, -1).map((line, j) => (
          <span key={`${i}-${j}`} className={`block whitespace-pre ${bg}`}>
            {prefix} {line}
          </span>
        ));
      })}
    </pre>
  );
}
