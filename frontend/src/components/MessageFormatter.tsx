import React from "react";
import { FileText } from "lucide-react";

import { cn } from "@/lib/utils";

interface FormatterProps {
  content: string;
  onCitationClick: (docId: string, page: string) => void;
}

export const MessageFormatter: React.FC<FormatterProps> = ({
  content,
  onCitationClick,
}) => {
  // Matches the strict citation format requested in the backend System Prompt:
  // [Doc: <docId>, Page: <n>]
  const citationRegex = /\[Doc:\s*([^,]+),\s*Page:\s*(\d+)\]/g;

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(content)) !== null) {
    // 1. Preceding standard text
    if (match.index > lastIndex) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {content.substring(lastIndex, match.index)}
        </span>
      );
    }

    // 2. Interactive citation chip
    const docId = match[1];
    const page = match[2];

    parts.push(
      <button
        key={`cite-${match.index}`}
        type="button"
        onClick={() => onCitationClick(docId, page)}
        title="Click to view source document"
        className={cn(
          "mx-1 inline-flex items-center gap-1 rounded-md border border-primary/20 bg-primary/10 px-2 py-0.5",
          "align-baseline text-xs font-semibold text-primary shadow-sm transition-colors",
          "hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
        )}
      >
        <FileText className="h-3 w-3" />
        {docId} (p. {page})
      </button>
    );

    lastIndex = citationRegex.lastIndex;
  }

  // 3. Any remaining text
  if (lastIndex < content.length) {
    parts.push(
      <span key={`text-${lastIndex}`}>{content.substring(lastIndex)}</span>
    );
  }

  return (
    <div className="prose prose-slate max-w-none whitespace-pre-wrap leading-relaxed text-foreground">
      {parts.length > 0 ? parts : content}
    </div>
  );
};
