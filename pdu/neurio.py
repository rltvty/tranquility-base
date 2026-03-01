from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

_ROW_RE = re.compile(r'<tr\s+align="right">\s*(.*?)\s*</tr>', re.S | re.I)
_CELL_RE = re.compile(r"<td>\s*([^<]*)\s*</td>", re.I)


@dataclass(frozen=True)
class SensorReading:
    channel: int
    power_kw: float
    reactive_kvar: float
    voltage_v: float
    energy_imported_kwh: float


def fetch_sensor_readings(ip: str, client: httpx.Client) -> list[SensorReading]:
    """Fetch and parse sensor readings from Neurio's both_tables.html page.

    Returns an empty list when the device returns no usable data (common).
    """
    url = f"http://{ip}/both_tables.html"
    resp = client.get(
        url,
        headers={
            "User-Agent": "neurio-poll/0.1",
            "Accept": "text/html,*/*",
            "Connection": "close",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        timeout=5,
    )
    resp.raise_for_status()
    html = resp.text

    if "Sensor Readings" not in html:
        return []

    _, sensor_part = html.split("Sensor Readings", 1)

    readings: list[SensorReading] = []
    for row_html in _ROW_RE.findall(sensor_part):
        cells = [c.strip() for c in _CELL_RE.findall(row_html)]
        if len(cells) < 6:
            continue
        ch, kw, imp, _exp, kvar, v = cells[:6]
        try:
            channel = int(ch)
        except (ValueError, TypeError):
            continue
        if channel not in (1, 2, 3):
            continue
        try:
            readings.append(
                SensorReading(
                    channel=channel,
                    power_kw=float(kw),
                    reactive_kvar=float(kvar),
                    voltage_v=float(v),
                    energy_imported_kwh=float(imp),
                )
            )
        except (ValueError, TypeError):
            continue

    return readings
