"""
FinTrust AI — India GST Integrity Engine
========================================
Dedicated module for Indian Goods and Services Tax (GST) verification:
1. Structural and Luhn mod 36 checksum validation of 15-character GSTINs.
2. State and Union Territory code extraction and classification.
3. Supplier and Recipient GSTIN reconciliation against trusted vendor/PO baselines.
4. Place-of-supply consistency checking.
5. Deterministic tax-type classification (Intra-State CGST+SGST/UTGST vs Inter-State IGST)
   for supported transaction profiles (STANDARD_DOMESTIC).
6. Tax component breakdown verification (CGST, SGST, UTGST, IGST, Cess).
7. GST component reconciliation against declared invoice total GST.
8. Defense-in-depth safety flags for special cases requiring manual human review.

Statutory and Technical References:
- CGST Rules, 2017, Rule 10: Structure of GSTIN (State code + PAN/TAN + Entity code + Checksum).
- CGST Rules, 2017, Rule 46: Mandatory tax invoice particulars.
- IGST Act, 2017, Section 7: Inter-state supplies.
- IGST Act, 2017, Section 8: Intra-state supplies.
- IGST Act, 2017, Sections 10 & 12: Place of supply for goods and services.
- Union Territory Goods and Services Tax Act, 2017 (UTGST Act), Section 1(2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .financial import from_paise, to_paise

# Character mapping for GSTIN base-36 character set (0-9 followed by A-Z)
BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE36_MAP = {c: i for i, c in enumerate(BASE36_CHARS)}

# Official 2-digit Indian State and Union Territory GST codes catalogue
# Distinguishes States and UTs with legislative assemblies (which levy SGST)
# from UTs without legislative assemblies (which levy UTGST under the UTGST Act).
STATE_CATALOGUE: dict[str, dict[str, Any]] = {
    "01": {"name": "Jammu and Kashmir", "tax_type": "SGST", "is_ut": True, "has_legislature": True},
    "02": {"name": "Himachal Pradesh", "tax_type": "SGST", "is_ut": False},
    "03": {"name": "Punjab", "tax_type": "SGST", "is_ut": False},
    "04": {"name": "Chandigarh", "tax_type": "UTGST", "is_ut": True, "has_legislature": False},
    "05": {"name": "Uttarakhand", "tax_type": "SGST", "is_ut": False},
    "06": {"name": "Haryana", "tax_type": "SGST", "is_ut": False},
    "07": {"name": "Delhi", "tax_type": "SGST", "is_ut": True, "has_legislature": True},
    "08": {"name": "Rajasthan", "tax_type": "SGST", "is_ut": False},
    "09": {"name": "Uttar Pradesh", "tax_type": "SGST", "is_ut": False},
    "10": {"name": "Bihar", "tax_type": "SGST", "is_ut": False},
    "11": {"name": "Sikkim", "tax_type": "SGST", "is_ut": False},
    "12": {"name": "Arunachal Pradesh", "tax_type": "SGST", "is_ut": False},
    "13": {"name": "Nagaland", "tax_type": "SGST", "is_ut": False},
    "14": {"name": "Manipur", "tax_type": "SGST", "is_ut": False},
    "15": {"name": "Mizoram", "tax_type": "SGST", "is_ut": False},
    "16": {"name": "Tripura", "tax_type": "SGST", "is_ut": False},
    "17": {"name": "Meghalaya", "tax_type": "SGST", "is_ut": False},
    "18": {"name": "Assam", "tax_type": "SGST", "is_ut": False},
    "19": {"name": "West Bengal", "tax_type": "SGST", "is_ut": False},
    "20": {"name": "Jharkhand", "tax_type": "SGST", "is_ut": False},
    "21": {"name": "Odisha", "tax_type": "SGST", "is_ut": False},
    "22": {"name": "Chhattisgarh", "tax_type": "SGST", "is_ut": False},
    "23": {"name": "Madhya Pradesh", "tax_type": "SGST", "is_ut": False},
    "24": {"name": "Gujarat", "tax_type": "SGST", "is_ut": False},
    "25": {"name": "Daman and Diu", "tax_type": "UTGST", "is_ut": True, "has_legislature": False},  # Merged into 26
    "26": {"name": "Dadra and Nagar Haveli and Daman and Diu", "tax_type": "UTGST", "is_ut": True, "has_legislature": False},
    "27": {"name": "Maharashtra", "tax_type": "SGST", "is_ut": False},
    "28": {"name": "Andhra Pradesh (Former)", "tax_type": "SGST", "is_ut": False},
    "29": {"name": "Karnataka", "tax_type": "SGST", "is_ut": False},
    "30": {"name": "Goa", "tax_type": "SGST", "is_ut": False},
    "31": {"name": "Lakshadweep", "tax_type": "UTGST", "is_ut": True, "has_legislature": False},
    "32": {"name": "Kerala", "tax_type": "SGST", "is_ut": False},
    "33": {"name": "Tamil Nadu", "tax_type": "SGST", "is_ut": False},
    "34": {"name": "Puducherry", "tax_type": "SGST", "is_ut": True, "has_legislature": True},
    "35": {"name": "Andaman and Nicobar Islands", "tax_type": "UTGST", "is_ut": True, "has_legislature": False},
    "36": {"name": "Telangana", "tax_type": "SGST", "is_ut": False},
    "37": {"name": "Andhra Pradesh", "tax_type": "SGST", "is_ut": False},
    "38": {"name": "Ladakh", "tax_type": "UTGST", "is_ut": True, "has_legislature": False},
    "97": {"name": "Other Territory", "tax_type": "UTGST", "is_ut": True, "has_legislature": False},
    "99": {"name": "Centre Jurisdiction / Special", "tax_type": "IGST", "is_ut": False},
}

# Transaction profiles supported by the engine
GST_PROFILE_STANDARD_DOMESTIC = "STANDARD_DOMESTIC"
GST_PROFILE_SPECIAL_CASE_REVIEW = "SPECIAL_CASE_REVIEW"
GST_PROFILE_NOT_CONFIGURED = "NOT_CONFIGURED"

# Standard validation result codes
RESULT_FORMAT_VALID = "FORMAT_VALID"
RESULT_INVALID_FORMAT = "INVALID_FORMAT"
RESULT_INVALID_STATE_CODE = "INVALID_STATE_CODE"
RESULT_CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
RESULT_CHECKSUM_NOT_EVALUATED = "CHECKSUM_NOT_EVALUATED"

# Finding status values
STATUS_PASS = "PASS"
STATUS_MISMATCH = "MISMATCH"
STATUS_MISSING = "MISSING"
STATUS_NOT_EVALUATED = "NOT_EVALUATED"
STATUS_MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

# Severity levels
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"
SEVERITY_INFO = "info"

# Rounding tolerance for component sum vs total GST (100 paise = ₹1.00)
GST_SUM_TOLERANCE_PAISE = 100

# Disclaimer required by Phase 2 & Phase 11
GSTIN_LEGAL_DISCLAIMER = (
    "GSTIN format and internal record consistency checks do not confirm "
    "active registration with the GST authorities."
)


@dataclass
class GSTFinding:
    finding_code: str
    severity: str
    status: str
    field_name: str
    invoice_value: str | None
    trusted_value: str | None
    explanation: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_code": self.finding_code,
            "severity": self.severity,
            "status": self.status,
            "field_name": self.field_name,
            "invoice_value": self.invoice_value,
            "trusted_value": self.trusted_value,
            "explanation": self.explanation,
            "recommended_action": self.recommended_action,
        }


@dataclass
class GSTIntegrityReport:
    supplier_gstin_result: dict[str, Any]
    recipient_gstin_result: dict[str, Any]
    place_of_supply_result: dict[str, Any]
    tax_classification_result: dict[str, Any]
    component_reconciliation_result: dict[str, Any]
    findings: list[GSTFinding] = field(default_factory=list)
    overall_status: str = STATUS_PASS
    requires_hold: bool = False
    requires_manual_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "supplier_gstin_result": self.supplier_gstin_result,
            "recipient_gstin_result": self.recipient_gstin_result,
            "place_of_supply_result": self.place_of_supply_result,
            "tax_classification_result": self.tax_classification_result,
            "component_reconciliation_result": self.component_reconciliation_result,
            "findings": [f.to_dict() for f in self.findings],
            "overall_status": self.overall_status,
            "requires_hold": self.requires_hold,
            "requires_manual_review": self.requires_manual_review,
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }


def normalize_gstin(value: str | None) -> str | None:
    """Trim whitespace and convert GSTIN to uppercase."""
    if value is None:
        return None
    cleaned = value.strip().upper()
    return cleaned if cleaned else None


def calculate_gstin_checksum(gstin_first_14: str) -> str:
    """
    Calculate the Luhn mod 36 check character for the first 14 characters of a GSTIN.
    Algorithm:
    - Alternating weights 1 and 2 for indices 0 to 13.
    - factor = code_point * weight
    - quotient = factor // 36, remainder = factor % 36
    - sum += quotient + remainder
    - check_code = (36 - (sum % 36)) % 36
    - check_char = BASE36_CHARS[check_code]
    """
    total = 0
    for idx, char in enumerate(gstin_first_14):
        code_point = BASE36_MAP[char]
        weight = 1 if (idx % 2 == 0) else 2
        factor = code_point * weight
        total += (factor // 36) + (factor % 36)
    check_code = (36 - (total % 36)) % 36
    return BASE36_CHARS[check_code]


def validate_gstin(raw_gstin: str | None) -> dict[str, Any]:
    """
    Validate a 15-character Indian GSTIN syntactically.
    Returns a dictionary detailing:
    - is_valid: bool
    - result_code: FORMAT_VALID, INVALID_FORMAT, INVALID_STATE_CODE, CHECKSUM_MISMATCH, etc.
    - state_code: 2-digit string or None
    - state_name: state name or None
    - checksum_evaluated: bool
    - checksum_matched: bool
    - normalized: normalized string
    - disclaimer: notice that format validity != active government registration
    """
    normalized = normalize_gstin(raw_gstin)
    if not normalized:
        return {
            "is_valid": False,
            "result_code": RESULT_INVALID_FORMAT,
            "state_code": None,
            "state_name": None,
            "checksum_evaluated": False,
            "checksum_matched": False,
            "normalized": None,
            "message": "GSTIN value is empty or missing.",
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }

    if len(normalized) != 15:
        return {
            "is_valid": False,
            "result_code": RESULT_INVALID_FORMAT,
            "state_code": None,
            "state_name": None,
            "checksum_evaluated": False,
            "checksum_matched": False,
            "normalized": normalized,
            "message": f"GSTIN must be exactly 15 alphanumeric characters; observed length is {len(normalized)}.",
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }

    # Verify all characters belong to Base-36
    if any(c not in BASE36_MAP for c in normalized):
        return {
            "is_valid": False,
            "result_code": RESULT_INVALID_FORMAT,
            "state_code": None,
            "state_name": None,
            "checksum_evaluated": False,
            "checksum_matched": False,
            "normalized": normalized,
            "message": "GSTIN contains characters outside the standard alphanumeric base-36 character set.",
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }

    state_code = normalized[:2]
    if not state_code.isdigit():
        return {
            "is_valid": False,
            "result_code": RESULT_INVALID_FORMAT,
            "state_code": None,
            "state_name": None,
            "checksum_evaluated": False,
            "checksum_matched": False,
            "normalized": normalized,
            "message": "The first two characters of a GSTIN must be numeric state digits.",
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }

    state_info = STATE_CATALOGUE.get(state_code)
    if state_info is None:
        return {
            "is_valid": False,
            "result_code": RESULT_INVALID_STATE_CODE,
            "state_code": state_code,
            "state_name": None,
            "checksum_evaluated": False,
            "checksum_matched": False,
            "normalized": normalized,
            "message": f"State code '{state_code}' is not recognized in the official GST State/UT catalogue.",
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }

    # Standard entity structure: 10-char PAN or TAN identifier, followed by 2-char entity code, 1 checksum
    # Under standard rules:
    # - Standard PAN: 5 letters, 4 digits, 1 letter (positions 3-12)
    # - Government/TAN or special registration: 4 letters, 5 digits, 1 letter
    # - We do not rigidly reject unusual entity codes, but verify 10-char PAN/TAN pattern
    identifier_part = normalized[2:12]
    is_pan = bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", identifier_part))
    is_tan = bool(re.match(r"^[A-Z]{4}[0-9]{5}[A-Z]$", identifier_part))

    if not (is_pan or is_tan):
        return {
            "is_valid": False,
            "result_code": RESULT_INVALID_FORMAT,
            "state_code": state_code,
            "state_name": state_info["name"],
            "checksum_evaluated": False,
            "checksum_matched": False,
            "normalized": normalized,
            "message": f"Identifier part '{identifier_part}' does not conform to a standard PAN or TAN pattern.",
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }

    # Checksum validation (Luhn mod 36)
    expected_checksum = calculate_gstin_checksum(normalized[:14])
    actual_checksum = normalized[14]
    checksum_matched = (expected_checksum == actual_checksum)

    if not checksum_matched:
        return {
            "is_valid": False,
            "result_code": RESULT_CHECKSUM_MISMATCH,
            "state_code": state_code,
            "state_name": state_info["name"],
            "checksum_evaluated": True,
            "checksum_matched": False,
            "expected_checksum": expected_checksum,
            "actual_checksum": actual_checksum,
            "normalized": normalized,
            "message": f"Checksum character '{actual_checksum}' did not match expected check digit '{expected_checksum}'.",
            "disclaimer": GSTIN_LEGAL_DISCLAIMER,
        }

    return {
        "is_valid": True,
        "result_code": RESULT_FORMAT_VALID,
        "state_code": state_code,
        "state_name": state_info["name"],
        "checksum_evaluated": True,
        "checksum_matched": True,
        "normalized": normalized,
        "message": "GSTIN conforms to 15-character State, PAN, entity, and Luhn mod 36 checksum specifications.",
        "disclaimer": GSTIN_LEGAL_DISCLAIMER,
    }


def mask_gstin(gstin: str | None) -> str:
    """Mask a GSTIN for secure UI display (e.g. 27AAPCA****1Z5)."""
    if not gstin or len(gstin) < 10:
        return gstin or "—"
    return f"{gstin[:7]}****{gstin[-3:]}"


def extract_state_code(gstin: str | None) -> str | None:
    """Extract the 2-digit State/UT code from a GSTIN string if available."""
    normalized = normalize_gstin(gstin)
    if normalized and len(normalized) >= 2 and normalized[:2].isdigit():
        return normalized[:2]
    return None


def match_supplier_gstin(
    invoice_gstin: str | None,
    trusted_gstin: str | None,
) -> tuple[dict[str, Any], GSTFinding | None]:
    """
    Compare invoice supplier GSTIN against trusted vendor master GSTIN.
    """
    norm_inv = normalize_gstin(invoice_gstin)
    norm_trusted = normalize_gstin(trusted_gstin)

    val_res = validate_gstin(norm_inv) if norm_inv else None

    if not norm_inv:
        finding = GSTFinding(
            finding_code="supplier_gstin_missing",
            severity=SEVERITY_HIGH,
            status=STATUS_MISSING,
            field_name="supplier_gstin",
            invoice_value=None,
            trusted_value=mask_gstin(norm_trusted),
            explanation="Invoice does not specify a supplier GSTIN.",
            recommended_action="Request a formal tax invoice containing the supplier's valid registered GSTIN.",
        )
        return {
            "status": STATUS_MISSING,
            "matched": False,
            "validation": val_res,
            "invoice_gstin": None,
            "trusted_gstin": norm_trusted,
        }, finding

    if not norm_trusted:
        finding = GSTFinding(
            finding_code="trusted_supplier_gstin_missing",
            severity=SEVERITY_MEDIUM,
            status=STATUS_MANUAL_REVIEW_REQUIRED,
            field_name="supplier_gstin",
            invoice_value=mask_gstin(norm_inv),
            trusted_value=None,
            explanation="The vendor record in the database has no registered GSTIN configured.",
            recommended_action="Verify vendor GST credentials and update vendor master record.",
        )
        return {
            "status": STATUS_MANUAL_REVIEW_REQUIRED,
            "matched": False,
            "validation": val_res,
            "invoice_gstin": norm_inv,
            "trusted_gstin": None,
        }, finding

    if not val_res or not val_res["is_valid"]:
        finding = GSTFinding(
            finding_code="supplier_gstin_format_invalid",
            severity=SEVERITY_HIGH,
            status=STATUS_MISMATCH,
            field_name="supplier_gstin",
            invoice_value=norm_inv,
            trusted_value=mask_gstin(norm_trusted),
            explanation=f"Supplier GSTIN fails structural validation: {val_res.get('message', 'Invalid format')}",
            recommended_action="Review invoice document to confirm supplier GSTIN correctness.",
        )
        return {
            "status": STATUS_MISMATCH,
            "matched": False,
            "validation": val_res,
            "invoice_gstin": norm_inv,
            "trusted_gstin": norm_trusted,
        }, finding

    if norm_inv == norm_trusted:
        finding = GSTFinding(
            finding_code="supplier_gstin_matched",
            severity=SEVERITY_LOW,
            status=STATUS_PASS,
            field_name="supplier_gstin",
            invoice_value=mask_gstin(norm_inv),
            trusted_value=mask_gstin(norm_trusted),
            explanation="Supplier GSTIN on invoice matches trusted vendor master record.",
            recommended_action="No action required.",
        )
        return {
            "status": STATUS_PASS,
            "matched": True,
            "validation": val_res,
            "invoice_gstin": norm_inv,
            "trusted_gstin": norm_trusted,
        }, finding

    finding = GSTFinding(
        finding_code="supplier_gstin_mismatch",
        severity=SEVERITY_HIGH,
        status=STATUS_MISMATCH,
        field_name="supplier_gstin",
        invoice_value=mask_gstin(norm_inv),
        trusted_value=mask_gstin(norm_trusted),
        explanation=(
            f"Invoice supplier GSTIN ({mask_gstin(norm_inv)}) does not match "
            f"the trusted vendor master GSTIN ({mask_gstin(norm_trusted)})."
        ),
        recommended_action="Hold invoice; investigate potential vendor identity discrepancy or branch mismatch.",
    )
    return {
        "status": STATUS_MISMATCH,
        "matched": False,
        "validation": val_res,
        "invoice_gstin": norm_inv,
        "trusted_gstin": norm_trusted,
    }, finding


def match_recipient_gstin(
    invoice_recipient_gstin: str | None,
    trusted_recipient_gstin: str | None,
    profile: str = GST_PROFILE_STANDARD_DOMESTIC,
) -> tuple[dict[str, Any], GSTFinding | None]:
    """
    Compare invoice recipient GSTIN against PO-configured recipient GSTIN.
    """
    norm_inv = normalize_gstin(invoice_recipient_gstin)
    norm_trusted = normalize_gstin(trusted_recipient_gstin)

    val_res = validate_gstin(norm_inv) if norm_inv else None

    # If the PO does not mandate an enterprise recipient GSTIN (e.g. unregistered buyer / B2C)
    if not norm_trusted:
        if norm_inv:
            finding = GSTFinding(
                finding_code="recipient_gstin_unconfigured_on_po",
                severity=SEVERITY_INFO,
                status=STATUS_PASS,
                field_name="recipient_gstin",
                invoice_value=mask_gstin(norm_inv),
                trusted_value=None,
                explanation="Invoice specifies a recipient GSTIN, but the purchase order has no recipient GSTIN requirement configured.",
                recommended_action="Confirm whether recipient GSTIN should be recorded on PO.",
            )
            return {
                "status": STATUS_PASS,
                "matched": True,
                "validation": val_res,
                "invoice_gstin": norm_inv,
                "trusted_gstin": None,
            }, finding

        # Both empty -> legitimately absent
        finding = GSTFinding(
            finding_code="recipient_gstin_not_required",
            severity=SEVERITY_INFO,
            status=STATUS_PASS,
            field_name="recipient_gstin",
            invoice_value=None,
            trusted_value=None,
            explanation="Purchase order does not mandate a registered recipient GSTIN.",
            recommended_action="No action required.",
        )
        return {
            "status": STATUS_PASS,
            "matched": True,
            "validation": None,
            "invoice_gstin": None,
            "trusted_gstin": None,
        }, finding

    # PO mandates a recipient GSTIN
    if not norm_inv:
        finding = GSTFinding(
            finding_code="recipient_gstin_missing",
            severity=SEVERITY_HIGH,
            status=STATUS_MISSING,
            field_name="recipient_gstin",
            invoice_value=None,
            trusted_value=mask_gstin(norm_trusted),
            explanation="Invoice is missing the buyer/recipient GSTIN mandated by the approved purchase order.",
            recommended_action="Hold invoice; request supplier reissue invoice with correct buyer GSTIN to claim Input Tax Credit (ITC).",
        )
        return {
            "status": STATUS_MISSING,
            "matched": False,
            "validation": None,
            "invoice_gstin": None,
            "trusted_gstin": norm_trusted,
        }, finding

    if not val_res or not val_res["is_valid"]:
        finding = GSTFinding(
            finding_code="recipient_gstin_format_invalid",
            severity=SEVERITY_HIGH,
            status=STATUS_MISMATCH,
            field_name="recipient_gstin",
            invoice_value=norm_inv,
            trusted_value=mask_gstin(norm_trusted),
            explanation=f"Recipient GSTIN fails structural validation: {val_res.get('message', 'Invalid format')}",
            recommended_action="Review invoice to confirm recipient GSTIN digits.",
        )
        return {
            "status": STATUS_MISMATCH,
            "matched": False,
            "validation": val_res,
            "invoice_gstin": norm_inv,
            "trusted_gstin": norm_trusted,
        }, finding

    if norm_inv == norm_trusted:
        finding = GSTFinding(
            finding_code="recipient_gstin_matched",
            severity=SEVERITY_LOW,
            status=STATUS_PASS,
            field_name="recipient_gstin",
            invoice_value=mask_gstin(norm_inv),
            trusted_value=mask_gstin(norm_trusted),
            explanation="Recipient GSTIN on invoice matches the buyer entity on the purchase order.",
            recommended_action="No action required.",
        )
        return {
            "status": STATUS_PASS,
            "matched": True,
            "validation": val_res,
            "invoice_gstin": norm_inv,
            "trusted_gstin": norm_trusted,
        }, finding

    finding = GSTFinding(
        finding_code="recipient_gstin_mismatch",
        severity=SEVERITY_HIGH,
        status=STATUS_MISMATCH,
        field_name="recipient_gstin",
        invoice_value=mask_gstin(norm_inv),
        trusted_value=mask_gstin(norm_trusted),
        explanation=(
            f"Invoice recipient GSTIN ({mask_gstin(norm_inv)}) does not match "
            f"the approved PO buyer GSTIN ({mask_gstin(norm_trusted)})."
        ),
        recommended_action="Hold invoice; incorrect buyer GSTIN prevents claiming Input Tax Credit (ITC).",
    )
    return {
        "status": STATUS_MISMATCH,
        "matched": False,
        "validation": val_res,
        "invoice_gstin": norm_inv,
        "trusted_gstin": norm_trusted,
    }, finding


def match_place_of_supply(
    invoice_pos_code: str | None,
    po_pos_code: str | None,
) -> tuple[dict[str, Any], GSTFinding | None]:
    """
    Compare invoice place of supply against PO-confirmed place of supply.
    """
    norm_inv_pos = invoice_pos_code.strip() if invoice_pos_code else None
    norm_po_pos = po_pos_code.strip() if po_pos_code else None

    # Pad single-digit state code if needed (e.g. '7' -> '07')
    if norm_inv_pos and len(norm_inv_pos) == 1 and norm_inv_pos.isdigit():
        norm_inv_pos = f"0{norm_inv_pos}"
    if norm_po_pos and len(norm_po_pos) == 1 and norm_po_pos.isdigit():
        norm_po_pos = f"0{norm_po_pos}"

    inv_state_name = STATE_CATALOGUE.get(norm_inv_pos, {}).get("name") if norm_inv_pos else None
    po_state_name = STATE_CATALOGUE.get(norm_po_pos, {}).get("name") if norm_po_pos else None

    if not norm_po_pos:
        finding = GSTFinding(
            finding_code="po_place_of_supply_missing",
            severity=SEVERITY_MEDIUM,
            status=STATUS_MANUAL_REVIEW_REQUIRED,
            field_name="place_of_supply_state_code",
            invoice_value=norm_inv_pos,
            trusted_value=None,
            explanation="Purchase order does not have a confirmed place-of-supply state code configured.",
            recommended_action="Finance reviewer must confirm delivery location and set PO place of supply.",
        )
        return {
            "status": STATUS_MANUAL_REVIEW_REQUIRED,
            "matched": False,
            "invoice_pos": norm_inv_pos,
            "po_pos": None,
        }, finding

    if not norm_inv_pos:
        finding = GSTFinding(
            finding_code="invoice_place_of_supply_missing",
            severity=SEVERITY_MEDIUM,
            status=STATUS_MISSING,
            field_name="place_of_supply_state_code",
            invoice_value=None,
            trusted_value=f"{norm_po_pos} ({po_state_name})" if po_state_name else norm_po_pos,
            explanation="Invoice does not specify the place of supply state code.",
            recommended_action="Hold invoice; rule 46 requires place of supply for inter-state and B2B invoices.",
        )
        return {
            "status": STATUS_MISSING,
            "matched": False,
            "invoice_pos": None,
            "po_pos": norm_po_pos,
        }, finding

    if norm_inv_pos == norm_po_pos:
        finding = GSTFinding(
            finding_code="place_of_supply_matched",
            severity=SEVERITY_LOW,
            status=STATUS_PASS,
            field_name="place_of_supply_state_code",
            invoice_value=f"{norm_inv_pos} ({inv_state_name})" if inv_state_name else norm_inv_pos,
            trusted_value=f"{norm_po_pos} ({po_state_name})" if po_state_name else norm_po_pos,
            explanation="Place of supply on invoice matches PO-confirmed delivery location.",
            recommended_action="No action required.",
        )
        return {
            "status": STATUS_PASS,
            "matched": True,
            "invoice_pos": norm_inv_pos,
            "po_pos": norm_po_pos,
        }, finding

    finding = GSTFinding(
        finding_code="place_of_supply_mismatch",
        severity=SEVERITY_HIGH,
        status=STATUS_MISMATCH,
        field_name="place_of_supply_state_code",
        invoice_value=f"{norm_inv_pos} ({inv_state_name})" if inv_state_name else norm_inv_pos,
        trusted_value=f"{norm_po_pos} ({po_state_name})" if po_state_name else norm_po_pos,
        explanation=(
            f"Invoice declared place of supply '{norm_inv_pos} ({inv_state_name})' differs "
            f"from PO-confirmed place of supply '{norm_po_pos} ({po_state_name})'."
        ),
        recommended_action="Hold invoice; place-of-supply discrepancy affects tax-type determination.",
    )
    return {
        "status": STATUS_MISMATCH,
        "matched": False,
        "invoice_pos": norm_inv_pos,
        "po_pos": norm_po_pos,
    }, finding


def classify_tax_type(
    supplier_state_code: str | None,
    po_pos_state_code: str | None,
    profile: str = GST_PROFILE_STANDARD_DOMESTIC,
) -> tuple[dict[str, Any], GSTFinding | None]:
    """
    Determine expected tax classification (Intra-State vs Inter-State) under supported profiles.
    - Intra-State: supplier_state == po_pos_state -> CGST + SGST (or CGST + UTGST for non-legislative UTs)
    - Inter-State: supplier_state != po_pos_state -> IGST
    """
    if profile == GST_PROFILE_SPECIAL_CASE_REVIEW:
        finding = GSTFinding(
            finding_code="special_case_profile_review_required",
            severity=SEVERITY_MEDIUM,
            status=STATUS_MANUAL_REVIEW_REQUIRED,
            field_name="gst_transaction_profile",
            invoice_value=None,
            trusted_value=profile,
            explanation="This purchase order is designated as SPECIAL_CASE_REVIEW. Complex legal GST treatment requires manual human assessment.",
            recommended_action="Perform manual tax review (e.g. SEZ, reverse charge, or high-seas sales).",
        )
        return {
            "status": STATUS_MANUAL_REVIEW_REQUIRED,
            "profile": profile,
            "tax_type": "SPECIAL_CASE",
            "expected_components": [],
            "explanation": "Special case profile requires manual legal review.",
        }, finding

    if profile == GST_PROFILE_NOT_CONFIGURED:
        finding = GSTFinding(
            finding_code="gst_profile_not_configured",
            severity=SEVERITY_MEDIUM,
            status=STATUS_MANUAL_REVIEW_REQUIRED,
            field_name="gst_transaction_profile",
            invoice_value=None,
            trusted_value=profile,
            explanation="GST transaction profile is NOT_CONFIGURED on this purchase order.",
            recommended_action="Configure PO GST profile as STANDARD_DOMESTIC or SPECIAL_CASE_REVIEW.",
        )
        return {
            "status": STATUS_MANUAL_REVIEW_REQUIRED,
            "profile": profile,
            "tax_type": "UNKNOWN",
            "expected_components": [],
            "explanation": "Profile not configured.",
        }, finding

    if not supplier_state_code or not po_pos_state_code:
        finding = GSTFinding(
            finding_code="tax_classification_inputs_missing",
            severity=SEVERITY_MEDIUM,
            status=STATUS_MANUAL_REVIEW_REQUIRED,
            field_name="tax_type",
            invoice_value=None,
            trusted_value=None,
            explanation="Supplier state code or place-of-supply state code is missing, preventing deterministic tax classification.",
            recommended_action="Ensure vendor master GSTIN and PO place of supply are populated.",
        )
        return {
            "status": STATUS_MANUAL_REVIEW_REQUIRED,
            "profile": profile,
            "tax_type": "UNKNOWN",
            "expected_components": [],
            "explanation": "Missing state codes.",
        }, finding

    supp_info = STATE_CATALOGUE.get(supplier_state_code)
    pos_info = STATE_CATALOGUE.get(po_pos_state_code)

    if not supp_info or not pos_info:
        finding = GSTFinding(
            finding_code="unrecognized_state_code_classification",
            severity=SEVERITY_HIGH,
            status=STATUS_MANUAL_REVIEW_REQUIRED,
            field_name="tax_type",
            invoice_value=None,
            trusted_value=f"Supplier: {supplier_state_code}, POS: {po_pos_state_code}",
            explanation="Supplier state or POS state is not found in the valid GST State/UT catalogue.",
            recommended_action="Verify state codes against official GST catalogue.",
        )
        return {
            "status": STATUS_MANUAL_REVIEW_REQUIRED,
            "profile": profile,
            "tax_type": "UNKNOWN",
            "expected_components": [],
            "explanation": "Unrecognized state code.",
        }, finding

    # Standard Domestic Logic:
    if supplier_state_code == po_pos_state_code:
        # Intra-State Supply
        ut_tax_type = pos_info["tax_type"]  # "SGST" or "UTGST"
        expected_components = ["CGST", ut_tax_type]
        explanation = (
            f"Intra-state supply within {pos_info['name']} ({po_pos_state_code}). "
            f"Requires CGST + {ut_tax_type} under Section 8 of the IGST Act."
        )
        return {
            "status": STATUS_PASS,
            "profile": profile,
            "tax_type": "INTRA_STATE",
            "state_tax_type": ut_tax_type,
            "expected_components": expected_components,
            "explanation": explanation,
        }, None

    # Inter-State Supply
    expected_components = ["IGST"]
    explanation = (
        f"Inter-state supply from {supp_info['name']} ({supplier_state_code}) "
        f"to {pos_info['name']} ({po_pos_state_code}). "
        f"Requires IGST under Section 7 of the IGST Act."
    )
    return {
        "status": STATUS_PASS,
        "profile": profile,
        "tax_type": "INTER_STATE",
        "state_tax_type": None,
        "expected_components": expected_components,
        "explanation": explanation,
    }, None


def validate_tax_components(
    invoice_components: dict[str, int],
    po_components: dict[str, int],
    classification: dict[str, Any],
) -> tuple[dict[str, Any], list[GSTFinding]]:
    """
    Validate tax component structure and compare against PO approved components.
    All monetary amounts must be in integer paise.
    Components checked: CGST, SGST, UTGST, IGST, Cess.
    """
    findings: list[GSTFinding] = []
    tax_type = classification.get("tax_type")
    expected_components = classification.get("expected_components", [])

    inv_cgst = invoice_components.get("cgst", 0)
    inv_sgst = invoice_components.get("sgst", 0)
    inv_utgst = invoice_components.get("utgst", 0)
    inv_igst = invoice_components.get("igst", 0)
    inv_cess = invoice_components.get("cess", 0)

    po_cgst = po_components.get("cgst", 0)
    po_sgst = po_components.get("sgst", 0)
    po_utgst = po_components.get("utgst", 0)
    po_igst = po_components.get("igst", 0)
    po_cess = po_components.get("cess", 0)

    # 1. Prohibited component checks
    if tax_type == "INTRA_STATE":
        if inv_igst > 0:
            findings.append(
                GSTFinding(
                    finding_code="prohibited_igst_on_intra_state",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISMATCH,
                    field_name="igst",
                    invoice_value=f"₹{from_paise(inv_igst):,.2f}",
                    trusted_value="₹0.00 (Intra-state)",
                    explanation="Invoice incorrectly charges IGST for an intra-state supply.",
                    recommended_action="Hold invoice; request supplier reissue invoice with CGST and SGST/UTGST.",
                )
            )

        if "SGST" in expected_components and inv_utgst > 0:
            findings.append(
                GSTFinding(
                    finding_code="invalid_utgst_charged_in_state",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISMATCH,
                    field_name="utgst",
                    invoice_value=f"₹{from_paise(inv_utgst):,.2f}",
                    trusted_value="₹0.00 (State levies SGST)",
                    explanation="Invoice charges UTGST in a State or Union Territory with a legislature (which levies SGST).",
                    recommended_action="Hold invoice; replace UTGST with SGST.",
                )
            )

        if "UTGST" in expected_components and inv_sgst > 0:
            findings.append(
                GSTFinding(
                    finding_code="invalid_sgst_charged_in_ut",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISMATCH,
                    field_name="sgst",
                    invoice_value=f"₹{from_paise(inv_sgst):,.2f}",
                    trusted_value="₹0.00 (UT levies UTGST)",
                    explanation="Invoice charges SGST in a Union Territory without a legislature (which levies UTGST under the UTGST Act).",
                    recommended_action="Hold invoice; replace SGST with UTGST.",
                )
            )

        if inv_sgst > 0 and inv_utgst > 0:
            findings.append(
                GSTFinding(
                    finding_code="combined_sgst_utgst_unsupported",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISMATCH,
                    field_name="sgst_utgst",
                    invoice_value=f"SGST: ₹{from_paise(inv_sgst):,.2f}, UTGST: ₹{from_paise(inv_utgst):,.2f}",
                    trusted_value="Only one of SGST or UTGST permitted per supply",
                    explanation="Invoice simultaneously charges both SGST and UTGST for the same transaction.",
                    recommended_action="Hold invoice; a single transaction cannot attract both SGST and UTGST.",
                )
            )

    elif tax_type == "INTER_STATE":
        if inv_cgst > 0 or inv_sgst > 0 or inv_utgst > 0:
            findings.append(
                GSTFinding(
                    finding_code="prohibited_intra_tax_on_inter_state",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISMATCH,
                    field_name="cgst_sgst_on_interstate",
                    invoice_value=(
                        f"CGST: ₹{from_paise(inv_cgst):,.2f}, SGST: ₹{from_paise(inv_sgst):,.2f}, "
                        f"UTGST: ₹{from_paise(inv_utgst):,.2f}"
                    ),
                    trusted_value="₹0.00 (Inter-state requires IGST)",
                    explanation="Invoice charges intra-state taxes (CGST/SGST/UTGST) on an inter-state supply.",
                    recommended_action="Hold invoice; inter-state supplies require IGST under Section 7 of the IGST Act.",
                )
            )

    # 2. Missing mandatory components (when PO has approved amounts)
    for comp in expected_components:
        if comp == "CGST" and po_cgst > 0 and inv_cgst == 0:
            findings.append(
                GSTFinding(
                    finding_code="missing_mandatory_cgst",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISSING,
                    field_name="cgst",
                    invoice_value="₹0.00",
                    trusted_value=f"₹{from_paise(po_cgst):,.2f}",
                    explanation="Invoice does not specify CGST, which is required for this intra-state supply.",
                    recommended_action="Hold invoice; request supplier include CGST breakdown.",
                )
            )
        elif comp == "SGST" and po_sgst > 0 and inv_sgst == 0:
            findings.append(
                GSTFinding(
                    finding_code="missing_mandatory_sgst",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISSING,
                    field_name="sgst",
                    invoice_value="₹0.00",
                    trusted_value=f"₹{from_paise(po_sgst):,.2f}",
                    explanation="Invoice does not specify SGST, which is required for this intra-state supply.",
                    recommended_action="Hold invoice; request supplier include SGST breakdown.",
                )
            )
        elif comp == "UTGST" and po_utgst > 0 and inv_utgst == 0:
            findings.append(
                GSTFinding(
                    finding_code="missing_mandatory_utgst",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISSING,
                    field_name="utgst",
                    invoice_value="₹0.00",
                    trusted_value=f"₹{from_paise(po_utgst):,.2f}",
                    explanation="Invoice does not specify UTGST, which is required for this supply within a Union Territory.",
                    recommended_action="Hold invoice; request supplier include UTGST breakdown.",
                )
            )
        elif comp == "IGST" and po_igst > 0 and inv_igst == 0:
            findings.append(
                GSTFinding(
                    finding_code="missing_mandatory_igst",
                    severity=SEVERITY_HIGH,
                    status=STATUS_MISSING,
                    field_name="igst",
                    invoice_value="₹0.00",
                    trusted_value=f"₹{from_paise(po_igst):,.2f}",
                    explanation="Invoice does not specify IGST, which is required for this inter-state supply.",
                    recommended_action="Hold invoice; request supplier include IGST breakdown.",
                )
            )

    # 3. Variance comparisons against PO approved component amounts
    components_to_check = [
        ("cgst", "CGST", inv_cgst, po_cgst),
        ("sgst", "SGST", inv_sgst, po_sgst),
        ("utgst", "UTGST", inv_utgst, po_utgst),
        ("igst", "IGST", inv_igst, po_igst),
        ("cess", "Cess", inv_cess, po_cess),
    ]

    for comp_key, comp_label, inv_amt, po_amt in components_to_check:
        if po_amt > 0 or inv_amt > 0:
            variance = inv_amt - po_amt
            if variance != 0:
                direction = "exceeds" if variance > 0 else "is less than"
                diff_str = f"₹{from_paise(abs(variance)):,.2f}"
                findings.append(
                    GSTFinding(
                        finding_code=f"{comp_key}_component_variance",
                        severity=SEVERITY_MEDIUM,
                        status=STATUS_MISMATCH,
                        field_name=comp_key,
                        invoice_value=f"₹{from_paise(inv_amt):,.2f}",
                        trusted_value=f"₹{from_paise(po_amt):,.2f}",
                        explanation=f"Invoice {comp_label} ({f'₹{from_paise(inv_amt):,.2f}'}) {direction} approved PO {comp_label} by {diff_str}.",
                        recommended_action=f"Reconcile {comp_label} component with purchase order agreement.",
                    )
                )

    result_summary = {
        "invoice_components": {k: float(from_paise(v)) for k, v in invoice_components.items()},
        "po_components": {k: float(from_paise(v)) for k, v in po_components.items()},
        "findings_count": len(findings),
        "status": STATUS_MISMATCH if findings else STATUS_PASS,
    }
    return result_summary, findings


def reconcile_gst_totals(
    declared_total_gst_paise: int,
    invoice_components: dict[str, int],
    tolerance_paise: int = GST_SUM_TOLERANCE_PAISE,
) -> tuple[dict[str, Any], GSTFinding | None]:
    """
    Verify that CGST + SGST + UTGST + IGST + Cess sums to the invoice declared total GST,
    subject to an explicit documented rounding tolerance.
    """
    component_sum = sum(invoice_components.values())
    variance = component_sum - declared_total_gst_paise

    if abs(variance) == 0:
        return {
            "status": STATUS_PASS,
            "component_sum_paise": component_sum,
            "declared_total_paise": declared_total_gst_paise,
            "variance_paise": 0,
            "within_tolerance": True,
        }, None

    if abs(variance) <= tolerance_paise:
        # Small rounding discrepancy (e.g. fractional paise round-off)
        finding = GSTFinding(
            finding_code="gst_total_rounding_tolerance",
            severity=SEVERITY_INFO,
            status=STATUS_PASS,
            field_name="gst_amount",
            invoice_value=f"₹{from_paise(declared_total_gst_paise):,.2f}",
            trusted_value=f"₹{from_paise(component_sum):,.2f}",
            explanation=(
                f"Minor component sum rounding difference of ₹{from_paise(abs(variance)):,.2f} "
                f"is within the accepted threshold of ₹{from_paise(tolerance_paise):,.2f}."
            ),
            recommended_action="No action required; minor round-off accepted.",
        )
        return {
            "status": STATUS_PASS,
            "component_sum_paise": component_sum,
            "declared_total_paise": declared_total_gst_paise,
            "variance_paise": variance,
            "within_tolerance": True,
        }, finding

    # Unacceptable discrepancy
    diff_str = f"₹{from_paise(abs(variance)):,.2f}"
    direction = "exceeds" if variance > 0 else "is less than"
    finding = GSTFinding(
        finding_code="gst_component_sum_mismatch",
        severity=SEVERITY_HIGH,
        status=STATUS_MISMATCH,
        field_name="gst_amount",
        invoice_value=f"₹{from_paise(declared_total_gst_paise):,.2f}",
        trusted_value=f"₹{from_paise(component_sum):,.2f}",
        explanation=(
            f"The sum of invoice tax components (₹{from_paise(component_sum):,.2f}) {direction} "
            f"the declared total GST amount (₹{from_paise(declared_total_gst_paise):,.2f}) by {diff_str}."
        ),
        recommended_action="Hold invoice; arithmetic inconsistency between tax components and total tax.",
    )
    return {
        "status": STATUS_MISMATCH,
        "component_sum_paise": component_sum,
        "declared_total_paise": declared_total_gst_paise,
        "variance_paise": variance,
        "within_tolerance": False,
    }, finding


def evaluate_gst_integrity(
    *,
    invoice_supplier_gstin: str | None,
    trusted_supplier_gstin: str | None,
    invoice_recipient_gstin: str | None,
    trusted_recipient_gstin: str | None,
    invoice_pos_code: str | None,
    po_pos_code: str | None,
    gst_profile: str = GST_PROFILE_STANDARD_DOMESTIC,
    invoice_components: dict[str, int],
    po_components: dict[str, int],
    declared_total_gst_paise: int,
) -> GSTIntegrityReport:
    """
    Run the end-to-end GST integrity evaluation pipeline.
    Combines GSTIN validation, vendor matching, place of supply, classification,
    component checks, and total reconciliation into a unified audit report.
    """
    all_findings: list[GSTFinding] = []

    # 1. Supplier GSTIN match and structure
    supp_res, supp_finding = match_supplier_gstin(invoice_supplier_gstin, trusted_supplier_gstin)
    if supp_finding:
        all_findings.append(supp_finding)

    # 2. Recipient GSTIN match and structure
    recip_res, recip_finding = match_recipient_gstin(
        invoice_recipient_gstin, trusted_recipient_gstin, profile=gst_profile
    )
    if recip_finding:
        all_findings.append(recip_finding)

    # 3. Place of supply match
    pos_res, pos_finding = match_place_of_supply(invoice_pos_code, po_pos_code)
    if pos_finding:
        all_findings.append(pos_finding)

    # 4. Tax-type classification
    supp_state = extract_state_code(trusted_supplier_gstin) or extract_state_code(invoice_supplier_gstin)
    class_res, class_finding = classify_tax_type(supp_state, po_pos_code, profile=gst_profile)
    if class_finding:
        all_findings.append(class_finding)

    # 5. Component breakdown validation
    comp_res, comp_findings = validate_tax_components(invoice_components, po_components, class_res)
    all_findings.extend(comp_findings)

    # 6. Total GST reconciliation
    # Note: Only reconcile if invoice components are provided (i.e. at least one non-zero component)
    has_any_invoice_components = any(v > 0 for v in invoice_components.values())
    if has_any_invoice_components:
        recon_res, recon_finding = reconcile_gst_totals(declared_total_gst_paise, invoice_components)
        if recon_finding:
            all_findings.append(recon_finding)
    else:
        # If PO expects tax components, but invoice provided 0 components
        has_any_po_components = any(v > 0 for v in po_components.values())
        if has_any_po_components and declared_total_gst_paise > 0:
            all_findings.append(
                GSTFinding(
                    finding_code="tax_components_missing",
                    severity=SEVERITY_MEDIUM,
                    status=STATUS_MISSING,
                    field_name="tax_components",
                    invoice_value="Not itemized",
                    trusted_value="Itemized components expected",
                    explanation="Invoice provides total GST without itemizing CGST, SGST/UTGST, or IGST components.",
                    recommended_action="Request itemized tax breakdown from supplier.",
                )
            )
        recon_res = {
            "status": STATUS_NOT_EVALUATED,
            "component_sum_paise": 0,
            "declared_total_paise": declared_total_gst_paise,
            "variance_paise": 0,
            "within_tolerance": True,
        }

    # Evaluate overall decision flags
    requires_hold = False
    requires_manual_review = False

    for f in all_findings:
        if f.severity == SEVERITY_HIGH:
            requires_hold = True
        elif f.status in (STATUS_MISMATCH, STATUS_MISSING):
            requires_hold = True
        elif f.status == STATUS_MANUAL_REVIEW_REQUIRED:
            requires_manual_review = True

    # If manual review required, invoice must be held
    if requires_manual_review:
        requires_hold = True

    overall_status = STATUS_PASS
    if requires_hold:
        overall_status = STATUS_MISMATCH if any(f.status == STATUS_MISMATCH for f in all_findings) else STATUS_MANUAL_REVIEW_REQUIRED

    return GSTIntegrityReport(
        supplier_gstin_result=supp_res,
        recipient_gstin_result=recip_res,
        place_of_supply_result=pos_res,
        tax_classification_result=class_res,
        component_reconciliation_result=recon_res,
        findings=all_findings,
        overall_status=overall_status,
        requires_hold=requires_hold,
        requires_manual_review=requires_manual_review,
    )
