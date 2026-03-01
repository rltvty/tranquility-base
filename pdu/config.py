from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    neurio_ip: str
    influxdb_url: str
    influxdb_token: str
    influxdb_org: str
    influxdb_bucket: str
    influxdb_bucket_long: str
    poll_interval: float


def load() -> Config:
    load_dotenv()
    return Config(
        neurio_ip=os.environ.get("NEURIO_IP", "192.168.10.51"),
        influxdb_url=os.environ["INFLUXDB_URL"],
        influxdb_token=os.environ["INFLUXDB_TOKEN"],
        influxdb_org=os.environ["INFLUXDB_ORG"],
        influxdb_bucket=os.environ.get("INFLUXDB_BUCKET", "power_raw"),
        influxdb_bucket_long=os.environ.get("INFLUXDB_BUCKET_LONG", "power_hourly"),
        poll_interval=float(os.environ.get("POLL_INTERVAL", "2")),
    )
