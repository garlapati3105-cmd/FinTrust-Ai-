from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import database
from app.financial import from_paise, normalize_invoice_number, to_paise
from app.main import app
from app.repository import (
    append_audit_event,
    insert_invoice,
    list_audit_events,
    list_invoices,
    list_purchase_orders,
    list_vendors,
)
from app.seed import seed_database


@pytest.fixture
def temporary_database(tmp_path):
    database_path = tmp_path / "fintrust-test.db"
    database.initialize_database(database_path)
    return database_path


def test_initialization_creates_all_tables_and_enables_foreign_keys(temporary_database):
    with database.get_connection(temporary_database) as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {"vendors", "purchase_orders", "invoices", "audit_events"} <= tables
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO purchase_orders (
                    po_number, vendor_id, approved_total_paise, approved_gst_paise,
                    approved_line_items, status, issue_date, created_at
                )
                VALUES ('PO-INVALID', 999, 100, 0, 1, 'approved', '2026-01-01', '2026-01-01')
                """
            )

    with database.get_connection(temporary_database) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_database_path_is_derived_from_backend_location():
    assert database.DB_PATH.name == "fintrust.db"
    assert database.DB_PATH.parent.name == "backend"


def test_synthetic_vendor_seed_records(temporary_database):
    seeded = seed_database(temporary_database)
    vendors = list_vendors(temporary_database)

    assert seeded["vendors"] == 3
    assert [(vendor["vendor_code"], vendor["name"]) for vendor in vendors] == [
        ("VND-1001", "Aster Office Supplies"),
        ("VND-1002", "BluePeak Technologies"),
        ("VND-1003", "GreenField Logistics"),
    ]
    assert all(vendor["bank_account_ref"].startswith("DEMO-ACCT-") for vendor in vendors)


def test_purchase_orders_are_related_to_the_expected_vendors(temporary_database):
    seed_database(temporary_database)
    orders = list_purchase_orders(temporary_database)

    assert [(order["po_number"], order["vendor_code"]) for order in orders] == [
        ("PO-1001", "VND-1001"),
        ("PO-1002", "VND-1002"),
        ("PO-1003", "VND-1003"),
    ]
    assert [order["approved_total_paise"] for order in orders] == [
        8_500_000,
        12_000_000,
        4_650_000,
    ]
    assert all(order["status"] == "approved" for order in orders)


def test_seed_is_idempotent_and_does_not_create_invoices_or_audit_events(temporary_database):
    first = seed_database(temporary_database)
    second = seed_database(temporary_database)

    assert first == {
        "vendors": 3,
        "purchase_orders": 3,
        "invoices": 0,
        "audit_events": 0,
    }
    assert second == {
        "vendors": 0,
        "purchase_orders": 0,
        "invoices": 0,
        "audit_events": 0,
    }
    assert list_invoices(temporary_database) == []
    assert list_audit_events(temporary_database) == []


def test_seed_fills_missing_records_without_duplicating_existing_ones(temporary_database):
    seed_database(temporary_database)
    with database.get_connection(temporary_database) as connection:
        connection.execute("DELETE FROM purchase_orders WHERE po_number = ?", ("PO-1002",))

    result = seed_database(temporary_database)
    assert result == {
        "vendors": 0,
        "purchase_orders": 1,
        "invoices": 0,
        "audit_events": 0,
    }
    assert len(list_vendors(temporary_database)) == 3
    assert len(list_purchase_orders(temporary_database)) == 3


def test_reinitialization_preserves_existing_invoice_and_audit_records(temporary_database):
    seed_database(temporary_database)
    vendor_id = list_vendors(temporary_database)[0]["id"]
    insert_invoice(
        invoice_number="INV-PERSIST",
        vendor_id=vendor_id,
        invoice_total="25.00",
        gst_amount="3.81",
        line_items=1,
        db_path=temporary_database,
    )
    append_audit_event(
        entity_type="invoice",
        entity_id=1,
        event_type="test_event",
        db_path=temporary_database,
    )

    database.initialize_database(temporary_database)

    assert len(list_invoices(temporary_database)) == 1
    assert len(list_audit_events(temporary_database)) == 1


def test_invoice_data_persists_in_integer_paise_and_normalizes_number(temporary_database):
    seed_database(temporary_database)
    vendor_id = list_vendors(temporary_database)[0]["id"]

    inserted_id = insert_invoice(
        invoice_number="  inv-2026-001  ",
        vendor_id=vendor_id,
        invoice_total=Decimal("85000.25"),
        gst_amount=Decimal("12966.10"),
        line_items=5,
        db_path=temporary_database,
    )
    invoice = list_invoices(temporary_database)[0]

    assert invoice["id"] == inserted_id
    assert invoice["invoice_number"] == "  inv-2026-001  "
    assert invoice["normalized_invoice_number"] == "INV-2026-001"
    assert invoice["invoice_total_paise"] == 8_500_025
    assert invoice["gst_amount_paise"] == 1_296_610


def test_invoice_number_normalization_and_unique_per_vendor(temporary_database):
    seed_database(temporary_database)
    vendors = list_vendors(temporary_database)

    assert normalize_invoice_number("  inv-42  ") == "INV-42"
    insert_invoice(
        invoice_number=" inv-42 ",
        vendor_id=vendors[0]["id"],
        invoice_total="10.00",
        gst_amount="1.00",
        line_items=1,
        db_path=temporary_database,
    )
    with pytest.raises(sqlite3.IntegrityError):
        insert_invoice(
            invoice_number="INV-42",
            vendor_id=vendors[0]["id"],
            invoice_total="10.00",
            gst_amount="1.00",
            line_items=1,
            db_path=temporary_database,
        )

    insert_invoice(
        invoice_number="INV-42",
        vendor_id=vendors[1]["id"],
        invoice_total="10.00",
        gst_amount="1.00",
        line_items=1,
        db_path=temporary_database,
    )
    assert len(list_invoices(temporary_database)) == 2


def test_decimal_money_conversion_uses_integer_paise():
    assert to_paise(Decimal("85000.00")) == 8_500_000
    assert from_paise(8_500_025) == Decimal("85000.25")
    with pytest.raises(ValueError, match="two decimal places"):
        to_paise(Decimal("0.005"))
    with pytest.raises(ValueError, match="two decimal places"):
        to_paise(Decimal("-0.005"))


def test_audit_events_are_inserted_and_returned_chronologically(temporary_database):
    append_audit_event(
        entity_type="invoice",
        entity_id=2,
        event_type="review_requested",
        decision="hold",
        reason="Test-only event",
        created_at="2026-11-02T10:00:00+00:00",
        db_path=temporary_database,
    )
    append_audit_event(
        entity_type="invoice",
        entity_id=1,
        event_type="received",
        created_at="2026-11-01T10:00:00+00:00",
        db_path=temporary_database,
    )

    events = list_audit_events(temporary_database)
    assert [event["event_type"] for event in events] == ["received", "review_requested"]
    assert events[1]["decision"] == "hold"


def test_api_health_dashboard_and_financial_data_endpoints(
    monkeypatch, tmp_path
):
    database_path = tmp_path / "api-test.db"
    monkeypatch.setattr(database, "DB_PATH", database_path)

    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/health").json()["status"] == "healthy"
        assert client.get("/api/health").json()["status"] == "healthy"
        assert client.get("/api/dashboard").json()["status"] == "healthy"

        vendors_response = client.get("/api/vendors")
        orders_response = client.get("/api/purchase-orders")
        invoices_response = client.get("/api/invoices")
        audit_response = client.get("/api/audit-events")

    assert vendors_response.status_code == 200
    assert len(vendors_response.json()) == 3
    assert vendors_response.json()[0]["bank_account_ref"] == "DEMO-ACCT-1001"
    assert orders_response.status_code == 200
    assert orders_response.json()[0]["vendor_code"] == "VND-1001"
    assert orders_response.json()[0]["vendor_name"] == "Aster Office Supplies"
    assert invoices_response.status_code == 200
    assert invoices_response.json() == []
    assert audit_response.status_code == 200
    assert audit_response.json() == []
    assert client.put("/api/audit-events/1").status_code == 404
    assert client.delete("/api/audit-events/1").status_code == 404
    assert str(database_path) not in vendors_response.text


def test_verify_api_uses_database_trusted_decimal_values(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "verify-api-test.db")
    with TestClient(app) as client:
        response = client.post(
            "/api/verify-invoice",
            json={
                "invoice_number": "INV-DECIMAL",
                "vendor_name": "Aster Office Supplies",
                "po_number": "PO-1001",
                "invoice_total": 85000.01,
                "gst_amount": 12966.10,
                "line_items": 5,
                "invoice_bank_account_ref": "DEMO-ACCT-1001",
            },
        )

    assert response.status_code == 200
    assert response.json()["variance"]["amount"] == 0.01
    assert response.json()["decision"] == "HOLD"
