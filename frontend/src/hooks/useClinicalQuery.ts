import { useState } from 'react';

export type CitationData = { docId: string; page: string };

export type SourceDoc = {
  doc_id: string;
  title: string;
  department: string | null;
  page_number: number | null;
  paragraph_text: string;
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/query';
const SOURCE_URL = API_URL.replace(/\/query$/, '/source');

export function useClinicalQuery() {
  const [query, setQuery] = useState('');
  const [responseStream, setResponseStream] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CitationData | null>(null);

  // retrieval metadata (from response headers)
  const [confidence, setConfidence] = useState<string | null>(null);
  const [topSimilarity, setTopSimilarity] = useState<number | null>(null);
  const [phiRedacted, setPhiRedacted] = useState(false);

  // source verification panel
  const [source, setSource] = useState<SourceDoc | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState<string | null>(null);

  const submitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setResponseStream('');
    setActiveCitation(null);
    setSource(null);
    setSourceError(null);
    setConfidence(null);
    setTopSimilarity(null);
    setPhiRedacted(false);

    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, k_chunks: 5 }),
      });

      setConfidence(res.headers.get('X-Retrieval-Confidence'));
      const sim = res.headers.get('X-Top-Similarity');
      setTopSimilarity(sim ? parseFloat(sim) : null);
      setPhiRedacted(res.headers.get('X-PHI-Redacted') === 'true');

      if (!res.body) throw new Error('No readable stream returned from backend.');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        setResponseStream((prev) => prev + decoder.decode(value, { stream: true }));
      }
    } catch (error) {
      console.error('Streaming Error:', error);
      setResponseStream(
        (prev) => prev + '\n[System Error: Unable to connect to Clinical Knowledge Base.]'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const onCitationClick = async (docId: string, page: string) => {
    setActiveCitation({ docId, page });
    setSource(null);
    setSourceError(null);
    setSourceLoading(true);
    try {
      const url = `${SOURCE_URL}?doc_id=${encodeURIComponent(docId)}&page=${encodeURIComponent(page)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Source not found (${res.status})`);
      setSource((await res.json()) as SourceDoc);
    } catch (err) {
      setSourceError(err instanceof Error ? err.message : 'Failed to load source.');
    } finally {
      setSourceLoading(false);
    }
  };

  return {
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
  };
}
