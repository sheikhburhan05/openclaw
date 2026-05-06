"""Sales Navigator Playwright helpers (connect, save, InMail).
CLI entry: ``scripts/linkedin_sales_nav_cli.py`` (optional ``sales_nav_connect.py`` forwarder).
"""

from .common import DEFAULT_OPENCLAW_CDP_URL
from .connect_actions import send_sales_nav_connection_request
from .inmail import send_inmail_message
from .save import DEFAULT_LIST_NAME, save_lead_to_list

__all__ = (
    "DEFAULT_OPENCLAW_CDP_URL",
    "DEFAULT_LIST_NAME",
    "save_lead_to_list",
    "send_inmail_message",
    "send_sales_nav_connection_request",
)
