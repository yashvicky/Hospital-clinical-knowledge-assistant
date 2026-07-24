import { useState } from 'react';

export type CitationData = { docId: string; page: string };

export function useClinicalQuery() {
  const [query, setQuery] = useState('');
  const [responseStream, setResponseStream] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CitationData | null>(null);

  const submitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setResponseStream('');
    setActiveCitation(null);

    try {
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, k_chunks: 5 }),
      });

      if (!res.body) throw new Error('No readable stream returned from backend.');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      // Read chunks as they stream in from FastAPI/Claude
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        setResponseStream((prev) => prev + chunk);
      }
    } catch (error) {
      console.error("Streaming Error:", error);
      setResponseStream((prev) => prev + "\n[System Error: Unable to connect to Clinical Knowledge Base.]");
    } finally {
      setIsLoading(false);
    }
  };

  return {
    query,
    setQuery,
    submitQuery,
    responseStream,
    isLoading,
    activeCitation,
    setActiveCitation
  };
}
