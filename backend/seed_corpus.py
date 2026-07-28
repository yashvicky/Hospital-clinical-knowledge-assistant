"""
Seed corpus for the demo knowledge base.

Each entry is one retrievable chunk (doc_id + page_number + text). bootstrap.py
embeds and upserts these on startup. Multi-section SOPs are split into a few
chunks so citations point at the right page/section and retrieval is precise.

Add your own entries here for a quick demo, or use the LlamaIndex ingestion
pipeline (ingest/) to load real PDFs/DOCX at scale.
"""

DOCUMENTS = [
    {
        "doc_id": "SOP-SEPSIS-2026", "title": "Emergency Department Sepsis Management",
        "department": "ER", "page_number": 3,
        "paragraph_text": (
            "Sepsis 1-Hour Bundle: upon recognition of sepsis or septic shock, measure "
            "lactate, obtain blood cultures before antibiotics, administer broad-spectrum "
            "antibiotics, begin 30 mL/kg crystalloid for hypotension or lactate >= 4 mmol/L, "
            "and apply vasopressors to maintain MAP >= 65 mmHg."
        ),
    },
    {
        "doc_id": "SOP-WARFARIN-2026", "title": "Anticoagulation Drug Interactions",
        "department": "Pharmacy", "page_number": 7,
        "paragraph_text": (
            "Concurrent use of NSAIDs such as ibuprofen with warfarin increases bleeding risk "
            "due to additive antiplatelet effects and gastric irritation. Prefer acetaminophen "
            "for analgesia in anticoagulated patients."
        ),
    },
    {
        "doc_id": "SOP-ANAPHYLAXIS-2026", "title": "Anaphylaxis First-Line Management",
        "department": "ER", "page_number": 2,
        "paragraph_text": (
            "Anaphylaxis: administer intramuscular epinephrine 0.3-0.5 mg (1:1000) into the "
            "anterolateral thigh immediately, repeat every 5-15 minutes as needed, position the "
            "patient supine, give high-flow oxygen, and establish IV access for fluids."
        ),
    },
    {
        "doc_id": "SOP-CODE-STROKE-2026", "title": "Code Stroke - Acute Ischemic Stroke Pathway",
        "department": "Emergency / Neurology", "page_number": 1,
        "paragraph_text": (
            "Code Stroke protocol for suspected acute ischemic stroke (time is brain tissue). "
            "Domain: Emergency Medicine / Neurology. Trigger: patient presents with sudden "
            "facial droop, arm drift, or slurred speech (F.A.S.T. criteria). Critical timeline "
            "goals: Door-to-Doctor under 10 minutes; Door-to-CT scan under 25 minutes "
            "(non-contrast CT of the head to rule out hemorrhage); establish Last Known Well "
            "(LKW), the exact time the patient was last at their neurological baseline."
        ),
    },
    {
        "doc_id": "SOP-CODE-STROKE-2026", "title": "Code Stroke - Acute Ischemic Stroke Pathway",
        "department": "Emergency / Neurology", "page_number": 2,
        "paragraph_text": (
            "Code Stroke intervention pathway. If the non-contrast CT shows no bleeding and the "
            "Last Known Well is less than 4.5 hours, the patient may be a candidate for "
            "intravenous fibrinolytic (thrombolytic) therapy such as Alteplase (tPA). The "
            "Alteplase / tPA administration window is within 4.5 hours of last known well. "
            "Contraindications: do not administer fibrinolytics if blood pressure is actively "
            "elevated, there is a history of intracranial hemorrhage, or blood glucose is "
            "less than 50 mg/dL."
        ),
    },
    {
        "doc_id": "SOP-CODE-STEMI-2026", "title": "Code STEMI - ST-Elevation Myocardial Infarction",
        "department": "Emergency / Cardiology", "page_number": 1,
        "paragraph_text": (
            "Code STEMI protocol for ST-Segment Elevation Myocardial Infarction, a severe heart "
            "attack caused by a completely blocked coronary artery. Domain: Emergency Medicine / "
            "Cardiology. Trigger: severe chest pain, shortness of breath, or diaphoresis "
            "(sweating). Critical timeline goals: Door-to-ECG within 10 minutes of arrival "
            "(obtain and interpret a 12-lead ECG); if the ECG confirms ST elevation, bypass the "
            "ED if possible and directly activate the Cardiac Catheterization Laboratory (CCL); "
            "Door-to-Balloon under 90 minutes."
        ),
    },
    {
        "doc_id": "SOP-CODE-STEMI-2026", "title": "Code STEMI - ST-Elevation Myocardial Infarction",
        "department": "Emergency / Cardiology", "page_number": 2,
        "paragraph_text": (
            "Code STEMI immediate medical interventions. Administer 160-325 mg chewed Aspirin "
            "immediately. Provide sublingual Nitroglycerin 0.3-0.4 mg every 5 minutes if systolic "
            "blood pressure remains above 100 mmHg. Contraindications: avoid Nitroglycerin if a "
            "right ventricular (RV) infarction is suspected or if the patient recently used "
            "phosphodiesterase inhibitors such as sildenafil (Viagra)."
        ),
    },
]
