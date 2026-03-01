# PDU — Power Distribution Unit Monitor

Lightweight poller that scrapes a Neurio sensor's local HTTP page and writes readings to InfluxDB Cloud. Designed to run on a minimal-resource Ubuntu box.

## What it captures

The Neurio sensor exposes `both_tables.html` with two tables. We read the **Sensor Readings** table (channels 1, 2, 3) and store:

| Field | Description |
|---|---|
| `power_kw` | Instantaneous real power |
| `reactive_kvar` | Instantaneous reactive power |
| `voltage_v` | Line voltage |
| `energy_imported_kwh` | Cumulative energy counter (may reset on device reboot) |

Channel 3 is the whole-home total and the primary metric for dashboards and analysis.

## Telemetry plan

### Bucket A — `power_raw` (high-frequency)
- **Resolution**: ~every 2 seconds (configurable via `POLL_INTERVAL`)
- **Retention**: 30 days
- **Channels**: 1, 2, 3
- All four fields above per sample

### Bucket B — `power_hourly` (downsampled)
- **Resolution**: 1-hour aggregates
- **Retention**: uncapped (no expiry)
- **Channel**: 3 only
- Computed fields:
  - `mean_power_kw` — average load during hour
  - `max_power_kw` — peak load during hour
  - `mean_voltage_v` — average voltage
  - `energy_kwh` — delta of `energy_imported_kwh` counter over the hour

Downsampling is handled by an InfluxDB task created automatically on first run.

## Polling behavior

The Neurio device frequently returns empty data. On each poll tick the service retries (with 0.5s back-off) until a valid sensor reading is returned, then writes to InfluxDB and sleeps for `POLL_INTERVAL` seconds.

## Setup

1. **Install dependencies**
   ```bash
   cd pdu
   uv sync
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Neurio IP and InfluxDB Cloud credentials
   ```

3. **Run**
   ```bash
   uv run python main.py
   ```

### Running as a systemd service

Create `/etc/systemd/system/pdu.service`:

```ini
[Unit]
Description=PDU Neurio poller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/pdu
EnvironmentFile=/opt/pdu/.env
ExecStart=/usr/bin/env uv run python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pdu
```
