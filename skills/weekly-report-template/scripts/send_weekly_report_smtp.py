#!/usr/bin/env python3
"""Send a rendered weekly report through Aliyun Enterprise Mail SMTP."""

from __future__ import annotations

import argparse
import html.parser
import json
import os
import smtplib
import subprocess
import sys
from email.header import Header
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any

import render_weekly_report


LOCAL_DEFAULTS_PATH = Path(__file__).resolve().parents[1] / "references" / "local-smtp-defaults.md"


def text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


class HTMLToText(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "h1", "h2", "h3", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        raw = " ".join(self.parts)
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        return "\n".join(line for line in lines if line).strip()


def split_addresses(values: list[str] | None) -> list[str]:
    addresses: list[str] = []
    for value in values or []:
        for part in value.split(","):
            address = part.strip()
            if address:
                addresses.append(address)
    return addresses


def env_addresses(name: str) -> list[str]:
    value = os.environ.get(name, "").strip()
    return split_addresses([value]) if value else []


def load_local_defaults(path: Path = LOCAL_DEFAULTS_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    defaults: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("export ") or "=" not in stripped:
            continue
        name, raw_value = stripped[len("export ") :].split("=", 1)
        name = name.strip()
        value = raw_value.strip().strip("\"'")
        if name.startswith("ALIMAIL_"):
            defaults[name] = value
    return defaults


def config_value(name: str, defaults: dict[str, str], fallback: str = "") -> str:
    return os.environ.get(name, "").strip() or defaults.get(name, "").strip() or fallback


def config_addresses(name: str, defaults: dict[str, str]) -> list[str]:
    value = config_value(name, defaults)
    return split_addresses([value]) if value else []


def load_payload(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("Payload must be a JSON object.")
    return payload


def html_to_text(html_body: str) -> str:
    parser = HTMLToText()
    parser.feed(html_body)
    return parser.text()


def keychain_password() -> str:
    service = os.environ.get("ALIMAIL_KEYCHAIN_SERVICE", "ALIMAIL_SMTP_PASSWORD").strip()
    account = os.environ.get("ALIMAIL_KEYCHAIN_ACCOUNT", os.environ.get("USER", "")).strip()
    if not service or not account:
        return ""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def require_config(name: str, defaults: dict[str, str]) -> str:
    value = config_value(name, defaults)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def require_smtp_password() -> str:
    value = os.environ.get("ALIMAIL_SMTP_PASSWORD", "").strip() or keychain_password()
    if not value:
        raise SystemExit(
            "Missing SMTP password. Set ALIMAIL_SMTP_PASSWORD or store it in macOS Keychain "
            "with service ALIMAIL_SMTP_PASSWORD."
        )
    return value


def build_message(
    *,
    smtp_user: str,
    from_name: str,
    to: list[str],
    cc: list[str],
    subject: str,
    html_body: str,
    inline_files: list[tuple[Path, str]],
) -> MIMEMultipart:
    message = MIMEMultipart("related")
    message["Subject"] = str(Header(subject, "utf-8"))
    message["From"] = formataddr((str(Header(from_name, "utf-8")), smtp_user)) if from_name else smtp_user
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(html_to_text(html_body), "plain", "utf-8"))
    alternative.attach(MIMEText(html_body, "html", "utf-8"))
    message.attach(alternative)
    for path, cid in inline_files:
        if not path.exists():
            continue
        subtype = "svg+xml" if path.suffix.lower() == ".svg" else "octet-stream"
        part = MIMEBase("image", subtype)
        part.set_payload(path.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-ID", f"<{cid}>")
        part.add_header("Content-Disposition", "inline", filename=path.name)
        message.attach(part)
    return message


def inline_chart_files(payload: dict[str, Any], html_body: str, base_dir: Path) -> tuple[str, list[tuple[Path, str]]]:
    chart = payload.get("dashboard_chart")
    if not isinstance(chart, dict):
        return html_body, []
    path_text = text(chart.get("path"))
    if not path_text:
        return html_body, []
    path = Path(path_text)
    if not path.is_absolute():
        path = base_dir / path
    cid = "weekly-dashboard-chart"
    source = f'src="{html.escape(path_text, quote=True)}"'
    if source not in html_body:
        return html_body, []
    updated = html_body.replace(source, f'src="cid:{cid}"')
    return updated, [(path, cid)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="Path to normalized weekly report JSON, or '-' for stdin")
    parser.add_argument("--to", action="append", help="Recipient address; repeat or comma-separate. Defaults to ALIMAIL_DEFAULT_TO.")
    parser.add_argument("--cc", action="append", help="CC address; repeat or comma-separate. Defaults to ALIMAIL_DEFAULT_CC.")
    parser.add_argument("--bcc", action="append", help="BCC address; repeat or comma-separate. Defaults to ALIMAIL_DEFAULT_BCC.")
    parser.add_argument("--subject", help="Override rendered subject")
    parser.add_argument("--from-name", help="Optional sender display name. Defaults to ALIMAIL_FROM_NAME.")
    parser.add_argument("--confirm-send", action="store_true", help="Actually send. Without this flag, only print a dry-run summary.")
    args = parser.parse_args()

    defaults = load_local_defaults()
    to = split_addresses(args.to) or config_addresses("ALIMAIL_DEFAULT_TO", defaults)
    cc = split_addresses(args.cc) or config_addresses("ALIMAIL_DEFAULT_CC", defaults)
    bcc = split_addresses(args.bcc) or config_addresses("ALIMAIL_DEFAULT_BCC", defaults)
    if not to:
        raise SystemExit("At least one --to recipient is required.")

    payload = load_payload(args.payload)
    rendered = render_weekly_report.render(payload)
    payload_base_dir = Path.cwd() if args.payload == "-" else Path(args.payload).resolve().parent
    subject = args.subject or rendered["subject"]
    html_body = rendered["html_body"]
    html_body, inline_files = inline_chart_files(payload, html_body, payload_base_dir)
    smtp_user = require_config("ALIMAIL_SMTP_USER", defaults)
    from_name = args.from_name if args.from_name is not None else config_value("ALIMAIL_FROM_NAME", defaults)
    host = config_value("ALIMAIL_SMTP_HOST", defaults, "smtp.qiye.aliyun.com")
    port = int(config_value("ALIMAIL_SMTP_PORT", defaults, "465"))

    summary = {
        "to": to,
        "cc": cc,
        "bcc": bcc,
        "subject": subject,
        "smtp_user": smtp_user,
        "host": host,
        "port": port,
        "text_preview": rendered.get("text_preview", ""),
        "inline_files": [str(path) for path, _ in inline_files],
        "sent": False,
    }

    if not args.confirm_send:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    smtp_password = require_smtp_password()
    message = build_message(
        smtp_user=smtp_user,
        from_name=from_name,
        to=to,
        cc=cc,
        subject=subject,
        html_body=html_body,
        inline_files=inline_files,
    )
    recipients = to + cc + bcc
    with smtplib.SMTP_SSL(summary["host"], summary["port"], timeout=20) as client:
        client.login(smtp_user, smtp_password)
        client.sendmail(smtp_user, recipients, message.as_string())

    summary["sent"] = True
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
