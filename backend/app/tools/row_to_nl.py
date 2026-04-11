"""Template-based converter: SQLite row dicts → natural language prose.

Each table has a dedicated template function that arranges columns into
readable sentences. No LLM calls — pure string formatting.

Used by fts_search.py and sqlite_query.py to replace pipe-joined content
so the LLM gets better context and users see clean source cards.
"""

import json

from app.knowledge_pack.loader import get_active_pack

_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _month_name(m: int | None) -> str:
    if m and 1 <= m <= 12:
        return _MONTHS[m]
    return str(m) if m else ""


def _crop_name(crop_id: int | None) -> str:
    """Resolve crop_id to crop name via the active pack's SQLite connection."""
    if not crop_id:
        return ""
    mapping = _get_crop_mapping()
    return mapping.get(crop_id, "")


_crop_mapping_cache: dict[int, str] | None = None
_disease_mapping_cache: dict[int, str] | None = None


def _get_crop_mapping() -> dict[int, str]:
    """Cache crop id→name mapping. Only caches non-empty results."""
    global _crop_mapping_cache
    if _crop_mapping_cache is not None:
        return _crop_mapping_cache
    pack = get_active_pack()
    if not pack:
        return {}
    try:
        rows = pack.sqlite_conn.execute("SELECT id, name FROM crops").fetchall()
        mapping = {r[0]: r[1] for r in rows}
        if mapping:
            _crop_mapping_cache = mapping
        return mapping
    except Exception:
        return {}


def _disease_name(disease_id: int | None) -> str:
    """Resolve disease_id to disease name via the active pack's SQLite connection."""
    if not disease_id:
        return ""
    mapping = _get_disease_mapping()
    return mapping.get(disease_id, "")


def _get_disease_mapping() -> dict[int, str]:
    """Cache disease id→name mapping. Only caches non-empty results."""
    global _disease_mapping_cache
    if _disease_mapping_cache is not None:
        return _disease_mapping_cache
    pack = get_active_pack()
    if not pack:
        return {}
    try:
        rows = pack.sqlite_conn.execute("SELECT id, name FROM diseases").fetchall()
        mapping = {r[0]: r[1] for r in rows}
        if mapping:
            _disease_mapping_cache = mapping
        return mapping
    except Exception:
        return {}


def _parse_json_field(val: str | None) -> list | dict | str:
    """Try to parse a JSON string field; return original on failure."""
    if not val:
        return ""
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


def _join_list(val: str | None) -> str:
    """Parse a JSON list and join into comma-separated string."""
    parsed = _parse_json_field(val)
    if isinstance(parsed, list):
        return ", ".join(str(x) for x in parsed)
    return str(val) if val else ""


def _g(row: dict, key: str, default: str = "") -> str:
    """Get a row value as string, returning default if missing/None."""
    v = row.get(key)
    return str(v) if v is not None else default


# ============================================================
# Per-table template functions
# ============================================================

def _nl_crops(row: dict) -> str:
    name = _g(row, "name").capitalize()
    sci = _g(row, "scientific_name")
    family = _g(row, "family")
    parts = [f"{name}"]
    if sci:
        parts[0] += f" ({sci})"
    if family:
        parts[0] += f", family {family}"
    parts[0] += "."

    season = _g(row, "growing_season")
    if season:
        parts.append(f"Growing season: {season}.")

    water = row.get("water_needs_mm_per_week")
    drought = _g(row, "drought_tolerance")
    if water and drought:
        parts.append(f"Needs about {water} mm water per week with {drought} drought tolerance.")
    elif water:
        parts.append(f"Needs about {water} mm water per week.")
    elif drought:
        parts.append(f"Drought tolerance: {drought}.")

    region = _g(row, "region_suitability")
    if region:
        parts.append(region)

    planting = _g(row, "planting_notes")
    if planting:
        parts.append(f"Planting: {planting}")

    harvest = _g(row, "harvest_notes")
    if harvest:
        parts.append(f"Harvest: {harvest}")

    ph_min = row.get("soil_ph_min")
    ph_max = row.get("soil_ph_max")
    if ph_min and ph_max:
        parts.append(f"Optimal soil pH: {ph_min}–{ph_max}.")

    seed = row.get("seed_rate_kg_per_ha")
    if seed:
        parts.append(f"Seed rate: {seed} kg/ha.")

    companions = _join_list(_g(row, "intercrop_companions"))
    if companions:
        parts.append(f"Good intercrop companions: {companions}.")

    return " ".join(parts)


def _nl_diseases(row: dict) -> str:
    name = _g(row, "name")
    dtype = _g(row, "type")
    severity = _g(row, "severity_scale")
    parts = [f"{name}"]
    if dtype:
        parts[0] += f" ({dtype} disease"
        if severity:
            parts[0] += f", {severity} severity"
        parts[0] += ")"
    parts[0] += "."

    common = _join_list(_g(row, "common_names"))
    if common:
        parts.append(f"Also known as: {common}.")

    symptoms = _g(row, "symptoms_text")
    if symptoms:
        parts.append(f"Symptoms: {symptoms}")

    visual = _g(row, "visual_markers")
    if visual:
        parts.append(f"Visual identification: {visual}")

    spread = _g(row, "spread_mechanism")
    if spread:
        parts.append(f"Spreads by: {spread}.")

    prevention = _g(row, "prevention_notes")
    if prevention:
        parts.append(f"Prevention: {prevention}")

    stage = _g(row, "affected_growth_stage")
    if stage:
        parts.append(f"Most affects the {stage} growth stage.")

    peak = _g(row, "season_risk_peak")
    if peak:
        parts.append(f"Peak risk season: {peak}.")

    return " ".join(parts)


def _nl_treatments(row: dict) -> str:
    method = _g(row, "method")
    desc = _g(row, "description")
    parts = [f"{method}: {desc}" if desc else method + "."]

    materials = _join_list(_g(row, "materials_needed"))
    if materials:
        parts.append(f"Materials needed: {materials}.")

    difficulty = _g(row, "difficulty")
    organic = row.get("is_organic")
    if difficulty or organic is not None:
        tags = []
        if difficulty:
            tags.append(f"{difficulty} difficulty")
        if organic:
            tags.append("organic")
        parts.append(f"This treatment is {', '.join(tags)}.")

    avail = _g(row, "local_availability")
    if avail:
        parts.append(f"Local availability: {avail}.")

    effectiveness = _g(row, "effectiveness")
    if effectiveness:
        parts.append(f"Effectiveness: {effectiveness}.")

    timing = _g(row, "application_timing")
    if timing:
        parts.append(f"Timing: {timing}")

    safety = _g(row, "safety_notes")
    if safety:
        parts.append(f"Safety: {safety}")

    cost = row.get("cost_estimate_xof")
    if cost:
        parts.append(f"Estimated cost: {cost:,} XOF/ha.")

    ttype = _g(row, "treatment_type")
    if ttype:
        parts.append(f"Type: {ttype}.")

    return " ".join(parts)


def _nl_climate(row: dict) -> str:
    region = _g(row, "region")
    month = _month_name(row.get("month"))
    parts = []
    if region and month:
        parts.append(f"{region} in {month}:")
    elif region:
        parts.append(f"{region}:")
    elif month:
        parts.append(f"{month}:")

    rain = row.get("rainfall_mm")
    if rain is not None:
        parts.append(f"average rainfall {rain} mm.")

    temp = row.get("temperature_avg_c")
    if temp is not None:
        parts.append(f"Average temperature {temp}°C.")

    hum = row.get("humidity_pct")
    if hum is not None:
        parts.append(f"Humidity around {hum}%.")

    drought = _g(row, "drought_risk")
    if drought:
        parts.append(f"Drought risk: {drought}.")

    flood = _g(row, "flooding_risk")
    if flood:
        parts.append(f"Flooding risk: {flood}.")

    evap = row.get("evapotranspiration_mm")
    if evap:
        parts.append(f"Evapotranspiration: {evap} mm.")

    notes = _g(row, "notes")
    if notes:
        parts.append(notes)

    return " ".join(parts)


def _nl_pests(row: dict) -> str:
    name = _g(row, "name")
    ptype = _g(row, "type")
    crop = _crop_name(row.get("crop_id"))
    header = name
    if ptype:
        header += f" ({ptype})"
    if crop:
        header += f", affecting {crop}"
    parts = [header + "."]

    common = _join_list(_g(row, "common_names"))
    if common:
        parts.append(f"Also known as: {common}.")

    damage = _g(row, "damage_description")
    if damage:
        parts.append(f"Damage: {damage}")

    season = _g(row, "season_peak")
    if season:
        parts.append(f"Peak season: {season}.")

    ident = _g(row, "identification_notes")
    if ident:
        parts.append(f"How to identify: {ident}")

    organic = _g(row, "control_organic")
    if organic:
        parts.append(f"Organic control: {organic}")

    chemical = _g(row, "control_chemical")
    if chemical:
        parts.append(f"Chemical control: {chemical}")

    threshold = _g(row, "economic_threshold")
    if threshold:
        parts.append(f"Economic threshold: {threshold}")

    prevention = _g(row, "prevention_notes")
    if prevention:
        parts.append(f"Prevention: {prevention}")

    return " ".join(parts)


def _nl_varieties(row: dict) -> str:
    name = _g(row, "name")
    crop = _crop_name(row.get("crop_id"))
    header = f"{name}"
    if crop:
        header += f" ({crop} variety)"
    parts = [header + "."]

    local = _join_list(_g(row, "local_names"))
    if local:
        parts.append(f"Local names: {local}.")

    days = row.get("days_to_maturity")
    if days:
        parts.append(f"Matures in {days} days.")

    yld = row.get("yield_potential_kg_per_ha")
    if yld:
        parts.append(f"Yield potential: {yld:,.0f} kg/ha.")

    resist = _g(row, "disease_resistance")
    if resist:
        parsed = _parse_json_field(resist)
        if isinstance(parsed, dict):
            items = [f"{k}: {v}" for k, v in parsed.items()]
            parts.append(f"Disease resistance — {', '.join(items)}.")
        else:
            parts.append(f"Disease resistance: {resist}.")

    drought = _g(row, "drought_tolerance")
    if drought:
        parts.append(f"Drought tolerance: {drought}.")

    source = _g(row, "seed_source_in_region")
    if source:
        parts.append(f"Seed available from: {source}.")

    density = _g(row, "planting_density")
    if density:
        parts.append(f"Planting density: {density}.")

    notes = _g(row, "notes")
    if notes:
        parts.append(notes)

    return " ".join(parts)


def _nl_fertilization_schedule(row: dict) -> str:
    crop = _crop_name(row.get("crop_id"))
    stage = _g(row, "growth_stage")
    fert = _g(row, "fertilizer_type")
    dose = _g(row, "dose_per_ha")

    parts = []
    if crop and stage:
        parts.append(f"For {crop} during the {stage} stage:")
    elif stage:
        parts.append(f"During the {stage} stage:")

    if dose and fert:
        # Check if fertilizer name (or its core word) already appears in the dose string
        fert_core = fert.split("(")[0].split("/")[0].strip().lower()
        redundant = fert.lower() in dose.lower() or fert_core in dose.lower()
        parts.append(f"apply {dose}." if redundant else f"apply {dose} of {fert}.")
    elif fert:
        parts.append(f"apply {fert}.")

    method = _g(row, "application_method")
    if method:
        parts.append(f"Application method: {method}")

    timing = _g(row, "timing_notes")
    if timing:
        parts.append(timing)

    alt = _g(row, "organic_alternative")
    if alt:
        parts.append(f"Organic alternative: {alt}")

    cost = row.get("cost_estimate_xof")
    if cost:
        parts.append(f"Estimated cost: {cost:,} XOF/ha.")

    return " ".join(parts)


def _nl_planting_calendar(row: dict) -> str:
    crop = _crop_name(row.get("crop_id"))
    month = _month_name(row.get("month"))
    activity = _g(row, "activity")
    details = _g(row, "details")
    critical = row.get("is_critical")

    parts = []
    if crop and month:
        parts.append(f"{crop.capitalize()} in {month} — {activity}." if activity else f"{crop.capitalize()} in {month}.")
    elif month and activity:
        parts.append(f"{month}: {activity}.")
    elif activity:
        parts.append(f"{activity}.")

    if critical:
        parts.append("This is a critical activity.")

    if details:
        parts.append(details)

    return " ".join(parts)


def _nl_storage_guidelines(row: dict) -> str:
    crop = _crop_name(row.get("crop_id"))
    method = _g(row, "method")
    parts = []
    if crop:
        parts.append(f"Storage for {crop}: {method}." if method else f"Storage for {crop}.")
    elif method:
        parts.append(f"Storage method: {method}.")

    temp = _g(row, "optimal_temp_c")
    if temp:
        parts.append(f"Optimal temperature: {temp}°C.")

    moisture = row.get("moisture_target_pct")
    if moisture:
        parts.append(f"Target moisture: {moisture}%.")

    dur = row.get("max_duration_months")
    if dur:
        parts.append(f"Maximum storage duration: {dur} months.")

    pests = _g(row, "pest_risks")
    if pests:
        parts.append(f"Pest risks: {pests}")

    quality = _g(row, "quality_indicators")
    if quality:
        parts.append(f"Quality indicators: {quality}")

    materials = _g(row, "local_materials")
    if materials:
        parts.append(f"Local materials: {materials}")

    return " ".join(parts)


def _nl_soil_requirements(row: dict) -> str:
    crop = _crop_name(row.get("crop_id"))
    parts = []
    if crop:
        parts.append(f"Soil requirements for {crop}.")
    else:
        parts.append("Soil requirements.")

    ph_min = row.get("ph_min")
    ph_max = row.get("ph_max")
    if ph_min and ph_max:
        parts.append(f"pH range: {ph_min}–{ph_max}.")

    texture = _g(row, "preferred_texture")
    if texture:
        parts.append(f"Preferred soil texture: {texture}.")

    drainage = _g(row, "drainage_needs")
    if drainage:
        parts.append(f"Drainage: {drainage}")

    amend = _g(row, "amendments_needed")
    if amend:
        parsed = _parse_json_field(amend)
        if isinstance(parsed, list):
            parts.append("Amendments: " + "; ".join(str(x) for x in parsed) + ".")
        else:
            parts.append(f"Amendments: {amend}")

    prep = _g(row, "preparation_notes")
    if prep:
        parts.append(f"Preparation: {prep}")

    return " ".join(parts)


def _nl_crop_diseases(row: dict) -> str:
    crop = _crop_name(row.get("crop_id"))
    disease = _disease_name(row.get("disease_id"))
    susceptibility = _g(row, "susceptibility")
    if crop and disease and susceptibility:
        return f"{crop.capitalize()} has {susceptibility} susceptibility to {disease}."
    elif crop and disease:
        return f"{crop.capitalize()} is affected by {disease}."
    elif disease and susceptibility:
        return f"{disease} — susceptibility: {susceptibility}."
    return _fallback(row)


def _nl_image_refs(row: dict) -> str:
    img_type = _g(row, "type")
    desc = _g(row, "description")
    crop = _crop_name(row.get("crop_id"))
    disease = _disease_name(row.get("disease_id"))
    parts = []
    label = img_type.replace("_", " ") if img_type else "image"
    if crop and disease:
        parts.append(f"Reference {label} for {disease} on {crop}.")
    elif disease:
        parts.append(f"Reference {label} for {disease}.")
    elif crop:
        parts.append(f"Reference {label} for {crop}.")
    else:
        parts.append(f"Reference {label}.")
    if desc:
        parts.append(desc)
    visual = _g(row, "visual_features")
    if visual:
        parts.append(f"Visual features: {visual}")
    return " ".join(parts)


def _nl_field_observations(row: dict) -> str:
    obs_type = _g(row, "type").replace("_", " ")
    location = _g(row, "location")
    details = _g(row, "details")
    severity = _g(row, "severity_observed")
    timestamp = _g(row, "timestamp")
    crop = _crop_name(row.get("crop_id"))

    parts = []
    header = f"Field observation ({obs_type})" if obs_type else "Field observation"
    if location:
        header += f" at {location}"
    if timestamp:
        date = timestamp.split("T")[0] if "T" in timestamp else timestamp
        header += f" on {date}"
    parts.append(header + ".")
    if severity:
        parts.append(f"Severity: {severity}.")
    if crop:
        parts.append(f"Crop: {crop}.")
    if details:
        parts.append(details)
    return " ".join(parts)


# ============================================================
# Dispatch table and public API
# ============================================================

_TABLE_CONVERTERS = {
    "crops": _nl_crops,
    "diseases": _nl_diseases,
    "crop_diseases": _nl_crop_diseases,
    "treatments": _nl_treatments,
    "climate": _nl_climate,
    "image_refs": _nl_image_refs,
    "field_observations": _nl_field_observations,
    "pests": _nl_pests,
    "varieties": _nl_varieties,
    "fertilization_schedule": _nl_fertilization_schedule,
    "planting_calendar": _nl_planting_calendar,
    "storage_guidelines": _nl_storage_guidelines,
    "soil_requirements": _nl_soil_requirements,
}


def row_to_nl(row: dict, table: str) -> str:
    """Convert a SQLite row dict to natural language prose.

    Falls back to pipe-joined key: value pairs if no template exists
    or if conversion fails.
    """
    converter = _TABLE_CONVERTERS.get(table)
    if not converter:
        return _fallback(row)
    try:
        result = converter(row)
        return result if result.strip() else _fallback(row)
    except Exception:
        return _fallback(row)


def _fallback(row: dict) -> str:
    """Pipe-joined fallback matching the old behavior."""
    parts = []
    for k, v in row.items():
        if v is not None and k != "bm25_score":
            parts.append(f"{k}: {v}")
    return " | ".join(parts) if parts else str(row)
