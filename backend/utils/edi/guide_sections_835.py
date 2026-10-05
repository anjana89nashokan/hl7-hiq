"""Group decoded 835 segments into companion-guide loops (1000A/B, 2100, 2110, PLB)."""

from __future__ import annotations

from typing import Any

from .guides.code_sets_835 import lookup_code as _lookup_code

_ENVELOPE_SEGS = frozenset({"ISA", "GS", "ST"})
_TRAILER_SEGS = frozenset({"SE", "GE", "IEA"})
_HEADER_SEGS = frozenset({"BPR", "TRN", "REF", "DTM", "RDM", "CUR"})

_N1_LOOP_TITLES = {
    "PR": "LOOP 1000A — Payer identification",
    "PE": "LOOP 1000B — Payee identification",
}


def _element_value(seg: dict[str, Any], element_id: str) -> str:
    for el in seg.get("elements") or []:
        if el.get("element_id") == element_id:
            return (el.get("value") or "").strip()
    return ""


def assign_guide_sections(decoded_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not decoded_segments:
        return []

    groups: list[dict[str, Any]] = []
    bucket: list[dict[str, Any]] = []
    current_id = "envelope"
    current_title = "Interchange / functional group"
    in_claim_loop = False

    def flush() -> None:
        nonlocal bucket, in_claim_loop
        if not bucket:
            return
        groups.append({
            "section_id": current_id,
            "title": current_title,
            "segments": bucket,
        })
        bucket = []
        in_claim_loop = False

    for seg in decoded_segments:
        sid = seg.get("segment_id") or ""

        if sid in _ENVELOPE_SEGS:
            if sid == "ISA":
                flush()
                current_id = "envelope"
                current_title = "Interchange / functional group"
            bucket.append(seg)
            continue

        if sid in _TRAILER_SEGS:
            if not bucket or bucket[-1].get("segment_id") not in _TRAILER_SEGS:
                flush()
                current_id = "trailers"
                current_title = "Transaction / interchange trailers"
            bucket.append(seg)
            continue

        if sid == "BPR":
            flush()
            current_id = "remittance-header"
            current_title = "Remittance header — payment (BPR)"
            bucket.append(seg)
            continue

        if sid in _HEADER_SEGS and current_id == "remittance-header":
            bucket.append(seg)
            continue

        if sid == "N1":
            ent = _element_value(seg, "N101")
            ent_label = _lookup_code("N101", ent) if ent else ""
            flush()
            loop_title = _N1_LOOP_TITLES.get(ent)
            if loop_title:
                current_id = f"loop-1000-{ent.lower()}-{seg.get('sequence')}"
                current_title = loop_title
            elif ent_label:
                current_id = f"party-n1-{seg.get('sequence')}-{ent}"
                current_title = f"{ent_label} (N1*{ent})"
            else:
                current_id = f"party-n1-{seg.get('sequence')}"
                current_title = "Party identification (N1)"
            bucket.append(seg)
            continue

        if sid in ("N3", "N4", "REF", "PER") and current_id.startswith(("loop-1000", "party-n1")):
            bucket.append(seg)
            continue

        if sid == "LX":
            flush()
            line = _element_value(seg, "LX01") or "?"
            current_id = f"loop-2100-{seg.get('sequence')}"
            current_title = f"LOOP 2100 — Claim payment (LX {line})"
            in_claim_loop = True
            bucket.append(seg)
            continue

        if sid == "PLB":
            flush()
            current_id = f"plb-{seg.get('sequence')}"
            current_title = "Provider level adjustment (PLB)"
            bucket.append(seg)
            continue

        if sid in ("TS2", "TS3"):
            flush()
            current_id = f"summary-{sid.lower()}-{seg.get('sequence')}"
            current_title = f"Provider summary ({sid})"
            bucket.append(seg)
            continue

        if in_claim_loop or current_id.startswith("loop-2100"):
            bucket.append(seg)
            continue

        bucket.append(seg)

    flush()
    return _enrich_sections(groups)


def _enrich_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for section in sections:
        section_id = section.get("section_id") or ""
        section["combined_table"] = section_id.startswith("loop-2100")
        section_title = section.get("title") or ""
        for seg in section.get("segments") or []:
            seg["guide_section_title"] = section_title
    return sections
