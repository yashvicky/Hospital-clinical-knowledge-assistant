import React from "react";
import { FileText, FileSearch, Loader2, AlertCircle, ShieldCheck } from "lucide-react";

import { CitationData, SourceDoc } from "@/hooks/useClinicalQuery";
import { Badge } from "@/components/ui/badge";

interface DocumentPanelProps {
  citation: CitationData | null;
  source: SourceDoc | null;
  loading: boolean;
  error: string | null;
  queryTerms: string;
}

function highlight(text: string, terms: string): React.ReactNode {
  const words = Array.from(
    new Set(terms.toLowerCase().match(/[a-z0-9]+/g)?.filter((w) => w.length > 3) ?? [])
  );
  if (words.length === 0) return text;
  const re = new RegExp(`\\b(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`, "gi");
  return text.split(re).map((part, i) =>
    words.includes(part.toLowerCase()) ? (
      <mark key={i} className="rounded bg-amber-100 px-0.5 text-amber-900">{part}</mark>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export const DocumentPanel: React.FC<DocumentPanelProps> = ({ citation, source, loading, error, queryTerms }) => {
  if (!citation) {
    return (
      <div className="flex h-full flex-col items-center justify-center border-l border-slate-200/70 bg-slate-50/50 p-10 text-center">
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-soft ring-1 ring-slate-200/70">
          <FileSearch className="h-7 w-7 text-slate-300" />
        </div>
        <p className="font-semibold text-slate-700">Source verification</p>
        <p className="mt-1.5 max-w-[15rem] text-sm text-slate-500">
          Click any citation in a response to see the exact approved source, with your terms highlighted.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col border-l border-slate-200/70 bg-slate-50/50">
      <div className="flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-5 py-4 backdrop-blur">
        <div className="min-w-0">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <FileText className="h-4 w-4 text-primary" /> Source Verification
          </h3>
          <p className="mt-0.5 truncate text-xs text-slate-500">
            <span className="font-mono text-primary">{citation.docId}</span>
            {source?.department ? <span> · {source.department}</span> : null}
          </p>
        </div>
        <Badge variant="secondary" className="shrink-0">Page {citation.page}</Badge>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {loading ? (
          <div className="flex h-full items-center justify-center text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading source…
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" /> {error}
          </div>
        ) : source ? (
          <div className="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-soft">
            <p className="mb-3 text-sm font-semibold text-slate-800">{source.title}</p>
            <p className="text-[15px] leading-7 text-slate-700">
              {highlight(source.paragraph_text, queryTerms)}
            </p>
            <div className="mt-5 flex items-start gap-2 border-t border-slate-100 pt-4 text-xs text-slate-500">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
              <span>Verified excerpt from the approved knowledge base (doc {source.doc_id}, page {source.page_number}). Matched terms highlighted.</span>
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-400">No source content.</div>
        )}
      </div>
    </div>
  );
};
