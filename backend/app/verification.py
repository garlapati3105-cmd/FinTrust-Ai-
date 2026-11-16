from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any

from .database import get_connection
from .financial import from_paise, normalize_invoice_number, to_paise
from .schemas import InvoiceVerificationRequest

HIGH_RISK_AMOUNT_VARIANCE_PAISE = to_paise(Decimal("50000"))


def _normalize_vendor_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _normalize_account_ref(value: str | None) -> str | None:
    return value.strip().upper() if value and value.strip() else None


def _append_audit_event(
    connection: sqlite3.Connection,
    *,
    entity_id: int | None,
    event_type: str,
    decision: str,
    reason: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO audit_events (
            entity_type, entity_id, event_type, decision, reason, created_at
        )
        VALUES ('invoice', ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            event_type,
            decision,
            reason,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    return int(cursor.lastrowid)


def _hold_response(
    payload: InvoiceVerificationRequest,
    *,
    finding: dict[str, str],
    risk_level: str = "high",
    po_number: str | None = None,
    audit_event_id: int | None = None,
    decision: str = "HOLD",
) -> dict[str, Any]:
    return {
        "decision": decision,
        "status": "Review required",
        "risk_level": risk_level,
        "findings": [finding],
        "invoice_id": None,
        "audit_event_id": audit_event_id,
        "duplicate_of_invoice_id": None,
        "duplicate": False,
        "po_number": po_number or payload.po_number,
        "vendor_id": None,
        "vendor_code": None,
        "vendor_name": None,
        "invoice_number": payload.invoice_number,
        "invoice_total": float(payload.invoice_total),
        "gst_amount": float(payload.gst_amount),
        "line_items": payload.line_items,
        "approved_total": None,
        "approved_gst": None,
        "approved_line_items": None,
        "variance": {"amount": None, "gst": None, "line_items": None},
    }


def _evaluate(
    payload: InvoiceVerificationRequest,
    po: sqlite3.Row,
) -> tuple[list[dict[str, str]], str, dict[str, int]]:
    findings: list[dict[str, str]] = []
    high_risk = False

    if not po["vendor_id"]:
        findings.append({
            "code": "vendor_record_missing",
            "title": "Trusted vendor unavailable",
            "detail": "The purchase order has no associated vendor record; manual review is required.",
            "level": "high",
        })
        return findings, "high", {"amount": 0, "gst": 0, "line_items": 0}

    if not po["is_active"]:
        high_risk = True
        findings.append({
            "code": "vendor_inactive",
            "title": "Vendor inactive",
            "detail": "The vendor linked to this purchase order is inactive; approval is not permitted.",
            "level": "high",
        })

    if _normalize_vendor_name(payload.vendor_name) != _normalize_vendor_name(po["vendor_name"]):
        findings.append({
            "code": "vendor_mismatch",
            "title": "Vendor identity mismatch",
            "detail": f"Invoice vendor does not match the vendor on the selected PO ({po['vendor_name']}).",
            "level": "medium",
        })

    invoice_total_paise = to_paise(payload.invoice_total)
    gst_amount_paise = to_paise(payload.gst_amount)
    amount_variance = invoice_total_paise - po["approved_total_paise"]
    gst_variance = gst_amount_paise - po["approved_gst_paise"]
    item_variance = payload.line_items - po["approved_line_items"]

    if amount_variance:
        if amount_variance > HIGH_RISK_AMOUNT_VARIANCE_PAISE:
            high_risk = True
        amount = from_paise(abs(amount_variance))
        direction = "exceeds" if amount_variance > 0 else "is less than"
        detail = (
            f"Invoice total {direction} the approved PO by ₹{amount:,.2f}."
            if amount_variance > 0
            else f"Invoice total is ₹{amount:,.2f} less than the approved PO."
        )
        findings.append({
            "code": "amount_mismatch",
            "title": "Amount mismatch",
            "detail": detail,
            "level": "high" if amount_variance > HIGH_RISK_AMOUNT_VARIANCE_PAISE else "medium",
        })

    if gst_variance:
        gst = from_paise(abs(gst_variance))
        findings.append({
            "code": "gst_mismatch",
            "title": "GST mismatch",
            "detail": f"Invoice GST differs from the approved PO GST by ₹{gst:,.2f}.",
            "level": "medium",
        })

    if item_variance:
        item_detail = (
            f"Invoice contains {item_variance} more line item(s) than the approved PO."
            if item_variance > 0
            else f"Invoice contains {abs(item_variance)} fewer line item(s) than the approved PO."
        )
        findings.append({
            "code": "line_items_mismatch",
            "title": "Line-item mismatch",
            "detail": item_detail,
            "level": "medium",
        })

    submitted_ref = _normalize_account_ref(payload.invoice_bank_account_ref)
    trusted_ref = _normalize_account_ref(po["bank_account_ref"])
    if submitted_ref is None:
        findings.append({
            "code": "bank_reference_missing",
            "title": "Account reference missing",
            "detail": "Invoice did not provide an internal account reference; human review is required.",
            "level": "medium",
        })
    elif submitted_ref != trusted_ref:
        findings.append({
            "code": "bank_reference_mismatch",
            "title": "Account reference mismatch",
            "detail": "Invoice account reference differs from the trusted internal vendor reference. This comparison does not verify account ownership.",
            "level": "medium",
        })

    if po["status"].casefold() != "approved":
        high_risk = True
        findings.append({
            "code": "purchase_order_not_approved",
            "title": "Purchase order not approved",
            "detail": f"The selected PO status is '{po['status']}', not approved.",
            "level": "high",
        })

    risk_level = "high" if high_risk else ("medium" if findings else "low")
    variance = {
        "amount": amount_variance,
        "gst": gst_variance,
        "line_items": item_variance,
    }
    return findings, risk_level, variance


def _format_response(
    payload: InvoiceVerificationRequest,
    *,
    decision: str,
    risk_level: str,
    findings: list[dict[str, str]],
    po: sqlite3.Row | None,
    invoice_id: int | None = None,
    audit_event_id: int | None = None,
    duplicate_of_invoice_id: int | None = None,
    duplicate: bool = False,
    variance: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "decision": decision,
        "status": "Approved" if decision == "APPROVE" else "Review required",
        "risk_level": risk_level,
        "findings": findings,
        "invoice_id": invoice_id,
        "audit_event_id": audit_event_id,
        "duplicate_of_invoice_id": duplicate_of_invoice_id,
        "duplicate": duplicate,
        "po_number": payload.po_number,
        "vendor_id": po["vendor_id"] if po is not None else None,
        "vendor_code": po["vendor_code"] if po is not None else None,
        "vendor_name": po["vendor_name"] if po is not None else None,
        "invoice_number": payload.invoice_number,
        "invoice_total": float(payload.invoice_total),
        "gst_amount": float(payload.gst_amount),
        "line_items": payload.line_items,
        "approved_total": (
            float(from_paise(po["approved_total_paise"])) if po is not None else None
        ),
        "approved_gst": float(from_paise(po["approved_gst_paise"])) if po is not None else None,
        "approved_line_items": po["approved_line_items"] if po is not None else None,
        "variance": (
            {
                "amount": float(from_paise(variance["amount"])),
                "gst": float(from_paise(variance["gst"])),
                "line_items": variance["line_items"],
            }
            if variance is not None
            else {"amount": None, "gst": None, "line_items": None}
        ),
    }


def verify_and_record_invoice(payload: InvoiceVerificationRequest) -> dict[str, Any]:
    normalized_number = normalize_invoice_number(payload.invoice_number)

    try:
        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            po = connection.execute(
                """
                SELECT
                    po.id AS po_id,
                    po.po_number,
                    po.vendor_id,
                    po.approved_total_paise,
                    po.approved_gst_paise,
                    po.approved_line_items,
                    po.status,
                    v.vendor_code,
                    v.name AS vendor_name,
                    v.bank_account_ref,
                    v.is_active
                FROM purchase_orders AS po
                LEFT JOIN vendors AS v ON v.id = po.vendor_id
                WHERE po.po_number = ?
                """,
                (payload.po_number,),
            ).fetchone()

            if po is None:
                finding = {
                    "code": "purchase_order_not_found",
                    "title": "Purchase order not found",
                    "detail": "No trusted purchase order matches this reference; manual review is required.",
                    "level": "high",
                }
                audit_event_id = _append_audit_event(
                    connection,
                    entity_id=None,
                    event_type="invoice_verification_held",
                    decision="HOLD",
                    reason=finding["detail"],
                )
                return _hold_response(
                    payload, finding=finding, audit_event_id=audit_event_id
                )

            if po["vendor_id"] is None or po["vendor_name"] is None:
                finding = {
                    "code": "vendor_record_missing",
                    "title": "Trusted vendor unavailable",
                    "detail": "The purchase order has no associated vendor record; manual review is required.",
                    "level": "high",
                }
                audit_event_id = _append_audit_event(
                    connection,
                    entity_id=None,
                    event_type="invoice_verification_held",
                    decision="HOLD",
                    reason=finding["detail"],
                )
                return _hold_response(
                    payload,
                    finding=finding,
                    po_number=po["po_number"],
                    audit_event_id=audit_event_id,
                )

            existing = connection.execute(
                """
                SELECT id
                FROM invoices
                WHERE vendor_id = ? AND normalized_invoice_number = ?
                """,
                (po["vendor_id"], normalized_number),
            ).fetchone()

            if existing is not None:
                reason = (
                    "Duplicate invoice submission; original invoice record "
                    f"{existing['id']} was retained."
                )
                audit_event_id = _append_audit_event(
                    connection,
                    entity_id=existing["id"],
                    event_type="duplicate_invoice_submission",
                    decision="HOLD",
                    reason=reason,
                )
                finding = {
                    "code": "duplicate_invoice",
                    "title": "Duplicate invoice",
                    "detail": reason,
                    "level": "medium",
                }
                return _format_response(
                    payload,
                    decision="HOLD",
                    risk_level="medium",
                    findings=[finding],
                    po=po,
                    invoice_id=existing["id"],
                    audit_event_id=audit_event_id,
                    duplicate_of_invoice_id=existing["id"],
                    duplicate=True,
                )

            findings, risk_level, variance = _evaluate(payload, po)
            decision = "HOLD" if findings else "APPROVE"
            cursor = connection.execute(
                """
                INSERT INTO invoices (
                    invoice_number,
                    normalized_invoice_number,
                    vendor_id,
                    po_id,
                    invoice_total_paise,
                    gst_amount_paise,
                    line_items,
                    invoice_bank_account_ref,
                    decision,
                    risk_level,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.invoice_number,
                    normalized_number,
                    po["vendor_id"],
                    po["po_id"],
                    to_paise(payload.invoice_total),
                    to_paise(payload.gst_amount),
                    payload.line_items,
                    payload.invoice_bank_account_ref,
                    decision,
                    risk_level,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            invoice_id = int(cursor.lastrowid)
            reason = (
                "All configured evidence checks matched internal records."
                if decision == "APPROVE"
                else "; ".join(finding["title"] for finding in findings)
            )
            audit_event_id = _append_audit_event(
                connection,
                entity_id=invoice_id,
                event_type="invoice_verified",
                decision=decision,
                reason=reason,
            )
            return _format_response(
                payload,
                decision=decision,
                risk_level=risk_level,
                findings=findings,
                po=po,
                invoice_id=invoice_id,
                audit_event_id=audit_event_id,
                variance=variance,
            )
    except sqlite3.IntegrityError:
        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            po = connection.execute(
                "SELECT vendor_id FROM purchase_orders WHERE po_number = ?",
                (payload.po_number,),
            ).fetchone()
            if po is None:
                raise
            existing = connection.execute(
                """
                SELECT id
                FROM invoices
                WHERE vendor_id = ? AND normalized_invoice_number = ?
                """,
                (po["vendor_id"], normalized_number),
            ).fetchone()
            if existing is None:
                raise

            reason = (
                "Duplicate invoice submission; original invoice record "
                f"{existing['id']} was retained."
            )
            audit_event_id = _append_audit_event(
                connection,
                entity_id=existing["id"],
                event_type="duplicate_invoice_submission",
                decision="HOLD",
                reason=reason,
            )
            stored_po = connection.execute(
                """
                SELECT
                    po.id AS po_id, po.po_number, po.vendor_id,
                    po.approved_total_paise, po.approved_gst_paise,
                    po.approved_line_items, po.status, v.vendor_code,
                    v.name AS vendor_name, v.bank_account_ref, v.is_active
                FROM purchase_orders AS po
                JOIN vendors AS v ON v.id = po.vendor_id
                WHERE po.po_number = ?
                """,
                (payload.po_number,),
            ).fetchone()
            finding = {
                "code": "duplicate_invoice",
                "title": "Duplicate invoice",
                "detail": reason,
                "level": "medium",
            }
            return _format_response(
                payload,
                decision="HOLD",
                risk_level="medium",
                findings=[finding],
                po=stored_po,
                invoice_id=existing["id"],
                audit_event_id=audit_event_id,
                duplicate_of_invoice_id=existing["id"],
                duplicate=True,
            )
