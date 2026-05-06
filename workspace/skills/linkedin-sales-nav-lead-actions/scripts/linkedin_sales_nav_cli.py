#!/usr/bin/env python3
"""
CLI for Sales Navigator lead actions (`/sales/lead/...`): **connect**, **save**, **InMail**.

Library code lives in ``linkedin_sales_nav/``. Run this file from cron/shell:

    python3 …/linkedin_sales_nav_cli.py --openclaw --action …

OpenClaw: ``--openclaw`` / CDP. No credentials.

Install: pip3 install playwright && python3 -m playwright install chromium
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, Optional

from linkedin_sales_nav import DEFAULT_LIST_NAME
from linkedin_sales_nav.common import DEFAULT_OPENCLAW_CDP_URL
from linkedin_sales_nav.connect_actions import send_sales_nav_connection_request
from linkedin_sales_nav.inmail import send_inmail_message
from linkedin_sales_nav.save import save_lead_to_list


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sales Nav automation. Use --openclaw / CDP (no passwords)."
    )
    parser.add_argument(
        "--action",
        choices=["connect", "save", "inmail"],
        default="connect",
        help="Action: connect (default); save adds lead to list; inmail sends InMail.",
    )
    parser.add_argument(
        "--list-name",
        default=DEFAULT_LIST_NAME,
        help=f"(save) List name. Default: '{DEFAULT_LIST_NAME}'.",
    )
    parser.add_argument(
        "--subject",
        default="",
        help="InMail subject (required for --action inmail).",
    )
    parser.add_argument(
        "--body",
        default="",
        help="InMail body (required for --action inmail).",
    )
    parser.add_argument(
        "--no-send",
        action="store_true",
        help="Compose InMail but do not click Send.",
    )
    parser.add_argument(
        "--profile-url",
        required=True,
        help="Sales Navigator lead URL.",
    )
    parser.add_argument(
        "--note",
        default="",
        help="(connect) Optional invitation note.",
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    parser.add_argument("--user-data-dir", default="", help="Standalone Chromium profile path.")
    parser.add_argument(
        "--openclaw",
        action="store_true",
        help="CDP attach to OpenClaw browser (--browser-profile openclaw).",
    )
    parser.add_argument("--cdp-url", default="", help="Override OPENCLAW_BROWSER_CDP_URL.")

    args = parser.parse_args(list(argv) if argv is not None else None)

    cdp_arg = (args.cdp_url or "").strip()
    if args.user_data_dir.strip() and (args.openclaw or cdp_arg):
        parser.error("Use either --user-data-dir or CDP (--openclaw / --cdp-url), not both.")

    oc_browser = False
    cdp_kw: Optional[str] = None
    if args.openclaw:
        oc_browser = True
        cdp_kw = cdp_arg or None
    elif cdp_arg:
        cdp_kw = cdp_arg

    if args.action == "inmail":
        if not args.subject.strip():
            parser.error("--subject is required for --action inmail")
        if not args.body.strip():
            parser.error("--body is required for --action inmail")
        out = send_inmail_message(
            args.profile_url,
            subject=args.subject,
            body=args.body,
            send=not args.no_send,
            dry_run=args.dry_run,
            user_data_dir=(args.user_data_dir.strip() or None),
            use_openclaw_browser=oc_browser,
            cdp_url=cdp_kw,
        )
    elif args.action == "save":
        out = save_lead_to_list(
            args.profile_url,
            list_name=args.list_name,
            dry_run=args.dry_run,
            user_data_dir=(args.user_data_dir.strip() or None),
            use_openclaw_browser=oc_browser,
            cdp_url=cdp_kw,
        )
    else:
        out = send_sales_nav_connection_request(
            args.profile_url,
            note=(args.note or None),
            headless=args.headless,
            dry_run=args.dry_run,
            user_data_dir=(args.user_data_dir.strip() or None),
            use_openclaw_browser=oc_browser,
            cdp_url=cdp_kw,
        )
    print(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
