"""Decode X12 835 remittance into ordered segment tables (companion guide semantics)."""

from __future__ import annotations

from typing import Any

from .format_meanings import semantic_meaning
from .guide_sections_835 import assign_guide_sections
from .guides.elements_835 import SEGMENT_NAMES, resolve_element_def
from .guides.code_sets_835 import lookup_code as _lookup_code
from .parser import Delimiters, InterchangeMessage, Segment
from .target_keys import target_for_element

# Reuse stored-message helpers from 837 decode (same X12 shape).
from .decode_837 import message_from_stored, serialize_messages

_GUIDE_REF = "835_compguide (HIPAA 005010X221 remittance)"


def _element_id(segment: str, position_1based: int) -> str:
    return f"{segment}{position_1based:02d}"


def _meaning_for_value(
    code_set_id: str | None,
    value: str,
    segment: str,
    position: int,
) -> str:
    if not value.strip():
        return ""
    if code_set_id:
        label = _lookup_code(code_set_id, value)
        if label:
            return label
    if segment == "ST" and position == 1:
        guides = {
            "835": "Health Care Claim Payment/Advice (835)",
            "837": "Health Care Claim (837)",
        }
        return guides.get(value.strip(), f"Transaction set {value}")
    if segment == "SVC" and position == 1 and ":" in value:
        return _decode_svc_composite(value)
    return ""


def _decode_svc_composite(value: str) -> str:
    if ":" not in value:
        return value
    qual, code = value.split(":", 1)
    qual_label = _lookup_code("SVC01", qual) if qual else qual
    return f"{qual_label or qual}; procedure/service code {code}"


def _decode_element(
    segment: str,
    position: int,
    value: str,
    name: str,
    code_set_id: str | None,
    sibling_fields: list[str],
) -> dict[str, Any]:
    elem_id = _element_id(segment, position)
    meaning = _meaning_for_value(code_set_id, value, segment, position)
    if not meaning and code_set_id:
        meaning = _lookup_code(code_set_id, value) or ""
    if not meaning:
        meaning = semantic_meaning(
            segment,
            position,
            value,
            element_name=name,
            sibling_fields=sibling_fields,
        )
    return {
        "element_id": elem_id,
        "element_name": name,
        "value": value,
        "meaning": meaning,
        "target": target_for_element(elem_id, name),
    }


def _finalize_nm1_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(elements):
        el = elements[i]
        if (
            el.get("element_id") == "NM108"
            and i + 1 < len(elements)
            and elements[i + 1].get("element_id") == "NM109"
        ):
            n109 = elements[i + 1]
            qual = (el.get("value") or "").strip()
            qual_meaning = _lookup_code("NM108", qual) or el.get("meaning") or ""
            id_val = (n109.get("value") or "").strip()
            merged = dict(el)
            merged["children"] = [{
                "element_id": "NM109",
                "element_name": "Identification Code",
                "value": n109.get("value", ""),
                "meaning": n109.get("meaning") or (f"{qual_meaning}: {id_val}" if id_val else ""),
                "target": target_for_element("NM109", "Identification Code"),
            }]
            merged["target"] = target_for_element("NM108", el.get("element_name", "Identification Code Qualifier"))
            if qual_meaning and not merged.get("meaning"):
                merged["meaning"] = qual_meaning
            out.append(merged)
            i += 2
            continue
        out.append(el)
        i += 1
    return out


def _party_segment_label(segment_id: str, elements: list[dict[str, Any]]) -> tuple[str, str]:
    code_el = "N101" if segment_id == "N1" else "NM101"
    lookup = "N101" if segment_id == "N1" else "NM101"
    ent = ""
    for el in elements:
        if el.get("element_id") == code_el:
            ent = (el.get("value") or "").strip()
            break
    if not ent:
        return "", ""
    label = _lookup_code(lookup, ent) or ""
    return ent, label


def decode_segment(seg: Segment, delimiters: Delimiters) -> dict[str, Any]:
    segment_title = SEGMENT_NAMES.get(seg.name, seg.name)
    elements: list[dict[str, Any]] = []
    for i in range(seg.field_count()):
        raw = seg.fields[i]
        if seg.name in ("NM1", "N1") and not (raw or "").strip():
            continue
        name, code_set = resolve_element_def(seg.name, i + 1)
        elements.append(
            _decode_element(seg.name, i + 1, raw, name, code_set, list(seg.fields))
        )

    party_code = ""
    segment_label = ""
    if seg.name == "NM1":
        elements = _finalize_nm1_elements(elements)
        party_code, segment_label = _party_segment_label("NM1", elements)
    elif seg.name == "N1":
        party_code, segment_label = _party_segment_label("N1", elements)

    payload: dict[str, Any] = {
        "sequence": seg.index + 1,
        "segment_id": seg.name,
        "segment_name": segment_title,
        "elements": elements,
    }
    if segment_label:
        payload["segment_label"] = segment_label
        payload["party_code"] = party_code
    return payload


def decode_message(message: InterchangeMessage) -> dict[str, Any]:
    segments = [decode_segment(s, message.delimiters) for s in message.segments]
    sections = assign_guide_sections(segments)
    return {
        "source_file": message.source_file,
        "transaction_set": message.transaction_set,
        "implementation_guide": message.implementation_guide,
        "guide_reference": _GUIDE_REF,
        "version": message.version,
        "control_id": message.control_id,
        "segments": segments,
        "sections": sections,
    }


def decode_from_stored(stored_messages: list[dict[str, Any]]) -> dict[str, Any]:
    messages = [message_from_stored(item) for item in stored_messages]
    return decode_messages(messages)


def decode_messages(messages: list[InterchangeMessage]) -> dict[str, Any]:
    by_file: dict[str, list[dict[str, Any]]] = {}
    for msg in messages:
        decoded = decode_message(msg)
        fname = msg.source_file or "unknown"
        by_file.setdefault(fname, []).append(decoded)
    return {
        "guide_reference": _GUIDE_REF,
        "files": [
            {"filename": filename, "messages": file_messages}
            for filename, file_messages in by_file.items()
        ],
    }
