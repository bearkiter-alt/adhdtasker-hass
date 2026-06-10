"""Constants for the ADHDTasker integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "adhdtasker"

# The family-scoped inbound API (generate a key in the web app → Manage → Inbound API).
DEFAULT_API_URL = "https://us-central1-adhdtasker-68a50.cloudfunctions.net/api"
DEFAULT_SCAN_INTERVAL = 60  # seconds

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SECRET = "secret"
CONF_WEBHOOK_ID = "webhook_id"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.TODO, Platform.BUTTON]

# Event fired on the HA bus when an ADHDTasker webhook arrives (secret stripped).
EVENT_RECEIVED = f"{DOMAIN}_event"

# Service names
SERVICE_ADD_TASK = "add_task"
SERVICE_ADD_INTERRUPT = "add_interrupt"
SERVICE_CLAIM_TASK = "claim_task"
SERVICE_COMPLETE_TASK = "complete_task"
SERVICE_APPROVE_TASK = "approve_task"
SERVICE_PING = "ping"
SERVICE_NAMES = (
    SERVICE_ADD_TASK,
    SERVICE_ADD_INTERRUPT,
    SERVICE_CLAIM_TASK,
    SERVICE_COMPLETE_TASK,
    SERVICE_APPROVE_TASK,
    SERVICE_PING,
)
