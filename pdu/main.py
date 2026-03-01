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
            # Sleep until the next poll_interval boundary on the wall clock.
            # This ensures all boxes wake at the same time regardless of start.
            now = time.time()
            next_tick = (now // cfg.poll_interval + 1) * cfg.poll_interval
            sleep_for = next_tick - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            if _shutdown:
                break

            # Capture the tick we woke up for — retries may take time but
            # the timestamp written to InfluxDB should match this boundary.
            tick_ts = next_tick

            readings = _poll_until_valid(http_client, cfg.neurio_ip)
            if not readings:
                break  # shutdown requested
            influxdb.write_readings(influx_client, cfg.influxdb_bucket, readings, tick_ts)
            for r in readings:
                log.info(
                    "sample_written",
                    channel=r.channel,
                    power_kw=r.power_kw,
                    reactive_kvar=r.reactive_kvar,
                    voltage_v=r.voltage_v,
                    energy_imported_kwh=r.energy_imported_kwh,
                )
    finally:
        http_client.close()
        influx_client.close()
        log.info("stopped")


if __name__ == "__main__":
    main()
