# Onboarding: HL7 v2 and X12 EDI in el7-hiq

This guide is for an engineer joining the project who needs to work on the HL7 or EDI
paths. It explains what happens from upload to export, which files own each step, how
data is stored, and how to run and extend it. It describes the code as it is today.

Related diagrams: [`ai-flow-hl7-edi.svg`](ai-flow-hl7-edi.svg) (this path) and
[`ai-flow-sttm-extract.svg`](ai-flow-sttm-extract.svg) (the data-file / BRD path, which
is separate and not covered here).

**Module READMEs (backend, deeper detail):**

| Path | README |
| --- | --- |
| HL7 v2 | [`backend/utils/hl7/README.md`](../backend/utils/hl7/README.md) — governance rules, confidence scoring weights, spike runner, module table |
| X12 EDI | [`backend/utils/edi/README.md`](../backend/utils/edi/README.md) — supported transactions, API summary, decode modules, sample corpus links |

This onboarding doc is the end-to-end tour; use those READMEs when you are changing
parser, inference, mapping, or guide-decode code.

---

## 1. The two-minute version

- The app's normal upload path loads tabular files into dataframes. HL7 and X12 files are
  trees, not tables, so they are detected on the Upload page and sent to dedicated
  endpoints: `POST /hl7/upload` and `POST /edi/upload`.
- **HL7 v2** (`.hl7`): parse → profile the corpus → score site-defined Z-segment fields
  (semantic confidence + stability) → propose canonical mappings → human review →
  publish an immutable versioned package. FHIR is an optional projection.
- **X12 EDI** (`.edi`, X12-shaped `.dat`): parse → identify the transaction set (ST01).
  - **837 claims / 835 remittance**: decode every segment against the companion guide into
    hierarchical sections (LOOP 2300, LOOP 1000A, …) → JSON mapping page where only
    date/time fields are transformable → approve → download hierarchical JSON.
  - **270 / 271 eligibility**: rule-based mapping to a canonical model, then the same
    review workbench as HL7.
- Everything is deterministic. There are no LLM calls on either path. The confidence
  scores in HL7 come from lexicon matching and value-shape rules, not a model.
- Both formats share one storage table, `hl7_sessions`, and one URL space, `/hl7/:id`.
  EDI sessions are distinguished by `format: "x12"` and a `view_mode`.

---

## 2. Phase-1 requirements and what we built

### Problem context (HL7)

The customer receives healthcare data from hundreds of hospitals and trading partners.
Messages generally follow HL7 v2, but each site can use different field structures,
custom mappings, validation rules, and site-specific Z-segments. Much of today’s
transformation logic lives in individual Mirth channels, which makes onboarding and
maintenance slow and hard to scale.

Phase 1 extends the existing STTM (source-to-target mapping) capability to HL7 and
related interchange formats, with the same human-review and approval model as tabular
STTM—not a separate silo.

### HL7 phase-1 scope

| Requirement | Status | Where in this repo |
| --- | --- | --- |
| Parse and profile HL7 v2 messages | **Done** | `backend/utils/hl7/parser.py`, `profiler.py`; `POST /hl7/upload` |
| Support message types such as **ORU^R01** and **MDM^T02** | **Done** | Standard rules and entity coverage in `mapping_engine.py`; optional FHIR in `fhir_mapper.py` |
| Detect standard segments and **custom Z-segments** | **Done** | `parser.py` (Z detection); corpus profiling in `profiler.py` |
| Map HL7 fields to a **target canonical structure** | **Done** | `canonical_model.py`, `mapping_engine.py` → `mappings_json` |
| Structured outputs (**JSON**; CSV for downstream tools) | **JSON done**; CSV not a first-class export yet | Published package + `GET /hl7/sessions/{id}/export/mappings`; canonical JSON is the required artifact (FHIR optional). CSV / Workato-style feeds are listed as a later integration item in the BRD, not implemented as a dedicated exporter here. |
| Surface **unmapped, ambiguous, or low-confidence** fields for review | **Done** | Z-segment routing in `zsegment_inference.py`; `HUMAN_REQUIRED` / `REVIEW`; standard fields can be `unresolved`; readiness blocks publish |
| Retain **STTM human review and approval** (approve, edit, reject, audit, publish) | **Done** | `mapping_package.py`, `HL7MappingReview.tsx`, `/hl7/sessions/{id}/review` and publish/audit endpoints |

**Confidence and routing (foundation for a smarter MVP):** semantic confidence and
stability scores, explicit reasons per field, and routing thresholds are implemented
deterministically in `zsegment_inference.py` (no LLM). That matches the “mapping
recommendations + confidence scores + human-in-the-loop” direction for a later phase.

**Explicitly out of scope for the current build (future MVP):** LLM-based mapping
recommendations, automated transformation test generation, Workato (or similar)
connectors, and fully automated format detection beyond `.hl7` upload routing.

### EDI phase-1 scope

| Requirement | Status | Where in this repo |
| --- | --- | --- |
| Parse HIPAA **X12** (ISA / GS / ST) | **Done** | `backend/utils/edi/parser.py`; `POST /edi/upload` |
| **837** professional / institutional claims — companion-guide decode | **Done** | `decode_837.py`, `guide_sections.py`, `guides/elements_837.py`, `guides/code_sets_837.py`; `view_mode: 837_decode` |
| **835** remittance — companion-guide decode | **Done** | `decode_835.py`, `guide_sections_835.py`, `guides/elements_835.py`, `guides/code_sets_835.py`; `view_mode: 835_decode` |
| Hierarchical loops/sections in **file order**, snake_case JSON targets | **Done** | Guide section assigners + `target_keys.py`; decode UI + JSON mapping step |
| **270 / 271** eligibility — canonical mapping + review | **Done** | `mapping_engine.py`, `canonical_model.py`; `view_mode: x12_mapping`; same review workbench as HL7 |
| Human review on mappings (837/835: per-field transform approval; 270/271: mapping review) | **Done** | `EDI837JsonMapping.tsx` (browser-local mapping package today); `/hl7/{id}/review` for eligibility |
| Authoritative **companion guide PDFs** kept with the project | **Done** | Checked in under `docs/` (see below) |
| **Guide tables** (element names, loops, code meanings) encoded for decode | **Done** | `backend/utils/edi/guides/*` — maintained to match the PDFs |

#### Companion guide PDFs (source of truth for decode tables)

These PDFs are the references used to build and validate the Python guide tables. Keep
them in `docs/` when updating decode logic:

| Transaction | HIPAA guide (repo copy) |
| --- | --- |
| **837** health care claim | [`docs/837-health-care-claim-companion-guide.pdf`](837-health-care-claim-companion-guide.pdf) |
| **835** remittance / payment | [`docs/835_compguide.pdf`](835_compguide.pdf) (HIPAA **005010X221**) |

Implementation detail in code points at the same sources, e.g. `decode_835.py` references
`835_compguide (HIPAA 005010X221 remittance)`.

#### Sample EDI files (external — not shipped in this repo)

This repository does **not** include example `.edi` or X12 `.dat` files. For manual
testing and demos, use the Healthcare Data Insight **api-examples** corpus — especially
the folders that match what we decode in phase 1:

| Folder in api-examples | Transaction | Use in this app |
| --- | --- | --- |
| [`edi_files/837`](https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files/837) | **837** health care claim | Companion-guide **decode** + JSON mapping |
| [`edi_files/835`](https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files/835) | **835** remittance / payment | Companion-guide **decode** + JSON mapping |

Browse the full tree from the release branch:
**[https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files](https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files)**

Download any file from `837/` or `835/`, save it anywhere on your machine, and upload on
the **Upload** page (`.edi` or healthcare `.dat` whose content starts with `ISA`).

---

## 3. Vocabulary

| Term | Meaning |
| --- | --- |
| **MSH** | Message Header, the mandatory first segment of every HL7 v2 message. Declares delimiters, sender, receiver, message type, version. The parser reads delimiters from it. |
| **Z-segment** | Site-defined HL7 segment whose name starts with `Z` (`ZLB`, `ZPD`, …). No published schema, so the meaning of each field must be inferred. |
| **ISA / GS / ST** | X12 envelope: Interchange (ISA), Functional Group (GS), Transaction Set (ST). `ST01` is the transaction type: `837`, `835`, `270`, `271`. |
| **Companion guide** | Payer/HIPAA PDF describing loops, segment order, element names, and code meanings. Repo copies: [`docs/837-health-care-claim-companion-guide.pdf`](837-health-care-claim-companion-guide.pdf), [`docs/835_compguide.pdf`](835_compguide.pdf). Decode tables live in `backend/utils/edi/guides/`. |
| **Loop** | A repeatable group of segments in X12 (`LOOP 2300` = claim, `LOOP 2400` = service line, `LOOP 1000A` = payer). Decode output is organised by loop. |
| **Canonical model** | The governed target schema we map into. For HL7 it is in `backend/utils/hl7/canonical_model.py`; for 270/271 in `backend/utils/edi/canonical_model.py`. |
| **Semantic confidence** | How sure the engine is about what a Z-field *means*. 0–1. |
| **Stability** | How consistently a Z-field is populated across occurrences of its segment. `populated / total`. |
| **Routing** | Where a Z-field goes based on the two scores: `AUTO_MAP`, `AUTO_MAP_OPTIONAL`, `REVIEW`, `HUMAN_REQUIRED`. |
| **HITL** | Human in the loop. Every mapping on both paths needs a human approval before it can be published or downloaded. |

---

## 4. Running it

```bash
# one-shot (backend + frontend)
./start.sh

# or separately
cd backend && PYTHONPATH=. .venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev -- --host 127.0.0.1        # http://127.0.0.1:5173, proxies /sttm-api → 8000
```

- Health: `http://127.0.0.1:8000/health`
- Storage: SQLite at `backend/data/app.db` (override with `APP_DB_PATH`). Tables are
  created with `create_all()` on startup; there is no migration tool.
- No LLM key is required for HL7/EDI. `GOOGLE_API_KEY` etc. only matter for the
  data-file / BRD agents; without them the backend prints an "Auth:" notice at startup
  and the HL7/EDI endpoints still work.
- Sample EDI: use **`837/`** and **`835/`** under
  [api-examples `edi_files`](https://github.com/Healthcare-Data-Insight/api-examples/tree/release/2.15.0/edi_files)
  (not bundled in this repo). Upload from your machine via the UI.
- HL7 samples: `hl7-samples/` for the spike runner
  (`python -m utils.hl7.run_spike --samples DIR` from `backend/`).
- Tests: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/test_decode_837.py`.

---

## 5. Upload and format detection

Both paths start on the Upload page (`frontend/src/app/pages/UploadIdentifier.tsx`).

```text
frontend/src/app/end-points/hl7Api.ts   isHL7File(file)      → name ends with .hl7
frontend/src/app/end-points/ediApi.ts   isEDIFileByName(file) → .edi or .dat
                                        sniffEDIFile(file)    → .edi always; .dat only if the
                                                                first 4 KB look like ISA/GS/ST
```

Why the sniff: the project also accepts fixed-width tabular `.dat` files on the normal
path. Only `.dat` files whose head is X12 go to `/edi/upload`.

Server side the same check is repeated: `backend/utils/edi/parser.py::looks_like_x12`
rejects anything that does not start with `ISA` (or contain `GS`/`ST` in the head).
HL7 parsing fails with a clear message if the file does not begin with `MSH`.

Both upload endpoints accept an optional `app_session_id` form field so the result is
linked to the current app session (that is what makes it appear under Recent Sessions
in the sidebar).

---

## 6. HL7 v2 path

See also [`backend/utils/hl7/README.md`](../backend/utils/hl7/README.md) (governance
`RULE-*` checks, routing table, `run_spike`, and per-file roles).

### 6.1 Request flow

```text
POST /hl7/upload  (backend/api/routers/hl7.py::upload_hl7)
  for each file:
    parse()          utils/hl7/parser.py          segments, fields, components; delimiters from MSH;
                                                  Z-segment detection; MLLP de-framing
    profile([msg])   utils/hl7/profiler.py        per-file segment frequency + field population
    infer_corpus()   utils/hl7/zsegment_inference.py   per-file Z-field scores
  across all files:
    profile(messages)          corpus profile
    infer_corpus(messages)     corpus-level Z-field inference (more evidence → better scores)
    build_mappings()           utils/hl7/mapping_engine.py   proposed canonical targets
    map_message()              utils/hl7/fhir_mapper.py      optional FHIR docs (ORU→Observation, MDM→DocumentReference)
  persist:
    Hl7Repository.create()     db/hl7_repository.py          result_json, mappings_json, fhir_json
    sync_custom_targets_from_mappings()
    AppSessionRepository.link_hl7_session()
```

The response is the session payload (`hl7_session_id`, `summary`, `routing_summary`,
`files[]`, `profile`, `inference`, `mapping_summary`, `fhir_available`).

### 6.2 How Z-field scoring works

`backend/utils/hl7/zsegment_inference.py`. Pure Python, no dependencies, no model.

Semantic confidence is a weighted sum of signals:

| Signal | Weight |
| --- | --- |
| Field is self-describing (`LABEL^VALUE`) | +0.40 |
| Label tokens resolve against the healthcare `LEXICON` dict | up to +0.30 |
| Value shape is determinate (boolean, integer, code, identifier, datetime) | +0.20 |
| Value set is small and closed | +0.10 |
| Values corroborate the label (e.g. valid DICOM modality codes) | +0.10 |
| Label differs between occurrences of the same position | −0.15 |
| Segment appears only once in the corpus | −0.10 |

Stability is `occurrences populated / total occurrences`.

Routing:

| Semantic | Stability | Routing |
| --- | --- | --- |
| ≥ 0.85 | 1.0 | `AUTO_MAP` |
| ≥ 0.85 | < 1.0 | `AUTO_MAP_OPTIONAL` (map, mark optional) |
| 0.50 – 0.85 | any | `REVIEW` |
| < 0.50 | any | `HUMAN_REQUIRED` (no target proposed) |

Every `Inference` carries a `reasons` list so a reviewer can audit the number. If you
need a new field to resolve, the first place to look is the `LEXICON` dict and
`detect_datatype()`.

### 6.3 Review and publish

`backend/utils/hl7/mapping_package.py` owns the governance rules; the router just calls it.

| Endpoint | What it does |
| --- | --- |
| `GET  /hl7/sessions/{id}/mappings` | Mappings, readiness, custom targets, canonical model slice |
| `POST /hl7/sessions/{id}/review` | One decision: `approve`, `reject`, `defer`, `edit`, `reset`. `reject` and `edit` require a comment. |
| `POST /hl7/sessions/{id}/bulk-approve` | Approve all auto-approvable standard mappings |
| `POST /hl7/sessions/{id}/bulk-approve-selected` | Approve a chosen list |
| `POST /hl7/sessions/{id}/publish` | Writes `vN` to `hl7_published_packages`; refuses if readiness is not met; never overwrites |
| `GET  /hl7/sessions/{id}/versions[/{v}]` | Published packages |
| `GET  /hl7/sessions/{id}/audit` | Every decision with before/after state |
| `GET  /hl7/sessions/{id}/export/mappings` | Download |
| `GET  /hl7/sessions/{id}/fhir/{name}` | FHIR document per source file |

Mapping statuses: `proposed → approved | rejected | deferred`, plus `unresolved` for
standard fields with no target (nothing is silently dropped).

Rules enforced in code, not by convention: Z-segment mappings are never
auto-approvable; confidence < 0.50 yields no target; required unresolved mappings block
publication; a published version is immutable.

### 6.4 Frontend

| Route | Component | Purpose |
| --- | --- | --- |
| `/hl7/:id` | `pages/HL7Results.tsx` | Profile: files, segments, Z-field inference, routing summary |
| `/hl7/:id/review` | `pages/HL7MappingReview.tsx` | Mapping workbench: approve / edit / reject, bulk approve, publish, versions, audit |

API client: `frontend/src/app/end-points/hl7Api.ts` (types `HL7Result`, `FieldMapping`,
`MappingStatus`, `ReviewAction`; functions `uploadHL7Files`, `getHL7Session`,
`getHL7Mappings`, `reviewHL7Mapping`, `publishHL7Package`, …).

---

## 7. X12 EDI path

See also [`backend/utils/edi/README.md`](../backend/utils/edi/README.md) (transaction
matrix, `POST /edi/upload` behaviour, module list, **837** / **835** sample links).

### 7.1 Request flow

```text
POST /edi/upload  (backend/api/routers/edi.py::upload_edi)
  for each file:
    extension must be .edi or .dat
    looks_like_x12(text)                  utils/edi/parser.py
    parse_documents(text)                 one InterchangeMessage per ST..SE; delimiters from ISA;
                                          elements addressable as NM1-9, CLM-2 …
  across all files:
    txns = {m.transaction_set}
    if txns == {"837"}:  edi_decoded = decode_edi_837(messages); view_mode = "837_decode"
    if txns == {"835"}:  edi_decoded = decode_edi_835(messages); view_mode = "835_decode"
    else (270/271):      mappings = build_mappings(messages)  → view_mode = "x12_mapping"
  persist in hl7_sessions with format="x12", view_mode, edi_parsed, edi_decoded
```

A session must be all-837 or all-835 to get the decode view. Mixed uploads fall to the
mapping view.

Other endpoints:

| Endpoint | What it does |
| --- | --- |
| `GET /edi/sessions/{id}/decoded` | Re-decodes from the stored `edi_parsed` with the right decoder (so decoder fixes apply to old sessions) |
| `GET /edi/sessions/{id}/export/json` | Server-side hierarchical JSON (no transforms) |
| `GET /edi/canonical-model` | Target entities for the 270/271 review UI |

### 7.2 Companion-guide decode (837 and 835)

Module layout in `backend/utils/edi/`:

| File | Role |
| --- | --- |
| `parser.py` | X12 tokeniser; `looks_like_x12`, `parse_documents`, `InterchangeMessage`, `Segment`, `Delimiters` |
| `decode_837.py` | Per-segment decode for 837. Also owns the shared helpers `message_from_stored`, `serialize_messages`, HI composite handling, `NM1` party labels |
| `decode_835.py` | Per-segment decode for 835 (BPR, TRN, CLP, SVC, CAS, PLB, …). Reuses the helpers above |
| `guide_sections.py` | 837 loop assignment: which section each segment belongs to, in file order |
| `guide_sections_835.py` | 835 loop assignment: Remittance header (BPR), LOOP 1000A payer, LOOP 1000B payee, LOOP 2100 per LX, PLB, trailers |
| `guide_section_labels.py` | `json_segment_label()` — the label used in JSON output (e.g. BHT → "Transaction header") |
| `guides/elements_837.py`, `guides/elements_835.py` | Segment names and element definitions (`ELEMENT_DEFS`), `resolve_element_def` |
| `guides/code_sets_837.py`, `guides/code_sets_835.py` | Code → meaning tables (`CLP02` claim status, `CAS01` group, `BPR04` payment method, …), `lookup_code` |
| `guides/nm1_guide_elements.py` | NM1 qualifier handling shared by both |
| `format_meanings.py` | Human-readable meanings for dates (`CCYYMMDD`, `RD8`), times, amounts, control numbers, DTP qualifiers |
| `target_keys.py` | `target_for_element()` → snake_case JSON key for each element |
| `export_json.py` | `decoded_corpus_to_json()` — the server-side hierarchical export |

Decoded shape (what the frontend receives as `edi_decoded`):

```text
files[]
  messages[]
    sections[]                 one per guide section, in file order
      section_id, title        e.g. "loop-2300-1", "LOOP 2300 — Claim information (1)"
      segments[]
        sequence, segment_id, segment_label, party_code
        elements[]
          element_id           e.g. "CLM02"
          element_name         from the companion guide
          value, meaning       raw value + decoded meaning (code lookup / date format)
          target               snake_case key
          children[]           composites (HI, NM108+NM109) nest here
```

To add a segment or code: add the element definition to `guides/elements_8xx.py`, the
code table to `guides/code_sets_8xx.py`, and if it starts a new loop, a rule in
`guide_sections[_835].py`. The decoder picks it up without other changes.

### 7.3 JSON mapping step (frontend only)

The mapping and transform choices for 837/835 live entirely in the browser; the server
export does not apply them.

| File | Role |
| --- | --- |
| `pages/EDI837Decode.tsx` | `/hl7/:id` for 837/835 sessions. Section tables in file order. "Map to JSON" button → mapping page |
| `pages/EDI837JsonMapping.tsx` | `/hl7/:id/json-mapping`. Table: Source · Target · Transform · Example · Preview · Status · Actions. Filters, pagination, Edit drawer, Approve / Approve all, Download Mapping |
| `utils/edi837MappingRows.ts` | Flattens the decoded tree into one row per leaf element; `mappingRowId()` = `filename|control_id|sequence|segment|element` |
| `utils/edi837Transforms.ts` | `classifyEdi837Temporal()` (DTP → date; BHT05/time names → time; CCYYMMDD/D8 → date), format options, `applyEdi837Transform()`, `defaultRowMappingConfig()`, `previewMappingValue()` |
| `utils/edi837MappingStorage.ts` | Persists row decisions in `localStorage` under `edi837-json-mappings:{sessionId}` (v2 package) |
| `utils/edi837ExportJson.ts` | Builds the hierarchical JSON with transforms applied; `download837Json()` → `{basename}-mapped.json` |

Behaviour to know:

- Non date/time rows are `Direct` and locked, auto-approved.
- Date/time rows default to `Transform` with a suggested format and `pending` status.
  The user can pick another format or switch to Direct.
- "Download Mapping" is disabled while any date/time row is pending.
- Because decisions are in `localStorage`, they are per browser. Clearing site data loses
  them. Moving this server-side is the obvious next step if needed.

### 7.4 270 / 271 path

`backend/utils/edi/mapping_engine.py` applies deterministic rules from X12 element paths
to `canonical_model.py` entities. The result is stored as `mappings_json` and reviewed in
the same `/hl7/:id/review` workbench as HL7, using the same `/hl7/sessions/{id}/…`
endpoints.

---

## 8. Storage

All four tables are in `backend/db/models.py`; access goes through
`backend/db/hl7_repository.py`.

| Table | Contents |
| --- | --- |
| `hl7_sessions` | `id`, `app_session_id`, `user_key`, `result_json` (the upload payload incl. `format`, `view_mode`, `edi_parsed`, `edi_decoded`), `mappings_json`, `fhir_json` |
| `hl7_custom_targets` | Reviewer-created targets, unique per `(session_id, target_path)` |
| `hl7_audit_events` | One row per review / publish decision |
| `hl7_published_packages` | `(session_id, version)` → immutable package JSON |

`view_mode` values and what they render:

| `view_mode` | Format | `/hl7/:id` shows | Second step |
| --- | --- | --- | --- |
| *(absent)* | HL7 | `HL7Results` profile | `/review` |
| `x12_mapping` | X12 270/271 | `HL7Results` profile | `/review` |
| `837_decode` | X12 837 | `EDI837DecodeView` | `/json-mapping` |
| `835_decode` | X12 835 | `EDI837DecodeView` | `/json-mapping` |

---

## 9. Session navigation (sidebar and Sessions page)

`frontend/src/app/utils/interchangeSessionLabel.ts` is the single place that decides
labels and routes for HL7/EDI sessions:

- `isEdiCompanionDecode(meta)` → true for `837_decode` / `835_decode`
- `interchangeOpenActionLabel()` → "Decode" (EDI) or "Profile" (HL7)
- `interchangeMappingPath()` → `/json-mapping` (EDI decode) or `/review`
- `interchangeMappingActionLabel()` → "Mapping" (EDI) or "Review" / "Mapped" (HL7)

`appSessionsApi.ts::getAppSessionOpenRoute()` returns `/hl7/{id}` whenever an app session
has a linked HL7/EDI session. `HL7Results.tsx` refetches on `params.hl7SessionId` /
`location.key`, so clicking between sessions reloads correctly.

---

## 10. Where to start for common tasks

| Task | Start here |
| --- | --- |
| A Z-field scores too low | `zsegment_inference.py`: `LEXICON`, `detect_datatype`, weights in `infer_field` |
| An 837/835 element shows the raw code instead of a meaning | `guides/code_sets_8xx.py` then `format_meanings.semantic_meaning` |
| A segment lands in the wrong loop | `guide_sections.py` / `guide_sections_835.py::assign_guide_sections` |
| Wrong `segment_label` or JSON key in export | `guide_section_labels.py`, `target_keys.py` |
| A field should (or should not) be date/time transformable | `edi837Transforms.ts::classifyEdi837Temporal` |
| New transaction set (e.g. 276/277) | Add decoder + sections + guides modules, branch in `edi.py::upload_edi`, new `view_mode`, extend `InterchangeViewMode` in `interchangeSessionLabel.ts` |
| Add a governance rule for HL7 review | `mapping_package.py` (`apply_review`, `readiness`, `publish`) |
| Persist EDI mapping decisions server-side | Add a column/table in `models.py`, endpoint in `edi.py`, replace `edi837MappingStorage.ts` |

---

## 11. Known limits

- No LLM on these paths; the HL7 README describes where one would help (positional
  Z-segments with no inline label).
- HL7: no table validation against v2.5.1 code sets, no LOINC/UCUM validation, first
  repetition only, no ACK generation, no MLLP transport.
- EDI: 837/835 decode covers the segments in the two companion guides; unknown segments
  still decode with generic element ids. Mixed 837+835 uploads fall back to the mapping view.
- EDI mapping decisions are browser-local (see 6.3).
- Schema changes require manual handling; `create_all()` does not alter existing tables.
