from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InvoiceVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_number: str = Field(min_length=1, max_length=128)
    vendor_name: str = Field(min_length=1, max_length=256)
    po_number: str = Field(min_length=1, max_length=128)
    invoice_total: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    gst_amount: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    line_items: int = Field(ge=1, le=1_000_000, strict=True)
    invoice_bank_account_ref: str | None = Field(
        default=None,
        max_length=128,
        description=(
            "Internal synthetic reference for matching only; this does not verify "
            "bank-account ownership."
        ),
    )
    supplier_gstin: str | None = Field(
        default=None,
        max_length=15,
        description="Declared supplier GSTIN on invoice.",
    )
    recipient_gstin: str | None = Field(
        default=None,
        max_length=15,
        description="Declared buyer/recipient GSTIN on invoice.",
    )
    place_of_supply_state_code: str | None = Field(
        default=None,
        max_length=128,
        description="Place of supply state code or recognized state name (e.g. '27' or 'Maharashtra').",
    )
    cgst_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    sgst_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    utgst_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    igst_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    cess_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)

    @field_validator("invoice_number", "vendor_name", "po_number")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This value must not be blank.")
        return normalized

    @field_validator("invoice_bank_account_ref", "supplier_gstin", "recipient_gstin", "place_of_supply_state_code")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("invoice_total", "gst_amount", "cgst_amount", "sgst_amount", "utgst_amount", "igst_amount", "cess_amount")
    @classmethod
    def require_paise_precision(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite():
            raise ValueError("Money amounts must be finite.")
        if value.as_tuple().exponent < -2:
            raise ValueError("Money amounts may have no more than two decimal places.")
        return value

    @model_validator(mode="after")
    def gst_must_not_exceed_invoice_total(self) -> "InvoiceVerificationRequest":
        if self.gst_amount > self.invoice_total:
            raise ValueError(
                f"gst_amount ({self.gst_amount}) cannot exceed invoice_total ({self.invoice_total})."
            )
        return self


class VerificationFinding(BaseModel):
    code: str
    title: str
    detail: str
    level: str


class InvoiceVerificationResponse(BaseModel):
    decision: str
    status: str = ""
    risk_level: str
    findings: list[VerificationFinding]
    invoice_id: int | None = None
    audit_event_id: int | None = None
    duplicate_of_invoice_id: int | None = None
    duplicate: bool = False
    po_number: str
    vendor_id: int | None = None
    vendor_code: str | None = None
    vendor_name: str | None = None
    invoice_number: str
    invoice_total: float
    gst_amount: float
    line_items: int
    approved_total: float | None = None
    approved_gst: float | None = None
    approved_line_items: int | None = None
    variance: dict[str, float | int | None] = Field(default_factory=dict)
    # GST Integrity fields
    supplier_gstin: str | None = None
    recipient_gstin: str | None = None
    place_of_supply_state_code: str | None = None
    gst_checks: dict[str, Any] | None = None


class VendorRead(BaseModel):
    id: int
    vendor_code: str
    name: str
    bank_account_ref: str
    is_active: bool
    gstin: str | None = None
    gstin_verification_status: str = "NOT_VERIFIED"
    created_at: str


class PurchaseOrderRead(BaseModel):
    id: int
    po_number: str
    vendor_id: int
    vendor_code: str
    vendor_name: str
    approved_total_paise: int
    approved_gst_paise: int
    approved_line_items: int
    status: str
    issue_date: str
    recipient_gstin: str | None = None
    place_of_supply_state_code: str | None = None
    gst_transaction_profile: str = "STANDARD_DOMESTIC"
    approved_cgst_paise: int = 0
    approved_sgst_paise: int = 0
    approved_utgst_paise: int = 0
    approved_igst_paise: int = 0
    approved_cess_paise: int = 0
    created_at: str


class InvoiceRead(BaseModel):
    id: int
    invoice_number: str
    normalized_invoice_number: str
    vendor_id: int
    po_id: int | None
    invoice_total_paise: int
    gst_amount_paise: int
    line_items: int
    invoice_bank_account_ref: str | None
    decision: str | None
    risk_level: str | None
    supplier_gstin: str | None = None
    recipient_gstin: str | None = None
    place_of_supply_state_code: str | None = None
    cgst_paise: int = 0
    sgst_paise: int = 0
    utgst_paise: int = 0
    igst_paise: int = 0
    cess_paise: int = 0
    gst_validation_status: str | None = None
    created_at: str


class AuditEventRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int | None
    event_type: str
    decision: str | None
    reason: str | None
    created_at: str


class ExtractedField(BaseModel):
    field: str
    value: str | int | None = None
    page_number: int | None = None
    evidence_quote: str | None = None
    confidence: float = 0.0
    evidence_verified: bool = False
    warning: str | None = None


class DocumentPage(BaseModel):
    page_number: int
    text: str
    ocr_applied: bool = False


class DocumentExtractionResponse(BaseModel):
    filename: str
    file_type: str
    page_count: int
    pages: list[DocumentPage]
    raw_text: str
    ocr_applied: bool
    ocr_engine: str | None = None
    ai_extraction_available: bool
    ai_model: str | None = None
    fields: dict[str, ExtractedField]
    suspicious_content_detected: bool = False
    suspicious_warnings: list[str] = Field(default_factory=list)
    processing_warnings: list[str] = Field(default_factory=list)

