#!/usr/bin/env python3
"""
Data Coherence Audit: verify JSON seasonal data matches parquet reality.
Checks:
1. Publisher IDs exist in parquet
2. Yearly avg eCPM values are plausible (cross-check against raw parquet)
3. eCPM pattern delta percentages are reasonable
4. All labels/text are in Italian (no English remnants)
5. Optimization windows publisher IDs exist, have 2024+2025 data, Italian text
6. Seasonal analysis periods and week mappings
7. Cross-check sample publisher (mondadori) eCPM values against parquet
"""

import json
import re
import sys
import os
import numpy as np

import pyarrow.parquet as pq
import pandas as pd

BASE = "/Users/admintemp/Downloads/Claude/value-network-alerting"
PARQUET = os.path.join(BASE, "data/baseline/daily_adrequests_aggregated.parquet")
ENRICHED = os.path.join(BASE, "data/seasonal/enriched-recurring-patterns.json")
OPTWIN = os.path.join(BASE, "data/seasonal/optimization-windows-enriched.json")
SEASONAL = os.path.join(BASE, "data/seasonal/ecpm-seasonal-analysis.json")

# English words that should NOT appear in Italian labels/text
ENGLISH_WORDS = re.compile(
    r'\b(Drop|Surge|Dip|Rise|Summer|Winter|Spring|Fall|Autumn|Christmas|'
    r'New Year|Valentine|Back to School|Black Friday|Holiday|Revenue Drop|'
    r'Revenue Surge|Impression Drop|Coverage Drop|Traffic Drop)\b',
    re.IGNORECASE
)

issues = []
warnings = []
info = []

def issue(msg):
    issues.append(msg)
    print(f"  [ISSUE] {msg}")

def warn(msg):
    warnings.append(msg)
    print(f"  [WARN]  {msg}")

def ok(msg):
    info.append(msg)
    print(f"  [OK]    {msg}")


# ── Load data ──────────────────────────────────────────────────────────────
print("=" * 70)
print("LOADING DATA")
print("=" * 70)

table = pq.read_table(PARQUET)
df = table.to_pandas()
print(f"Parquet loaded: {len(df)} rows, columns: {list(df.columns)}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")

pub_col = 'publisher_id'
rev_col = 'revenue'
imp_col = 'impressions'
print(f"Publisher column: '{pub_col}'")
parquet_publishers = set(df[pub_col].str.lower().str.strip().unique())
print(f"Unique publishers in parquet: {len(parquet_publishers)}")
print(f"Sample publishers: {sorted(list(parquet_publishers))[:10]}")

with open(ENRICHED) as f:
    enriched = json.load(f)

with open(OPTWIN) as f:
    optwin = json.load(f)

with open(SEASONAL) as f:
    seasonal = json.load(f)


# ── 1. Enriched Recurring Patterns ────────────────────────────────────────
print("\n" + "=" * 70)
print("CHECK 1: enriched-recurring-patterns.json")
print("=" * 70)

enriched_pubs = list(enriched.get("publishers", {}).keys())
print(f"Publishers in enriched JSON: {len(enriched_pubs)}")

# 1a. Publisher IDs exist in parquet
print("\n--- 1a. Publisher ID existence ---")
missing_pubs = []
for pid in enriched_pubs:
    pid_lower = pid.lower().strip()
    if pid_lower not in parquet_publishers:
        missing_pubs.append(pid)
if missing_pubs:
    issue(f"Publishers in enriched JSON but NOT in parquet: {missing_pubs}")
else:
    ok(f"All {len(enriched_pubs)} publishers exist in parquet")

# 1b. Yearly avg eCPM cross-check (sample 4 publishers)
print("\n--- 1b. Yearly avg eCPM cross-check ---")

# Compute eCPM from parquet: revenue / impressions * 1000
df['date'] = pd.to_datetime(df['date'])
df['year'] = df['date'].dt.year
print(f"Revenue col: {rev_col}, Impressions col: {imp_col}")

# We need to compute weekly eCPM per publisher
# First, let's understand the data better
sample_pubs_to_check = []
for p in ['mondadori', 'vocento', 'adplay', 'fanpage']:
    if p in enriched.get("publishers", {}):
        sample_pubs_to_check.append(p)
if len(sample_pubs_to_check) < 3:
    sample_pubs_to_check = enriched_pubs[:4]

print(f"Cross-checking publishers: {sample_pubs_to_check}")

for pub_name in sample_pubs_to_check:
    pub_data = enriched["publishers"][pub_name]
    yearly = pub_data.get("yearly_avg", {})

    # Filter parquet for this publisher
    mask = df[pub_col].str.lower().str.strip() == pub_name.lower()
    pub_df = df[mask]

    if len(pub_df) == 0:
        issue(f"Publisher '{pub_name}' has 0 rows in parquet")
        continue

    for year in [2024, 2025]:
        json_ecpm = yearly.get(f"ecpm_{year}")
        if json_ecpm is None:
            continue

        year_df = pub_df[pub_df['year'] == year]
        if len(year_df) == 0:
            warn(f"Publisher '{pub_name}' has no data for {year}")
            continue

        # Try to compute eCPM from available columns
        if rev_col and imp_col:
            total_rev = year_df[rev_col].sum()
            total_imp = year_df[imp_col].sum()
            if total_imp > 0:
                computed_ecpm = total_rev / total_imp * 1000
                diff_pct = abs(computed_ecpm - json_ecpm) / json_ecpm * 100
                if diff_pct > 15:
                    issue(f"eCPM mismatch for {pub_name} {year}: JSON={json_ecpm:.4f}, computed={computed_ecpm:.4f} (diff={diff_pct:.1f}%)")
                elif diff_pct > 5:
                    warn(f"eCPM slight diff for {pub_name} {year}: JSON={json_ecpm:.4f}, computed={computed_ecpm:.4f} (diff={diff_pct:.1f}%)")
                else:
                    ok(f"eCPM match for {pub_name} {year}: JSON={json_ecpm:.4f}, computed={computed_ecpm:.4f} (diff={diff_pct:.1f}%)")
        # Also check other yearly_avg metrics if columns available
        for metric, json_key in [('revenue', f'revenue_{year}'), ('impressions', f'impressions_{year}')]:
            json_val = yearly.get(json_key)
            if json_val is None:
                continue
            col = rev_col if metric == 'revenue' else imp_col
            if col:
                total = year_df[col].sum()
                diff_pct = abs(total - json_val) / max(json_val, 1) * 100
                if diff_pct > 15:
                    issue(f"{metric} mismatch for {pub_name} {year}: JSON={json_val:.2f}, parquet={total:.2f} (diff={diff_pct:.1f}%)")
                elif diff_pct > 5:
                    warn(f"{metric} slight diff for {pub_name} {year}: JSON={json_val:.2f}, parquet={total:.2f} (diff={diff_pct:.1f}%)")
                else:
                    ok(f"{metric} match for {pub_name} {year}: JSON={json_val:.2f}, parquet={total:.2f} (diff={diff_pct:.1f}%)")


# 1c. eCPM pattern delta percentages: not all identical, reasonable range
print("\n--- 1c. eCPM pattern delta percentages ---")
all_deltas_2024 = []
all_deltas_2025 = []
identical_count = 0
total_patterns = 0

for pub_name, pub_data in enriched.get("publishers", {}).items():
    for pattern in pub_data.get("ecpm_patterns", []):
        total_patterns += 1
        d24 = pattern.get("avg_delta_pct_2024")
        d25 = pattern.get("avg_delta_pct_2025")
        if d24 is not None:
            all_deltas_2024.append(d24)
        if d25 is not None:
            all_deltas_2025.append(d25)
        if d24 is not None and d25 is not None and d24 == d25:
            identical_count += 1

if total_patterns > 0:
    print(f"Total eCPM patterns: {total_patterns}")
    if all_deltas_2024:
        print(f"2024 deltas: min={min(all_deltas_2024):.2f}%, max={max(all_deltas_2024):.2f}%, std={np.std(all_deltas_2024):.2f}")
    if all_deltas_2025:
        print(f"2025 deltas: min={min(all_deltas_2025):.2f}%, max={max(all_deltas_2025):.2f}%, std={np.std(all_deltas_2025):.2f}")

    identical_pct = identical_count / total_patterns * 100
    if identical_pct > 30:
        issue(f"{identical_pct:.0f}% of patterns have identical 2024/2025 deltas ({identical_count}/{total_patterns})")
    elif identical_pct > 10:
        warn(f"{identical_pct:.0f}% of patterns have identical 2024/2025 deltas ({identical_count}/{total_patterns})")
    else:
        ok(f"Only {identical_pct:.0f}% patterns have identical 2024/2025 deltas - good variance")

    # Check for extreme values
    all_deltas = all_deltas_2024 + all_deltas_2025
    extreme = [d for d in all_deltas if abs(d) > 100]
    if extreme:
        warn(f"Found {len(extreme)} extreme delta values (>100%): {extreme[:5]}...")


# 1d. Italian language check on enriched patterns
print("\n--- 1d. Italian language check (enriched patterns) ---")
english_found = []
for pub_name, pub_data in enriched.get("publishers", {}).items():
    # Check ecpm_patterns
    for pattern in pub_data.get("ecpm_patterns", []):
        for field in ["label", "rationale", "driver_explanation"]:
            text = pattern.get(field, "")
            if text and ENGLISH_WORDS.search(text):
                english_found.append(f"{pub_name} ecpm_pattern '{pattern.get('id')}' field '{field}': '{ENGLISH_WORDS.search(text).group()}'")

    # Check hidden_patterns
    for pattern in pub_data.get("hidden_patterns", []):
        for field in ["label", "business_impact"]:
            text = pattern.get(field, "")
            if text and ENGLISH_WORDS.search(text):
                english_found.append(f"{pub_name} hidden_pattern '{pattern.get('id')}' field '{field}': '{ENGLISH_WORDS.search(text).group()}'")

    # Check danger_zones
    for dz in pub_data.get("danger_zones", []):
        for field in ["label", "explanation"]:
            text = dz.get(field, "")
            if text and ENGLISH_WORDS.search(text):
                english_found.append(f"{pub_name} danger_zone '{dz.get('id')}' field '{field}': '{ENGLISH_WORDS.search(text).group()}'")

if english_found:
    issue(f"Found {len(english_found)} English remnants in enriched patterns:")
    for ef in english_found[:10]:
        print(f"    - {ef}")
else:
    ok("No English remnants found in enriched patterns (labels, rationale, business_impact, explanations)")


# ── 2. Optimization Windows ──────────────────────────────────────────────
print("\n" + "=" * 70)
print("CHECK 2: optimization-windows-enriched.json")
print("=" * 70)

optwin_pubs = list(optwin.get("publishers", {}).keys())
print(f"Publishers in optwin JSON: {len(optwin_pubs)}")

# 2a. Publisher IDs exist in parquet
print("\n--- 2a. Publisher ID existence ---")
missing_optwin = []
for pid in optwin_pubs:
    if pid.lower().strip() not in parquet_publishers:
        missing_optwin.append(pid)
if missing_optwin:
    issue(f"Publishers in optwin JSON but NOT in parquet: {missing_optwin}")
else:
    ok(f"All {len(optwin_pubs)} publishers exist in parquet")

# 2b. Both 2024 and 2025 data for top publishers
print("\n--- 2b. Year coverage in optimization windows ---")
pubs_missing_years = []
for pub_name, pub_data in optwin.get("publishers", {}).items():
    windows = pub_data.get("windows", [])
    years = set(w.get("year") for w in windows)
    if 2024 not in years and 2025 not in years:
        pubs_missing_years.append(f"{pub_name}: has years {years}")
    elif 2025 not in years:
        pubs_missing_years.append(f"{pub_name}: missing 2025 (has {years})")

if pubs_missing_years:
    warn(f"Publishers missing year data in optwin: {len(pubs_missing_years)}")
    for p in pubs_missing_years[:5]:
        print(f"    - {p}")
else:
    ok("All publishers have 2025 data in optimization windows")

# 2c. Italian language check on optwin
print("\n--- 2c. Italian language check (optimization windows) ---")
english_optwin = []
for pub_name, pub_data in optwin.get("publishers", {}).items():
    for window in pub_data.get("windows", []):
        for field in ["driver_explanation", "period_label"]:
            text = window.get(field, "")
            if text and ENGLISH_WORDS.search(text):
                english_optwin.append(f"{pub_name} window '{window.get('period_id')}' field '{field}': '{ENGLISH_WORDS.search(text).group()}'")

if english_optwin:
    issue(f"Found {len(english_optwin)} English remnants in optwin:")
    for ef in english_optwin[:10]:
        print(f"    - {ef}")
else:
    ok("No English remnants found in optimization windows")


# ── 3. Seasonal Analysis ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CHECK 3: ecpm-seasonal-analysis.json")
print("=" * 70)

# 3a. Period labels in Italian
print("\n--- 3a. Period labels in Italian ---")
english_seasonal = []
for period in seasonal.get("seasonal_periods", []):
    label = period.get("label", "")
    if ENGLISH_WORDS.search(label):
        english_seasonal.append(f"period '{period.get('id')}' label: '{label}'")

# Also check for specific English period names
for period in seasonal.get("seasonal_periods", []):
    label = period.get("label", "")
    # Check for common English that might not be in our regex
    if re.search(r'\b(Post-New Year|Valentine\'?s?\s+Day)\b', label, re.IGNORECASE):
        english_seasonal.append(f"period '{period.get('id')}' label: '{label}' (English holiday name)")

if english_seasonal:
    issue(f"Found English in seasonal labels: {english_seasonal}")
else:
    ok("All seasonal period labels are in Italian")

# Check for "Singles Day" and "Black Friday" which are international terms
intl_terms = []
for period in seasonal.get("seasonal_periods", []):
    label = period.get("label", "")
    pid = period.get("id", "")
    if "Singles Day" in label:
        intl_terms.append(f"'{pid}': '{label}' -- 'Singles Day' is English")
    if "Black Friday" in label:
        intl_terms.append(f"'{pid}': '{label}' -- 'Black Friday' is international, acceptable")

if intl_terms:
    for t in intl_terms:
        warn(f"International term in seasonal: {t}")

# 3b. Week mappings coverage
print("\n--- 3b. Week mappings coverage ---")
week_map = seasonal.get("week_date_ranges", {})
mapped_weeks = set(int(k) for k in week_map.keys())
all_weeks_1_52 = set(range(1, 53))
missing_weeks = all_weeks_1_52 - mapped_weeks
extra_weeks = mapped_weeks - all_weeks_1_52

if missing_weeks:
    warn(f"Missing weeks in mapping: {sorted(missing_weeks)}")
else:
    ok("All 52 weeks are mapped")

if extra_weeks:
    warn(f"Extra weeks in mapping: {sorted(extra_weeks)}")

# Check that all periods' weeks are covered by mappings
period_weeks = set()
for period in seasonal.get("seasonal_periods", []):
    for w in period.get("weeks", []):
        period_weeks.add(w)

unmapped_period_weeks = period_weeks - mapped_weeks
if unmapped_period_weeks:
    issue(f"Period weeks NOT in week_date_ranges: {sorted(unmapped_period_weeks)}")
else:
    ok("All period weeks have date range mappings")

# Check for gaps between periods
all_period_weeks = set()
for period in seasonal.get("seasonal_periods", []):
    for w in period.get("weeks", []):
        all_period_weeks.add(w)
gap_weeks = all_weeks_1_52 - all_period_weeks
if gap_weeks:
    warn(f"Weeks not assigned to any period: {sorted(gap_weeks)} ({len(gap_weeks)} weeks)")


# ── 4. Cross-check: sample publisher eCPM vs parquet ─────────────────────
print("\n" + "=" * 70)
print("CHECK 4: Cross-check sample publisher weekly eCPM")
print("=" * 70)

# Pick mondadori or first available
cross_check_pub = None
for p in ['mondadori', 'vocento', 'fanpage']:
    if p in enriched.get("publishers", {}):
        cross_check_pub = p
        break

if cross_check_pub is None:
    cross_check_pub = enriched_pubs[0] if enriched_pubs else None

if cross_check_pub:
    print(f"\nCross-checking: {cross_check_pub}")

    # Get parquet data for this publisher
    mask = df[pub_col].str.lower().str.strip() == cross_check_pub.lower()
    pub_df = df[mask].copy()
    pub_df['date'] = pd.to_datetime(pub_df['date'])

    # Filter 2025
    pub_2025 = pub_df[pub_df['date'].dt.year == 2025].copy()
    print(f"Rows for {cross_check_pub} in 2025: {len(pub_2025)}")

    if len(pub_2025) > 0:
        # Add ISO week
        pub_2025['week'] = pub_2025['date'].dt.isocalendar().week.astype(int)

        # Compute weekly eCPM
        # Need revenue and impressions
        if rev_col and imp_col:
            weekly = pub_2025.groupby('week').agg({
                rev_col: 'sum',
                imp_col: 'sum'
            }).reset_index()
            weekly['ecpm'] = weekly[rev_col] / weekly[imp_col] * 1000
            weekly['ecpm'] = weekly['ecpm'].replace([np.inf, -np.inf], np.nan)
            weekly = weekly.dropna(subset=['ecpm'])

            yearly_avg_ecpm = weekly['ecpm'].mean()
            print(f"Computed yearly avg weekly eCPM for {cross_check_pub} 2025: {yearly_avg_ecpm:.4f}")

            json_ecpm_2025 = enriched["publishers"][cross_check_pub]["yearly_avg"].get("ecpm_2025")
            if json_ecpm_2025:
                diff = abs(yearly_avg_ecpm - json_ecpm_2025) / json_ecpm_2025 * 100
                if diff > 15:
                    issue(f"Cross-check eCPM mismatch {cross_check_pub} 2025: JSON={json_ecpm_2025:.4f}, computed weekly avg={yearly_avg_ecpm:.4f} ({diff:.1f}% diff)")
                else:
                    ok(f"Cross-check eCPM for {cross_check_pub} 2025: JSON={json_ecpm_2025:.4f}, computed={yearly_avg_ecpm:.4f} ({diff:.1f}% diff)")

            # Check optimization windows for this publisher
            if cross_check_pub in optwin.get("publishers", {}):
                windows = optwin["publishers"][cross_check_pub]["windows"]
                # Check a sample window's eCPM
                for window in windows[:3]:
                    if window.get("year") == 2025:
                        win_weeks = window.get("weeks", [])
                        win_data = weekly[weekly['week'].isin(win_weeks)]
                        if len(win_data) > 0:
                            computed_win_ecpm = win_data['ecpm'].mean()
                            json_win_ecpm = window.get("avg_ecpm")
                            if json_win_ecpm:
                                diff = abs(computed_win_ecpm - json_win_ecpm) / json_win_ecpm * 100
                                period = window.get("period_label", window.get("period_id", "?"))
                                if diff > 20:
                                    issue(f"Window eCPM mismatch {cross_check_pub} '{period}' W{win_weeks}: JSON={json_win_ecpm:.4f}, computed={computed_win_ecpm:.4f} ({diff:.1f}% diff)")
                                elif diff > 10:
                                    warn(f"Window eCPM slight diff {cross_check_pub} '{period}' W{win_weeks}: JSON={json_win_ecpm:.4f}, computed={computed_win_ecpm:.4f} ({diff:.1f}% diff)")
                                else:
                                    ok(f"Window eCPM match {cross_check_pub} '{period}' W{win_weeks}: JSON={json_win_ecpm:.4f}, computed={computed_win_ecpm:.4f} ({diff:.1f}% diff)")
        else:
            warn(f"Cannot compute eCPM: no revenue or impressions columns found")
else:
    warn("No publisher available for cross-check")


# ── 5. Additional checks ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CHECK 5: Additional consistency checks")
print("=" * 70)

# 5a. Check that all enriched publishers match optwin publishers
print("\n--- 5a. Publisher set consistency ---")
enriched_set = set(enriched.get("publishers", {}).keys())
optwin_set = set(optwin.get("publishers", {}).keys())

only_enriched = enriched_set - optwin_set
only_optwin = optwin_set - enriched_set

if only_enriched:
    warn(f"Publishers in enriched but NOT in optwin ({len(only_enriched)}): {sorted(only_enriched)[:10]}")
if only_optwin:
    warn(f"Publishers in optwin but NOT in enriched ({len(only_optwin)}): {sorted(only_optwin)[:10]}")
if not only_enriched and not only_optwin:
    ok(f"Publisher sets match between enriched ({len(enriched_set)}) and optwin ({len(optwin_set)})")

# 5b. Check that consistency_score is in [0, 1] range
print("\n--- 5b. Consistency score ranges ---")
bad_scores = []
for pub_name, pub_data in enriched.get("publishers", {}).items():
    for pattern in pub_data.get("ecpm_patterns", []):
        score = pattern.get("consistency_score")
        if score is not None and (score < 0 or score > 1):
            bad_scores.append(f"{pub_name}/{pattern.get('id')}: {score}")
    for pattern in pub_data.get("hidden_patterns", []):
        score = pattern.get("consistency_score")
        if score is not None and (score < 0 or score > 1):
            bad_scores.append(f"{pub_name}/{pattern.get('id')}: {score}")

if bad_scores:
    issue(f"Consistency scores outside [0,1]: {bad_scores}")
else:
    ok("All consistency scores are in [0, 1] range")

# 5c. Danger zones check - verify they exist and have required fields
print("\n--- 5c. Danger zones structure ---")
pubs_with_dz = 0
pubs_without_dz = 0
dz_missing_fields = []
for pub_name, pub_data in enriched.get("publishers", {}).items():
    dzs = pub_data.get("danger_zones", [])
    if dzs:
        pubs_with_dz += 1
        for dz in dzs:
            for req_field in ["id", "label", "explanation"]:
                if req_field not in dz or not dz[req_field]:
                    dz_missing_fields.append(f"{pub_name}/{dz.get('id', '?')}: missing '{req_field}'")
    else:
        pubs_without_dz += 1

print(f"Publishers with danger_zones: {pubs_with_dz}, without: {pubs_without_dz}")
if dz_missing_fields:
    issue(f"Danger zones with missing fields: {dz_missing_fields[:5]}")
else:
    ok("All danger zones have required fields")


# ── SUMMARY ───────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)
print(f"ISSUES (must fix):  {len(issues)}")
for i, iss in enumerate(issues, 1):
    print(f"  {i}. {iss}")
print(f"\nWARNINGS (review):  {len(warnings)}")
for i, w in enumerate(warnings, 1):
    print(f"  {i}. {w}")
print(f"\nPASSED checks:      {len(info)}")
print()

if issues:
    print("VERDICT: ISSUES FOUND - requires attention")
    sys.exit(1)
elif warnings:
    print("VERDICT: PASSED with warnings")
    sys.exit(0)
else:
    print("VERDICT: ALL CLEAR")
    sys.exit(0)
