# FinTrust AI — India GST Integrity Engine Specification

## 1. Overview & Architectural Role

The **India GST Integrity Engine** is a dedicated, deterministic verification layer within FinTrust AI. It analyzes declared Goods and Services Tax (GST) data on incoming invoices against statutory Indian tax rules, trusted SQLite purchase order baselines, and master vendor records.

The engine does not guess or use generative models for financial rules. Instead, it applies authoritative, statutory deterministic logic across six core dimensions:
1. **GSTIN Structural & Checksum Validation** (Luhn mod 36 algorithm).
2. **State & Union Territory Catalogue Identification** (38 official GST state codes).
3. **Supplier & Recipient GSTIN Reconciliation** against trusted database master records.
4. **Place of Supply (POS) Consistency** against purchase order authorizations.
5. **Tax-Type Classification** (Intra-State CGST+SGST/UTGST vs. Inter-State IGST).
6. **Component Reconciliation & Integer Paise Rounding Tolerance** (CGST, SGST, UTGST, IGST, Cess).

---

## 2. Statutory References & Legal Foundations

The GST Integrity Engine implements codified rules from Indian tax statutes:

- **Rule 10(1), Central Goods and Services Tax (CGST) Rules, 2017** (read with Section 25(12) of the CGST Act, 2017): Governs the issuance of the certificate of registration in FORM GST REG-06 and defines the official 15-character alphanumeric Goods and Services Tax Identification Number (GSTIN) structure:
  - Characters 1–2: Two-digit State/UT code.
  - Characters 3–12: Ten-character Permanent Account Number (PAN) or Tax Deduction and Collection Account Number (TAN) of the entity.
  - Characters 13–14: Entity registration code.
  - Character 15: Checksum digit generated via the Luhn mod 36 algorithm.
- **Rule 46, CGST Rules, 2017**: Mandates tax invoice particulars, including supplier GSTIN, recipient GSTIN, place of supply, and individual component breakdowns for CGST, SGST, UTGST, IGST, and Cess.
- **Section 7, Integrated Goods and Services Tax (IGST) Act, 2017**: Defines inter-state supplies where the location of the supplier and the place of supply are in different States, different Union Territories, or a State and a Union Territory. Inter-state supplies mandate Integrated Tax (IGST).
- **Section 8, IGST Act, 2017**: Defines intra-state supplies where the location of the supplier and the place of supply are in the same State or same Union Territory. Intra-state supplies mandate Central Tax (CGST) and State Tax (SGST) or Union Territory Tax (UTGST).
- **Sections 10 & 12, IGST Act, 2017**: Principles for determining the Place of Supply (POS) for goods and services. FinTrust AI performs evidence verification of the declared invoice POS against the confirmed Purchase Order delivery baseline; it does not legally adjudicate complex multi-party POS determination under Sections 10 through 14 of the IGST Act (such as bill-to/ship-to arrangements or complex cross-border scenarios).
- **Section 1(2), Union Territory Goods and Services Tax (UTGST) Act, 2017**: Establishes UTGST for Union Territories without a legislative assembly.

---

## 3. State & Union Territory Catalogue

The engine maintains a static, exhaustive catalogue of official 2-digit Indian State and Union Territory GST codes issued under the GST framework. Critically, it distinguishes between Union Territories with legislative assemblies (which levy SGST) and Union Territories without legislative assemblies (which levy UTGST):

| Code | State / Union Territory | Category | Applicable State Tax |
| :--- | :--- | :--- | :--- |
| `01` | Jammu and Kashmir | Union Territory (with Legislature) | **SGST** |
| `02` | Himachal Pradesh | State | **SGST** |
| `03` | Punjab | State | **SGST** |
| `04` | Chandigarh | Union Territory (without Legislature) | **UTGST** |
| `05` | Uttarakhand | State | **SGST** |
| `06` | Haryana | State | **SGST** |
| `07` | Delhi | Union Territory (with Legislature) | **SGST** |
| `08` | Rajasthan | State | **SGST** |
| `09` | Uttar Pradesh | State | **SGST** |
| `10` | Bihar | State | **SGST** |
| `24` | Gujarat | State | **SGST** |
| `26` | Dadra and Nagar Haveli and Daman and Diu | Union Territory (without Legislature) | **UTGST** |
| `27` | Maharashtra | State | **SGST** |
| `29` | Karnataka | State | **SGST** |
| `31` | Lakshadweep | Union Territory (without Legislature) | **UTGST** |
| `32` | Kerala | State | **SGST** |
| `33` | Tamil Nadu | State | **SGST** |
| `34` | Puducherry | Union Territory (with Legislature) | **SGST** |
| `35` | Andaman and Nicobar Islands | Union Territory (without Legislature) | **UTGST** |
| `36` | Telangana | State | **SGST** |
| `37` | Andhra Pradesh | State | **SGST** |
| `38` | Ladakh | Union Territory (without Legislature) | **UTGST** |

---

## 4. Luhn Mod 36 Checksum Algorithm

The 15th character of every standard Indian GSTIN is a checksum calculated across the first 14 characters using a modified Luhn algorithm over the base-36 alphanumeric character set (`0-9` followed by `A-Z`, representing values `0` through `35`).

### Algorithm Steps:
1. Map each character of the 14-character prefix to its numeric value `0–35`.
2. Apply alternating weights of `1` and `2` from index `0` to `13` (even index: weight `1`, odd index: weight `2`).
3. For each character:
   $$\text{factor} = \text{code\_point} \times \text{weight}$$
   $$\text{sum} += (\text{factor} // 36) + (\text{factor} \% 36)$$
4. Compute the check code:
   $$\text{check\_code} = (36 - (\text{sum} \% 36)) \% 36$$
5. Map `check_code` back to the Base-36 character set.

### Test Vectors Verified:
- `27AAPCA1234A1Z5` -> Checksum: `5` (Maharashtra, Valid)
- `29ABCDE1234F1ZW` -> Checksum: `W` (Karnataka, Valid)
- `04AAACG1234D1ZG` -> Checksum: `G` (Chandigarh, Valid)
- `27AABCF1234F1Z4` -> Checksum: `4` (Buyer organization demo GSTIN, Valid)
- `27AAPCA1234A1Z9` -> Checksum: `5` expected, `9` observed -> `CHECKSUM_MISMATCH`

---

## 5. Tax Type Classification & Component Reconciliation

### Standard Domestic Supply Profiles:
- **Intra-State Supply** ($\text{Supplier State} = \text{Place of Supply}$):
  - In a State or UT with legislature: Requires Central Tax (**CGST**) + State Tax (**SGST**). Charging IGST or UTGST triggers a deterministic `HOLD`.
  - In a UT without legislature: Requires Central Tax (**CGST**) + Union Territory Tax (**UTGST**). Charging SGST or IGST triggers a deterministic `HOLD`.
- **Inter-State Supply** ($\text{Supplier State} \neq \text{Place of Supply}$):
  - Requires Integrated Tax (**IGST**). Charging CGST, SGST, or UTGST triggers a deterministic `HOLD` (`prohibited_intra_tax_on_inter_state`).

### Component Reconciliation & Rounding Tolerance:
- All monetary arithmetic is strictly computed in **integer paise** ($1\text{ INR} = 100\text{ paise}$) using Python `Decimal` to avoid binary floating-point inaccuracy.
- The engine reconciles:
  $$\text{Declared Total GST} \stackrel{?}{=} \text{CGST} + \text{SGST} + \text{UTGST} + \text{IGST} + \text{Cess}$$
- **Internal Business Rounding Tolerance**: While Section 170 of the CGST Act permits rounding tax amounts to the nearest rupee, line-by-line commercial rounding in multi-item invoices often creates small fractional discrepancies against header totals. FinTrust AI enforces an internal business rule tolerance of $\le 100\text{ paise}$ ($\le ₹1.00$) between itemized component sums and declared total GST (`gst_total_rounding_tolerance`). Differences $> 100\text{ paise}$ trigger `HOLD` (`gst_component_sum_mismatch`). This ₹1.00 threshold is an internal verification policy, not a statutory tax margin.

---

## 6. Operational Boundaries & Mandatory Disclaimers

### Disclaimer 1: Offline Syntactic Validation Only
> **Syntactic structure and Luhn mod 36 checksum validation confirms format adherence and catches transcription typos only. FinTrust AI operates entirely offline; it does not scrape, bypass CAPTCHA, or integrate directly with the government GST Portal (gst.gov.in). Checksum validity does not prove that a GSTIN is currently active, suspended, or cancelled by tax authorities.**

### Disclaimer 2: Standard Domestic Scope & Manual Review
> **Automated tax classification applies standard domestic supply rules under Sections 7, 8, 10, and 12 of the IGST Act, 2017. Complex transactions (including Special Economic Zone / SEZ supplies, export/import transactions, and reverse charge mechanisms) require manual tax specialist review.**
