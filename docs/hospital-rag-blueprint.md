Here is the Product Requirements Document rewritten using the **BMAD (Breakthrough Method for Agile AI-Driven Development)** framework.  
In the BMAD methodology, the PRD is not just a human-readable document — it is a highly structured, versioned artifact designed to be ingested by a downstream AI Architect agent. It explicitly defines constraints, business goals, and epics so the AI does not make unapproved scoping decisions or "hallucinate" features during the development phase.

# **PRD: Hospital Clinical Knowledge Assistant**

**BMAD Workflow:** bmad-bmm-create-prd  
**Current Phase:** Phase 2 (Planning)  
**Downstream Handoff:** Architect Agent (bmad-architecture-design)

## **1\. Business Goal & Executive Summary**

**Mission:** Transform how healthcare professionals retrieve critical medical information by deploying an AI-driven, Retrieval-Augmented Generation (RAG) platform.  
**Business Goal:** Reduce manual search time for clinical guidelines and SOPs by 80%, accelerating emergency decision-making and eliminating protocol deviations caused by outdated information.

## **2\. Stakeholders & Approvals**

*This section defines who owns the decisions to prevent scope creep during AI implementation.*

| Stakeholder | Role | Approval Status | Open Concerns |
| :---- | :---- | :---- | :---- |
| **Chief Medical Officer** | Clinical workflows & accuracy | Pending | Ensuring drug interaction data is updated weekly. |
| **Compliance Officer** | HIPAA & Data Governance | Approved | Strict enforcement of zero PHI in query logs. |
| **Director of IT** | Infrastructure integration | Approved | System must have a clear fallback if the LLM fails. |

## **3\. Constraints & Guardrails**

*Invariants that the Architecture and Developer agents MUST adhere to. Any deviation during code generation requires user confirmation.*

* **Regulatory (HIPAA):** The system must not ingest, process, or store Patient Health Information (PHI). Chat history must be strictly anonymized or ephemeral.  
* **Architectural Pattern:** Must utilize a RAG architecture. The LLM cannot be fine-tuned on hospital data; all factual claims must be retrieved exclusively from the vector database.  
* **Performance:** End-to-end query latency must be **less than 3 seconds**.  
* **Data Provenance:** The system is forbidden from generating answers without a direct semantic match in the source documents. If no source is found, the system must explicitly state: *"Information not found in approved clinical guidelines."*

## **4\. Functional Requirements**

* **Data Ingestion:** Automated pipelines to ingest and chunk text from internal hospital SOPs, WHO/CDC guidelines, and approved drug manuals.  
* **Conversational Interface:** NLP search accepting medical shorthand (e.g., "tx for sepsis," "contraindications ibuprofen/warfarin").  
* **Verifiability Engine:** Every generated claim must include an inline citation linked to the specific source chunk.  
* **Source Highlighting:** Clicking a citation opens a side panel displaying the exact source paragraph, visually highlighted for the clinician to verify.  
* **Confidence Scoring:** The UI must display a retrieval confidence metric (e.g., "High: 95%") based on vector similarity.

## **5\. Epic Roadmap**

*Structured for the Architect agent to break down into actionable technical stories.*

### **Epic 1: Knowledge Base Ingestion Pipeline**

* **Story 1.1:** Build a document parser capable of extracting text and tables from PDFs and Word documents (SOPs, WHO guidelines).  
* **Story 1.2:** Implement an automated weekly sync with the hospital's internal policy repository.  
* **Story 1.3:** Chunk documents and generate embeddings using a medical-grade embedding model, storing them in a secure Vector DB.

### **Epic 2: RAG Engine & LLM Orchestration**

* **Story 2.1:** Develop the semantic search retrieval API to fetch the top-k most relevant chunks based on user queries.  
* **Story 2.2:** Engineer the system prompt to force the LLM to ground its answers strictly in the provided context window.  
* **Story 2.3:** Implement the confidence scoring algorithm based on retrieval density and semantic match.

### **Epic 3: Clinical User Interface**

* **Story 3.1:** Build a chat interface optimized for mobile and desktop clinical workstations.  
* **Story 3.2:** Develop the citation rendering component to support clickable inline links.  
* **Story 3.3:** Build the side-panel document viewer that highlights the source text associated with a clicked citation.

## **6\. Success Metrics & Acceptance Criteria**

* **Latency:** 95th percentile query response time is under 3 seconds.  
* **Accuracy / Hallucination Rate:** 0% hallucination rate on a standardized test suite of 500 clinical queries during QA.  
* **Adoption:** Greater than 60% Daily Active Users (DAU) among shift staff within 30 days of launch.  
* **Verifiability:** Citation click-through rate exceeds 40%.

# **System Architecture Document: Hospital Clinical Knowledge Assistant**

**BMAD Workflow:** bmad-architecture-design

**Current Phase:** Phase 3 (Architecture & Design) — *Updated for Anthropic Claude Ecosystem*

**Downstream Handoff:** Developer Agent (bmad-implementation)

## **1\. Architecture Overview**

This revised System Architecture Document updates the LLM engine to leverage the **Anthropic Claude model family** (deployed via HIPAA-compliant infrastructure like AWS Bedrock or GCP Vertex AI).

The system retains its core advanced Retrieval-Augmented Generation (RAG) pattern, engineered for strict factual grounding, low latency (\< 3 seconds), zero retention of Patient Health Information (PHI), and exact document citations using Claude's native XML tag parsing capabilities.

\+-----------------------------------------------------------------------------------+  
|                                  CLINICAL USER                                    |  
|                       (Next.js Dashboard / Workstation UI)                        |  
\+-----------------------------------------------------------------------------------+  
                                         |  
                                         v  
\+-----------------------------------------------------------------------------------+  
|                                FASTAPI BACKEND API                                |  
|  \- Request Validation & PHI Redaction Filter                                     |  
|  \- Context Orchestration (LlamaIndex)                                            |  
\+-----------------------------------------------------------------------------------+  
             |                                                  |  
             v (1. Vector Query)                                v (2. Context \+ Prompt)  
\+--------------------------+                      \+---------------------------------+  
|   POSTGRESQL \+ PGVECTOR  |                      |   ANTHROPIC CLAUDE LLM SERVICE    |  
|                          |                      |   (AWS Bedrock / GCP Vertex AI) |  
| \- Hospital SOPs          |                      | \- Primary: Claude Sonnet 5      |  
| \- WHO / CDC Guidelines   |                      | \- Fast Tier: Claude Haiku 4.5   |  
| \- Drug Manuals           |                      | \- Feature: Prompt Caching       |  
\+--------------------------+                      \+---------------------------------+

## **2\. Updated Tech Stack**

| Component | Technology | Rationale / Architectural Advantage |
| :---- | :---- | :---- |
| **Frontend UI** | Next.js (React), Tailwind CSS | Fast rendering, responsive across mobile tablets and nursing station desktop monitors. |
| **Backend API** | FastAPI (Python) | Async handling for streaming Claude responses and DB vector queries. |
| **Orchestration** | LangChain / LlamaIndex | Standardized orchestration for document ingestion, chunking, metadata injection, and citation tracking. |
| **LLM Provider** | **Anthropic Claude (via AWS Bedrock / GCP Vertex AI)** | **Primary:** Claude Sonnet 5 (high-accuracy reasoning, zero-hallucination compliance). **Speed Fallback:** Claude Haiku 4.5 (sub-second simple checklists). |
| **Embedding Model** | `bge-large-en-v1.5` or `nomic-embed-text-v1.5` | Highly ranked on MTEB, open-weight, supports dense clinical context retrieval. |
| **Model Serving** | Text Embeddings Inference (TEI) in Docker | Extremely low-latency tokenization and embedding generation (< 50ms). |
| **Vector Database** | `pgvector` (PostgreSQL) or `Qdrant` | Open-source, handles standard 768/1024 dimensions, easy to self-host inside hospital IT infrastructure. |
| **Document Parsing** | Unstructured.io | Extracts structured text, tables, and headers from clinical PDFs/SOPs for semantic chunking. |

## **3\. Claude-Specific Architecture & Optimization Strategy**

Integrating Claude brings structural advantages to medical RAG systems through specialized prompting capabilities and infrastructure features:

### **A. Structured XML Context Isolation**

Claude models process and respect XML-tagged inputs natively. The backend orchestrator formats the prompt to strictly segregate retrieved clinical knowledge from system instructions:

XML  
\<system\_instructions\>  
You are an expert clinical knowledge assistant. Answer the user's query using ONLY the verified excerpts provided in \<retrieved\_documents\>.   
If the information is not explicitly present, reply: "Information not found in approved clinical guidelines."  
Include inline citation tags like \[Doc X, Page Y\] matching the document metadata.  
\</system\_instructions\>

\<retrieved\_documents\>  
  \<document id="SOP-SEPSIS-2025" page="3"\>  
    ...retrieved chunk text...  
  \</document\>  
\</retrieved\_documents\>

\<user\_query\>  
What is the 1-hour sepsis protocol?  
\</user\_query\>

### **B. Prompt Caching for Reduced Latency & Cost**

Using **Claude Prompt Caching** (supported natively in AWS Bedrock and Anthropic API), static assets—such as system guardrails, clinical acronym dictionaries, and core hospital policy definitions—are cached at the API layer.

* **Latency Impact:** Reduces processing time for large system prompts by up to 80%, guaranteeing response delivery within the **3-second KPI**.  
* **Cost Efficiency:** Reduces input token costs by up to 90% on repeated system context.

### **C. Model Routing & Load Balancing**

* **Complex Queries (e.g., Multi-Drug Interactions, Differential Diagnoses):** Routed to **Claude Sonnet 5** for deep context understanding and precise reasoning.  
* **Standard Retrieval (e.g., Post-Op Checklists, SOP lookups):** Routed to **Claude Haiku 4.5** for maximum streaming throughput and sub-second initial token delivery.

## **4\. End-to-End Data Flow**

### **Synchronous Clinical Query Pipeline (\< 3s Latency)**

1. **Query Ingestion:** Nurse/Doctor enters a query (e.g., *"Can Ibuprofen be prescribed with Warfarin?"*).  
2. **Pre-processing:** FastAPI applies regex/NLP scrubbers to strip accidental PHI input before logging or API transit.  
3. **Semantic Vector Search:** PostgreSQL pgvector executes a cosine distance search across the indexed embeddings, retrieving the top $K$ relevant chunks ($K=5$).  
4. **Distance Check & Confidence Score:**  
   * If similarity score $\\ge 0.82$, Confidence \= **High**.  
   * If $0.65 \\le$ similarity $\< 0.82$, Confidence \= **Moderate**.  
   * If similarity $\< 0.65$, bypass LLM and immediately return *"No matching clinical guideline found."*  
5. **Prompt Assembly & Claude Execution:** LlamaIndex wraps retrieved chunks inside XML structures and sends the payload to Claude (Sonnet 5/Haiku 4.5).  
6. **Streaming & Side-Panel Highlighting:** Claude streams the answer back. The Next.js frontend renders inline citations; clicking a citation opens a side panel highlighting the corresponding chunk in the raw SOP PDF.

## **5\. Security & Governance**

* **Business Associate Agreement (BAA):** Deployment via **AWS Bedrock** or **GCP Vertex AI** guarantees zero data retention by Anthropic and enforces HIPAA compliance.  
* **Zero Model Training:** Customer queries and retrieved SOP data are explicitly excluded from model training or continuous improvement logs.  
* **Client-Side Ephemeral Sessions:** Conversation state resides in browser session storage and is purged automatically upon browser tab termination.

# **System Architecture Document Addendum: Embedding Model Selection**

**BMAD Workflow:** bmad-architecture-design

**Current Phase:** Phase 3 (Architecture & Design) — *Embedding Layer*

**Downstream Handoff:** Developer Agent (bmad-implementation)

## **1\. Primary Recommendation: Open-Source, Self-Hosted Embeddings**

To guarantee zero reliance on third-party commercial embedding APIs — eliminating external price hikes, vendor lock-in, and any dependency on sending hospital SOP text outside the trusted network boundary — the embedding layer is built entirely on open-weight models self-hosted inside hospital IT infrastructure.

| Layer | Recommended Choice | Why It Fits This Project |
| :---- | :---- | :---- |
| **Embedding Model** | `bge-large-en-v1.5` or `nomic-embed-text-v1.5` | Highly ranked on MTEB, open-weight, supports dense clinical context retrieval. |
| **Model Serving** | Text Embeddings Inference (TEI) in Docker | Extremely low-latency tokenization and embedding generation (< 50ms). |
| **Vector Database** | `pgvector` (PostgreSQL) or `Qdrant` | Open-source, handles standard 768/1024 dimensions, easy to self-host inside hospital IT infrastructure. |
| **RAG Framework** | LangChain / LlamaIndex | Standardized orchestration for document ingestion, chunking, and semantic search. |

### **The Single-Model Serving Strategy**

Unlike a commercial asymmetric-embedding setup, TEI serves one consistent open-weight model for both ingestion and query time, keeping the entire embedding pipeline on infrastructure the hospital directly controls:

* **Offline Data Ingestion:** Cron jobs processing hospital SOPs and CDC/WHO guidelines call the TEI container's `/embed` endpoint directly with raw passage text (no special prefix).  
* **Real-Time Clinical Queries:** The FastAPI backend calls the same TEI container, prefixing the query text with the BGE retrieval instruction (`"Represent this sentence for searching relevant passages: "`) so the query and passage vector spaces align correctly.

**Why this fits the PRD:** Running inference locally via TEI keeps embedding latency well under 50ms per call, safely securing the **\< 3-second response KPI**, while satisfying the Compliance Officer's requirement to keep clinical SOP text from ever leaving the hospital's trusted network boundary.

## **2\. Model Alternatives**

| Model | Parameters | License | Architectural Fit for Clinical RAG |
| :---- | :---- | :---- | :---- |
| **bge-large-en-v1.5** (by BAAI) | 335M | MIT | Primary recommendation. 1024-dimensional output, top-tier MTEB retrieval ranking, handles dense clinical terminology well. |
| **nomic-embed-text-v1.5** (by Nomic AI) | 137M | Apache 2.0 | Long-context alternative (8192 tokens) for lengthy CDC/WHO guideline documents; supports Matryoshka truncation. |
| **MedCPT** (by NCBI) | 110M | Open | Pre-trained on 255 million PubMed query-article pairs; strongest zero-shot biomedical retrieval fit if clinical-domain specialization outweighs general MTEB ranking. |
| **BGE-M3** (by BAAI) | 568M | MIT | Multilingual alternative; handles complex enterprise formatting (tables and lists inside PDFs) well. |

## **3\. Storage & Integration Guardrails**

* **Dimensionality Configuration:** `bge-large-en-v1.5` outputs 1024-dimensional vectors, matching the `clinical_sops.embedding` column. If choosing `nomic-embed-text-v1.5` instead (768-dimensional, with Matryoshka truncation support), update the schema's `vector(1024)` column accordingly.  
* **Query vs. Document Instructions:** The Developer Agent must be instructed to prefix query text with `"Represent this sentence for searching relevant passages: "` at query time, and to embed document/passage chunks without any prefix during ingestion, so both vector spaces stay aligned.  
* **Cost & Longevity Guardrail:** Maintain zero reliance on third-party commercial embedding APIs to prevent external price hikes and vendor lock-in.

Here is the complete FastAPI backend implementation for Phase 4\.

⚠️ **Superseded:** This listing used Claude Sonnet 5 \+ pgvector and predates the **Finalized Production Tech Stack** section near the end of this document. The maintained implementation now lives in `backend/main.py` and uses BGE-M3 (via TEI) \+ Qdrant \+ Llama 3 (via vLLM) instead. This code block is kept only for historical context — do not implement against it.

### **Core Backend Implementation (`main.py`) — historical, superseded**

Python  
import os  
import json  
from contextlib import asynccontextmanager  
from typing import AsyncGenerator

import asyncpg  
from fastapi import FastAPI, HTTPException  
from fastapi.responses import StreamingResponse  
from pydantic import BaseModel, Field  
import voyageai  
from anthropic import AsyncAnthropic

\# \---------------------------------------------------------  
\# 1\. App Lifespan & Global Clients  
\# \---------------------------------------------------------  
pool: asyncpg.Pool \= None  
voyage\_client \= voyageai.AsyncClient(api\_key=os.environ.get("VOYAGE\_API\_KEY"))  
anthropic\_client \= AsyncAnthropic(api\_key=os.environ.get("ANTHROPIC\_API\_KEY"))

@asynccontextmanager  
async def lifespan(app: FastAPI):  
    global pool  
    \# Initialize connection pool to PostgreSQL with pgvector support  
    pool \= await asyncpg.create\_pool(  
        dsn=os.environ.get("DATABASE\_URL"),  
        min\_size=2,  
        max\_size=10  
    )  
    yield  
    await pool.close()

app \= FastAPI(  
    title="Hospital Clinical Knowledge Assistant API",  
    description="Asymmetric RAG using Voyage-4-Lite and Claude Sonnet 5",  
    lifespan=lifespan  
)

\# \---------------------------------------------------------  
\# 2\. Pydantic Models  
\# \---------------------------------------------------------  
class ClinicalQueryRequest(BaseModel):  
    query: str \= Field(..., description="The medical query from the clinician")  
    k\_chunks: int \= Field(5, description="Number of context chunks to retrieve")

\# \---------------------------------------------------------  
\# 3\. Core RAG Endpoint  
\# \---------------------------------------------------------  
@app.post("/api/v1/query")  
async def clinical\_query(request: ClinicalQueryRequest):  
    """  
    Executes the clinical RAG pipeline:   
    1\. Embed query with Voyage Lite  
    2\. Vector search via pgvector  
    3\. Filter by similarity threshold  
    4\. Stream response via Claude Sonnet 5  
    """  
      
    \# STEP 1: Embed the user query using the fast Voyage Lite model  
    try:  
        embed\_res \= await voyage\_client.embed(  
            texts=\[request.query\],  
            model="voyage-4-lite",  
            input\_type="query" \# Crucial: aligns query vector space  
        )  
        query\_vector \= embed\_res.embeddings\[0\]  
    except Exception as e:  
        raise HTTPException(status\_code=500, detail=f"Embedding failure: {str(e)}")

    \# STEP 2: Vector Search via pgvector  
    \# Uses cosine distance (\<=\>). In pgvector, cosine similarity \= 1 \- cosine distance.  
    search\_query \= """  
        SELECT   
            document\_id,   
            page\_number,   
            chunk\_text,   
            1 \- (embedding \<=\> $1::vector) AS similarity  
        FROM clinical\_sops  
        ORDER BY embedding \<=\> $1::vector  
        LIMIT $2;  
    """  
      
    async with pool.acquire() as conn:  
        rows \= await conn.fetch(search\_query, json.dumps(query\_vector), request.k\_chunks)  
      
    \# STEP 3: Apply Confidence Thresholds (Guardrails)  
    if not rows:  
        return StreamingResponse(  
            chunk\_generator("Information not found in approved clinical guidelines."),  
            media\_type="text/event-stream"  
        )  
          
    top\_similarity \= rows\[0\]\['similarity'\]  
      
    \# Hard cutoff if the highest match is below 0.65  
    if top\_similarity \< 0.65:  
        return StreamingResponse(  
            chunk\_generator(f"No matching clinical guideline found. Highest similarity was only {top\_similarity:.2f}."),  
            media\_type="text/event-stream"  
        )

    \# STEP 4: Assemble Context & XML Prompts  
    context\_xml \= "\<retrieved\_documents\>\\n"  
    for idx, row in enumerate(rows):  
        context\_xml \+= f'  \<document id="{row\["document\_id"\]}" page="{row\["page\_number"\]}"\>\\n'  
        context\_xml \+= f'    {row\["chunk\_text"\]}\\n'  
        context\_xml \+= f'  \</document\>\\n'  
    context\_xml \+= "\</retrieved\_documents\>"

    system\_prompt \= f"""  
    You are an expert clinical knowledge assistant. Answer the user's query using ONLY the verified excerpts provided in the \<retrieved\_documents\> XML block.  
      
    Strict Rules:  
    1\. If the context does not explicitly contain the answer, reply ONLY with: "Information not found in approved clinical guidelines."  
    2\. Do not use outside medical knowledge.  
    3\. You must include inline citations using the exact document id and page number provided in the XML, formatted as: \[Doc: ID, Page: Y\].  
      
    {context\_xml}  
    """

    \# STEP 5: Stream Claude Sonnet 5 Response  
    async def generate\_claude\_stream() \-\> AsyncGenerator\[str, None\]:  
        try:  
            stream \= await anthropic\_client.messages.create(  
                model="claude-sonnet-5",  
                max\_tokens=1024,  
                thinking={"type": "adaptive"}, \# Ensures fast, tailored reasoning effort  
                effort="high", \# Sonnet 5 specific tuning parameter  
                system=system\_prompt,  
                messages=\[  
                    {"role": "user", "content": request.query}  
                \],  
                stream=True  
            )  
              
            async for event in stream:  
                if event.type \== "content\_block\_delta" and event.delta.type \== "text\_delta":  
                    yield event.delta.text  
                      
        except Exception as e:  
            yield f"\\n\[Generation Error: {str(e)}\]"

    return StreamingResponse(generate\_claude\_stream(), media\_type="text/event-stream")

async def chunk\_generator(text: str) \-\> AsyncGenerator\[str, None\]:  
    """Helper to stream static fallback text to the client."""  
    yield text

## **Key Implementation Details**

1. **Asymmetric Embedding Logic:** The code strictly sets `model="voyage-4-lite"` and `input_type="query"` for the runtime request. (The offline cron jobs ingesting the SOPs will use `model="voyage-4-large"` and `input_type="document"`).  
2. **pgvector Distance Math:** `pgvector`'s `<=>` operator computes *distance*. We calculate similarity inline via `1 - (embedding <=> $1::vector)` to explicitly evaluate our 0.65 fail-safe threshold.  
3. **Claude Sonnet 5 Parameters:** The API call explicitly drops older parameters like `temperature` in favor of the new `thinking` block, enabling Sonnet 5's adaptive reasoning logic for complex medical evaluations.  
4. **Streaming Delivery:** The `StreamingResponse` bypasses blocking wait times, achieving near-instant Time-To-First-Token (TTFT) on the frontend workstation, easily satisfying the \< 3-second KPI.  
   Here is the PostgreSQL setup script for the clinical\_sops table.

⚠️ **Superseded:** PostgreSQL \+ pgvector is no longer part of the primary stack (see **Finalized Production Tech Stack**). The vector store is now **Qdrant**; collection setup lives in `qdrant_init.py` instead of a SQL schema. This section is kept only for historical context.

This script is engineered to support the asymmetric RAG architecture, utilizing a 1024-dimensional vector space for the Voyage 4 embedding models. It provisions the pgvector extension, defines the table schema, and builds a Hierarchical Navigable Small World (HNSW) index optimized specifically for cosine distance searches.

## **1\. Extension and Table Definition — historical, superseded**

First, you must enable the pgvector extension on your database instance and create the table to hold the chunked hospital data.

SQL

5. \-- 1\. Enable the pgvector extension (must be run by a superuser or database owner)  
6. CREATE EXTENSION IF NOT EXISTS vector;  
7.   
8. \-- 2\. Create the clinical\_sops table  
9. CREATE TABLE IF NOT EXISTS clinical\_sops (  
10.     id BIGSERIAL PRIMARY KEY,  
11.     document\_id VARCHAR(255) NOT NULL,          \-- e.g., 'SOP-SEPSIS-2026'  
12.     page\_number INTEGER NOT NULL,               \-- Helps with exact citation generation  
13.     chunk\_text TEXT NOT NULL,                   \-- The actual text fed to Claude  
14.       
15.     \-- Voyage 4 models output 1024-dimensional vectors by default  
16.     embedding vector(1024) NOT NULL,  
17.       
18.     \-- Metadata for potential hybrid filtering (e.g., filtering out outdated SOPs)  
19.     created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP,  
20.     updated\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP,  
21.     department VARCHAR(100),                    \-- e.g., 'ER', 'Surgery', 'Pharmacy'  
22.     is\_active BOOLEAN DEFAULT TRUE  
23. );  
    

    ## **2\. HNSW Index Creation**

HNSW is the recommended index type for pgvector because it provides a superior speed-recall tradeoff compared to IVFFlat and can be built even if the table is currently empty.

Because your FastAPI backend calculates similarity using the cosine distance operator (\<=\>), you must strictly pair the index with the vector\_cosine\_ops operator class. If the index operator does not match the query operator, PostgreSQL will ignore the index and perform a severely slow sequential scan.

SQL

24. \-- 3\. Increase working memory temporarily for faster index generation  
25. \-- Note: Adjust this value based on your server's available RAM  
26. SET maintenance\_work\_mem \= '2GB';  
27.   
28. \-- 4\. Create the HNSW index optimized for cosine distance  
29. CREATE INDEX ON clinical\_sops   
30. USING hnsw (embedding vector\_cosine\_ops)   
31. WITH (  
32.     \-- 'm' defines the maximum number of connections per layer.   
33.     \-- 16 is the pgvector default and balances memory usage with performance.  
34.     m \= 16,   
35.       
36.     \-- 'ef\_construction' determines the size of the dynamic candidate list during index creation.  
37.     \-- 64 is the default; higher values increase build time but yield better search recall.  
38.     ef\_construction \= 64  
39. );  
    

    ## **3\. Performance & Maintenance Guardrails**

When pushing this schema to production, keep the following pgvector constraints in mind:

* **RAM Allocation:** HNSW indexes are memory-intensive. Ensure your PostgreSQL instance has enough RAM to comfortably hold the entire clinical\_sops index in memory, or your \< 3-second latency KPI will fail due to disk I/O bottlenecks.  
* **Search Tuning:** If you notice that the RAG retrieval occasionally misses relevant clinical chunks, you can increase search accuracy without rebuilding the index by increasing ef\_search at the query level. You would prepend SET LOCAL hnsw.ef\_search \= 100; to your FastAPI database transaction block.  
* **Dimensional Limits:** pgvector enforces a hard limit of 2,000 dimensions for indexing. If you ever switch to a larger embedding model (e.g., OpenAI's 3072-dimension model) in the future, you must truncate the vectors to $\\le 2000$ dimensions to maintain HNSW index support.

  # **Master Blueprint: Next.js Clinical Frontend**

**BMAD Workflow:** bmad-architecture-design

**Current Phase:** Phase 4 (Frontend Implementation)

**Upstream Handoff:** Complete (FastAPI Backend)

## **1\. Frontend Executive Summary**

The frontend for the Hospital Clinical Knowledge Assistant is built on **Next.js (App Router)** and **Tailwind CSS**. Its primary responsibilities are to securely consume the raw text stream from the FastAPI backend, parse Claude's inline text citations in real-time, and convert them into interactive React components.

* **Streaming UI:** The user must see the response type out in real-time. Because the backend accepts POST requests and streams raw text chunks (not standard SSE data: payloads), the frontend will utilize the native ReadableStream API via the fetch body.  
* **Split-Pane Verification View:** The UI is split into two halves: the chat/query interface on the left, and a Document Verification Panel on the right. When a user clicks a citation chip, the right panel activates to display the source document metadata.

  ## **2\. Frontend Tech Stack**

| Component | Technology | Rationale |
| :---- | :---- | :---- |
| **Framework** | Next.js 15 (App Router) | React Server Components for static shells; Client Components for stream state. |
| **Styling** | Tailwind CSS | Utility-first classes for building dense, highly readable clinical dashboards. |
| **Icons** | Lucide React | Clean, medical-appropriate iconography. |
| **State Management** | React Hooks (useState, useRef) | Ephemeral state only. No Redux/Zustand required, guaranteeing zero PHI retention across sessions. |

  ## **3\. Directory Structure**

For an AI coding agent (like Claude Cowork), the file structure should be scaffolded as follows:

Plaintext

src/

├── app/

│   ├── layout.tsx

│   └── page.tsx                 \# Main Split-Pane Dashboard

├── components/

│   ├── MessageFormatter.tsx     \# Regex parser for citations

│   ├── DocumentPanel.tsx        \# Right-side source viewer

│   └── ChatInput.tsx            \# Query text area

└── hooks/

    └── useClinicalQuery.ts      \# Custom hook for Fetch stream reading

## **4\. Master Frontend Code Implementation**

Feed this combined code specification to your development agent to generate the frontend in one shot.

### **File 1: The Stream Handler Hook (src/hooks/useClinicalQuery.ts)**

Because the backend expects a POST request, standard EventSource cannot be used. We implement a custom reader using the fetch API's body.getReader().

TypeScript

import { useState } from 'react';

export type CitationData \= { docId: string; page: string };

export function useClinicalQuery() {

  const \[query, setQuery\] \= useState('');

  const \[responseStream, setResponseStream\] \= useState('');

  const \[isLoading, setIsLoading\] \= useState(false);

  const \[activeCitation, setActiveCitation\] \= useState\<CitationData | null\>(null);

  const submitQuery \= async (e: React.FormEvent) \=\> {

    e.preventDefault();

    if (\!query.trim()) return;

    setIsLoading(true);

    setResponseStream('');

    setActiveCitation(null);

    try {

      const res \= await fetch(process.env.NEXT\_PUBLIC\_API\_URL || 'http://localhost:8000/api/v1/query', {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ query, k\_chunks: 5 }),

      });

      if (\!res.body) throw new Error('No readable stream returned from backend.');

      const reader \= res.body.getReader();

      const decoder \= new TextDecoder();

      // Read chunks as they stream in from FastAPI/Claude

      while (true) {

        const { done, value } \= await reader.read();

        if (done) break;

        

        const chunk \= decoder.decode(value, { stream: true });

        setResponseStream((prev) \=\> prev \+ chunk);

      }

    } catch (error) {

      console.error("Streaming Error:", error);

      setResponseStream((prev) \=\> prev \+ "\\n\[System Error: Unable to connect to Clinical Knowledge Base.\]");

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

### **File 2: Citation Parser Component (src/components/MessageFormatter.tsx)**

This component scans the streaming text for the exact marker generated by Claude (e.g., \[Doc: SOP-SEPSIS-2025, Page: 3\]) and replaces it on the fly with a clickable React button.

TypeScript

import React from 'react';

interface FormatterProps {

  content: string;

  onCitationClick: (docId: string, page: string) \=\> void;

}

export const MessageFormatter: React.FC\<FormatterProps\> \= ({ content, onCitationClick }) \=\> {

  // Matches the strict citation format requested in the backend System Prompt

  const citationRegex \= /\\\[Doc:\\s\*(\[^,\]+),\\s\*Page:\\s\*(\\d+)\\\]/g;


  const parts \= \[\];

  let lastIndex \= 0;

  let match;

  while ((match \= citationRegex.exec(content)) \!== null) {

    // 1\. Push preceding standard text

    if (match.index \> lastIndex) {

      parts.push(\<span key={\`text-${lastIndex}\`}\>{content.substring(lastIndex, match.index)}\</span\>);

    }

    

    // 2\. Push the interactive citation chip

    const docId \= match\[1\];

    const page \= match\[2\];

    

    parts.push(

      \<button 

        key={\`cite-${match.index}\`}

        onClick={() \=\> onCitationClick(docId, page)}

        className="inline-flex items-center px-2 py-0.5 mx-1 text-xs font-semibold text-blue-800 bg-blue-100 rounded hover:bg-blue-200 cursor-pointer transition-colors shadow-sm"

        title="Click to view source document"

      \>

        📑 {docId} (p. {page})

      \</button\>

    );

    

    lastIndex \= citationRegex.lastIndex;

  }

  // 3\. Push any remaining text

  if (lastIndex \< content.length) {

    parts.push(\<span key={\`text-${lastIndex}\`}\>{content.substring(lastIndex)}\</span\>);

  }

  return (

    \<div className="prose max-w-none text-slate-800 whitespace-pre-wrap leading-relaxed"\>

      {parts.length \> 0 ? parts : content}

    \</div\>

  );

};

### **File 3: The Verification Panel (src/components/DocumentPanel.tsx)**

This handles the right side of the screen. In a full production build, this would fetch the actual PDF page from an S3 bucket or internal server.

TypeScript

import React from 'react';

import { CitationData } from '../hooks/useClinicalQuery';

interface DocumentPanelProps {

  citation: CitationData | null;

}

export const DocumentPanel: React.FC\<DocumentPanelProps\> \= ({ citation }) \=\> {

  if (\!citation) {

    return (

      \<div className="flex flex-col items-center justify-center h-full text-slate-400 bg-slate-50 border-l border-slate-200 p-8"\>

        \<svg className="w-16 h-16 mb-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"\>

          \<path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"\>\</path\>

        \</svg\>

        \<p className="text-center font-medium"\>No document selected\</p\>

        \<p className="text-sm text-center mt-2"\>Click a citation tag in the response to verify the clinical source.\</p\>

      \</div\>

    );

  }

  return (

    \<div className="h-full flex flex-col bg-white border-l border-slate-200 shadow-sm"\>

      \<div className="bg-slate-100 px-4 py-3 border-b border-slate-200 flex justify-between items-center"\>

        \<div\>

          \<h3 className="font-semibold text-slate-800 text-sm"\>Source Verification\</h3\>

          \<p className="text-xs text-slate-500 mt-0.5"\>Document ID: \<span className="font-mono text-blue-600"\>{citation.docId}\</span\>\</p\>

        \</div\>

        \<span className="bg-slate-200 text-slate-700 text-xs px-2 py-1 rounded font-medium"\>Page {citation.page}\</span\>

      \</div\>

      

      {/\* 

        In production, this iframe or PDF viewer would load the authenticated 

        document URL based on the docId and jump to the specific page number.

      \*/}

      \<div className="flex-1 p-6 bg-slate-50 overflow-y-auto"\>

        \<div className="bg-white border border-slate-200 rounded p-6 shadow-sm h-full flex flex-col items-center justify-center text-slate-400"\>

          \<p className="font-mono text-sm"\>\[PDF Render Placeholder\]\</p\>

          \<p className="text-xs mt-2 text-center"\>Fetching chunk matching {citation.docId}...\</p\>

        \</div\>

      \</div\>

    \</div\>

  );

};

### **File 4: Main Dashboard Page (src/app/page.tsx)**

This ties the streaming logic and the split-pane UI together.

TypeScript

'use client';

import { useClinicalQuery } from '@/hooks/useClinicalQuery';

import { MessageFormatter } from '@/components/MessageFormatter';

import { DocumentPanel } from '@/components/DocumentPanel';

export default function ClinicalDashboard() {

  const { 

    query, 

    setQuery, 

    submitQuery, 

    responseStream, 

    isLoading, 

    activeCitation, 

    setActiveCitation 

  } \= useClinicalQuery();

  return (

    \<main className="flex h-screen w-full bg-slate-50 overflow-hidden font-sans"\>

      

      {/\* LEFT PANE: Clinical Assistant Chat \*/}

      \<section className="flex flex-col w-3/5 h-full relative"\>

        \<header className="bg-blue-900 text-white p-4 shadow-md z-10 flex items-center justify-between"\>

          \<h1 className="text-lg font-bold tracking-tight"\>Hospital Clinical Knowledge Assistant\</h1\>

          \<span className="text-xs bg-blue-800 px-2 py-1 rounded font-mono text-blue-200 tracking-wider"\>HIPAA SECURE\</span\>

        \</header\>

        {/\* Streaming Output Area \*/}

        \<div className="flex-1 overflow-y-auto p-8"\>

          {\!responseStream && \!isLoading ? (

            \<div className="flex items-center justify-center h-full text-slate-400 font-medium"\>

              Awaiting clinical query...

            \</div\>

          ) : (

            \<div className="bg-white border border-slate-200 shadow-sm rounded-lg p-6 max-w-4xl"\>

              \<div className="mb-4 pb-4 border-b border-slate-100"\>

                \<span className="text-xs text-slate-400 font-bold uppercase tracking-wider"\>Clinical Query\</span\>

                \<p className="text-slate-800 mt-1 font-medium"\>{query}\</p\>

              \</div\>

              \<span className="text-xs text-blue-600 font-bold uppercase tracking-wider mb-2 block"\>AI Assessment\</span\>

              

              {/\* This renders the streamed text and swaps citations to buttons \*/}

              \<MessageFormatter 

                content={responseStream} 

                onCitationClick={(docId, page) \=\> setActiveCitation({ docId, page })} 

              /\>

              

              {isLoading && (

                \<span className="inline-block w-2 h-4 ml-1 bg-blue-500 animate-pulse" /\>

              )}

            \</div\>

          )}

        \</div\>

        {/\* Input Area \*/}

        \<div className="p-4 bg-white border-t border-slate-200 shadow-\[0\_-4px\_6px\_-1px\_rgba(0,0,0,0.05)\]"\>

          \<form onSubmit={submitQuery} className="flex gap-4 max-w-4xl mx-auto"\>

            \<input

              type="text"

              value={query}

              onChange={(e) \=\> setQuery(e.target.value)}

              placeholder="E.g., What is the sepsis 1-hour bundle protocol?"

              className="flex-1 px-4 py-3 rounded-md border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm transition-shadow"

              disabled={isLoading}

            /\>

            \<button

              type="submit"

              disabled={isLoading || \!query.trim()}

              className="bg-blue-700 hover:bg-blue-800 text-white px-6 py-3 rounded-md font-medium disabled:opacity-50 transition-colors shadow-sm"

            \>

              {isLoading ? 'Searching...' : 'Ask Assistant'}

            \</button\>

          \</form\>

          \<p className="text-center text-xs text-slate-400 mt-3"\>

            AI-generated content. Always verify against primary hospital documentation using the verification panel.

          \</p\>

        \</div\>

      \</section\>

      {/\* RIGHT PANE: Document Verification Panel \*/}

      \<section className="w-2/5 h-full relative z-20"\>

        \<DocumentPanel citation={activeCitation} /\>

      \</section\>

    \</main\>

  );

}

System Architecture Document (SAD)Project Name: Hospital Clinical Knowledge Assistant 🏥Document Standard: BMAD Architect Specification (bmad-architecture-design)Phase: Phase 3 (Architecture & System Design)Upstream Artifact: Product Requirements Document (PRD v1.2)Target Execution Engine: Docker / Kubernetes (On-Premises / Private Cloud)1. Architecture Overview & Design PrinciplesThe Hospital Clinical Knowledge Assistant employs an on-premises, enterprise-grade Retrieval-Augmented Generation (RAG) architecture. Designed around strict HIPAA compliance, high speed, and zero reliance on external third-party embedding APIs, all document parsing, chunking, vector generation, and search indexing occur entirely within the hospital’s security perimeter.

```
                  ┌─────────────────────────────────────────┐
                  │        Clinical UI (React / Next.js)    │
                  └────────────────────┬────────────────────┘
                                       │ HTTPS / WSS
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          API Gateway & Auth Service                      │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  RAG Orchestration Engine (FastAPI / Python)             │
│                                                                          │
│  ┌───────────────────────┐   ┌──────────────────┐   ┌─────────────────┐  │
│  │ Medical Term Expansion │   │ Hybrid Search    │   │ Citation &      │  │
│  │ (Shorthand Normalizer) │   │ Controller       │   │ Score Engine    │  │
│  └───────────────────────┘   └──────────────────┘   └─────────────────┘  │
└────────────┬─────────────────────────┬───────────────────────┬───────────┘
             │                         │                       │
             ▼                         ▼                       ▼
┌─────────────────────────┐ ┌───────────────────┐ ┌────────────────────────┐
│ Hugging Face TEI        │ │ Qdrant Vector DB  │ │ Local LLM Inference    │
│ Container               │ │ (or pgvector)     │ │ Engine (vLLM / Ollama) │
│ (bge-large-en-v1.5)     │ │                   │ │ (e.g., Llama-3-70B)   │
└─────────────────────────┘ └───────────────────┘ └────────────────────────┘
```

Core Architectural PrinciplesAir-Gapped & HIPAA-Compliant: Zero network egress for embedding generation or document storage. Patient queries and guidelines remain local.Deterministic Citation Mapping: Direct linkage between UI claim tokens and Vector DB chunk UUIDs.Sub-3-Second Latency Budget: Heavy optimization via asynchronous batching, Hugging Face Text Embeddings Inference (TEI), and hybrid dense-sparse indexing.2. Technology Stack SelectionComponent LayerSelectionJustification / Trade-offsEmbedding Modelbge-large-en-v1.5 (BAAI)Top-tier MTEB benchmark performance, 1024-dimension dense output, open-weight, robust with clinical prose.Model Serving EngineHugging Face TEI (Docker)Rust-backed inference server offering tokenization, continuous batching, and sub-30ms embedding generation.Vector DatabaseQdrant (Primary) / pgvector (Alternative)Qdrant provides native hybrid search (dense + BM25 sparse vectors), payload filtering, and high throughput. pgvector supported for hospitals with existing Postgres infrastructure.Orchestration FrameworkFastAPI + LlamaIndex / LangChain CoreLightweight Python framework with async capabilities to coordinate vector retrieval, prompt construction, and streaming output.LLM Inference EnginevLLM (serving open-weight clinical model like Llama 3/Meditron)High-throughput GPU inference with PagedAttention for continuous streaming without token bottlenecks.UI FrameworkReact / Next.js + Tailwind CSSFast, accessible desktop and mobile workspace rendering for clinical mobile carts (COWs).3. Data Flow & Sequence Diagrams3.1 Document Ingestion & Indexing Flow

```
[Hospital SOPs/WHO/CDC PDFs]
            │
            ▼
┌────────────────────────┐
│ PyMuPDF Parser         │ ──► Extracts text, tables, headers, and metadata
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Semantic Chunker       │ ──► Overlapping chunks (512 tokens, 64 token overlap)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ TEI Container          │ ──► Generates 1024-dim dense vector embeddings
│ (bge-large-en-v1.5)    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Qdrant Vector DB       │ ──► Stores vectors + Payload:
└────────────────────────┘     { chunk_id, doc_title, text, page_num, version }
```

3.2 Clinical Query Execution Flow

```
[User Query: "What is the sepsis protocol?"]
            │
            ▼
┌────────────────────────┐
│ Medical Expansion API  │ ──► Normalizes shorthand ("sepsis tx" -> "sepsis treatment protocol")
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ TEI Container          │ ──► Vectorizes query (1024-dim array) in < 20ms
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Qdrant Hybrid Search   │ ──► Retrieves Top-K (K=5) chunks via Dense Vector + BM25 match
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Context Builder &      │ ──► Computes confidence score based on similarity threshold;
│ Prompt Guardrail       │     formats prompt with strict anti-hallucination rules
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ vLLM Streaming Engine  │ ──► Streams answer back to UI with inline citation tokens
└────────────────────────┘
```

4. Component Details & Interface Contracts4.1 Embedding Service Deployment (TEI Docker Spec)

```yaml
version: '3.8'
services:
  tei-embedding-service:
    image: ghcr.io/huggingface/text-embeddings-inference:tgi-1.2
    container_name: clinical_tei_embedding
    environment:
      - MODEL_ID=BAAI/bge-large-en-v1.5
      - PORT=8080
      - MAX_CONCURRENT_REQUESTS=128
    volumes:
      - ./model_cache:/data
    ports:
      - "8080:8080"
    command: --model-id BAAI/bge-large-en-v1.5 --auto-truncate
    restart: always
```

4.2 Vector Payload Data Schema (Qdrant)

```json
{
  "id": "e4a2d81f-93b5-4b53-8e9d-12b234567890",
  "vector": [0.0123, -0.0456, 0.0891, "...", 0.0012],
  "payload": {
    "doc_id": "SOP-ER-2026-004",
    "title": "Emergency Department Sepsis Management",
    "category": "Hospital SOP",
    "version": "3.1",
    "section_title": "1-Hour Bundle Protocol",
    "page_number": 4,
    "paragraph_text": "Administer broad-spectrum antibiotics within 1 hour of recognition. Measure blood lactate levels immediately...",
    "access_level": "clinical_staff"
  }
}
```

5. Non-Functional Requirements (NFR) Validation5.1 Latency Budget Matrix (< 3.0 Seconds Target)PhaseTarget DurationStrategy / OptimizationQuery Pre-Processing20 msLocal regex and dictionary lookup for clinical abbreviations.Query Embedding Generation25 msHugging Face TEI running with SIMD/GPU acceleration.Vector DB Search45 msQdrant HNSW indexing with payload filtering.Context Assembly & Scoring10 msPython in-memory vector cosine distance mapping.LLM First-Token Generation300 msvLLM PagedAttention continuous batching.LLM Token Streaming1,500 msStream response over WebSockets / Server-Sent Events (SSE).Total Response Time~1.9 SecondsWell within 3.0s SLA.5.2 Confidence Score AlgorithmRetrieval confidence is calculated using a weighted combination of top vector similarity scores:

$$\text{Confidence Score} = \left( \alpha \cdot S_{\text{top1}} + (1 - \alpha) \cdot \frac{1}{K-1}\sum_{i=2}^{K} S_{\text{top}_i} \right) \times 100$$

Where $S$ is the Cosine Similarity score $[0, 1]$, $K=5$, and $\alpha = 0.7$.Threshold Rule: If $\text{Confidence Score} < 65\%$, the assistant output triggers an automatic disclaimer: "Low confidence retrieval. Please verify directly with official manuals."6. Implementation Checklist & Epic Mapping[x] Epic 1.1: Configure TEI container deployment for bge-large-en-v1.5.[x] Epic 1.2: Initialize Qdrant collection with 1024-dimension HNSW indexing.[x] Epic 2.1: Implement FastAPI query pipeline with medical term normalizer.[x] Epic 2.2: Build confidence score calculator and context assembly logic.[x] Epic 3.1: Connect front-end React citation panel to vector payload IDs.

# **Finalized Production Tech Stack (Authoritative)**

**Status:** This section is the authoritative, decision-final tech stack. It supersedes the earlier Anthropic Claude + Voyage AI + pgvector proposal and the exploratory Qdrant + vLLM System Architecture Document (SAD) draft above — both are kept in this file for historical context only.

**Design Principle:** Completely separate the heavy generative AI from the lightweight document retrieval layer, so the system stays HIPAA-compliant, sub-3-second, and cost-efficient without overpaying for server capacity.

## **1. The Inference & Embedding Layer (The Brain)**

* **Embedding Model:** `BGE-M3` (by BAAI) or `nomic-embed-text-v1.5`.
  * *Why:* `BGE-M3` is the open-source leader for hybrid search (semantic meaning + exact-keyword matches), which matters for medical acronyms and drug dosages. Both models support 8,192-token context windows, so a treatment protocol won't get chopped in half mid-chunk.
* **Embedding Server:** Hugging Face Text Embeddings Inference (TEI).
  * *Why:* Deployed via Docker, this Rust-based engine gives blazing-fast tokenization and sub-millisecond local API responses on a standard CPU.
* **Generative LLM:** `Llama 3` (8B or 70B) served via **vLLM**.
  * *Why:* vLLM is the industry standard for high-throughput, low-latency text streaming, and keeps generation entirely on infrastructure the hospital controls — no Anthropic/Bedrock/Vertex dependency.

## **2. The Data Layer (The Vault)**

* **Vector Database:** **Qdrant**.
  * *Why:* Open-source, hyper-fast, and deeply integrated with `BGE-M3` for native hybrid search. Runs seamlessly in Docker on the local network, ensuring zero clinical SOPs ever touch the public internet. (This replaces PostgreSQL + pgvector as the system of record for embeddings; pgvector is no longer part of the primary stack.)

## **3. The Orchestration & Logic Layer (The Engine)**

* **RAG Framework:** **LlamaIndex**.
  * *Why:* LlamaIndex is the undisputed king of document-first data processing, with superior built-in tools for extracting tables and structure from dense, complex PDFs like WHO guidelines. (LangChain remains a fine general-agent alternative but is not the primary choice.)
* **Backend API:** FastAPI (Python).
  * *Why:* High-performance async routing bridging the Next.js frontend, Qdrant, and the vLLM generation service.

## **4. The Presentation Layer (The Clinical Interface)**

* **Frontend Framework:** Next.js (React).
* **UI Components:** Tailwind CSS + shadcn/ui.
  * *Why:* Clean, accessible, highly responsive components that look native on hospital mobile carts (COWs) and tablets.
* **Frontend Hosting:** Vercel.
  * *Why:* Free, fast CI/CD for the UI only — the heavy ML services (Qdrant, TEI, vLLM) are never hosted on Vercel.

## **5. The Infrastructure Layer (Hardware & DevOps)**

* **Containerization:** Docker & Docker Compose — ensures parity between a developer laptop and the hospital server room.
* **Version Control:** Git, GitHub, & GitHub Actions — free, reliable automated testing of the FastAPI code before it ships.
* **Hosting Strategy:**
  * *Database & Embeddings:* a dedicated $10–$20/month Linux CPU VPS hosting Qdrant, TEI, and FastAPI.
  * *Generative Text:* a dedicated GPU server or dedicated API endpoint hosting the Llama 3 model via vLLM.

**The Big Takeaway:** Using LlamaIndex with `BGE-M3` and Qdrant locally keeps total control over the exact paragraphs the AI references, satisfying the zero-hallucination requirement from Section 3 of the PRD.

**Guardrails carried over unchanged from the PRD:** the < 3-second latency budget, the "Information not found in approved clinical guidelines" fallback for no-match queries, and the confidence-threshold gating before any LLM call — these are business requirements independent of which vector DB or LLM serves them.

<!-- End of blueprint. Implementation lives in this repository: backend/, frontend/, mocks/, scripts/, docker-compose.yml. -->
