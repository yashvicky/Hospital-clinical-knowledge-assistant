"use client";

import { useState } from "react";

import { ShieldCheck, Send, Stethoscope, ShieldAlert, FolderOpen } from "lucide-react";

import { useClinicalQuery } from "@/hooks/useClinicalQuery";
import { MessageFormatter } from "@/components/MessageFormatter";
import { DocumentPanel } from "@/components/DocumentPanel";
import { KnowledgeBase } from "@/components/KnowledgeBase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export default function ClinicalDashboard() {
  const {
    query,
    setQuery,
    submitQuery,
    responseStream,
    isLoading,
    confidence,
    topSimilarity,
    phiRedacted,
    activeCitation,
    source,
    sourceLoading,
    sourceError,
    onCitationClick,
  } = useClinicalQuery();

  const [kbOpen, setKbOpen] = useState(false);

  const showConfidence = confidence && confidence !== "None";
  const pct = topSimilarity != null ? Math.round(topSimilarity * 100) : null;

  return (
    <main className="flex h-screen w-full overflow-hidden bg-muted/40 font-sans">
      {/* LEFT PANE: Clinical Assistant Chat */}
      <section className="relative flex h-full w-3/5 flex-col">
        <header className="z-10 flex items-center justify-between bg-primary px-4 py-4 text-primary-foreground shadow-md">
          <h1 className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <Stethoscope className="h-5 w-5" />
            Hospital Clinical Knowledge Assistant
          </h1>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setKbOpen(true)}
              className="gap-1"
            >
              <FolderOpen className="h-4 w-4" />
              Manage Documents
            </Button>
            <Badge variant="secondary" className="gap-1 font-mono tracking-wider">
              <ShieldCheck className="h-3 w-3" />
              HIPAA SECURE
            </Badge>
          </div>
        </header>

        {/* Streaming Output Area */}
        <div className="flex-1 overflow-y-auto p-8">
          {!responseStream && !isLoading ? (
            <div className="flex h-full items-center justify-center font-medium text-muted-foreground">
              Awaiting clinical query...
            </div>
          ) : (
            <Card className="max-w-4xl">
              <CardContent className="p-6">
                <div className="mb-4 border-b pb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Clinical Query
                  </span>
                  <p className="mt-1 font-medium text-foreground">{query}</p>
                  {phiRedacted && (
                    <p className="mt-2 flex items-center gap-1 text-xs font-medium text-amber-600">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      Possible PHI was detected and redacted before processing.
                    </p>
                  )}
                </div>

                <div className="mb-2 flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-primary">
                    AI Assessment
                  </span>
                  {showConfidence && (
                    <Badge variant={confidence === "High" ? "success" : "secondary"}>
                      Confidence: {confidence}
                      {pct != null ? ` (${pct}%)` : ""}
                    </Badge>
                  )}
                </div>

                <MessageFormatter content={responseStream} onCitationClick={onCitationClick} />

                {isLoading && (
                  <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-primary align-middle" />
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t bg-background p-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          <form onSubmit={submitQuery} className="mx-auto flex max-w-4xl gap-3">
            <Input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="E.g., What is the sepsis 1-hour bundle protocol?"
              disabled={isLoading}
              className="flex-1"
            />
            <Button type="submit" disabled={isLoading || !query.trim()}>
              {isLoading ? (
                "Searching..."
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Ask Assistant
                </>
              )}
            </Button>
          </form>
          <p className="mt-3 text-center text-xs text-muted-foreground">
            AI-generated content. Always verify against primary hospital
            documentation using the verification panel.
          </p>
        </div>
      </section>

      {/* RIGHT PANE: Document Verification Panel */}
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
