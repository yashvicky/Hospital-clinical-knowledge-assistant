import React from "react";
import { FileText } from "lucide-react";

import { cn } from "@/lib/utils";

interface FormatterProps {
  content: string;
  onCitationClick: (docId: string, page: string) => void;
}

export const MessageFormatter: React.FC<FormatterProps> = ({ content, onCitationClick }) => {
  const citationRegex = /\[Doc:\s*([^,]+),\s*Page:\s*(\d+)\]/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<span key={`text-${lastIndex}`}>{content.substring(lastIndex, match.index)}</span>);
    }
    const docId = match[1];
    const page = match[2];
    parts.push(
      <button
        key={`cite-${match.index}`}
        type="button"
        onClick={() => onCitationClick(docId, page)}
        title="View source document"
        className={cn(
          "mx-0.5 inline-flex items-center gap-1 rounded-full border border-primary/15 bg-primary/[0.07] px-2.5 py-0.5",
          "align-baseline text-xs font-medium text-primary transition-all",
          "hover:border-primary/30 hover:bg-primary/[0.12] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
        )}
      >
        <FileText className="h-3 w-3" />
        {docId} · p.{page}
      </button>
    );
    lastIndex = citationRegex.lastIndex;
  }
  if (lastIndex < content.length) {
    parts.push(<span key={`text-${lastIndex}`}>{content.substring(lastIndex)}</span>);
  }

  return (
    <div className="max-w-none whitespace-pre-wrap text-[15px] leading-7 text-slate-700">
      {parts.length > 0 ? parts : content}
    </div>
  );
};
