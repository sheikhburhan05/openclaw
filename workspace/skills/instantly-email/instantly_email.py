#!/usr/bin/env python3
"""
Instantly Email API helper for OpenClaw skill workflows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


DEFAULT_BASE_URL = "https://api.instantly.ai"


def _build_url(base_url: str, path: str, query: Optional[Dict[str, Any]] = None) -> str:
    if not path.startswith("/"):
        path = "/" + path
    url = base_url.rstrip("/") + path
    if query:
        filtered = {k: v for k, v in query.items() if v is not None}
        if filtered:
            url += "?" + urllib.parse.urlencode(filtered)
    return url


def _request(method: str, path: str, api_key: str, base_url: str, body: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    data: Optional[bytes] = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        _build_url(base_url, path, query=query),
        method=method.upper(),
        headers=headers,
        data=data,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {"ok": True, "status": resp.status}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"ok": True, "status": resp.status, "raw": raw}
    except urllib.error.HTTPError as err:
        payload = err.read().decode("utf-8")
        try:
            parsed = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            parsed = {"raw": payload}
        return {
            "ok": False,
            "status": err.code,
            "error": parsed,
        }
    except urllib.error.URLError as err:
        return {"ok": False, "error": str(err)}


def _parse_json_arg(raw: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid JSON: {err}") from err
    if not isinstance(parsed, dict):
        raise ValueError("JSON payload must be an object.")
    return parsed


def _print(data: Dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=True))


def _require_api_key(args: argparse.Namespace) -> str:
    api_key = args.api_key or os.getenv("INSTANTLY_API_KEY")
    if not api_key:
        raise ValueError("Missing API key. Set --api-key or INSTANTLY_API_KEY.")
    return api_key


def _base_url(args: argparse.Namespace) -> str:
    return args.base_url or os.getenv("INSTANTLY_API_BASE_URL", DEFAULT_BASE_URL)


def cmd_list(args: argparse.Namespace) -> Dict[str, Any]:
    query = {
        "limit": args.limit,
        "starting_after": args.starting_after,
        "search": args.search,
        "mode": args.mode,
        "email_type": args.email_type,
    }
    if args.is_unread:
        query["is_unread"] = "true"
    return _request("GET", "/api/v2/emails", _require_api_key(args), _base_url(args), query=query)


def cmd_get(args: argparse.Namespace) -> Dict[str, Any]:
    return _request("GET", f"/api/v2/emails/{args.email_id}", _require_api_key(args), _base_url(args))


def cmd_test(args: argparse.Namespace) -> Dict[str, Any]:
    return _request("POST", "/api/v2/emails/test", _require_api_key(args), _base_url(args), body=_parse_json_arg(args.json))


def cmd_reply(args: argparse.Namespace) -> Dict[str, Any]:
    return _request("POST", "/api/v2/emails/reply", _require_api_key(args), _base_url(args), body=_parse_json_arg(args.json))


def cmd_forward(args: argparse.Namespace) -> Dict[str, Any]:
    return _request("POST", "/api/v2/emails/forward", _require_api_key(args), _base_url(args), body=_parse_json_arg(args.json))


def cmd_patch(args: argparse.Namespace) -> Dict[str, Any]:
    return _request("PATCH", f"/api/v2/emails/{args.email_id}", _require_api_key(args), _base_url(args), body=_parse_json_arg(args.json))


def cmd_delete(args: argparse.Namespace) -> Dict[str, Any]:
    return _request("DELETE", f"/api/v2/emails/{args.email_id}", _require_api_key(args), _base_url(args))


def cmd_unread_count(args: argparse.Namespace) -> Dict[str, Any]:
    return _request("GET", "/api/v2/emails/unread/count", _require_api_key(args), _base_url(args))


def cmd_mark_thread_read(args: argparse.Namespace) -> Dict[str, Any]:
    return _request(
        "POST",
        f"/api/v2/emails/threads/{args.thread_id}/mark-as-read",
        _require_api_key(args),
        _base_url(args),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Instantly Email API helper")
    parser.add_argument("--api-key", help="Instantly API key (fallback: INSTANTLY_API_KEY)")
    parser.add_argument("--base-url", help=f"API base URL (default: {DEFAULT_BASE_URL})")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="GET /api/v2/emails")
    p_list.add_argument("--limit", type=int, default=25)
    p_list.add_argument("--starting-after")
    p_list.add_argument("--search")
    p_list.add_argument("--mode", choices=["emode_focused", "emode_others", "emode_all"])
    p_list.add_argument("--is-unread", action="store_true")
    p_list.add_argument("--email-type", choices=["received", "sent", "manual"])
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="GET /api/v2/emails/{id}")
    p_get.add_argument("--email-id", required=True)
    p_get.set_defaults(func=cmd_get)

    p_test = sub.add_parser("test", help="POST /api/v2/emails/test")
    p_test.add_argument("--json", required=True, help="JSON body")
    p_test.set_defaults(func=cmd_test)

    p_reply = sub.add_parser("reply", help="POST /api/v2/emails/reply")
    p_reply.add_argument("--json", required=True, help="JSON body")
    p_reply.set_defaults(func=cmd_reply)

    p_forward = sub.add_parser("forward", help="POST /api/v2/emails/forward")
    p_forward.add_argument("--json", required=True, help="JSON body")
    p_forward.set_defaults(func=cmd_forward)

    p_patch = sub.add_parser("patch", help="PATCH /api/v2/emails/{id}")
    p_patch.add_argument("--email-id", required=True)
    p_patch.add_argument("--json", required=True, help="JSON body")
    p_patch.set_defaults(func=cmd_patch)

    p_delete = sub.add_parser("delete", help="DELETE /api/v2/emails/{id}")
    p_delete.add_argument("--email-id", required=True)
    p_delete.set_defaults(func=cmd_delete)

    p_unread = sub.add_parser("unread-count", help="GET /api/v2/emails/unread/count")
    p_unread.set_defaults(func=cmd_unread_count)

    p_mark = sub.add_parser("mark-thread-read", help="POST /api/v2/emails/threads/{thread_id}/mark-as-read")
    p_mark.add_argument("--thread-id", required=True)
    p_mark.set_defaults(func=cmd_mark_thread_read)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        _print(result)
        return 0 if result.get("ok", True) else 1
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
