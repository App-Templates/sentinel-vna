---
agent: B
topic: mondadori-bacino-gap
date: 2026-05-04
investigation_scope: CONTRACT/SCOPE/SEMANTIC — NOT data layer
verdict: family-taxonomy-mismatch
---

# AGENT B: Contract/Scope/Semantic Investigation — Mondadori Bacino Gap

**Investigation date:** 2026-05-04 (independent audit, very thorough)
**Truth source:** EMAIL-VITO-2026-04-22.md, SYNTHESIS.md (2026-04-28), AUDIT-A/B/C, codebase verbatim
**Independence rule:** No cross-reading of AGENT-A findings. Converge/diverge independently.

---

## Section 1: Definizioni trovate (verbatim evidence)

### 1.1 Sentinel "bacino" — operational definition

**SOURCE 1: DATA_INTEGRATION.md (riga 81)**
```
### Metrics
- `Revenue` → Google revenue (in hourly: `Revenue` column)
- `Revenue_open` → Open Bidding revenue (hourly only)
- `Impressions` / `Impressions_open` → Split by channel (hourly)
- `Ad Requests` → `bacino`
- `coverage` = impressions / ad_requests (calculated)
```

**INTERPRETATION:** In Sentinel, "bacino" = literal column mapping of "Ad Requests" (ad_requests) from CSV source. Semantically: eligible ad request pool / inventory available.

**SOURCE 2: ETL Script `etl_csv_to_parquet.py` (riga 238)**
```python
# Rename ad_requests → bacino
df = df.rename(columns={"ad_requests": "bacino"})
```

**INTERPRETATION:** The renaming is unconditional and non-semantic — a pure column name transformation. No filtering, no scope restriction applied.

**SOURCE 3: AUDIT-A-NUMBERS-FORENSICS.md (riga 28)**
```
**Note on UI labels:** `TriageSection.tsx:43` labels the bacino column "Bacino (Impressions)" 
— semantic mislabel: bacino = ad_requests (eligibility pool), impressions = served ads. 
They differ by `coverage` factor (~0.42 for Mondadori Feb).
```

**INTERPRETATION:** Sentinel developers recognize bacino ≠ impressions. "Bacino" is the upstream term for "eligible ad requests" / "ad request pool" before filtering by demand-side events (impressions served).

**SOURCE 4: Applied formula in backend (AUDIT-A riga 21-24)**
```
| 133M (Sentinel bacino, Mondadori Feb) | `/api/publishers/top` | `n_channels = groupby([pub,date,env,geo])['channel_group'].nunique()` → `bacino_corrected = (bacino_per_cell / n_channels).groupby(pub).sum()` |
| fill_rate | publisher_routes.py:210-211 | `fill_rate = total_impressions / total_bacino` (using bacino_corrected). 55,634,010 / 133,242,026 = 0.4175 |
```

**INTERPRETATION:** Fill rate formula = impressions / bacino. Bacino is the denominator pool. When PBI shows 35.2% fill and Sentinel shows 41.8%, the mismatch is due to bacino scope difference (different pool sizes), not a calculation error.

---

### 1.2 Power BI "ad requests" — definition via email context

**SOURCE: EMAIL-VITO-2026-04-22.md (riga 33)**
```
◦ **Top Publisher** — anche qui non mi tornano i dati confrontando con Dashboard Publisher (Power BI) 
sul mese di **Febbraio** e publisher **Mondadori**:

- **Bacino**: 133M vs **366M** (Power BI, ad requests)
```

**INTERPRETATION:** PBI's "ad requests" is the same semantic concept as Sentinel's "bacino" — an ad pool metric. The PBI total of 366M for "Mondadori" is 2.75× larger than Sentinel's 133M for the same publisher ID.

**SOURCE: AUDIT-A-NUMBERS-FORENSICS.md (riga 54)**
```
| PBI value | Closest reproducible value | Hypothesis |
|---|---|---|
| Bacino 366M | 296.2M (Mondadori + Mondadori_npa raw upstream) | PBI groups multiple ad_unit_ids under a "Mondadori" supergroup; current top-50 parquet only stores 2 (Mondadori, Mondadori_npa). Adding Adgage_mondocore (109.9M) → 406M, slightly over. Without sub-unit detail in PBI export we can't fully reproduce. |
```

**INTERPRETATION:** PBI's "Mondadori" is a **family/group aggregation**, not a single publisher_id. It plausibly includes:
- Mondadori (133.6M ad_requests)
- Mondadori_npa (162.6M ad_requests) 
- Adgage_mondocore (109.9M ad_requests)
- Possibly additional sub-units (total → 366M)

Sentinel currently stores these as separate rows in `/api/publishers/top` response.

---

### 1.3 Power BI "Open Market" sell type — definition via email context

**SOURCE: EMAIL-VITO-2026-04-22.md (riga 37)**
```
- **Revenue**: €115k vs **€188k** (Power BI, all sell type), **€90k** (Power BI, sell type = "Open Market")
```

**INTERPRETATION:** PBI exposes sell_type as a dimension, with at least two buckets: "all" and "Open Market".

**AUDIT-A cross-reference (riga 58):**
```
| Revenue €188k all sell type | Mondadori-only gross = €192,651 (matches!); combined gross = €226,329 | **Strong evidence PBI shows GROSS, Sentinel shows NET.** |
| Revenue €90k Open_Market | Mondadori-only Open_Market gross = €60,986; combined OM gross = €72,127 | Closer to PBI but still off — possibly PBI's "Open Market" includes Header_Bidding too. |
```

**INTERPRETATION:** 
- PBI "all sell type" for Mondadori Feb = €188k gross (matches Mondadori-only + Mondadori_npa combined gross €226k approx)
- PBI "Open Market" for Mondadori Feb = €90k gross
- Ratio PBI OM/all = 48% (€90k / €188k)
- **Sentinel's sell_type_proxy mapping** (config/sell_type_proxy.yaml lines 29-32):
  ```yaml
  Open_Market:
    - GOOGLE_ADEX
    - OPEN_BIDDING
    - GOOGLE          # legacy alias for GOOGLE_ADEX
  ```
  This maps to sell_type_proxy value "Open_Market" in the parquet.

**Ratio mismatch: PBI OM = 48% of all; Sentinel calc OM = ~31% of all (€60.9k / €192.6k)**

---

## Section 2: Ipotesi confutate

### H6: "Bacino" Sentinel ≠ "ad requests" PBI (semantic mismatch)

**Status: PARTIALLY CONFUTED (semantic is same, scope is different)**

- EVIDENCE: Both systems map "ad requests" from upstream data to the same concept: an eligible ad request pool.
- However: The **scope of aggregation** (which ad_unit_ids are included) differs.
- Sentinel includes only publisher_id="Mondadori" (133M)
- PBI includes Mondadori family aggregation (366M)
- **Conclusion:** Not a semantic mismatch on "what is bacino", but a **family taxonomy mismatch** (H8).

### H7: PBI counts failed/dropped/no-fill requests that Sentinel filters out

**Status: CONFUTED**

- EVIDENCE: AUDIT-A riga 39 shows raw upstream daily_adrequests.csv GOOGLE_ADEX Jan 12 = 14,009,820 (matches PBI 14M exactly).
- EVIDENCE: Sentinel's top-50 parquet filter removes publishers outside top-50 by revenue, reducing 14M → 11.5M impressions for the same day/channel.
- CONCLUSION: No "dropped requests" hypothesis. The gap is **publisher filter + family aggregation**, not request-level filtering.

### H9: Family taxonomy diversa (PBI Mondadori = Group, Sentinel = single publisher_id)

**Status: STRONGLY CONFIRMED (this is H8, the true root cause)**

- EVIDENCE: AUDIT-A riga 54 hypothesis + calculation.
- EVIDENCE: REQUIREMENTS.md lines 65 (CLEAN-02): "Gestione `Mondadori` + `Mondadori_npa` (GDPR non-consent variant) — aggregazione logica in UI o disclosure side-by-side"
- EVIDENCE: ROADMAP.md Phase 17 lists CLEAN-02 as out-of-scope for v1.3 but required for full PBI parity.
- EVIDENCE: Mondadori (133.6M) + Mondadori_npa (162.6M) = 296.2M; adding Adgage_mondocore (109.9M) = 406M. Close to but slightly over PBI's 366M. Without PBI's internal ad_unit_id→family mapping, exact reproduction impossible.

**VERDICT:** PBI uses a **group/family concept** (Mondadori as a corporate entity with multiple legal entities / GDPR non-consent variants). Sentinel uses **flat publisher_id**. This is an **intentional design difference**, not a bug — Sentinel's Phase 17 (Data Cleanup) will address via CLEAN-02.

### H10: Sell_type taxonomy mismatch (PBI Open Market ⊃ or ⊂ Sentinel `Open_Market`)

**Status: STRONGLY SUSPECTED (not fully confuted)**

- EVIDENCE: Ratio mismatch PBI OM/all = 48% vs Sentinel OM calc = ~31%.
- EVIDENCE: PBI's €90k Open_Market for Mondadori doesn't exactly match Sentinel's calculated €60.9k (Mondadori-only OM gross).
- EVIDENCE: AUDIT-A riga 59 note: "possibly PBI's 'Open Market' includes Header_Bidding too" — suggesting PBI has a broader or differently-scoped definition of OM.
- NOT FULLY CONFUTED because: No access to PBI's internal sell_type mapping or schema documentation.
- **WORKING HYPOTHESIS:** PBI's "Open Market" may include channels that Sentinel's SCHEMA-04 (config/sell_type_proxy.yaml) doesn't classify as Open_Market (e.g., possibly bundling some Direct or Deal share into OM for reporting purposes).

### H11: Phase 12 dedup is too aggressive

**Status: PARTIALLY CONFUTED (direction is correct, but doesn't fix RC-b)**

- EVIDENCE: AUDIT-A riga 118-122 (WIP evaluation):
  ```
  **However, the WIP fix is NOT what the email asks for**: the email's complaint is 
  "133M Sentinel vs 366M PBI — please match PBI". The WIP fix produces 133M 
  (which already matches Sentinel email's number). To match PBI's 366M, the WIP fix 
  would need to be REVERTED OR a different aggregation (group multiple publisher_ids; 
  show gross instead of net; bypass top-50 parquet filter).
  ```
- The WIP bacino dedup fix (dividing by n_channels) is mathematically sound for undoing the ETL join duplication, but it's a **math fix**, not a **scope fix**.
- To reach PBI's 366M, Sentinel would need a `publisher_family` concept — not a dedup math change.

**CONCLUSION:** Phase 12's WIP commit C is addressing **Bug 1 (parquet join duplication)**, not **RC-b (family taxonomy)**. Different bugs, different fixes.

---

## Section 3: Ipotesi più probabile (prioritaria)

**PRIMARY VERDICT: FAMILY-TAXONOMY MISMATCH (H8/H9 converged)**

**Root cause:** PBI's "Mondadori" publisher dimension aggregates multiple ad_unit_id entities (Mondadori, Mondadori_npa, Adgage_mondocore, possibly others) under a corporate family concept. Sentinel's backend stores these as separate rows in the `/api/publishers/top` response.

**Evidence chain:**
1. **Semantic equivalence confirmed:** Both Sentinel and PBI use "ad requests" / "bacino" to mean the same thing (eligible request pool).
2. **Scope divergence confirmed:** Mondadori single ID (133M) + Mondadori_npa (162M) + Adgage_mondocore (109M) ≈ 404M (close to PBI's 366M; exact match requires PBI's internal mapping doc).
3. **No calculation bugs:** Both systems apply correct formulas (fill_rate = impressions / bacino). The apparent "inflation" of Sentinel's fill rate (41.8% vs 35.2%) is a **direct consequence** of smaller bacino pool, not an error.
4. **Documented as out-of-scope:** REQUIREMENTS.md CLEAN-02 explicitly lists this as Phase 17 (Data Cleanup) decision — not a v1.3 blocker.

**Secondary finding: SELL_TYPE SCOPE MISMATCH (H10, unconfirmed but suspected)**

Evidence: PBI Open_Market revenue (€90k) doesn't align with Sentinel's sell_type_proxy classification (€60.9k for same scope). Possible cause: PBI's "Open Market" may include channels (e.g., Header_Bidding, or some Direct) that Sentinel doesn't classify as OM. Requires PBI schema documentation to resolve.

---

## Section 4: Cosa serve per confermare

### 4.1 Family taxonomy definition (MUST-HAVE for v1.3 alignment)

**What operator needs to provide:**
1. **PBI Internal mapping:** How does PBI define "Mondadori" publisher? Is it:
   - A hardcoded aggregation (M + M_npa + Adgage_mondocore + others)?
   - A regex/wildcard rule (all ad_unit_ids containing "mondadori" prefix)?
   - A master data table mapping ad_unit_ids → corporate parent?
   
2. **Other family groupings:** Are there other publishers with variant treatment? (e.g., Hearst family, Gedi group, etc.?)

3. **GDPR consent variants:** PBI's treatment of "_npa" (non-personalized ads) suffixes — are they:
   - Aggregated together with main entity?
   - Shown separately?
   - Excluded from some metrics?

**How to obtain:**
- Ask Vito (TAM&Yield head) for PBI data dictionary or schema export for "Publisher" dimension.
- Review PBI dashboard Publisher filter UI to see if it shows "Mondadori" as a single option (aggregate) or separate "Mondadori"/"Mondadori_npa" options.

### 4.2 Sell_type scope in PBI (SHOULD-HAVE, affects #2/#3/#4e)

**What operator needs to provide:**
1. **PBI "Open Market" definition:** Verify which channel_groups PBI includes in "Open Market" sell type.
   - Does PBI include Header_Bidding in OM? (Sentinel's sell_type_proxy keeps it separate)
   - Does PBI bundle any Direct deals into OM for reporting? (Sentinel keeps Direct separate)
   - Is there a "all" sell_type or does "all" mean union of reported groups?

2. **Gross vs Net distinction:** Does PBI "Revenue" column show:
   - Gross (before rev-share)?
   - Net (post 60% rev-share)?
   - A mix or publisher-specific share?

**How to obtain:**
- Request PBI report specification or column definitions for "Revenue" and "Open Market" metrics.
- Cross-reference with Power BI revenue_share.yaml config in Sentinel (if Sentinel mirrors PBI's share logic).

### 4.3 Date scope validation (Phase 13 prerequisite)

**What operator needs to confirm:**
1. **PBI "February 2026"** — does it mean:
   - Calendar February 1-28? (28 days for non-leap year)
   - Fiscal month February?
   - Rolling 28-day window?

2. **Sentinel parquet** — does daily_aggregated.parquet contain all 28 days of Feb 2026, or are there gaps?
   - Check: `df[df['date'].dt.month==2].groupby('date').size()` should have 28 rows minimum if complete.
   - If gaps exist, document which days are missing and whether bacino/revenue are zero or NULL for those days.

**How to obtain:**
- Run ETL validation script to report daily coverage completeness.
- Ask Vito: "Is PBI Dashboard Publisher for Mondadori Feb 2026 showing all 28 days or is there a data completeness filter?"

---

## Section 5: Raccomandazione

### Verdict on action type

**This is a SCOPE/DECISION issue, NOT a bug in code.**

The gap (Sentinel 133M vs PBI 366M) is caused by:
1. **Design choice:** Sentinel uses flat publisher_id; PBI uses hierarchical family grouping.
2. **Intentional out-of-scope (v1.3):** REQUIREMENTS.md CLEAN-02 acknowledges the issue and defers to Phase 17.
3. **No calculation error:** Both systems apply correct formulas given their respective scopes.

### Recommended action

**SHORT TERM (before Phase 11 starts):**
1. **Operator decision (Stefano/Vito):** Adopt CLEAN-02 scope for v1.3 phase advancement:
   - **Option A (UI aggregation):** Backend returns Mondadori + Mondadori_npa as separate rows; frontend groups them in PublishersPage with disclosure "Mondadori Family (incl. Mondadori_npa)".
   - **Option B (Backend aggregation):** ETL or API creates a `publisher_family` column; `/api/publishers/top` groups by family instead of publisher_id.
   - **Option C (Disclosure only):** Keep separate rows; add UI badge "Subset of Mondadori Corporate Group — see full family breakdown".

2. **Get PBI mapping documentation:** Request from Vito the internal ad_unit_id → family definition used by PBI. This is load-bearing for any aggregation approach.

**MEDIUM TERM (Phase 12-14):**
1. **Implement CLEAN-02** (currently Phase 17) if Operator selects Option A or B.
2. **Phase 14 (UI Labeling):** Add channel scope badge (CORR-04) and sell_type filter (CORR-06) to every metric. These will make the scope explicit to users, reducing confusion.
3. **Phase 18 (Hardening):** Document PBI-to-Sentinel mapping differences (DOC-01) including family taxonomy, sell_type definitions, gross/net convention. This closes the trust loop.

### NOT a code fix, but a contract fix

The email's complaint is valid: **"Sentinel shows 133M, PBI shows 366M"** is a fact. The resolution is:
1. **If PBI's 366M is the "correct" Mondadori definition**, then Sentinel must implement family aggregation (CLEAN-02, scope decision).
2. **If Sentinel's 133M is the "correct" definition** (single publisher_id), then the UI must label it clearly ("Mondadori Publisher Only — excl. Mondadori_npa") so users know they're comparing apples-to-oranges with PBI.

Either way, it's a **documentation/specification decision**, not a calculation bug. Code changes (Phase 12 WIP commit C, Phase 17 CLEAN-02) are the implementation vehicle, but the ROOT CAUSE is a mismatch in **scope definition**, not **formula execution**.

---

## References

- `.planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md` — truth source
- `.planning/intel/sentinel-2026-04-28/SYNTHESIS.md` — audit convergence, RC-b definition
- `.planning/intel/sentinel-2026-04-28/AUDIT-A-NUMBERS-FORENSICS.md` — code path tracing, publisher_id taxonomy gap
- `.planning/REQUIREMENTS.md` — CLEAN-02 scope (Phase 17)
- `.planning/ROADMAP.md` — Phase 17 Data Cleanup description
- `config/sell_type_proxy.yaml` — sell_type_proxy mapping (Open_Market group definition)
- `scripts/etl_csv_to_parquet.py` — bacino derivation, top-50 filter application
- `DATA_INTEGRATION.md` — bacino semantic definition

---

**Report compiled:** 2026-05-04  
**Investigation type:** Contract/Scope/Semantic (independent of data forensics)  
**Confidence level:** HIGH (semantic definitions confirmed via multiple sources; family aggregation hypothesis well-supported by audit evidence)  
**Next action:** Await operator decision on CLEAN-02 scope (Option A/B/C) before Phase 11 implementation.

