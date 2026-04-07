"""Open-Meteo climate data fetcher and aggregator.

Replaces weather-and-climate.com (403 bot detection). Fetches 21 years
of daily data from the Open-Meteo Archive API (free, no auth), then
aggregates to 12-month normals in Python. No LLM needed.

Variables: precipitation_sum (mm), temperature_2m_mean (°C),
           relative_humidity_2m_mean (%).
"""

from __future__ import annotations

import httpx

from app.logger import Step, pipeline_logger as log

_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
_START_DATE = "2000-01-01"
_END_DATE = "2020-12-31"
_DAILY_VARS = "precipitation_sum,temperature_2m_mean,relative_humidity_2m_mean"
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


async def fetch_climate_open_meteo(
    lat: float,
    lon: float,
    region: str,
) -> list[dict]:
    """Fetch daily climate data and aggregate to 12-month normals.

    Args:
        lat: Latitude of the city.
        lon: Longitude of the city.
        region: City/region name for labeling records.

    Returns:
        List of 12 dicts (one per month), each with:
          region, month, rainfall_mm, temperature_avg_c, humidity_pct,
          drought_risk.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": _START_DATE,
        "end_date": _END_DATE,
        "daily": _DAILY_VARS,
        "timezone": "Africa/Dakar",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            log.log_step(Step.SYSTEM, "open_meteo_fetch_failed", level="WARNING",
                         details={"region": region, "error": str(exc)[:200]})
            return []

    daily = data.get("daily", {})
    times = daily.get("time", [])
    precip = daily.get("precipitation_sum", [])
    temp = daily.get("temperature_2m_mean", [])
    humidity = daily.get("relative_humidity_2m_mean", [])

    if not times:
        log.log_step(Step.SYSTEM, "open_meteo_empty", level="WARNING",
                     details={"region": region})
        return []

    # Aggregate daily -> monthly normals
    # month_data[month] = {"precip": [yearly sums], "temp": [daily vals], "humid": [daily vals]}
    month_precip_yearly: dict[int, dict[int, float]] = {}  # month -> {year: sum}
    month_temp: dict[int, list[float]] = {m: [] for m in range(1, 13)}
    month_humid: dict[int, list[float]] = {m: [] for m in range(1, 13)}

    for i, date_str in enumerate(times):
        month = int(date_str[5:7])
        year = int(date_str[:4])

        if i < len(precip) and precip[i] is not None:
            if month not in month_precip_yearly:
                month_precip_yearly[month] = {}
            month_precip_yearly[month][year] = (
                month_precip_yearly[month].get(year, 0.0) + precip[i]
            )

        if i < len(temp) and temp[i] is not None:
            month_temp[month].append(temp[i])

        if i < len(humidity) and humidity[i] is not None:
            month_humid[month].append(humidity[i])

    # Build 12-month normals
    records: list[dict] = []
    for month in range(1, 13):
        rec: dict = {"region": region, "month": month}

        # Rainfall: average of yearly monthly totals
        yearly_sums = list(month_precip_yearly.get(month, {}).values())
        if yearly_sums:
            rec["rainfall_mm"] = round(sum(yearly_sums) / len(yearly_sums), 1)

        # Temperature: mean of all daily values for this month
        temps = month_temp[month]
        if temps:
            rec["temperature_avg_c"] = round(sum(temps) / len(temps), 1)

        # Humidity: mean of all daily values for this month
        humids = month_humid[month]
        if humids:
            rec["humidity_pct"] = round(sum(humids) / len(humids), 1)

        # Drought risk heuristic
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

        records.append(rec)

    log.log_step(Step.SYSTEM, "open_meteo_parsed", details={
        "region": region,
        "lat": lat,
        "lon": lon,
        "daily_rows": len(times),
        "months_with_rain": sum(1 for r in records if "rainfall_mm" in r),
    })

    return records
