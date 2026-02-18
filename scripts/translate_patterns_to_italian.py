#!/usr/bin/env python3
"""
Translate all English text in enriched JSON files to Italian.
Targets:
  1. data/seasonal/enriched-recurring-patterns.json
  2. data/seasonal/optimization-windows-enriched.json
"""

import json
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Month abbreviation mapping ──────────────────────────────────────────
MONTH_MAP = {
    "Jan": "Gen", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
    "May": "Mag", "Jun": "Giu", "Jul": "Lug", "Aug": "Ago",
    "Sep": "Set", "Oct": "Ott", "Nov": "Nov", "Dec": "Dic",
}

# ── Label translation: composite labels ─────────────────────────────────
# Labels follow patterns like "Jan to Feb Revenue Drop", "Early Fall Dip", etc.

# Map for the metric+direction part
METRIC_SIGNAL_MAP = {
    "Revenue Drop": "Calo Revenue",
    "Revenue Surge": "Crescita Revenue",
    "Impressions Drop": "Calo Impressions",
    "Impressions Surge": "Crescita Impressions",
    "Both Drop": "Calo Combinato",
    "Both Surge": "Crescita Combinata",
}

# Map for named ecpm_pattern labels
NAMED_LABEL_MAP = {
    "Early Fall Dip": "Calo Autunnale Anticipato",
    "Early Spring Trough": "Minimo Primaverile Anticipato",
    "Early Summer Rise": "Rialzo Estivo Anticipato",
    "Back-to-School Boost": "Crescita Rientro Scolastico",
    "Holiday Premium": "Premium Festivo",
    "Holiday Surge": "Crescita Festiva",
    "January Dip": "Calo di Gennaio",
    "Late Summer Dip": "Calo Estivo Tardivo",
    "Late Summer Lull": "Stasi Estiva Tardiva",
    "Late Winter Dip": "Calo Invernale Tardivo",
    "Mid-Year Trough": "Minimo di Meta Anno",
    "New Year Premium": "Premium Capodanno",
    "November Peak": "Picco di Novembre",
    "Pre-Summer Dip": "Calo Pre-Estivo",
    "Q1 Recovery": "Ripresa Q1",
    "Q1 Start Premium": "Premium Inizio Q1",
    "Spring Lull": "Stasi Primaverile",
    "Spring Uplift": "Rialzo Primaverile",
    "Summer Dip": "Calo Estivo",
    "Year-End Drop": "Calo di Fine Anno",
}


def translate_month(m: str) -> str:
    return MONTH_MAP.get(m, m)


def translate_week_range_label(wrl: str) -> str:
    """Translate month names inside week_range_label like 'W2-W7 (Jan-Feb)' -> 'W2-W7 (Gen-Feb)'."""
    def replace_month(match):
        return translate_month(match.group(0))
    return re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', replace_month, wrl)


def translate_label(label: str) -> str:
    """Translate a pattern label to Italian."""
    # First check named labels
    if label in NAMED_LABEL_MAP:
        return NAMED_LABEL_MAP[label]

    # Try metric+signal patterns: "Month to Month Metric Signal" or "Month Metric Signal"
    # Pattern: optional date prefix + metric signal suffix
    for eng, ita in METRIC_SIGNAL_MAP.items():
        if label.endswith(eng):
            prefix = label[: -len(eng)].strip()
            if prefix:
                # Translate month names in prefix
                translated_prefix = translate_date_prefix(prefix)
                return f"{ita} {translated_prefix}"
            return ita

    # Fallback: just translate month names
    return translate_week_range_label(label)


def translate_date_prefix(prefix: str) -> str:
    """Translate date prefix like 'Jan to Feb' -> 'Gen-Feb', 'Nov to Dec' -> 'Nov-Dic'."""
    # Handle "Month to Month" pattern
    m = re.match(r'^(\w+)\s+to\s+(\w+)$', prefix)
    if m:
        m1 = translate_month(m.group(1))
        m2 = translate_month(m.group(2))
        return f"{m1}-{m2}"

    # Single month
    if prefix in MONTH_MAP:
        return translate_month(prefix)

    # Fallback: translate any month names found
    return translate_week_range_label(prefix)


# ── Rationale translation (template-based) ──────────────────────────────
# Rationales follow a few templates with numbers plugged in.

def translate_rationale(rationale: str) -> str:
    """Translate a full rationale sentence to Italian."""

    # Pattern: "eCPM consistently trends above/below the yearly average during this period (X% in 2024, Y% in 2025), likely driven by ... This recurring pattern across both years suggests a structural seasonal effect."
    m = re.match(
        r"eCPM consistently trends (above|below) the yearly average during this period "
        r"\(([^)]+)\), likely driven by (.+?)\. This recurring pattern across both years suggests a structural seasonal effect\.",
        rationale
    )
    if m:
        direction = "sopra" if m.group(1) == "above" else "sotto"
        pcts = m.group(2)
        # translate "in" to "nel"
        pcts = pcts.replace(" in ", " nel ")
        cause = translate_cause_fragment(m.group(3))
        return (
            f"L'eCPM si posiziona costantemente {direction} la media annuale in questo periodo "
            f"({pcts}), probabilmente trainato da {cause}. "
            f"Questo andamento ricorrente in entrambi gli anni suggerisce un effetto stagionale strutturale."
        )

    # Fallback: return as-is (shouldn't happen with our data)
    return rationale


def translate_cause_fragment(cause: str) -> str:
    """Translate the 'likely driven by ...' cause fragment."""
    CAUSE_MAP = {
        "back-to-school campaigns and renewed advertiser spending":
            "campagne di rientro scolastico e ripresa della spesa pubblicitaria",
        "Q4 holiday advertising push and Black Friday/Christmas demand":
            "la spinta pubblicitaria del Q4 e la domanda Black Friday/Natale",
        "spring ad campaign launches and seasonal advertiser budgets":
            "il lancio di campagne pubblicitarie primaverili e budget stagionali",
        "post-holiday budget resets and reduced advertiser spending":
            "il reset dei budget post-festivi e la riduzione della spesa pubblicitaria",
        "summer slowdown in advertiser spending and seasonal audience shift":
            "il rallentamento estivo della spesa pubblicitaria e lo spostamento stagionale dell'audience",
        "year-end holiday advertising push and Black Friday/Christmas demand":
            "la spinta pubblicitaria di fine anno e la domanda Black Friday/Natale",
        "holiday advertising push and Black Friday/Christmas demand":
            "la spinta pubblicitaria festiva e la domanda Black Friday/Natale",
        "Q1 budget renewals and fresh advertiser spending cycles":
            "i rinnovi budget del Q1 e i nuovi cicli di spesa pubblicitaria",
        "pre-holiday ramp-up and Q4 advertiser budget deployment":
            "la preparazione pre-festiva e il dispiegamento dei budget pubblicitari del Q4",
        "renewed advertiser activity after summer and back-to-school spending":
            "la ripresa dell'attivita pubblicitaria post-estiva e la spesa per il rientro scolastico",
        "seasonal advertiser budget deployment and campaign planning":
            "il dispiegamento dei budget pubblicitari stagionali e la pianificazione delle campagne",
        "mid-year budget reviews and summer campaign slowdown":
            "le revisioni budget di meta anno e il rallentamento delle campagne estive",
        "early spring advertiser spending and new budget cycles":
            "la spesa pubblicitaria di inizio primavera e i nuovi cicli di budget",
        "summer audience decline and advertiser pause":
            "il calo dell'audience estiva e la pausa degli advertiser",
        "seasonal demand fluctuations in the advertising market":
            "le fluttuazioni stagionali della domanda nel mercato pubblicitario",
        "peak holiday season with maximum advertiser competition for inventory":
            "il picco della stagione festiva con massima competizione tra advertiser per l'inventory",
        "peak summer traffic patterns and vacation-period ad demand":
            "i picchi di traffico estivo e la domanda pubblicitaria nel periodo vacanziero",
        "post-holiday budget resets and advertiser Q1 planning cycles":
            "il reset dei budget post-festivi e i cicli di pianificazione Q1 degli advertiser",
        "spring seasonal campaigns and increased brand spending":
            "le campagne stagionali primaverili e l'aumento della spesa dei brand",
        "summer audience shifts and seasonal advertising demand changes":
            "lo spostamento dell'audience estiva e le variazioni stagionali della domanda pubblicitaria",
    }
    return CAUSE_MAP.get(cause, cause)


# ── Driver explanation translation ──────────────────────────────────────

def translate_driver_explanation(text: str) -> str:
    """Translate driver_explanation text to Italian."""

    # Use .+? with end-of-string anchors to handle negative percentages containing dots

    # VOLUME_DRIVEN pattern
    m = re.match(
        r"eCPM drops because impression volume expands \(([^)]+)\), diluting average value with lower-quality impressions\. "
        r"Bacino: (.+?), coverage: (.+?)\. Revenue impact: (.+?)\.$",
        text
    )
    if m:
        return (
            f"L'eCPM cala perche il volume di impressions cresce ({m.group(1)}), diluendo il valore medio con impressions di qualita inferiore. "
            f"Bacino: {m.group(2)}, coverage: {m.group(3)}. Impatto revenue: {m.group(4)}."
        )

    # SEASONAL_DEMAND pattern
    m = re.match(
        r"eCPM drops because supply \(bacino ([^)]+)\) outpaces advertiser demand, compressing coverage \(([^)]+)\)\. "
        r"This is a classic seasonal demand gap\. Revenue impact: (.+?)\.$",
        text
    )
    if m:
        return (
            f"L'eCPM cala perche l'offerta (bacino {m.group(1)}) supera la domanda pubblicitaria, comprimendo la coverage ({m.group(2)}). "
            f"Si tratta di un classico gap di domanda stagionale. Impatto revenue: {m.group(3)}."
        )

    # MIXED pattern (ecpm_patterns)
    m = re.match(
        r"eCPM pattern doesn't fit a single clean driver\. "
        r"Bacino: (.+?), coverage: (.+?), impressions: (.+?)\. Revenue impact: (.+?)\.$",
        text
    )
    if m:
        return (
            f"L'andamento eCPM non corrisponde a un singolo driver chiaro. "
            f"Bacino: {m.group(1)}, coverage: {m.group(2)}, impressions: {m.group(3)}. Impatto revenue: {m.group(4)}."
        )

    # FILL_EFFECT pattern (two variants: with/without "from unfilled inventory")
    m = re.match(
        r"eCPM rises because coverage drops \(([^)]+)\), meaning only premium/high-value impressions are being served\. "
        r"The eCPM increase masks potential revenue loss(?:\s+from unfilled inventory)?\. "
        r"(?:Bacino: (.+?), impressions: (.+?)\. )?Revenue impact: (.+?)\.$",
        text
    )
    if m:
        base = (
            f"L'eCPM sale perche la coverage cala ({m.group(1)}), il che significa che vengono servite solo impressions premium/di alto valore. "
            f"L'aumento dell'eCPM maschera una potenziale perdita di revenue da inventario invenduto. "
        )
        if m.group(2) and m.group(3):
            base += f"Bacino: {m.group(2)}, impressions: {m.group(3)}. "
        base += f"Impatto revenue: {m.group(4)}."
        return base

    # DEMAND_DRIVEN pattern
    m = re.match(
        r"eCPM rises because real advertiser demand increases\. "
        r"Bacino \(([^)]+)\) and coverage \(([^)]+)\) remain healthy, confirming this is genuine demand-driven pricing\. "
        r"Revenue impact: (.+?)\.$",
        text
    )
    if m:
        return (
            f"L'eCPM sale grazie a un reale aumento della domanda pubblicitaria. "
            f"Bacino ({m.group(1)}) e coverage ({m.group(2)}) restano sani, confermando un pricing genuinamente trainato dalla domanda. "
            f"Impatto revenue: {m.group(3)}."
        )

    # SUPPLY_SQUEEZE pattern variant 1: with Coverage/impressions fields
    m = re.match(
        r"eCPM rises primarily because available inventory \(bacino\) contracts \(([^)]+)\)\. "
        r"With less supply, eCPM is artificially inflated\. "
        r"This is potentially misleading[.\-].+?Coverage: (.+?), impressions: (.+?)\. Revenue impact: (.+?)\.$",
        text
    )
    if m:
        return (
            f"L'eCPM sale principalmente perche l'inventario disponibile (bacino) si contrae ({m.group(1)}). "
            f"Con meno offerta, l'eCPM risulta artificialmente gonfiato. "
            f"Questo dato puo essere fuorviante. Coverage: {m.group(2)}, impressions: {m.group(3)}. Impatto revenue: {m.group(4)}."
        )

    # SUPPLY_SQUEEZE pattern variant 2: without Coverage/impressions, just Revenue impact
    m = re.match(
        r"eCPM rises primarily because available inventory \(bacino\) contracts \(([^)]+)\)\. "
        r"With less supply, eCPM is artificially inflated\. "
        r"This is potentially misleading.+?Revenue impact: (.+?)\.$",
        text
    )
    if m:
        return (
            f"L'eCPM sale principalmente perche l'inventario disponibile (bacino) si contrae ({m.group(1)}). "
            f"Con meno offerta, l'eCPM risulta artificialmente gonfiato. "
            f"Questo dato puo essere fuorviante. Impatto revenue: {m.group(2)}."
        )

    # ── Optimization windows driver_explanation patterns ──

    if text == "Complex pattern with no single dominant driver. Multiple metrics moving in different directions.":
        return "Andamento complesso senza un singolo driver dominante. Metriche multiple in movimento in direzioni diverse."

    if text == "Genuine demand-driven eCPM increase. Supply stable/growing while prices rise \u2014 real advertiser demand.":
        return "Aumento eCPM genuinamente trainato dalla domanda. Offerta stabile/in crescita mentre i prezzi salgono \u2014 domanda pubblicitaria reale."

    if text == "Seasonal demand weakness: supply expands but demand doesn't follow, pushing coverage and eCPM down.":
        return "Debolezza stagionale della domanda: l'offerta si espande ma la domanda non segue, spingendo coverage ed eCPM verso il basso."

    if text == "eCPM dip offset by higher volume. More impressions at lower price \u2014 revenue may still be strong.":
        return "Calo eCPM compensato da volumi maggiori. Piu impressions a prezzo inferiore \u2014 il revenue potrebbe comunque essere forte."

    if text == "eCPM rise coincides with reduced supply (bacino down). Higher price may reflect scarcity, not demand strength.":
        return "L'aumento dell'eCPM coincide con una riduzione dell'offerta (bacino in calo). Il prezzo piu alto potrebbe riflettere scarsita, non forza della domanda."

    if text == "eCPM rise with lower fill rate. Fewer impressions served at higher price \u2014 may not reflect true demand increase.":
        return "Aumento eCPM con fill rate inferiore. Meno impressions servite a prezzo piu alto \u2014 potrebbe non riflettere un reale aumento della domanda."

    # Fallback
    return text


# ── Business impact translation ─────────────────────────────────────────

def translate_business_impact(text: str) -> str:
    """Translate hidden_pattern business_impact to Italian."""

    # "Both revenue and impressions drop ~X% proportionally -- eCPM masks a broad contraction"
    m = re.match(r"Both revenue and impressions drop ~(\d+)% proportionally -- eCPM masks a broad contraction", text)
    if m:
        return f"Sia revenue che impressions calano ~{m.group(1)}% proporzionalmente -- l'eCPM maschera una contrazione generalizzata"

    # "Revenue drops ~X% while eCPM appears healthy -- supply contraction masks revenue loss"
    m = re.match(r"Revenue drops ~(\d+)% while eCPM appears healthy -- supply contraction masks revenue loss", text)
    if m:
        return f"Il revenue cala ~{m.group(1)}% mentre l'eCPM appare sano -- la contrazione dell'offerta maschera la perdita di revenue"

    # "Revenue grows ~X% while eCPM is flat -- volume-driven growth not visible in efficiency metrics"
    m = re.match(r"Revenue grows ~(\d+)% while eCPM is flat -- volume-driven growth not visible in efficiency metrics", text)
    if m:
        return f"Il revenue cresce ~{m.group(1)}% mentre l'eCPM e piatto -- crescita trainata dal volume non visibile nelle metriche di efficienza"

    # "Impressions drop ~X% while eCPM holds -- reduced reach without pricing signal"
    m = re.match(r"Impressions drop ~(\d+)% while eCPM holds -- reduced reach without pricing signal", text)
    if m:
        return f"Le impressions calano ~{m.group(1)}% mentre l'eCPM tiene -- reach ridotta senza segnale di prezzo"

    # "Volume and eCPM both down -- pattern visible in eCPM analysis"
    if text == "Volume and eCPM both down -- pattern visible in eCPM analysis":
        return "Volume ed eCPM entrambi in calo -- andamento visibile nell'analisi eCPM"

    # "Volume and eCPM both up -- pattern visible in eCPM analysis"
    if text == "Volume and eCPM both up -- pattern visible in eCPM analysis":
        return "Volume ed eCPM entrambi in crescita -- andamento visibile nell'analisi eCPM"

    # "Volume down ~X% while eCPM up -- divergent signals"
    m = re.match(r"Volume down ~(\d+)% while eCPM up -- divergent signals", text)
    if m:
        return f"Volume in calo ~{m.group(1)}% mentre l'eCPM sale -- segnali divergenti"

    # "Volume up ~X% while eCPM down -- divergent signals"
    m = re.match(r"Volume up ~(\d+)% while eCPM down -- divergent signals", text)
    if m:
        return f"Volume in crescita ~{m.group(1)}% mentre l'eCPM cala -- segnali divergenti"

    return text


# ── Danger zone explanation translation ─────────────────────────────────

def translate_danger_explanation(text: str) -> str:
    """Translate danger_zone explanation to Italian."""
    # Pattern: "Both eCPM (X%) and coverage (Y%) drop simultaneously during W..-W.. (Mon-Mon).
    # This indicates a genuine monetization weakness -- notable/critical risk period for revenue."
    m = re.match(
        r"Both eCPM \(([^)]+)\) and coverage \(([^)]+)\) drop simultaneously during (.+?)\. "
        r"This indicates a genuine monetization weakness -- (notable|critical) risk period(?:\s+for revenue)?\.$",
        text
    )
    if m:
        severity = "notevole" if m.group(4) == "notable" else "critico"
        period = translate_week_range_label(m.group(3))
        return (
            f"Sia l'eCPM ({m.group(1)}) che la coverage ({m.group(2)}) calano simultaneamente durante {period}. "
            f"Questo indica una reale debolezza di monetizzazione -- periodo di rischio {severity} per il revenue."
        )

    return text


# ── Main processing ─────────────────────────────────────────────────────

def process_enriched_recurring_patterns():
    path = os.path.join(BASE_DIR, "data/seasonal/enriched-recurring-patterns.json")
    with open(path) as f:
        data = json.load(f)

    for pub_id, pub in data["publishers"].items():
        for p in pub.get("ecpm_patterns", []):
            p["label"] = translate_label(p["label"])
            p["week_range_label"] = translate_week_range_label(p["week_range_label"])
            p["rationale"] = translate_rationale(p["rationale"])
            p["driver_explanation"] = translate_driver_explanation(p["driver_explanation"])

        for p in pub.get("hidden_patterns", []):
            p["label"] = translate_label(p["label"])
            p["week_range_label"] = translate_week_range_label(p["week_range_label"])
            p["business_impact"] = translate_business_impact(p["business_impact"])

        for p in pub.get("danger_zones", []):
            p["label"] = translate_label(p["label"])
            p["week_range_label"] = translate_week_range_label(p["week_range_label"])
            p["explanation"] = translate_danger_explanation(p["explanation"])

    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] enriched-recurring-patterns.json translated ({len(data['publishers'])} publishers)")
    return data


def process_optimization_windows():
    path = os.path.join(BASE_DIR, "data/seasonal/optimization-windows-enriched.json")
    with open(path) as f:
        data = json.load(f)

    for pub_id, pub in data["publishers"].items():
        for w in pub.get("windows", []):
            w["driver_explanation"] = translate_driver_explanation(w["driver_explanation"])

    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] optimization-windows-enriched.json translated ({len(data['publishers'])} publishers)")
    return data


if __name__ == "__main__":
    data1 = process_enriched_recurring_patterns()
    data2 = process_optimization_windows()

    # ── Verification ──
    print("\n=== VERIFICATION ===")

    # Check a few ecpm_pattern labels
    first_pub = list(data1["publishers"].keys())[0]
    pub = data1["publishers"][first_pub]
    print(f"\nPublisher: {first_pub}")
    for p in pub.get("ecpm_patterns", [])[:2]:
        print(f"  label: {p['label']}")
        print(f"  week_range_label: {p['week_range_label']}")
        print(f"  rationale: {p['rationale'][:100]}...")
        print(f"  driver_explanation: {p['driver_explanation'][:100]}...")

    for p in pub.get("hidden_patterns", [])[:2]:
        print(f"  hidden label: {p['label']}")
        print(f"  business_impact: {p['business_impact']}")

    for p in pub.get("danger_zones", [])[:1]:
        print(f"  danger label: {p['label']}")
        print(f"  explanation: {p['explanation'][:100]}...")

    # Check optimization windows
    first_pub2 = list(data2["publishers"].keys())[0]
    pub2 = data2["publishers"][first_pub2]
    print(f"\nOpt windows - Publisher: {first_pub2}")
    for w in pub2.get("windows", [])[:2]:
        print(f"  driver_explanation: {w['driver_explanation'][:100]}...")

    # ── Check for untranslated English ──
    print("\n=== CHECKING FOR UNTRANSLATED TEXT ===")
    english_markers = [
        "consistently trends", "likely driven by", "recurring pattern",
        "drops because", "rises because", "doesn't fit",
        "Volume and eCPM both", "while eCPM", "divergent signals",
        "genuine monetization weakness", "Complex pattern with no single",
        "Genuine demand-driven", "Seasonal demand weakness",
        "eCPM dip offset", "eCPM rise coincides", "eCPM rise with lower"
    ]

    untranslated = 0
    for pub_id, pub in data1["publishers"].items():
        for p in pub.get("ecpm_patterns", []):
            for field in ["rationale", "driver_explanation"]:
                val = p.get(field, "")
                for marker in english_markers:
                    if marker in val:
                        print(f"  UNTRANSLATED [{pub_id}] ecpm_patterns.{field}: ...{marker}...")
                        untranslated += 1
                        break
        for p in pub.get("hidden_patterns", []):
            val = p.get("business_impact", "")
            for marker in english_markers:
                if marker in val:
                    print(f"  UNTRANSLATED [{pub_id}] hidden_patterns.business_impact: ...{marker}...")
                    untranslated += 1
                    break
        for p in pub.get("danger_zones", []):
            val = p.get("explanation", "")
            for marker in english_markers:
                if marker in val:
                    print(f"  UNTRANSLATED [{pub_id}] danger_zones.explanation: ...{marker}...")
                    untranslated += 1
                    break

    for pub_id, pub in data2["publishers"].items():
        for w in pub.get("windows", []):
            val = w.get("driver_explanation", "")
            for marker in english_markers:
                if marker in val:
                    print(f"  UNTRANSLATED [{pub_id}] windows.driver_explanation: ...{marker}...")
                    untranslated += 1
                    break

    if untranslated == 0:
        print("  All text translated successfully!")
    else:
        print(f"  WARNING: {untranslated} untranslated entries found")
