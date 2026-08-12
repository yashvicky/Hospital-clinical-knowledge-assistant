"use client";

import React, { useCallback, useEffect, useState } from "react";
import { X, Upload, Trash2, FileText, Loader2, RefreshCw, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1/query";
const BASE = API_URL.replace(/\/query$/, "");

type SourceDoc = {
  doc_id: string;
  title: string;
  department: string | null;
  chunks: number;
  pages: number[];
  version?: string | null;
  approval_status?: string | null;
  access_level?: string | null;
  effective_date?: string | null;
  expiry_date?: string | null;
};

interface Props {
  open: boolean;
  onClose: () => void;
  onChanged?: () => void;
}

function approvalStyle(s?: string | null) {
  if (s === "approved") return "bg-emerald-50 text-emerald-700 ring-emerald-600/20";
  if (s === "retired") return "bg-slate-100 text-slate-500 ring-slate-400/20";
  return "bg-amber-50 text-amber-700 ring-amber-600/20"; // draft / unknown
}

export const KnowledgeBase: React.FC<Props> = ({ open, onClose, onChanged }) => {
  const [docs, setDocs] = useState<SourceDoc[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [docId, setDocId] = useState("");
  const [version, setVersion] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [approvalStatus, setApprovalStatus] = useState("approved");
  const [accessLevel, setAccessLevel] = useState("general");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const loadDocs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/sources`);
      const json = await res.json();
      setDocs(json.documents ?? []);
    } catch {
      setMessage({ kind: "err", text: "Could not load the knowledge base." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      loadDocs();
      setMessage(null);
    }
  }, [open, loadDocs]);

  if (!open) return null;

  const resetForm = () => {
    setTitle(""); setDepartment(""); setDocId(""); setVersion("");
    setEffectiveDate(""); setExpiryDate(""); setApprovalStatus("approved");
    setAccessLevel("general"); setText(""); setFile(null);
    const input = document.getElementById("kb-file") as HTMLInputElement | null;
    if (input) input.value = "";
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file && !text.trim()) {
      setMessage({ kind: "err", text: "Upload a file or paste some text first." });
      return;
    }
    setSubmitting(true);
    setMessage(null);
    try {
      const fd = new FormData();
      if (file) fd.append("file", file);
      if (text.trim()) fd.append("text", text);
      if (docId.trim()) fd.append("doc_id", docId.trim());
      if (title.trim()) fd.append("title", title.trim());
      fd.append("department", department.trim() || "General");
      fd.append("version", version.trim() || "1");
      if (effectiveDate) fd.append("effective_date", effectiveDate);
      if (expiryDate) fd.append("expiry_date", expiryDate);
      fd.append("approval_status", approvalStatus);
      fd.append("access_level", accessLevel.trim() || "general");

      const res = await fetch(`${BASE}/ingest`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Ingest failed (${res.status})`);
      }
      const json = await res.json();
      setMessage({
        kind: "ok",
        text: `Added "${json.doc_id}" (${json.approval_status}) — ${json.chunks_added} chunk(s) embedded.`,
      });
      resetForm();
      await loadDocs();
      onChanged?.();
    } catch (err) {
      setMessage({ kind: "err", text: err instanceof Error ? err.message : "Ingestion failed." });
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (id: string) => {
    try {
      const res = await fetch(`${BASE}/source?doc_id=${encodeURIComponent(id)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
      await loadDocs();
      onChanged?.();
    } catch (err) {
      setMessage({ kind: "err", text: err instanceof Error ? err.message : "Delete failed." });
    }
  };

  const inputCls = "h-9 text-sm";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="flex max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border-slate-200/70 shadow-soft-lg">
        <div className="flex items-center justify-between border-b bg-muted/50 px-5 py-3">
          <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
            <FileText className="h-4 w-4 text-primary" /> Knowledge Base
          </h2>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={loadDocs} title="Refresh"><RefreshCw className="h-4 w-4" /></Button>
            <Button variant="ghost" size="icon" onClick={onClose} title="Close"><X className="h-4 w-4" /></Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          <form onSubmit={submit} className="mb-6 rounded-xl border bg-muted/30 p-4">
            <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Plus className="h-4 w-4" /> Add a document
            </p>
            <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Input className={inputCls} placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Input className={inputCls} placeholder="Doc ID (optional)" value={docId} onChange={(e) => setDocId(e.target.value)} />
              <Input className={inputCls} placeholder="Department" value={department} onChange={(e) => setDepartment(e.target.value)} />
            </div>
            <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-slate-500">Approval</label>
                <select
                  value={approvalStatus}
                  onChange={(e) => setApprovalStatus(e.target.value)}
                  className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="approved">approved</option>
                  <option value="draft">draft</option>
                  <option value="retired">retired</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-slate-500">Access</label>
                <Input className={inputCls} value={accessLevel} onChange={(e) => setAccessLevel(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-slate-500">Effective</label>
                <Input className={inputCls} type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-slate-500">Expiry</label>
                <Input className={inputCls} type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
              </div>
            </div>
            <textarea
              className="mb-3 min-h-[100px] w-full rounded-md border border-input bg-background p-3 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="Paste document text here…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <input
                id="kb-file"
                type="file"
                accept=".pdf,.txt,.md"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="text-xs file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm file:font-medium"
              />
              <Button type="submit" disabled={submitting}>
                {submitting ? (<><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Ingesting…</>) : (<><Upload className="mr-2 h-4 w-4" /> Ingest document</>)}
              </Button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Only <b>approved</b>, non-expired documents are used to answer. Set an expiry to auto-retire content. Re-ingesting a Doc ID replaces it.
            </p>
            {message && (
              <p className={`mt-3 text-sm ${message.kind === "ok" ? "text-emerald-600" : "text-destructive"}`}>{message.text}</p>
            )}
          </form>

          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">Documents in the knowledge base</p>
            <Badge variant="secondary">{docs.length}</Badge>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground"><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…</div>
          ) : docs.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No documents yet. Add one above.</p>
          ) : (
            <ul className="divide-y rounded-xl border">
              {docs.map((d) => (
                <li key={d.doc_id} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-medium text-foreground">{d.title}</p>
                      <span className={`inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${approvalStyle(d.approval_status)}`}>
                        {d.approval_status ?? "draft"}
                      </span>
                    </div>
                    <p className="truncate text-xs text-muted-foreground">
                      <span className="font-mono text-primary">{d.doc_id}</span>
                      {d.department ? ` · ${d.department}` : ""}
                      {d.access_level ? ` · ${d.access_level}` : ""}
                      {d.version ? ` · v${d.version}` : ""} · {d.chunks} chunk{d.chunks === 1 ? "" : "s"}
                      {d.expiry_date ? ` · expires ${d.expiry_date}` : ""}
                    </p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => remove(d.doc_id)} title="Remove" className="text-destructive hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>
    </div>
  );
};
