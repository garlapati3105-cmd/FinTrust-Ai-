from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import database
from app.ai_extractor import verify_value_grounded_in_quote
from app.gst_integrity import (
    GST_PROFILE_STANDARD_DOMESTIC,
    GST_PROFILE_SPECIAL_CASE_REVIEW,
    RESULT_CHECKSUM_MISMATCH,
    RESULT_FORMAT_VALID,
    RESULT_INVALID_FORMAT,
    RESULT_INVALID_STATE_CODE,
    STATE_CATALOGUE,
    STATUS_MISMATCH,
    STATUS_PASS,
    calculate_gstin_checksum,
    classify_tax_type,
    evaluate_gst_integrity,
    normalize_gstin,
    reconcile_gst_totals,
    resolve_state_code,
    validate_gstin,
)
from app.main import app


# ==============================================================================
# 1. GSTIN NORMALIZATION & STRUCTURAL VALIDATION TESTS
# ==============================================================================

def test_normalize_gstin():
    assert normalize_gstin("  27aapca1234a1z5  ") == "27AAPCA1234A1Z5"
    assert normalize_gstin(None) is None
    assert normalize_gstin("") is None
    assert normalize_gstin("   ") is None


def test_validate_gstin_valid_vectors():
    # Known valid test vectors
    vectors = [
        "27AAPCA1234A1Z5",  # Maharashtra
        "29ABCDE1234F1ZW",  # Karnataka
        "04AAACG1234D1ZG",  # Chandigarh (UT)
        "27AABCF1234F1Z4",  # Buyer demo GSTIN
    ]
    for gstin in vectors:
        res = validate_gstin(gstin)
        assert res["result_code"] == RESULT_FORMAT_VALID, f"Failed for {gstin}: {res['message']}"
        assert res["state_code"] is not None
        assert res["is_valid"] is True
        assert res["checksum_evaluated"] is True
        assert res["checksum_matched"] is True


def test_validate_gstin_invalid_length():
    assert validate_gstin("27AAPCA1234A1Z")["result_code"] == RESULT_INVALID_FORMAT
    assert validate_gstin("27AAPCA1234A1Z55")["result_code"] == RESULT_INVALID_FORMAT
    assert validate_gstin("")["result_code"] == RESULT_INVALID_FORMAT
    assert validate_gstin(None)["result_code"] == RESULT_INVALID_FORMAT


def test_validate_gstin_invalid_characters():
    assert validate_gstin("27AAPCA1234A1Z@")["result_code"] == RESULT_INVALID_FORMAT
    assert validate_gstin("27AAPCA1234A1-5")["result_code"] == RESULT_INVALID_FORMAT


def test_validate_gstin_invalid_state_code():
    # 98 and 00 are not valid GST state codes
    res = validate_gstin("98AAPCA1234A1Z5")
    assert res["result_code"] == RESULT_INVALID_STATE_CODE
    res2 = validate_gstin("00AAPCA1234A1Z5")
    assert res2["result_code"] == RESULT_INVALID_STATE_CODE


def test_validate_gstin_checksum_mismatch():
    # Valid pattern, but checksum character corrupted (5 replaced by 9)
    res = validate_gstin("27AAPCA1234A1Z9")
    assert res["result_code"] == RESULT_CHECKSUM_MISMATCH
    assert res["is_valid"] is False
    assert res["checksum_matched"] is False


# ==============================================================================
# 2. STATE / UT CATALOGUE & SGST VS UTGST DISTINCTION TESTS
# ==============================================================================

def test_state_catalogue_completeness():
    assert len(STATE_CATALOGUE) >= 37
    assert "27" in STATE_CATALOGUE  # Maharashtra
    assert "29" in STATE_CATALOGUE  # Karnataka
    assert "07" in STATE_CATALOGUE  # Delhi
    assert "04" in STATE_CATALOGUE  # Chandigarh
    assert "38" in STATE_CATALOGUE  # Ladakh


def test_utgst_vs_sgst_distinction():
    # UTs without legislature levy UTGST under UTGST Act
    assert STATE_CATALOGUE["04"]["tax_type"] == "UTGST"  # Chandigarh
    assert STATE_CATALOGUE["04"]["is_ut"] is True
    assert STATE_CATALOGUE["04"]["has_legislature"] is False

    assert STATE_CATALOGUE["38"]["tax_type"] == "UTGST"  # Ladakh
    assert STATE_CATALOGUE["38"]["is_ut"] is True

    # Delhi has its own legislative assembly; levies SGST, NOT UTGST under GST law
    assert STATE_CATALOGUE["07"]["tax_type"] == "SGST"  # Delhi
    assert STATE_CATALOGUE["07"]["is_ut"] is True
    assert STATE_CATALOGUE["07"]["has_legislature"] is True

    # Puducherry also has its own legislative assembly; levies SGST
    assert STATE_CATALOGUE["34"]["tax_type"] == "SGST"  # Puducherry
    assert STATE_CATALOGUE["34"]["has_legislature"] is True

    # Standard state levies SGST
    assert STATE_CATALOGUE["27"]["tax_type"] == "SGST"  # Maharashtra
    assert STATE_CATALOGUE["27"]["is_ut"] is False


# ==============================================================================
# 3. LUHN MOD 36 CHECKSUM TEST VECTORS
# ==============================================================================

def test_luhn_mod36_positive_and_negative():
    assert calculate_gstin_checksum("27AAPCA1234A1Z") == "5"
    assert calculate_gstin_checksum("29ABCDE1234F1Z") == "W"
    assert calculate_gstin_checksum("04AAACG1234D1Z") == "G"
    assert calculate_gstin_checksum("27AABCF1234F1Z") == "4"


# ==============================================================================
# 4. TAX TYPE CLASSIFICATION LOGIC TESTS
# ==============================================================================

def test_classify_tax_type_intra_state():
    # Maharashtra supplier (27) to Maharashtra place of supply (27)
    res, finding = classify_tax_type("27", "27", profile=GST_PROFILE_STANDARD_DOMESTIC)
    assert res["tax_type"] == "INTRA_STATE"
    assert res["expected_components"] == ["CGST", "SGST"]
    assert finding is None


def test_classify_tax_type_intra_ut():
    # Chandigarh supplier (04) to Chandigarh POS (04)
    res, finding = classify_tax_type("04", "04", profile=GST_PROFILE_STANDARD_DOMESTIC)
    assert res["tax_type"] == "INTRA_STATE"
    assert res["state_tax_type"] == "UTGST"
    assert res["expected_components"] == ["CGST", "UTGST"]
    assert finding is None


def test_classify_tax_type_inter_state():
    # Karnataka supplier (29) to Maharashtra POS (27)
    res, finding = classify_tax_type("29", "27", profile=GST_PROFILE_STANDARD_DOMESTIC)
    assert res["tax_type"] == "INTER_STATE"
    assert res["expected_components"] == ["IGST"]
    assert finding is None


def test_classify_tax_type_special_case():
    # Non-standard profile (e.g. SEZ or import)
    res, finding = classify_tax_type("27", "27", profile=GST_PROFILE_SPECIAL_CASE_REVIEW)
    assert res["tax_type"] == "SPECIAL_CASE"
    assert finding is not None
    assert finding.status == "MANUAL_REVIEW_REQUIRED"


# ==============================================================================
# 5. TAX COMPONENT RECONCILIATION & TOLERANCE TESTS
# ==============================================================================

def test_reconcile_components_exact_match():
    # CGST 648305 + SGST 648305 = 1296610 paise
    components = {
        "cgst": 648305,
        "sgst": 648305,
        "utgst": 0,
        "igst": 0,
        "cess": 0,
    }
    res, finding = reconcile_gst_totals(1296610, components)
    assert res["within_tolerance"] is True
    assert res["variance_paise"] == 0
    assert finding is None


def test_reconcile_components_within_tolerance():
    # 50 paise rounding discrepancy (allowed under 100 paise tolerance)
    components = {
        "cgst": 648305,
        "sgst": 648305,
        "utgst": 0,
        "igst": 0,
        "cess": 0,
    }
    res, finding = reconcile_gst_totals(1296660, components, tolerance_paise=100)
    assert res["within_tolerance"] is True
    assert res["variance_paise"] == -50
    # Tolerance finding is informational and has status PASS
    assert finding is not None
    assert finding.status == STATUS_PASS


def test_reconcile_components_exceeds_tolerance():
    # 200 paise difference exceeds 100 paise tolerance
    components = {
        "cgst": 648305,
        "sgst": 648305,
        "utgst": 0,
        "igst": 0,
        "cess": 0,
    }
    res, finding = reconcile_gst_totals(1296810, components, tolerance_paise=100)
    assert res["within_tolerance"] is False
    assert abs(res["variance_paise"]) == 200
    assert finding is not None
    assert finding.finding_code == "gst_component_sum_mismatch"


# ==============================================================================
# 6. GST INTEGRITY ENGINE EVALUATION (COMPREHENSIVE)
# ==============================================================================

def test_evaluate_gst_integrity_clean_intra_state():
    report = evaluate_gst_integrity(
        invoice_supplier_gstin="27AAPCA1234A1Z5",
        trusted_supplier_gstin="27AAPCA1234A1Z5",
        invoice_recipient_gstin="27AABCF1234F1Z4",
        trusted_recipient_gstin="27AABCF1234F1Z4",
        invoice_pos_code="27",
        po_pos_code="27",
        gst_profile=GST_PROFILE_STANDARD_DOMESTIC,
        invoice_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        po_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        declared_total_gst_paise=1296610,
    )
    assert report.overall_status in ("PASS", "VALID")
    assert report.tax_classification_result["tax_type"] == "INTRA_STATE"
    assert report.component_reconciliation_result["within_tolerance"] is True
    # Should have 0 critical or warning findings
    critical_or_warn = [f for f in report.findings if f.severity in ("high", "medium")]
    assert len(critical_or_warn) == 0


def test_evaluate_gst_integrity_tax_type_mismatch():
    # Inter-state transaction (KA supplier to MH POS) but declared as CGST+SGST
    report = evaluate_gst_integrity(
        invoice_supplier_gstin="29ABCDE1234F1ZW",
        trusted_supplier_gstin="29ABCDE1234F1ZW",
        invoice_recipient_gstin="27AABCF1234F1Z4",
        trusted_recipient_gstin="27AABCF1234F1Z4",
        invoice_pos_code="27",
        po_pos_code="27",
        gst_profile=GST_PROFILE_STANDARD_DOMESTIC,
        invoice_components={
            "cgst": 915254,  # INCORRECT: Should be IGST
            "sgst": 915254,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        po_components={
            "cgst": 0,
            "sgst": 0,
            "utgst": 0,
            "igst": 1830508,
            "cess": 0,
        },
        declared_total_gst_paise=1830508,
    )
    assert report.requires_hold is True
    assert any("prohibited_intra_tax_on_inter_state" in f.finding_code for f in report.findings)


def test_evaluate_gst_integrity_vendor_gstin_mismatch():
    report = evaluate_gst_integrity(
        invoice_supplier_gstin="27AAPCA1234A1Z5",
        trusted_supplier_gstin="27XYZAB9999K1Z2",  # Different from invoice
        invoice_recipient_gstin="27AABCF1234F1Z4",
        trusted_recipient_gstin="27AABCF1234F1Z4",
        invoice_pos_code="27",
        po_pos_code="27",
        gst_profile=GST_PROFILE_STANDARD_DOMESTIC,
        invoice_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        po_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        declared_total_gst_paise=1296610,
    )
    assert any("supplier_gstin_mismatch" in f.finding_code for f in report.findings)


def test_evaluate_gst_integrity_pos_mismatch():
    report = evaluate_gst_integrity(
        invoice_supplier_gstin="27AAPCA1234A1Z5",
        trusted_supplier_gstin="27AAPCA1234A1Z5",
        invoice_recipient_gstin="27AABCF1234F1Z4",
        trusted_recipient_gstin="27AABCF1234F1Z4",
        invoice_pos_code="29",  # Invoice says 29
        po_pos_code="27",  # PO authorized 27
        gst_profile=GST_PROFILE_STANDARD_DOMESTIC,
        invoice_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        po_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        declared_total_gst_paise=1296610,
    )
    assert any("place_of_supply_mismatch" in f.finding_code for f in report.findings)


# ==============================================================================
# 7. DATABASE MIGRATION IDEMPOTENCY TEST
# ==============================================================================

def test_database_migration_idempotent(tmp_path, monkeypatch):
    test_db = tmp_path / "migration_test.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    database.initialize_database()
    with database.get_connection() as conn:
        database.migrate_database(conn)
        # Repeating multiple times must never throw OperationalError
        database.migrate_database(conn)
        database.migrate_database(conn)


# ==============================================================================
# 8. FULL END-TO-END API INTEGRATION TESTS WITH GST PAYLOAD
# ==============================================================================

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "gst-api-test.db")
    with TestClient(app) as test_client:
        yield test_client


def test_api_verify_invoice_with_clean_gst(client):
    payload = {
        "invoice_number": "INV-GST-1001",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
        "supplier_gstin": "27AAPCA1234A1Z5",
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "27",
        "cgst_amount": "6483.05",
        "sgst_amount": "6483.05",
        "utgst_amount": "0.00",
        "igst_amount": "0.00",
        "cess_amount": "0.00",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["supplier_gstin"] == "27AAPCA1234A1Z5"
    assert data["recipient_gstin"] == "27AABCF1234F1Z4"
    assert data["place_of_supply_state_code"] == "27"
    assert data["gst_checks"] is not None
    assert data["gst_checks"]["overall_status"] in ("VALID", "PASS")


def test_api_verify_invoice_tax_mismatch_triggers_hold(client):
    payload = {
        "invoice_number": "INV-GST-1002",
        "vendor_name": "BluePeak Technologies",
        "po_number": "PO-1002",
        "invoice_total": "119967.08",
        "gst_amount": "18305.08",
        "line_items": 8,
        "invoice_bank_account_ref": "DEMO-ACCT-1002",
        "supplier_gstin": "29ABCDE1234F1ZW",
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "27",
        "cgst_amount": "9152.54",  # Mismatch: Should be IGST for Inter-State
        "sgst_amount": "9152.54",
        "utgst_amount": "0.00",
        "igst_amount": "0.00",
        "cess_amount": "0.00",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HOLD"
    assert any("GST" in f["title"] or "Tax" in f["title"] or "Mismatch" in f["title"] or "Prohibited" in f["title"] for f in data["findings"])


def test_api_verify_invoice_audited_with_gst_findings(client):
    payload = {
        "invoice_number": "INV-GST-1003",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
        "supplier_gstin": "27AAPCA1234A1Z9",  # Invalid checksum
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "27",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HOLD"
    # Verify audit event records the event
    events = client.get("/api/audit-events").json()
    assert len(events) >= 1
    assert any(e["entity_id"] == data["invoice_id"] for e in events)


# ==============================================================================
# 9. ADDITIONAL GRANULAR COVERAGE TESTS (35+ REQUIREMENT)
# ==============================================================================

def test_utgst_territories_catalogue_dadra_daman():
    assert STATE_CATALOGUE["26"]["tax_type"] == "UTGST"
    assert STATE_CATALOGUE["26"]["is_ut"] is True
    assert STATE_CATALOGUE["26"]["has_legislature"] is False


def test_utgst_territories_catalogue_lakshadweep():
    assert STATE_CATALOGUE["31"]["tax_type"] == "UTGST"
    assert STATE_CATALOGUE["31"]["is_ut"] is True


def test_utgst_territories_catalogue_andaman():
    assert STATE_CATALOGUE["35"]["tax_type"] == "UTGST"
    assert STATE_CATALOGUE["35"]["is_ut"] is True


def test_sgst_territories_catalogue_jk():
    # Jammu and Kashmir has legislative assembly provision; levies SGST
    assert STATE_CATALOGUE["01"]["tax_type"] == "SGST"
    assert STATE_CATALOGUE["01"]["is_ut"] is True
    assert STATE_CATALOGUE["01"]["has_legislature"] is True


def test_validate_gstin_lowercase_normalization():
    res_lower = validate_gstin("27aapca1234a1z5")
    res_upper = validate_gstin("27AAPCA1234A1Z5")
    assert res_lower["result_code"] == res_upper["result_code"]
    assert res_lower["state_code"] == "27"
    assert res_lower["normalized"] == "27AAPCA1234A1Z5"


def test_validate_gstin_pan_structure_invalid():
    # PAN portion characters 3-12 must be 5 alpha, 4 digits, 1 alpha.
    # Here characters 3-7 have a digit: "271APCA1234A1Z5"
    res = validate_gstin("271APCA1234A1Z5")
    assert res["is_valid"] is False


def test_reconcile_components_with_cess():
    # CGST 500000 + SGST 500000 + Cess 200000 = 1200000 paise
    components = {
        "cgst": 500000,
        "sgst": 500000,
        "utgst": 0,
        "igst": 0,
        "cess": 200000,
    }
    res, finding = reconcile_gst_totals(1200000, components)
    assert res["within_tolerance"] is True
    assert res["variance_paise"] == 0
    assert finding is None


def test_evaluate_gst_integrity_clean_inter_state():
    # Clean Inter-State supply (Karnataka -> Maharashtra)
    report = evaluate_gst_integrity(
        invoice_supplier_gstin="29ABCDE1234F1ZW",
        trusted_supplier_gstin="29ABCDE1234F1ZW",
        invoice_recipient_gstin="27AABCF1234F1Z4",
        trusted_recipient_gstin="27AABCF1234F1Z4",
        invoice_pos_code="27",
        po_pos_code="27",
        gst_profile=GST_PROFILE_STANDARD_DOMESTIC,
        invoice_components={
            "cgst": 0,
            "sgst": 0,
            "utgst": 0,
            "igst": 1830508,
            "cess": 0,
        },
        po_components={
            "cgst": 0,
            "sgst": 0,
            "utgst": 0,
            "igst": 1830508,
            "cess": 0,
        },
        declared_total_gst_paise=1830508,
    )
    assert report.overall_status in ("PASS", "VALID")
    assert report.tax_classification_result["tax_type"] == "INTER_STATE"
    assert report.requires_hold is False


def test_evaluate_gst_integrity_clean_intra_ut():
    # Clean Intra-UT supply (Chandigarh -> Chandigarh)
    report = evaluate_gst_integrity(
        invoice_supplier_gstin="04AAACG1234D1ZG",
        trusted_supplier_gstin="04AAACG1234D1ZG",
        invoice_recipient_gstin="04AABCF1234F1ZC",
        trusted_recipient_gstin="04AABCF1234F1ZC",
        invoice_pos_code="04",
        po_pos_code="04",
        gst_profile=GST_PROFILE_STANDARD_DOMESTIC,
        invoice_components={
            "cgst": 354661,
            "sgst": 0,
            "utgst": 354661,
            "igst": 0,
            "cess": 0,
        },
        po_components={
            "cgst": 354661,
            "sgst": 0,
            "utgst": 354661,
            "igst": 0,
            "cess": 0,
        },
        declared_total_gst_paise=709322,
    )
    assert report.overall_status in ("PASS", "VALID")
    assert report.tax_classification_result["tax_type"] == "INTRA_STATE"
    assert report.tax_classification_result["state_tax_type"] == "UTGST"
    assert report.requires_hold is False


def test_evaluate_gst_integrity_recipient_mismatch():
    # Recipient GSTIN on invoice doesn't match PO authorized buyer GSTIN
    # 36AABCF9999F1Z1 is valid format + valid checksum (1), but different buyer
    report = evaluate_gst_integrity(
        invoice_supplier_gstin="27AAPCA1234A1Z5",
        trusted_supplier_gstin="27AAPCA1234A1Z5",
        invoice_recipient_gstin="36AABCF9999F1Z1",
        trusted_recipient_gstin="27AABCF1234F1Z4",
        invoice_pos_code="27",
        po_pos_code="27",
        gst_profile=GST_PROFILE_STANDARD_DOMESTIC,
        invoice_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        po_components={
            "cgst": 648305,
            "sgst": 648305,
            "utgst": 0,
            "igst": 0,
            "cess": 0,
        },
        declared_total_gst_paise=1296610,
    )
    assert any("recipient_gstin_mismatch" in f.finding_code for f in report.findings)


def test_api_verify_invoice_intra_ut_approval(client):
    # Verify PO-1003 clean intra-UT approval against seed baseline (GreenField Logistics)
    payload = {
        "invoice_number": "INV-GST-1005",
        "vendor_name": "GreenField Logistics",
        "po_number": "PO-1003",
        "invoice_total": "46500.00",
        "gst_amount": "7093.22",
        "line_items": 4,
        "invoice_bank_account_ref": "DEMO-ACCT-1003",
        "supplier_gstin": "04AAACG1234D1ZG",
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "04",
        "cgst_amount": "3546.61",
        "sgst_amount": "0.00",
        "utgst_amount": "3546.61",
        "igst_amount": "0.00",
        "cess_amount": "0.00",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["gst_checks"]["overall_status"] in ("VALID", "PASS")


def test_api_verify_invoice_inter_state_approval(client):
    # Verify PO-1002 clean inter-state approval against seed baseline
    payload = {
        "invoice_number": "INV-GST-1006",
        "vendor_name": "BluePeak Technologies",
        "po_number": "PO-1002",
        "invoice_total": "120000.00",
        "gst_amount": "18305.08",
        "line_items": 8,
        "invoice_bank_account_ref": "DEMO-ACCT-1002",
        "supplier_gstin": "29ABCDE1234F1ZW",
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "27",
        "cgst_amount": "0.00",
        "sgst_amount": "0.00",
        "utgst_amount": "0.00",
        "igst_amount": "18305.08",
        "cess_amount": "0.00",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["gst_checks"]["tax_classification_result"]["tax_type"] == "INTER_STATE"


def test_api_verify_invoice_component_sum_mismatch_hold(client):
    # Sum of components (10,000) != total GST (12,966.10)
    payload = {
        "invoice_number": "INV-GST-1007",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
        "supplier_gstin": "27AAPCA1234A1Z5",
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "27",
        "cgst_amount": "5000.00",
        "sgst_amount": "5000.00",  # Sum = 10,000, mismatch > ₹1.00
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HOLD"
    assert any("sum" in f["code"].lower() for f in data["findings"])


# ==============================================================================
# 10. AUDIT HARDENING REGRESSION TESTS
# ==============================================================================

def test_regression_gst_configured_po_with_missing_invoice_gst_fields_held(client):
    """
    Scenario 1: Taxable PO (PO-1001 with ₹12,966.10 approved GST) must NOT silently bypass
    GST validation when invoice omits all GST fields. It must trigger HOLD with findings.
    """
    payload = {
        "invoice_number": "INV-REGRESS-001",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
        # All GST fields intentionally omitted
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HOLD"
    assert data["risk_level"] == "high"
    finding_codes = [f["code"] for f in data["findings"]]
    assert "supplier_gstin_missing" in finding_codes


def test_regression_taxable_po_missing_supplier_gstin_held(client):
    """
    Scenario 2: Missing supplier GSTIN on taxable PO must trigger HOLD.
    """
    payload = {
        "invoice_number": "INV-REGRESS-002",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
        "supplier_gstin": None,
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "27",
        "cgst_amount": "6483.05",
        "sgst_amount": "6483.05",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HOLD"
    assert any(f["code"] == "supplier_gstin_missing" for f in data["findings"])


def test_regression_legitimate_exempt_transaction_approved(client):
    """
    Scenario 3: Legitimate exempt/non-GST transaction (0 GST PO + 0 GST invoice)
    must APPROVE without false rejection.
    """
    with database.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO purchase_orders (
                po_number, vendor_id, approved_total_paise, approved_gst_paise,
                approved_line_items, issue_date, status, recipient_gstin,
                place_of_supply_state_code, gst_transaction_profile,
                approved_cgst_paise, approved_sgst_paise, approved_utgst_paise,
                approved_igst_paise, approved_cess_paise, created_at
            ) VALUES (
                'PO-EXEMPT-001', 1, 5000000, 0,
                3, '2026-11-10', 'approved', '27AABCF1234F1Z4',
                '27', 'EXEMPT',
                0, 0, 0, 0, 0, '2026-11-10T10:00:00'
            )
            """
        )

    payload = {
        "invoice_number": "INV-EXEMPT-001",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-EXEMPT-001",
        "invoice_total": "50000.00",
        "gst_amount": "0.00",
        "line_items": 3,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["risk_level"] == "low"
    assert len(data["findings"]) == 0


def test_regression_pos_state_name_resolution(client):
    """
    Scenario 4: Maharashtra as POS name (and MH abbreviation) resolves to state code 27.
    """
    # Direct function checks
    assert resolve_state_code("Maharashtra") == "27"
    assert resolve_state_code("maharashtra") == "27"
    assert resolve_state_code("MH") == "27"
    assert resolve_state_code("mh") == "27"
    assert resolve_state_code("Delhi") == "07"
    assert resolve_state_code("Chandigarh") == "04"
    assert resolve_state_code("Karnataka") == "29"

    # API endpoint check
    payload = {
        "invoice_number": "INV-POS-NAME-001",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
        "supplier_gstin": "27AAPCA1234A1Z5",
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "Maharashtra",
        "cgst_amount": "6483.05",
        "sgst_amount": "6483.05",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["gst_checks"]["place_of_supply_result"]["status"] == "PASS"
    assert data["gst_checks"]["place_of_supply_result"]["invoice_pos"] == "27"


def test_regression_unknown_place_of_supply_held(client):
    """
    Scenario 5: Unknown/ambiguous Place of Supply location must never be guessed
    and must trigger HOLD with invalid_state_code / place_of_supply_mismatch.
    """
    assert resolve_state_code("Atlantis") is None
    assert resolve_state_code("UnknownCity") is None

    payload = {
        "invoice_number": "INV-POS-UNKNOWN-001",
        "vendor_name": "Aster Office Supplies",
        "po_number": "PO-1001",
        "invoice_total": "85000.00",
        "gst_amount": "12966.10",
        "line_items": 5,
        "invoice_bank_account_ref": "DEMO-ACCT-1001",
        "supplier_gstin": "27AAPCA1234A1Z5",
        "recipient_gstin": "27AABCF1234F1Z4",
        "place_of_supply_state_code": "Atlantis",
        "cgst_amount": "6483.05",
        "sgst_amount": "6483.05",
    }
    response = client.post("/api/verify-invoice", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HOLD"
    finding_codes = [f["code"] for f in data["findings"]]
    assert "invalid_state_code" in finding_codes or "place_of_supply_mismatch" in finding_codes


def test_regression_evidence_grounding_rejects_empty_and_punctuation():
    """
    Scenario 6: Empty strings, whitespace-only, and punctuation-only values
    must be strictly rejected by server-side evidence grounding.
    """
    quote = "Supplier GSTIN: 27AAPCA1234A1Z5, Total: ₹85,000.00, PO-1001"

    # GSTIN empty / punctuation
    assert verify_value_grounded_in_quote("supplier_gstin", "", quote) is False
    assert verify_value_grounded_in_quote("supplier_gstin", "   ", quote) is False
    assert verify_value_grounded_in_quote("supplier_gstin", "--", quote) is False
    assert verify_value_grounded_in_quote("supplier_gstin", "***", quote) is False

    # Monetary empty / punctuation
    assert verify_value_grounded_in_quote("invoice_total", "", quote) is False
    assert verify_value_grounded_in_quote("invoice_total", "   ", quote) is False
    assert verify_value_grounded_in_quote("invoice_total", "$", quote) is False
    assert verify_value_grounded_in_quote("invoice_total", "₹", quote) is False

    # String identifiers empty / punctuation
    assert verify_value_grounded_in_quote("invoice_number", "", quote) is False
    assert verify_value_grounded_in_quote("invoice_number", "   ", quote) is False
    assert verify_value_grounded_in_quote("invoice_number", "---", quote) is False
    assert verify_value_grounded_in_quote("vendor_name", "   ", quote) is False
    assert verify_value_grounded_in_quote("line_items", "   ", quote) is False
    assert verify_value_grounded_in_quote("line_items", "none", quote) is False
    assert verify_value_grounded_in_quote("place_of_supply_state_code", "   ", quote) is False

    # Legitimate values must still ground correctly
    assert verify_value_grounded_in_quote("supplier_gstin", "27AAPCA1234A1Z5", quote) is True
    assert verify_value_grounded_in_quote("invoice_total", "85000.00", quote) is True
    assert verify_value_grounded_in_quote("po_number", "PO-1001", quote) is True


def test_regression_rounding_tolerance_boundaries():
    """
    Scenario 7: Component sum vs total GST rounding tolerance boundaries:
    - 0 paise difference: PASS
    - <= 100 paise difference: PASS (internal business tolerance)
    - >= 101 paise difference: MISMATCH (HOLD)
    """
    base_components = {"cgst": 50000, "sgst": 50000}  # sum = 100,000 paise (₹1,000.00)

    # 0 difference -> PASS, within_tolerance True
    res0, f0 = reconcile_gst_totals(100000, base_components)
    assert res0["within_tolerance"] is True
    assert res0["status"] == STATUS_PASS
    assert f0 is None

    # +100 paise (₹1.00) -> PASS, within_tolerance True
    res_pos100, f_pos100 = reconcile_gst_totals(99900, base_components)
    assert res_pos100["within_tolerance"] is True
    assert res_pos100["status"] == STATUS_PASS
    assert f_pos100 is not None
    assert f_pos100.finding_code == "gst_total_rounding_tolerance"

    # -100 paise (-₹1.00) -> PASS, within_tolerance True
    res_neg100, f_neg100 = reconcile_gst_totals(100100, base_components)
    assert res_neg100["within_tolerance"] is True
    assert res_neg100["status"] == STATUS_PASS
    assert f_neg100 is not None
    assert f_neg100.finding_code == "gst_total_rounding_tolerance"

    # +101 paise (₹1.01) -> MISMATCH, within_tolerance False
    res_pos101, f_pos101 = reconcile_gst_totals(99899, base_components)
    assert res_pos101["within_tolerance"] is False
    assert res_pos101["status"] == STATUS_MISMATCH
    assert f_pos101 is not None
    assert f_pos101.finding_code == "gst_component_sum_mismatch"

    # -101 paise (-₹1.01) -> MISMATCH, within_tolerance False
    res_neg101, f_neg101 = reconcile_gst_totals(100101, base_components)
    assert res_neg101["within_tolerance"] is False
    assert res_neg101["status"] == STATUS_MISMATCH
    assert f_neg101 is not None
    assert f_neg101.finding_code == "gst_component_sum_mismatch"

