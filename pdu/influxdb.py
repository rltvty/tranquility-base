from __future__ import annotations

from datetime import datetime, timezone

import structlog
from influxdb_client import BucketRetentionRules, InfluxDBClient, Point, TaskCreateRequest
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

from config import Config
from neurio import SensorReading

log = structlog.get_logger()

MEASUREMENT = "power_sensor"

# Retention: 30 days in seconds
_30_DAYS_S = 30 * 24 * 60 * 60

def _build_downsample_flux(
    task_name: str, src: str, dst: str, measurement: str, org: str
) -> str:
    """Build Flux script for hourly downsampling of channel 3."""
    # Using string concatenation to avoid {{}} escaping issues with Flux records.
    return (
        f'option task = {{name: "{task_name}", every: 1h}}\n'
        f"\n"
        f"data = from(bucket: \"{src}\")\n"
        f"  |> range(start: -1h)\n"
        f'  |> filter(fn: (r) => r._measurement == "{measurement}" and r.channel == "3")\n'
        f"\n"
        f'mean_power = data |> filter(fn: (r) => r._field == "power_kw") |> mean() |> set(key: "_field", value: "mean_power_kw")\n'
        f'max_power = data |> filter(fn: (r) => r._field == "power_kw") |> max() |> set(key: "_field", value: "max_power_kw")\n'
        f'mean_voltage = data |> filter(fn: (r) => r._field == "voltage_v") |> mean() |> set(key: "_field", value: "mean_voltage_v")\n'
        f'last_energy = data |> filter(fn: (r) => r._field == "energy_imported_kwh") |> last() |> set(key: "_field", value: "last_energy_kwh")\n'
        f'first_energy = data |> filter(fn: (r) => r._field == "energy_imported_kwh") |> first() |> set(key: "_field", value: "first_energy_kwh")\n'
        f"\n"
        f"union(tables: [mean_power, max_power, mean_voltage, last_energy, first_energy])\n"
        f"  |> pivot(rowKey: [\"_time\"], columnKey: [\"_field\"], valueColumn: \"_value\")\n"
        f"  |> map(fn: (r) => ({{ r with\n"
        f'      _measurement: "{measurement}_hourly",\n'
        f"      energy_kwh: r.last_energy_kwh - r.first_energy_kwh,\n"
        f"  }}))\n"
        f"  |> drop(columns: [\"last_energy_kwh\", \"first_energy_kwh\"])\n"
        f'  |> to(bucket: "{dst}", org: "{org}")\n'
    )


def _ensure_bucket(
    client: InfluxDBClient,
    org: str,
    name: str,
    retention_seconds: int,
) -> None:
    buckets_api = client.buckets_api()
    try:
        existing = buckets_api.find_bucket_by_name(name)
    except ApiException as e:
        if e.status == 404:
            existing = None
        else:
            raise
    if existing:
        log.info("bucket_exists", bucket=name)
        return
    rules = (
        [BucketRetentionRules(type="expire", every_seconds=retention_seconds)]
        if retention_seconds > 0
        else []
    )
    buckets_api.create_bucket(bucket_name=name, retention_rules=rules, org=org)
    log.info("bucket_created", bucket=name, retention_seconds=retention_seconds)


def _ensure_downsample_task(
    client: InfluxDBClient,
    org: str,
    src_bucket: str,
    dst_bucket: str,
) -> None:
    tasks_api = client.tasks_api()
    task_name = f"downsample_{src_bucket}_to_{dst_bucket}"
    existing = tasks_api.find_tasks(name=task_name)
    if existing:
        log.info("downsample_task_exists", task=task_name)
        return
    flux = _build_downsample_flux(
        task_name=task_name,
        src=src_bucket,
        dst=dst_bucket,
        measurement=MEASUREMENT,
        org=org,
    )
    org_id = _org_id(client, src_bucket)
    task_request = TaskCreateRequest(flux=flux, org_id=org_id, status="active")
    tasks_api.create_task(task_create_request=task_request)
    log.info("downsample_task_created", task=task_name)


def _org_id(client: InfluxDBClient, bucket_name: str) -> str:
    """Get org ID by looking up a known bucket (more reliable on InfluxDB Cloud)."""
    bucket = client.buckets_api().find_bucket_by_name(bucket_name)
    return bucket.org_id


def setup(cfg: Config) -> InfluxDBClient:
    """Create buckets and downsampling task if they don't exist. Return client."""
    client = InfluxDBClient(url=cfg.influxdb_url, token=cfg.influxdb_token, org=cfg.influxdb_org)
    _ensure_bucket(client, cfg.influxdb_org, cfg.influxdb_bucket, _30_DAYS_S)
    _ensure_bucket(client, cfg.influxdb_org, cfg.influxdb_bucket_long, 0)
    try:
        _ensure_downsample_task(client, cfg.influxdb_org, cfg.influxdb_bucket, cfg.influxdb_bucket_long)
    except ApiException as e:
        log.warning(
            "downsample_task_setup_failed",
            status=e.status,
            message=e.body,
            hint="Tasks API may not be available on your InfluxDB Cloud plan. "
            "You can create the downsampling task manually in the UI.",
        )
    return client


def write_readings(
    client: InfluxDBClient,
    bucket: str,
    readings: list[SensorReading],
) -> None:
    now = datetime.now(timezone.utc)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    points = []
    for r in readings:
        p = (
            Point(MEASUREMENT)
            .tag("channel", str(r.channel))
            .field("power_kw", r.power_kw)
            .field("reactive_kvar", r.reactive_kvar)
            .field("voltage_v", r.voltage_v)
            .field("energy_imported_kwh", r.energy_imported_kwh)
            .time(now)
        )
        points.append(p)
    write_api.write(bucket=bucket, record=points)
