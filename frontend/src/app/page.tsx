"use client";

import { useState } from "react";
import { ShieldCheck, Send, Stethoscope, ShieldAlert, FolderOpen, Sparkles } from "lucide-react";

import { useClinicalQuery } from "@/hooks/useClinicalQuery";
import { MessageFormatter } from "@/components/MessageFormatter";
import { DocumentPanel } from "@/components/DocumentPanel";
import { KnowledgeBase } from "@/components/KnowledgeBase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const EXAMPLES = [
  "What is the 1-hour sepsis bundle?",
  "Can ibuprofen be taken with warfarin?",
  "What is the Alteplase window for a stroke patient?",
  "Can I give Nitroglycerin to a STEMI patient?",
];

export default function ClinicalDashboard() {
  const {
    query, setQuery, submitQuery, responseStream, isLoading,
    confidence, topSimilarity, phiRedacted,
    activeCitation, source, sourceLoading, sourceError, onCitationClick,
  } = useClinicalQuery();

  const [kbOpen, setKbOpen] = useState(false);

  const showConfidence = confidence && confidence !== "None";
  const pct = topSimilarity != null ? Math.round(topSimilarity * 100) : null;
  const high = confidence === "High";

  return (
    <main className="flex h-screen w-full overflow-hidden bg-background font-sans">
      {/* LEFT PANE */}
      <section className="relative flex h-full w-3/5 flex-col">
        {/* Header */}
        <header className="z-10 flex items-center justify-between border-b border-slate-200/70 bg-white/80 px-6 py-4 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-soft">
              <Stethoscope className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-[15px] font-semibold tracking-tight text-slate-900">
                Hospital Clinical Knowledge Assistant
              </h1>
              <p className="text-xs text-slate-500">Retrieval-augmented clinical reference</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setKbOpen(true)} className="gap-1.5">
              <FolderOpen className="h-4 w-4" /> Manage Documents
            </Button>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> HIPAA Secure
            </span>
          </div>
        </header>

        {/* Output */}
        <div className="flex-1 overflow-y-auto px-6 py-8">
          {!responseStream && !isLoading ? (
            <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-soft ring-1 ring-slate-200/70">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-xl font-semibold tracking-tight text-slate-900">Ask a clinical question</h2>
              <p className="mt-2 max-w-md text-sm text-slate-500">
                Answers are grounded in approved guidelines and SOPs, with page-level citations. Try one:
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => setQuery(ex)}
                    className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-600 shadow-sm transition-colors hover:border-primary/30 hover:bg-primary/[0.04] hover:text-slate-900"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl rounded-2xl border border-slate-200/70 bg-white p-7 shadow-soft">
              <div className="mb-5 border-b border-slate-100 pb-5">
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Clinical Query</span>
                <p className="mt-1.5 text-lg font-medium leading-snug text-slate-900">{query}</p>
                {phiRedacted && (
                  <p className="mt-2.5 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20">
                    <ShieldAlert className="h-3.5 w-3.5" /> Possible PHI detected and redacted before processing
                  </p>
                )}
              </div>

              <div className="mb-3 flex items-center gap-2.5">
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">AI Assessment</span>
                {showConfidence && (
                  <span
                    className={
                      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset " +
                      (high
                        ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20"
                        : "bg-amber-50 text-amber-700 ring-amber-600/20")
                    }
                  >
                    <span className={"h-1.5 w-1.5 rounded-full " + (high ? "bg-emerald-500" : "bg-amber-500")} />
                    {confidence} confidence{pct != null ? ` · ${pct}%` : ""}
                  </span>
                )}
              </div>

              <MessageFormatter content={responseStream} onCitationClick={onCitationClick} />
              {isLoading && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-primary align-middle" />}
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-slate-200/70 bg-white/80 px-6 py-4 backdrop-blur-md">
          <form onSubmit={submitQuery} className="mx-auto flex max-w-3xl items-center gap-3">
            <Input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., What is the sepsis 1-hour bundle protocol?"
              disabled={isLoading}
              className="h-12 flex-1 rounded-xl bg-white text-[15px] shadow-sm"
            />
            <Button type="submit" disabled={isLoading || !query.trim()} className="h-12 rounded-full px-5 shadow-soft">
              {isLoading ? "Searching…" : (<><Send className="mr-2 h-4 w-4" /> Ask</>)}
            </Button>
          </form>
          <p className="mx-auto mt-3 max-w-3xl text-center text-xs text-slate-400">
            AI-generated · always verify against primary hospital documentation using the source panel.
          </p>
        </div>
      </section>

      {/* RIGHT PANE */}
      <section className="relative z-20 h-full w-2/5">
        <DocumentPanel
          citation={activeCitation}
          source={source}
          loading={sourceLoading}
          error={sourceError}
          queryTerms={query}
        />
      </section>

      <KnowledgeBase open={kbOpen} onClose={() => setKbOpen(false)} />
    </main>
  );
}
