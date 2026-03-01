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

The Neurio device frequently returns empty data. On each poll tick the service retries (with 0.5s back-off) until a valid sensor reading is returned, then writes to InfluxDB.

Polling is **wall-clock aligned** — all instances wake at the same epoch-aligned boundaries (e.g., every 30s: `:00`, `:30`, `:00`...) regardless of when they started. This is critical for multi-box dedup (see below).

## Multi-box redundancy

PDU is designed to run on multiple boxes simultaneously for durability. All instances poll the same Neurio and write to the same InfluxDB buckets.

Deduplication works because:
1. **Wall-clock aligned polling** — all boxes wake at the same `POLL_INTERVAL` boundaries
2. **Tick-pinned timestamps** — the timestamp is captured when the tick fires, not after retries complete
3. **InfluxDB upsert** — identical `measurement + tags + timestamp` = last writer wins (same data)

Requires NTP-synced clocks across boxes (standard on modern Linux).

## Deploying

### Prerequisites

1. SSH key access to target boxes (add entries to `~/.ssh/config`)
2. A configured `.env` file (see `.env.example`)

### Deploy to a box

```bash
cd pdu
./deploy.sh <ssh-host> .env
```

This will:
- Create `/opt/pdu` on the remote box
- Rsync the project files
- Copy your `.env`
- Install `uv` if needed and run `uv sync`
- Install and start the `pdu` systemd service

### Deploy to multiple boxes

```bash
./deploy.sh cb0 .env
./deploy.sh cb1 .env
./deploy.sh cb2 .env
```

### Manage the service

```bash
# Check status
ssh cb0 "sudo systemctl status pdu"

# View logs
ssh cb0 "journalctl -u pdu -f"

# Restart
ssh cb0 "sudo systemctl restart pdu"
```

## Local development

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

3. **Run locally**
   ```bash
   uv run python main.py
   ```

   If the Neurio is on a remote network, use an SSH tunnel:
   ```bash
   ssh -N -L 8080:192.168.10.51:80 <ssh-host>
   # Then in another terminal:
   NEURIO_IP=localhost:8080 uv run python main.py
   ```
