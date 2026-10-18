# Sample Deliverables & Output Artifacts

This directory contains pre-generated sample deliverables produced by the ARGUS PRISM engine:

| File | Type | Description |
| :--- | :--- | :--- |
| `client_audit_certificate.html` | Client Deliverable | Standalone, print-ready HTML verification certificate with timestamp, credibility badges, and primary citations. |
| `client_briefing.wav` | Spoken Audio | 60-second broadcast-quality spoken audio debrief synthesized via ElevenLabs. |
| `argus_enterprise_dossier.html` | Technical Dossier | Enterprise technical evidence dossier with mathematical formulas, Bayesian posteriors, and graph statistics. |

These files can be re-generated at any time by running:
```bash
python demo.py
# or: python -m argus.cli validate --file <your_draft.txt> --export-report examples/custom_certificate.html --audio examples/custom_briefing.wav
```
