"""Climate data parser for Phase A source gathering.

Parses HTML tables from weather-and-climate.com directly into
structured climate records. No LLM needed — pure table extraction.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.logger import Step, pipeline_logger as log

# Month names in table headers -> month numbers
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}


def parse_climate_tables(
    html: str,
    region: str,
    source_url: str,
) -> list[dict]:
    """Extract monthly climate records from weather-and-climate.com HTML.

    Returns a list of dicts ready for ClimateRecord construction:
      {"region": ..., "month": 1-12, "rainfall_mm": ..., "temperature_avg_c": ...}
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    # Accumulate data by month
    monthly: dict[int, dict] = {m: {"region": region, "month": m} for m in range(1, 13)}

    for table in tables:
        _parse_single_table(table, monthly)

    records = [monthly[m] for m in range(1, 13)]

    # Add drought risk heuristic based on rainfall
    for rec in records:
        rainfall = rec.get("rainfall_mm")
        if rainfall is not None:
            if rainfall < 10:
                rec["drought_risk"] = "severe"
            elif rainfall < 30:
                rec["drought_risk"] = "high"
            elif rainfall < 80:
                rec["drought_risk"] = "medium"
            else:
                rec["drought_risk"] = "low"

    non_empty = sum(1 for r in records if len(r) > 2)
    log.log_step(Step.SYSTEM, "parse_climate", details={
        "region": region, "url": source_url,
        "months_with_data": non_empty,
    })

    return records


def _parse_single_table(table, monthly: dict[int, dict]) -> None:
    """Try to extract monthly values from a single HTML table."""
    rows = table.find_all("tr")
    if len(rows) < 2:
        return

    # Try to find month headers in the first row
    header_cells = rows[0].find_all(["th", "td"])
    month_columns: dict[int, int] = {}  # col_index -> month_number

    for col_idx, cell in enumerate(header_cells):
        text = cell.get_text(strip=True).lower()
        month_num = _MONTH_MAP.get(text[:3])
        if month_num is not None:
            month_columns[col_idx] = month_num

    if not month_columns:
        return

    # Parse data rows
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue

        row_label = cells[0].get_text(strip=True).lower()
        field_name = _guess_climate_field(row_label)
        if not field_name:
            continue

        for col_idx, month_num in month_columns.items():
            if col_idx < len(cells):
                value = _parse_number(cells[col_idx].get_text(strip=True))
                if value is not None:
                    monthly[month_num][field_name] = value


def _guess_climate_field(label: str) -> str | None:
    """Map a row label to a ClimateRecord field name."""
    if any(w in label for w in ("rain", "precip")):
        return "rainfall_mm"
    if any(w in label for w in ("temp", "average")):
        if "max" not in label and "min" not in label:
            return "temperature_avg_c"
    if any(w in label for w in ("humid",)):
        return "humidity_pct"
    if any(w in label for w in ("evapotranspiration", "eto", "et0")):
        return "evapotranspiration_mm"
    return None


def _parse_number(text: str) -> float | None:
    """Extract a number from a table cell, ignoring units and whitespace."""
    cleaned = text.replace(",", ".").strip()
    # Take the first token that looks numeric
    for token in cleaned.split():
        try:
            return float(token)
        except ValueError:
            continue
    return None
