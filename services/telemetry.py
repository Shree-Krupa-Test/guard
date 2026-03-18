# services/telemetry.py
#
# Azure App Insights telemetry.
#
# FIX 1: Removed export_interval=0 — this was preventing events from
#         being exported because it bypassed the SDK's internal queue.
#         SDK default interval (15s) is used instead.
#
# FIX 2: Added explicit _handler.flush() after every track call to
#         force events to be sent immediately without waiting 15s.
#
# FIX 3: Added diagnostic print after each event so terminal confirms
#         events are being fired — makes it easy to debug if portal
#         still shows no data.
#
# SINGLETON: Handler created once at module import, reused forever.
# No new aiohttp sessions opened per request.

import os
import logging
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("APPINSIGHTS_CONNECTION_STRING")

# ── Logger ──
logger = logging.getLogger("devguard-metrics")
logger.setLevel(logging.INFO)

# ── Singleton handler — created once at import, reused for all requests ──
_handler = None

if connection_string:
    try:
        from opencensus.ext.azure.log_exporter import AzureLogHandler

        # Do NOT set export_interval=0 — it blocks the export queue
        _handler = AzureLogHandler(connection_string=connection_string)
        logger.addHandler(_handler)
        print("[Telemetry] Azure App Insights connected.")

    except Exception as e:
        print(f"[Telemetry] App Insights setup failed (non-fatal): {e}")
else:
    print("[Telemetry] APPINSIGHTS_CONNECTION_STRING not set — telemetry disabled.")


def _flush():
    """Force immediate export after each event — don't wait for 15s interval."""
    if _handler:
        try:
            _handler.flush()
        except Exception:
            pass


# ── Telemetry functions ──

def track_request(project_id: str):
    logger.info(
        "devguard_request",
        extra={"custom_dimensions": {"project_id": project_id}}
    )
    _flush()
    print(f"[Telemetry] Fired devguard_request for {project_id}")


def track_blocked(project_id: str, reason: str):
    logger.warning(
        "devguard_blocked",
        extra={"custom_dimensions": {
            "project_id": project_id,
            "reason":     reason,
        }}
    )
    _flush()
    print(f"[Telemetry] Fired devguard_blocked — {reason} for {project_id}")


def track_cost(project_id: str, cost: float):
    logger.info(
        "devguard_cost",
        extra={"custom_dimensions": {
            "project_id": project_id,
            "cost_usd":   str(cost),
        }}
    )
    _flush()
    print(f"[Telemetry] Fired devguard_cost — ${cost} for {project_id}")


def track_latency(project_id: str, latency: float):
    logger.info(
        "devguard_latency",
        extra={"custom_dimensions": {
            "project_id": project_id,
            "latency_ms": str(latency),
        }}
    )
    _flush()
    print(f"[Telemetry] Fired devguard_latency — {latency}ms for {project_id}")


def flush():
    """Call on app shutdown to close the aiohttp session cleanly."""
    if _handler:
        try:
            _handler.flush()
        except Exception:
            pass