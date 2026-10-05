"""Element names for 835 remittance segments (005010X221 companion guide)."""

from __future__ import annotations

from .elements_837 import ELEMENT_DEFS as _DEFS_837
from .elements_837 import SEGMENT_NAMES as _NAMES_837

_SHARED = ("ISA", "IEA", "GS", "GE", "ST", "SE", "N3", "N4", "REF", "PER", "DTM", "AMT", "NM1", "CAS")

SEGMENT_NAMES: dict[str, str] = {
    **_NAMES_837,
    "BPR": "Beginning Segment for Payment Order/Remittance Advice",
    "TRN": "Trace",
    "N1": "Party Identification",
    "LX": "Assigned Number",
    "CLP": "Claim Payment Information",
    "SVC": "Service Payment Information",
    "PLB": "Provider Level Adjustment",
    "MOA": "Medicare Outpatient Adjudication Information",
    "MIA": "Medicare Inpatient Adjudication Information",
    "QTY": "Quantity Information",
    "RDM": "Remittance Delivery Method",
    "TS3": "Provider Summary Information",
    "TS2": "Provider Supplemental Summary Information",
}

ELEMENT_DEFS: dict[str, list[tuple[str, str | None]]] = {
    k: list(v) for k, v in _DEFS_837.items() if k in _SHARED
}

ELEMENT_DEFS.update({
    "BPR": [
        ("Transaction Handling Code", "BPR01"),
        ("Total Actual Provider Payment Amount", None),
        ("Credit or Debit Flag Code", "BPR03"),
        ("Payment Method Code", "BPR04"),
        ("Payment Format Code", None),
        ("DFI ID Number Qualifier", None),
        ("DFI Identification Number", None),
        ("Account Number Qualifier", None),
        ("Account Number", None),
        ("Originating Company Identifier", None),
        ("Originating Company Supplemental Code", None),
        ("DFI ID Number Qualifier", None),
        ("DFI Identification Number", None),
        ("Account Number Qualifier", None),
        ("Account Number", None),
        ("Check Issue or EFT Effective Date", None),
    ],
    "TRN": [
        ("Trace Type Code", None),
        ("Check or EFT Trace Number", None),
        ("Originating Company Identifier", None),
        ("Originating Company Supplemental Code", None),
    ],
    "N1": [
        ("Entity Identifier Code", "N101"),
        ("Name", None),
        ("Identification Code Qualifier", None),
        ("Identification Code", None),
    ],
    "LX": [
        ("Assigned Number", None),
    ],
    "CLP": [
        ("Claim Submitter's Identifier", None),
        ("Claim Status Code", "CLP02"),
        ("Total Claim Charge Amount", None),
        ("Claim Payment Amount", None),
        ("Patient Responsibility Amount", None),
        ("Claim Filing Indicator Code", None),
        ("Payer Claim Control Number", None),
        ("Facility Type Code", None),
        ("Claim Frequency Code", None),
        ("Patient Status Code", None),
        ("Diagnosis Related Group (DRG) Code", None),
        ("Diagnosis Related Group (DRG) Weight", None),
        ("Discharge Fraction", None),
    ],
    "SVC": [
        ("Composite Medical Procedure Identifier", "SVC01"),
        ("Line Item Charge Amount", None),
        ("Line Item Provider Payment Amount", None),
        ("National Uniform Billing Committee Revenue Code", None),
        ("Units of Service Paid Count", None),
    ],
    "PLB": [
        ("Provider Identifier", None),
        ("Fiscal Period Date", None),
        ("Adjustment Identifier", None),
        ("Provider Adjustment Amount", None),
    ],
    "MOA": [
        ("Reimbursement Rate", None),
        ("HCPCS Payable Amount", None),
        ("Claim Payment Remark Code", None),
        ("Claim Payment Remark Code", None),
        ("Claim Payment Remark Code", None),
        ("Claim Payment Remark Code", None),
        ("Claim Payment Remark Code", None),
        ("Monetary Amount", None),
        ("Monetary Amount", None),
    ],
})

# CAS repeating pattern (same as 837)
from .elements_837 import _build_cas_element_defs  # noqa: E402

ELEMENT_DEFS["CAS"] = _build_cas_element_defs()


def resolve_element_def(segment: str, position_1based: int) -> tuple[str, str | None]:
    defs = ELEMENT_DEFS.get(segment, [])
    idx = position_1based - 1
    if 0 <= idx < len(defs):
        return defs[idx]
    return (f"{segment}{position_1based:02d}", None)
