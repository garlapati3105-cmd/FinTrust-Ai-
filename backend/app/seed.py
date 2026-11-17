from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .database import get_connection
from .financial import to_paise

# Synthetic Demonstration GST fixtures (Fictional demonstration entities only)
VENDORS = (
    ("VND-1001", "Aster Office Supplies", "DEMO-ACCT-1001", "27AAPCA1234A1Z5"),  # SYNTHETIC DEMO DATA (MH)
    ("VND-1002", "BluePeak Technologies", "DEMO-ACCT-1002", "29ABCDE1234F1ZW"),  # SYNTHETIC DEMO DATA (KA)
    ("VND-1003", "GreenField Logistics", "DEMO-ACCT-1003", "04AAACG1234D1ZG"),   # SYNTHETIC DEMO DATA (CH)
)

# Buyer entity synthetic GSTIN (Maharashtra): 27AABCF1234F1Z4 (SYNTHETIC DEMO DATA)
DEFAULT_RECIPIENT_GSTIN = "27AABCF1234F1Z4"

PURCHASE_ORDERS = (
    # PO-1001: Intra-state MH -> MH (CGST: ₹6,483.05 + SGST: ₹6,483.05 = ₹12,966.10)
    (
        "PO-1001",
        "VND-1001",
        Decimal("85000.00"),
        Decimal("12966.10"),
        5,
        "2026-10-28",
        DEFAULT_RECIPIENT_GSTIN,
        "27",
        "STANDARD_DOMESTIC",
        648305,  # approved_cgst_paise
        648305,  # approved_sgst_paise
        0,       # approved_utgst_paise
        0,       # approved_igst_paise
        0,       # approved_cess_paise
    ),
    # PO-1002: Inter-state KA -> MH (IGST: ₹18,305.08)
    (
        "PO-1002",
        "VND-1002",
        Decimal("120000.00"),
        Decimal("18305.08"),
        8,
        "2026-11-02",
        DEFAULT_RECIPIENT_GSTIN,
        "27",
        "STANDARD_DOMESTIC",
        0,       # approved_cgst_paise
        0,       # approved_sgst_paise
        0,       # approved_utgst_paise
        1830508, # approved_igst_paise
        0,       # approved_cess_paise
    ),
    # PO-1003: Intra-UT CH -> CH (CGST: ₹3,546.61 + UTGST: ₹3,546.61 = ₹7,093.22)
    (
        "PO-1003",
        "VND-1003",
        Decimal("46500.00"),
        Decimal("7093.22"),
        4,
        "2026-11-05",
        DEFAULT_RECIPIENT_GSTIN,
        "04",
        "STANDARD_DOMESTIC",
        354661,  # approved_cgst_paise
        0,       # approved_sgst_paise
        354661,  # approved_utgst_paise
        0,       # approved_igst_paise
        0,       # approved_cess_paise
    ),
)


def seed_database(db_path: str | Path | None = None) -> dict[str, int]:
    inserted_vendors = 0
    inserted_purchase_orders = 0
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with get_connection(db_path) as connection:
        for vendor_code, name, bank_account_ref, gstin in VENDORS:
            existing = connection.execute(
                "SELECT id, gstin FROM vendors WHERE vendor_code = ?",
                (vendor_code,),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO vendors (vendor_code, name, bank_account_ref, is_active, gstin, gstin_verification_status, created_at)
                    VALUES (?, ?, ?, 1, ?, 'SYNTHETIC_VERIFIED', ?)
                    """,
                    (vendor_code, name, bank_account_ref, gstin, created_at),
                )
                inserted_vendors += 1
            elif not existing["gstin"]:
                # Idempotently populate GSTIN on existing seed records
                connection.execute(
                    "UPDATE vendors SET gstin = ?, gstin_verification_status = 'SYNTHETIC_VERIFIED' WHERE id = ?",
                    (gstin, existing["id"]),
                )

        for (
            po_number,
            vendor_code,
            total,
            gst,
            line_items,
            issue_date,
            recip_gstin,
            pos_state,
            profile,
            cgst_paise,
            sgst_paise,
            utgst_paise,
            igst_paise,
            cess_paise,
        ) in PURCHASE_ORDERS:
            existing = connection.execute(
                "SELECT id, recipient_gstin, place_of_supply_state_code FROM purchase_orders WHERE po_number = ?",
                (po_number,),
            ).fetchone()
            if existing is not None:
                # Idempotently update GST fields if missing
                if not existing["place_of_supply_state_code"]:
                    connection.execute(
                        """
                        UPDATE purchase_orders
                        SET recipient_gstin = ?,
                            place_of_supply_state_code = ?,
                            gst_transaction_profile = ?,
                            approved_cgst_paise = ?,
                            approved_sgst_paise = ?,
                            approved_utgst_paise = ?,
                            approved_igst_paise = ?,
                            approved_cess_paise = ?
                        WHERE id = ?
                        """,
                        (
                            recip_gstin,
                            pos_state,
                            profile,
                            cgst_paise,
                            sgst_paise,
                            utgst_paise,
                            igst_paise,
                            cess_paise,
                            existing["id"],
                        ),
                    )
                continue

            vendor = connection.execute(
                "SELECT id FROM vendors WHERE vendor_code = ?",
                (vendor_code,),
            ).fetchone()
            if vendor is None:
                raise ValueError(f"Cannot seed {po_number}: vendor {vendor_code} does not exist.")

            connection.execute(
                """
                INSERT INTO purchase_orders (
                    po_number,
                    vendor_id,
                    approved_total_paise,
                    approved_gst_paise,
                    approved_line_items,
                    status,
                    issue_date,
                    recipient_gstin,
                    place_of_supply_state_code,
                    gst_transaction_profile,
                    approved_cgst_paise,
                    approved_sgst_paise,
                    approved_utgst_paise,
                    approved_igst_paise,
                    approved_cess_paise,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, 'approved', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    po_number,
                    vendor["id"],
                    to_paise(total),
                    to_paise(gst),
                    line_items,
                    issue_date,
                    recip_gstin,
                    pos_state,
                    profile,
                    cgst_paise,
                    sgst_paise,
                    utgst_paise,
                    igst_paise,
                    cess_paise,
                    created_at,
                ),
            )
            inserted_purchase_orders += 1

    return {
        "vendors": inserted_vendors,
        "purchase_orders": inserted_purchase_orders,
        "invoices": 0,
        "audit_events": 0,
    }
