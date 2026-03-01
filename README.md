# 🌕 Tranquility Base

> "Houston, Tranquility Base here. The Eagle has landed."

**Tranquility Base** is a monorepo for home monitoring, telemetry, and
automation --- reimagined as a lunar habitat life-support system.

This house is no longer a house.

It is a **pressurized structure** operating in a hostile environment.
Energy, atmosphere, temperature, and resource flows are monitored as if
survival depends on them --- because in a lunar outpost, it would.

------------------------------------------------------------------------

## 🛰 Project Structure

### 🧱 Habitat Alpha

The core software system powering Tranquility Base.

-   Data ingestion pipelines
-   Device integrations (starting with Neurio power monitoring)
-   Telemetry collection
-   Cloud storage + retention policies
-   Automation hooks
-   Alerting and event logic

Habitat Alpha is the infrastructure layer.

------------------------------------------------------------------------

### 🎛 CommandDeck

The visualization and control interface.

Dashboards, charts, displays, and ambient screens throughout the
habitat.

When someone sees the dashboard, it should feel like this:

    CommandDeck — Tranquility Base

    Power Core: Nominal
    Atmosphere: Stable
    Thermal Regulation: 72°F
    External Grid Link: Connected

CommandDeck translates raw telemetry into mission status.

------------------------------------------------------------------------

## ⚡ Subsystems (Initial Focus)

Starting with whole-home energy monitoring via Neurio:

-   **Power Core** --- real-time load and energy reserves
-   **External Grid Link** --- utility import/export
-   **Surface Collection** --- future solar integration
-   **Load Distribution** --- phase-level metrics
-   **Reactive Field Stability** --- power factor & VAR tracking

Future systems may include:

-   Atmospheric monitoring (CO₂, humidity, pressure)
-   Thermal regulation tracking (HVAC, heat flow)
-   Water recycling throughput
-   Environmental integrity alerts
-   Resource forecasting

------------------------------------------------------------------------

## 🧠 Philosophy

Tranquility Base is not "smart home automation."

It is:

-   Systems engineering at domestic scale
-   Observability applied to habitat survival
-   Infrastructure thinking for everyday life

The goal is clarity, resilience, and immersion.

Everything is telemetry.
Everything is status.
Everything is mission-critical.

------------------------------------------------------------------------

## 🚀 Status

Phase 1: - Neurio local polling - Cloud time-series storage - Long +
short retention strategy - CommandDeck dashboard scaffolding

Next: - Subsystem expansion - Alert logic - Automation routines -
Immersive display modes

------------------------------------------------------------------------

**Habitat Alpha is operational.**

**CommandDeck coming online.**
