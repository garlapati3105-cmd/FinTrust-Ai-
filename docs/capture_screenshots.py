import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).resolve().parent / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1540, "height": 960},
            device_scale_factor=2,
        )
        page = context.new_page()

        print("Navigating to http://localhost:3000 ...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(2)

        # ---------------------------------------------------------------------
        # Screenshot 1: Overview Dashboard
        # ---------------------------------------------------------------------
        print("Capturing 1: Overview Dashboard...")
        page.locator("button:has-text('Overview')").first.click()
        time.sleep(2)
        page.wait_for_selector("text=Registered vendors")
        # Ensure KPI numbers are loaded (not LOADING...)
        page.wait_for_function("() => !document.body.innerText.includes('LOADING...')")
        dashboard_path = OUTPUT_DIR / "dashboard.png"
        page.screenshot(path=str(dashboard_path), full_page=False)
        print(f"Saved: {dashboard_path}")

        # ---------------------------------------------------------------------
        # Screenshot 2: Invoice Verification Workspace (Form & Evidence Baseline)
        # ---------------------------------------------------------------------
        print("Capturing 2: Invoice Verification Workspace...")
        page.locator("button:has-text('Invoice Verification')").first.click()
        time.sleep(1.5)
        preset_btn = page.locator("button:has-text('Intra-State Clean')").first
        if preset_btn.is_visible():
            preset_btn.click()
            time.sleep(1.5)

        page.wait_for_selector("text=PO-1001")
        inv_verif_path = OUTPUT_DIR / "invoice-verification.png"
        page.screenshot(path=str(inv_verif_path), full_page=False)
        print(f"Saved: {inv_verif_path}")

        # ---------------------------------------------------------------------
        # Screenshot 3: Clean Invoice Verification Result (APPROVE)
        # ---------------------------------------------------------------------
        print("Capturing 3: Clean Invoice Verification (APPROVE)...")
        # Ensure fresh unique invoice number
        unique_clean_num = f"INV-DEMO-APPROVE-{int(time.time()) % 10000}"
        page.locator("input#input-inv-num").fill(unique_clean_num)
        time.sleep(0.5)

        verify_btn = page.locator("button:has-text('Review and Verify Invoice')").first
        verify_btn.click()
        page.wait_for_selector("text=Decision: APPROVE", timeout=15000)
        time.sleep(1.5)
        clean_app_path = OUTPUT_DIR / "clean-approval.png"
        page.screenshot(path=str(clean_app_path), full_page=False)
        print(f"Saved: {clean_app_path}")

        # ---------------------------------------------------------------------
        # Screenshot 4: GST Mismatch / HOLD Result
        # ---------------------------------------------------------------------
        print("Capturing 4: GST Mismatch / HOLD Result...")
        mismatch_preset = page.locator("button:has-text('Tax Type Mismatch')").first
        mismatch_preset.click()
        time.sleep(1.5)

        unique_mismatch_num = f"INV-DEMO-MISMATCH-{int(time.time()) % 10000}"
        page.locator("input#input-inv-num").fill(unique_mismatch_num)
        time.sleep(0.5)

        verify_btn = page.locator("button:has-text('Review and Verify Invoice')").first
        verify_btn.click()
        page.wait_for_selector("text=Decision: HOLD", timeout=15000)
        time.sleep(1.5)
        gst_hold_path = OUTPUT_DIR / "gst-mismatch-hold.png"
        page.screenshot(path=str(gst_hold_path), full_page=False)
        print(f"Saved: {gst_hold_path}")

        # ---------------------------------------------------------------------
        # Screenshot 5: Risk Monitoring
        # ---------------------------------------------------------------------
        print("Capturing 5: Risk Monitoring...")
        page.locator("button:has-text('Risk Monitoring')").first.click()
        time.sleep(2)
        page.wait_for_selector("text=Risk")
        risk_path = OUTPUT_DIR / "risk-monitoring.png"
        page.screenshot(path=str(risk_path), full_page=False)
        print(f"Saved: {risk_path}")

        # ---------------------------------------------------------------------
        # Screenshot 6: Audit Trail
        # ---------------------------------------------------------------------
        print("Capturing 6: Audit Trail...")
        page.locator("button:has-text('Audit Trail')").first.click()
        time.sleep(2)
        page.wait_for_selector("text=Audit")
        audit_path = OUTPUT_DIR / "audit-trail.png"
        page.screenshot(path=str(audit_path), full_page=False)
        print(f"Saved: {audit_path}")

        browser.close()
        print("\nAll 6 screenshots successfully captured!")

if __name__ == "__main__":
    run()
