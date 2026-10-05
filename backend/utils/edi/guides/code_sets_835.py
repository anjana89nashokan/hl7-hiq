"""Code value meanings for HIPAA 835 (005010X221) — remittance companion guide."""

from __future__ import annotations

from .code_sets_837 import CODE_SETS as _BASE

N101_ENTITY = {
    "PR": "Payer",
    "PE": "Payee",
    "IL": "Insured or Subscriber",
    "QC": "Patient",
    "82": "Rendering Provider",
    "TT": "Transfer To",
    "PRP": "Primary Payer",
    "SEP": "Secondary Payer",
    "TTP": "Tertiary Payer",
}

BPR01_HANDLING = {
    "C": "Payment Accompanies Remittance Advice",
    "D": "Make Payment Only",
    "H": "Notification Only",
    "I": "Remittance Information Only",
    "P": "Prenotification of Future Transfers",
    "U": "Split Payment and Remittance",
    "X": "Handling Party's Option",
}

BPR03_CREDIT_DEBIT = {
    "C": "Credit",
    "D": "Debit",
}

BPR04_PAYMENT_METHOD = {
    "ACH": "Automated Clearing House",
    "BOP": "Financial Institution Option",
    "CHK": "Check",
    "FWT": "Federal Reserve Funds/Wire Transfer",
    "NON": "Non-Payment Data",
}

CLP02_CLAIM_STATUS = {
    "1": "Processed as Primary",
    "2": "Processed as Secondary",
    "3": "Processed as Tertiary",
    "4": "Denied",
    "19": "Processed as Primary, Forwarded to Additional Payer(s)",
    "20": "Processed as Secondary, Forwarded to Additional Payer(s)",
    "21": "Processed as Tertiary, Forwarded to Additional Payer(s)",
    "22": "Reversal of Previous Payment",
    "23": "Not Our Claim, Forwarded to Additional Payer(s)",
    "25": "Predetermination Pricing Only - No Payment",
}

CAS01_GROUP = {
    "CO": "Contractual Obligations",
    "CR": "Correction and Reversals",
    "OA": "Other Adjustments",
    "PI": "Payor Initiated Reductions",
    "PR": "Patient Responsibility",
}

CODE_SETS: dict[str, dict[str, str]] = {
    **_BASE,
    "N101": N101_ENTITY,
    "NM101": _BASE.get("NM101", {}),
    "BPR01": BPR01_HANDLING,
    "BPR03": BPR03_CREDIT_DEBIT,
    "BPR04": BPR04_PAYMENT_METHOD,
    "CLP02": CLP02_CLAIM_STATUS,
    "CAS01": CAS01_GROUP,
}


def lookup_code(code_set_id: str, value: str) -> str | None:
    table = CODE_SETS.get(code_set_id)
    if not table:
        return None
    return table.get((value or "").strip())
