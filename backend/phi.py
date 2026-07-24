"""
PHI redaction pre-filter.

Per the PRD constraint "the system must not ingest, process, or store PHI" and
the data-flow step "FastAPI applies regex scrubbers to strip accidental PHI
input before logging or API transit", this scrubs obvious identifiers from the
incoming query before it is embedded, sent to the LLM, or logged.

This is a pragmatic regex pass (defense-in-depth), not a certified de-identifier.
"""
import re

_PATTERNS = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("MRN", re.compile(r"\bMRN[:#]?\s*\d{4,}\b", re.IGNORECASE)),
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("DATE", re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
    # "patient John Doe" / "pt. Jane Smith" -> redact the following capitalized name(s)
    ("NAME", re.compile(r"\b(?:patient|pt\.?|name(?:d)?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})")),
]


def redact_phi(text: str) -> tuple[str, bool]:
    """Return (scrubbed_text, phi_found)."""
    scrubbed = text
    found = False
    for label, pat in _PATTERNS:
        if label == "NAME":
            def _repl(m):
                nonlocal found
                found = True
                return m.group(0)[: m.start(1) - m.start(0)] + "[REDACTED-NAME]"
            scrubbed = pat.sub(_repl, scrubbed)
        else:
            if pat.search(scrubbed):
                found = True
                scrubbed = pat.sub(f"[REDACTED-{label}]", scrubbed)
    return scrubbed, found
