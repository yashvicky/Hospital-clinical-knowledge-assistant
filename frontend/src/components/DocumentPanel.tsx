import React from "react";
import { FileText, FileSearch, Loader2, AlertCircle } from "lucide-react";

import { CitationData, SourceDoc } from "@/hooks/useClinicalQuery";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

interface DocumentPanelProps {
  citation: CitationData | null;
  source: SourceDoc | null;
  loading: boolean;
  error: string | null;
  queryTerms: string;
}

// Highlight words from the query (len > 3) within the source paragraph.
function highlight(text: string, terms: string): React.ReactNode {
  const words = Array.from(
    new Set(
      terms
        .toLowerCase()
        .match(/[a-z0-9]+/g)
        ?.filter((w) => w.length > 3) ?? []
    )
  );
  if (words.length === 0) return text;
  const re = new RegExp(`\\b(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`, "gi");
  const parts = text.split(re);
  return parts.map((part, i) =>
    words.includes(part.toLowerCase()) ? (
      <mark key={i} className="rounded bg-yellow-200 px-0.5 text-slate-900">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export const DocumentPanel: React.FC<DocumentPanelProps> = ({
  citation,
  source,
  loading,
  error,
  queryTerms,
}) => {
  if (!citation) {
    return (
      <div className="flex h-full flex-col items-center justify-center border-l bg-muted/40 p-8 text-muted-foreground">
        <FileSearch className="mb-4 h-16 w-16 text-muted-foreground/40" />
        <p className="text-center font-medium">No document selected</p>
        <p className="mt-2 text-center text-sm">
          Click a citation tag in the response to verify the clinical source.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-l bg-background shadow-sm">
      <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <FileText className="h-4 w-4 text-primary" />
            Source Verification
          </h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Document ID:{" "}
            <span className="font-mono text-primary">{citation.docId}</span>
            {source?.department ? (
              <span className="ml-2 text-muted-foreground">· {source.department}</span>
            ) : null}
          </p>
        </div>
        <Badge variant="secondary">Page {citation.page}</Badge>
      </div>

      <div className="flex-1 overflow-y-auto bg-muted/40 p-6">
        {loading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading source…
          </div>
        ) : error ? (
          <Card className="flex items-center gap-2 border-destructive/30 p-4 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" /> {error}
          </Card>
        ) : source ? (
          <Card className="p-5">
            <p className="mb-2 text-sm font-semibold text-foreground">{source.title}</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
              {highlight(source.paragraph_text, queryTerms)}
            </p>
            <p className="mt-4 border-t pt-3 text-xs text-muted-foreground">
              Verified excerpt retrieved from the approved clinical knowledge base
              (doc {source.doc_id}, page {source.page_number}). Matched query terms
              are highlighted.
            </p>
          </Card>
        ) : (
          <Card className="flex h-full flex-col items-center justify-center p-6 text-muted-foreground">
            <p className="font-mono text-sm">[No source content]</p>
          </Card>
        )}
      </div>
    </div>
  );
};
