# ad_unit_1_mapping.xlsx — Tracking Decision

**Decided:** 2026-05-19 (Phase 17.1, Plan 01, post checker-iter-1)
**File:** `data/sentinel_db/ad_unit_1_mapping.xlsx` (40 KB, 432 rows × 9 cols)
**Authoritative source:** Marco (TAM&Yield), shared 2026-05-18 in audit response

## Decision: COMMIT to git

### .gitignore state (verified 2026-05-19)

The current `.gitignore` does NOT contain a `data/sentinel_db/` exclusion line.
(CLAUDE.md mentions one but is stale — see commit log for evidence.)
Therefore tracking the xlsx requires NO `.gitignore` allow-rule — `git add`
succeeds directly. If a future maintainer adds a `data/sentinel_db/*`
exclusion, they MUST also add `!data/sentinel_db/ad_unit_1_mapping.xlsx`
immediately after it.

### Rationale

1. File is small (40 KB)
2. Backend `/api/publishers/top` + 5 drilldown endpoints break without it on fresh clone
3. Solo-dev + Claude workflow — no shared-drive automation
4. Authoritative for publisher aggregation correctness

### Refresh procedure (Marco recommended daily; Phase 17.1 scope is one-shot)

1. Marco emails new version OR shares via Drive
2. `cp ~/Downloads/ad_unit_1_mapping.xlsx data/sentinel_db/ad_unit_1_mapping.xlsx`
3. Run the Plan 01 Task 1 Step 2 Python smoke-check (assertions must pass)
4. `git add data/sentinel_db/ad_unit_1_mapping.xlsx && git commit -m "data(17.1): refresh ad_unit mapping YYYY-MM-DD"`
5. Daily cron automation deferred to Phase 18 per 17.1-CONTEXT.md

### Out-of-band alternative (NOT chosen)

Keep file out-of-git, maintain `scripts/sync_ad_unit_mapping.sh` that pulls from a Drive folder. Rejected for solo-dev workflow brittleness.

### File structure (verified 2026-05-19)

| Attribute | Value |
|-----------|-------|
| Shape | 432 rows × 9 columns |
| NULLs | 0 |
| Unique publishers | 259 |
| Columns | ad_unit_id, ad_unit_name, region, publisher_country, account_manager, technical_account_manager, zone, company, publisher |

### Spot-check mappings (verified 2026-05-19)

| ad_unit_name | publisher | Notes |
|--------------|-----------|-------|
| Mondadori | Mondadori | Identity for already-clean names |
| Mondadori_npa | Mondadori | GDPR non-consent variant, RC-(b) Mondadori family folds in |
| Mediamond | Mediamond | SEPARATE from Mondadori — Phase 17 wrongly folded |
| Adgage_mondocore | Mondocore | SEPARATE from Mondadori — Phase 17 wrongly folded |
| AdGage_Vocento | Vocento | AdGage_ prefix normalization works |

### Clusters present

- `OLD` cluster: 147 ad_units (per CONTEXT.md) — exclude from `/api/publishers/top` Top-N ranking via Plan 02 filter
- `test` cluster: 13 ad_units (per CONTEXT.md) — same exclusion path

## Reference

- 17.1-CONTEXT.md — binding decision document
- REQUIREMENTS.md — MAP-01..MAP-10 traceability
- Email Marco 2026-05-18 — original transmission of the mapping
