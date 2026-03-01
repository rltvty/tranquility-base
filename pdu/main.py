from __future__ import annotations

import signal
import time

import httpx
import structlog

import config
import influxdb
import neurio

log = structlog.get_logger()

_shutdown = False


def _handle_signal(signum: int, _frame: object) -> None:
    global _shutdown
    log.info("shutdown_signal", signal=signal.Signals(signum).name)
    _shutdown = True


def _poll_until_valid(client: httpx.Client, ip: str) -> list[neurio.SensorReading]:
    """Retry fetching sensor readings until a non-empty result is returned."""
    attempt = 0
    while not _shutdown:
        attempt += 1
        try:
            readings = neurio.fetch_sensor_readings(ip, client)
            if readings:
                if attempt > 1:
                    log.debug("poll_retry_succeeded", attempts=attempt)
                return readings
            log.debug("poll_empty_response", attempt=attempt)
        except Exception:
            log.warning("poll_error", attempt=attempt, exc_info=True)
        time.sleep(0.5)
    return []


def main() -> None:
    cfg = config.load()
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(min_level="DEBUG"),
    )
    log.info("starting", neurio_ip=cfg.neurio_ip, poll_interval=cfg.poll_interval)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    influx_client = influxdb.setup(cfg)
    http_client = httpx.Client()

    try:
        while not _shutdown:
            readings = _poll_until_valid(http_client, cfg.neurio_ip)
            if not readings:
                break  # shutdown requested
            influxdb.write_readings(influx_client, cfg.influxdb_bucket, readings)
            for r in readings:
                log.info(
                    "sample_written",
                    channel=r.channel,
                    power_kw=r.power_kw,
                    reactive_kvar=r.reactive_kvar,
                    voltage_v=r.voltage_v,
                    energy_imported_kwh=r.energy_imported_kwh,
                )
            time.sleep(cfg.poll_interval)
    finally:
        http_client.close()
        influx_client.close()
        log.info("stopped")


if __name__ == "__main__":
    main()
