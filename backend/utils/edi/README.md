# X12 EDI (HIPAA) support

Upload **`.edi`** or healthcare **`.dat`** files (X12 sniff: ISA/GS/ST).

**837 claims** and **835 remittance** use companion-guide **decode tables** (segment order
preserved, hierarchical sections) — not HL7-style profiling/mapping. Other guides (270/271) still
use canonical mapping review.

## Supported transactions

| Guide / family | ST01 | Notes |
| --- | --- | --- |
| 005010X279 | 270, 271 | Eligibility (`X279-*.edi` at repo root) |
| 005010X221 | 835 | Remittance — example files in [api-examples `edi_files/835`](https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files/835) |
| 005010X222/X223/X224 | 837 | Claims — example files in [api-examples `edi_files/837`](https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files/837) |

Companion references (repo copies): `docs/835_compguide.pdf`, `docs/837-health-care-claim-companion-guide.pdf`.
**Onboarding (full flow):** [`docs/onboarding-hl7-edi.md`](../../../docs/onboarding-hl7-edi.md)
(phase-1 requirements, UI routes, storage). This README is the EDI module cheat sheet.

Sample EDI files (not in this repo): use **`edi_files/837`** and **`edi_files/835`** in
[Healthcare-Data-Insight api-examples](https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files)
for claim and remittance decode testing.
Fixed-width tabular `.dat` files are **not** X12 — use the normal upload path.

## API

- `POST /edi/upload` — parse; 837 → `view_mode: 837_decode`, 835 → `835_decode` + `edi_decoded`
- `GET /edi/sessions/{id}/decoded` — 837/835 segment tables for a saved session
- `GET /edi/canonical-model` — governed target entities (non-837 review UI)

Sessions are stored in `hl7_sessions` with `format: "x12"` and reuse
`/hl7/sessions/{id}/mappings` for review.

## Modules

| File | Role |
| --- | --- |
| `parser.py` | ISA-delimited X12 parsing into segment/element paths (`NM1-9`, …) |
| `canonical_model.py` | Eligibility / envelope canonical entities |
| `decode_837.py` | 837 segment/element decode (companion guide) |
| `decode_835.py` | 835 remittance decode (005010X221 companion guide) |
| `guide_sections_835.py` | 835 loop sections (1000A/B, 2100, PLB) |
| `guides/` | Element names and code sets for 837/835 |
| `mapping_engine.py` | Deterministic X12 → canonical rules (non-837) |
