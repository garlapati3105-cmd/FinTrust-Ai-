from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "verification-test.db")
    with TestClient(app) as test_client:
        yield test_client


def valid_invoice(**overrides):
    payload = {
        "invoice_number": "INV-TEST-1001",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
    }
    return payload | overrides


def test_valid_invoice_is_approved_persisted_and_audited(client):
    response = client.post("/api/verify-invoice", json=valid_invoice())

    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "APPROVE"
    assert result["risk_level"] == "low"
    assert result["findings"] == []
    assert result["invoice_id"] is not None
    assert result["audit_event_id"] is not None
    assert result["approved_total"] == 85000.0
    assert result["approved_gst"] == 12966.10
    assert len(client.get("/api/invoices").json()) == 1
    events = client.get("/api/audit-events").json()
    assert len(events) == 1
    assert events[0]["entity_id"] == result["invoice_id"]
    assert events[0]["id"] == result["audit_event_id"]
    assert events[0]["decision"] == "APPROVE"


def test_amount_mismatch_requires_hold(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_total="85001.00"),
    )

    assert response.json()["decision"] == "HOLD"
    assert "amount_mismatch" in {finding["code"] for finding in response.json()["findings"]}


def test_gst_mismatch_requires_hold(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(gst_amount="12966.11"),
    )

    assert response.json()["decision"] == "HOLD"
    assert "gst_mismatch" in {finding["code"] for finding in response.json()["findings"]}


def test_vendor_mismatch_requires_hold(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(vendor_name="Another Fictional Supplier"),
    )

    assert response.json()["decision"] == "HOLD"
    assert "vendor_mismatch" in {finding["code"] for finding in response.json()["findings"]}


def test_vendor_name_matching_ignores_case_and_repeated_whitespace(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(vendor_name="  aStEr   oFfIcE supplies  "),
    )

    assert response.json()["decision"] == "APPROVE"


def test_bank_reference_mismatch_requires_hold(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_bank_account_ref="DEMO-ACCT-9999"),
    )

    result = response.json()
    assert result["decision"] == "HOLD"
    finding = next(item for item in result["findings"] if item["code"] == "bank_reference_mismatch")
    assert "does not verify account ownership" in finding["detail"]


def test_missing_bank_reference_requires_hold(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_bank_account_ref=None),
    )

    assert response.json()["decision"] == "HOLD"
    assert "bank_reference_missing" in {finding["code"] for finding in response.json()["findings"]}


def test_line_item_mismatch_explains_whether_items_are_more_or_fewer(client):
    more = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_number="INV-MORE", line_items=6),
    ).json()
    fewer = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_number="INV-FEWER", line_items=4),
    ).json()

    assert more["decision"] == "HOLD"
    assert "1 more line item" in next(
        finding["detail"] for finding in more["findings"] if finding["code"] == "line_items_mismatch"
    )
    assert fewer["decision"] == "HOLD"
    assert "1 fewer line item" in next(
        finding["detail"] for finding in fewer["findings"] if finding["code"] == "line_items_mismatch"
    )


def test_unapproved_purchase_order_requires_hold(client):
    with database.get_connection() as connection:
        connection.execute(
            "UPDATE purchase_orders SET status = ? WHERE po_number = ?",
            ("draft", "PO-1001"),
        )

    response = client.post("/api/verify-invoice", json=valid_invoice())

    assert response.json()["decision"] == "HOLD"
    assert "purchase_order_not_approved" in {
        finding["code"] for finding in response.json()["findings"]
    }


def test_duplicate_invoice_is_detected_and_original_is_returned(client):
    first = client.post("/api/verify-invoice", json=valid_invoice()).json()
    duplicate = client.post("/api/verify-invoice", json=valid_invoice()).json()

    assert duplicate["decision"] == "HOLD"
    assert duplicate["duplicate"] is True
    assert duplicate["duplicate_of_invoice_id"] == first["invoice_id"]
    assert duplicate["invoice_id"] == first["invoice_id"]


def test_invoice_number_case_and_whitespace_are_normalized_for_duplicates(client):
    first = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_number="  inv-test-1001 "),
    ).json()
    second = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_number="INV-TEST-1001"),
    ).json()

    assert second["duplicate"] is True
    assert second["duplicate_of_invoice_id"] == first["invoice_id"]
    assert len(client.get("/api/invoices").json()) == 1


def test_duplicate_attempt_does_not_insert_and_appends_audit_event(client):
    first = client.post("/api/verify-invoice", json=valid_invoice()).json()
    duplicate = client.post("/api/verify-invoice", json=valid_invoice()).json()

    assert duplicate["decision"] == "HOLD"
    assert len(client.get("/api/invoices").json()) == 1
    events = client.get("/api/audit-events").json()
    assert len(events) == 2
    assert events[1]["event_type"] == "duplicate_invoice_submission"
    assert events[1]["entity_id"] == first["invoice_id"]
    assert events[1]["decision"] == "HOLD"
    assert events[1]["id"] == duplicate["audit_event_id"]


def test_duplicate_event_references_original_invoice(client):
    original = client.post("/api/verify-invoice", json=valid_invoice()).json()
    duplicate = client.post("/api/verify-invoice", json=valid_invoice()).json()
    event = client.get("/api/audit-events").json()[-1]

    assert duplicate["duplicate_of_invoice_id"] == original["invoice_id"]
    assert event["entity_id"] == original["invoice_id"]


def test_unknown_purchase_order_is_held_and_audited_without_invoice(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(po_number="PO-UNKNOWN"),
    )

    assert response.json()["decision"] == "HOLD"
    assert response.json()["invoice_id"] is None
    assert client.get("/api/invoices").json() == []
    event = client.get("/api/audit-events").json()[0]
    assert event["decision"] == "HOLD"
    assert event["entity_id"] is None
    assert event["id"] == response.json()["audit_event_id"]


def test_missing_vendor_record_is_held_and_audited_without_invoice(client):
    with database.get_connection() as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "DELETE FROM vendors WHERE vendor_code = ?",
            ("VND-1001",),
        )

    response = client.post("/api/verify-invoice", json=valid_invoice())

    assert response.json()["decision"] == "HOLD"
    assert response.json()["invoice_id"] is None
    assert client.get("/api/invoices").json() == []
    assert client.get("/api/audit-events").json()[0]["entity_id"] is None


def test_inactive_vendor_cannot_be_approved(client):
    with database.get_connection() as connection:
        connection.execute(
            "UPDATE vendors SET is_active = 0 WHERE vendor_code = ?",
            ("VND-1001",),
        )

    response = client.post("/api/verify-invoice", json=valid_invoice())

    assert response.json()["decision"] == "HOLD"
    assert "vendor_inactive" in {finding["code"] for finding in response.json()["findings"]}


def test_client_cannot_supply_trusted_purchase_order_values(client):
    response = client.post(
        "/api/verify-invoice",
        json=valid_invoice(
            approved_total="1.00",
            approved_gst="0.00",
            approved_line_items=0,
        ),
    )

    assert response.status_code == 422
    assert client.get("/api/invoices").json() == []


def test_invoice_and_decision_persist_after_connection_reopens(client):
    result = client.post("/api/verify-invoice", json=valid_invoice()).json()

    with database.get_connection() as connection:
        row = connection.execute(
            "SELECT decision, invoice_total_paise FROM invoices WHERE id = ?",
            (result["invoice_id"],),
        ).fetchone()

    assert row["decision"] == "APPROVE"
    assert row["invoice_total_paise"] == 8_500_000


def test_every_first_time_persisted_invoice_has_an_audit_entry(client):
    first = client.post("/api/verify-invoice", json=valid_invoice()).json()
    second = client.post(
        "/api/verify-invoice",
        json=valid_invoice(invoice_number="INV-TEST-1002", line_items=4),
    ).json()

    assert second["decision"] == "HOLD"
    persisted_ids = {invoice["id"] for invoice in client.get("/api/invoices").json()}
    audited_ids = {
        event["entity_id"]
        for event in client.get("/api/audit-events").json()
        if event["event_type"] == "invoice_verified"
    }
    assert persisted_ids == {first["invoice_id"], second["invoice_id"]}
    assert audited_ids == persisted_ids


def test_health_and_dashboard_routes_remain_functional(client):
    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/api/health").json()["status"] == "healthy"
    assert client.get("/api/dashboard").json()["status"] == "healthy"


def test_invalid_money_precision_is_rejected(client):
    for amount in ("85000.001", 85000.001, "999999999999999.00"):
        response = client.post(
            "/api/verify-invoice",
            json=valid_invoice(invoice_total=amount),
        )

        assert response.status_code == 422
    assert client.get("/api/invoices").json() == []
