"""
Medical shorthand / term expansion.

Implements the SAD's "Medical Term Expansion (Shorthand Normalizer)" step:
clinicians type terse queries ("sepsis tx", "MI dx"), so we append expanded
forms of known abbreviations to improve both dense and sparse retrieval. The
original text is preserved; expansions are appended (never destructive).
"""
import re

# Common clinical abbreviations. Kept intentionally conservative to avoid
# wrong expansions; extend per your institution's approved list.
ABBREVIATIONS = {
    "tx": "treatment", "dx": "diagnosis", "rx": "prescription", "hx": "history",
    "sx": "symptoms", "fx": "fracture", "abx": "antibiotics", "bp": "blood pressure",
    "hr": "heart rate", "mi": "myocardial infarction", "chf": "congestive heart failure",
    "copd": "chronic obstructive pulmonary disease", "dvt": "deep vein thrombosis",
    "pe": "pulmonary embolism", "uti": "urinary tract infection", "aki": "acute kidney injury",
    "gi": "gastrointestinal", "iv": "intravenous", "im": "intramuscular", "po": "by mouth",
    "prn": "as needed", "npo": "nothing by mouth", "nsaid": "nonsteroidal anti-inflammatory drug",
    "map": "mean arterial pressure", "rsi": "rapid sequence intubation",
}

_token_re = re.compile(r"[A-Za-z]+")


def expand_shorthand(text: str) -> str:
    """Append expansions for any recognized abbreviations found in `text`."""
    seen = []
    for tok in _token_re.findall(text):
        exp = ABBREVIATIONS.get(tok.lower())
        if exp and exp not in text.lower() and exp not in seen:
            seen.append(exp)
    if not seen:
        return text
    return f"{text} ({'; '.join(seen)})"
