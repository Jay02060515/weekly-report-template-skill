#!/usr/bin/env python3
"""Render normalized weekly report JSON into an email subject and HTML body."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def esc(value: Any) -> str:
    return html.escape(text(value), quote=True)


def rich(value: Any) -> str:
    return esc(value).replace("\n", "<br>")


def parse_number(value: Any, default: float = 0.0) -> float:
    raw = text(value)
    if not raw:
        return default
    normalized = raw.replace(",", "").replace("，", "").strip()
    if normalized.endswith("%"):
        normalized = normalized[:-1].strip()
    try:
        return float(normalized)
    except ValueError:
        match = re.search(r"-?\d+(?:\.\d+)?", normalized)
        return float(match.group(0)) if match else default


def is_priority_item(item: Any) -> bool:
    return isinstance(item, dict) and any(text(item.get(key)) for key in ("customer", "issue", "conclusion"))


def format_int(value: Any) -> str:
    raw = text(value)
    if not raw:
        return "0"
    try:
        return str(int(float(raw)))
    except ValueError:
        parsed = parse_number(raw, default=0.0)
        return str(int(parsed)) if parsed else raw


def format_rate(value: Any) -> str:
    raw = text(value)
    if not raw:
        return "0.00%"
    try:
        number = float(raw)
    except ValueError:
        return raw if raw.endswith("%") else f"{raw}%"
    if number > 1:
        return f"{number:.2f}%"
    return f"{number * 100:.2f}%"


def current_workweek_label(today: date | None = None) -> str:
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return f"{monday:%Y/%m/%d} ~ {friday:%Y/%m/%d}"


def report_period(payload: dict[str, Any]) -> str:
    return text(payload.get("date_range")) or text(payload.get("week_label")) or current_workweek_label()


def render_overall_summary(summary: dict[str, Any]) -> str:
    total_raw = summary.get("total_tickets", 0)
    ticket_platform_raw = summary.get("ticket_platform_count", 0)
    total = int(parse_number(total_raw))
    ticket_platform = int(parse_number(ticket_platform_raw))
    message_feedback = summary.get("message_platform_feedback_count")
    if message_feedback is None:
        message_feedback = max(total - ticket_platform, 0)
    sentence = (
        f"本周总体工单{format_int(total)}个，总体透传率 {format_rate(summary.get('pass_through_rate'))}，"
        f"其中工单平台产生{format_int(ticket_platform)}个，各消息平台的用户反馈{format_int(message_feedback)}个。"
    )
    return esc(sentence)


def render_priority_item(item: dict[str, Any], index: int) -> str:
    customer = text(item.get("customer"))
    issue = text(item.get("issue"))
    conclusion = text(item.get("conclusion"))
    customer_label = esc(customer) if customer else "Unspecified customer"
    issue_html = rich(issue) if issue else "No issue detail provided."
    conclusion_html = rich(conclusion) if conclusion else "No conclusion provided."
    return (
        f"<div style=\"margin:0 0 18px 0;\">"
        f"<p>({index}) {customer_label}</p>"
        f"<p><strong>Issue:</strong> {issue_html}</p>"
        f"<p><strong>Conclusion:</strong> {conclusion_html}</p>"
        f"</div>"
    )


def render_item(item: dict[str, Any]) -> str:
    owner = text(item.get("owner"))
    project = text(item.get("project"))
    status = text(item.get("status"))
    impact = text(item.get("impact"))
    summary = text(item.get("summary"))
    link = text(item.get("link"))

    prefix_parts = [part for part in [project, owner] if part]
    prefix = f"<strong>{esc(' / '.join(prefix_parts))}</strong>: " if prefix_parts else ""
    status_html = f" <span style=\"color:#666;\">({esc(status)})</span>" if status else ""
    impact_html = f"<br><span style=\"color:#555;\">Impact: {esc(impact)}</span>" if impact else ""
    link_html = f" <a href=\"{esc(link)}\">Link</a>" if link else ""
    body = esc(summary) if summary else "No update detail provided."
    return f"<li>{prefix}{body}{status_html}{link_html}{impact_html}</li>"


def render_section(section: dict[str, Any]) -> str:
    title = text(section.get("title"), "Updates")
    items = section.get("items") or []
    if not isinstance(items, list):
        items = []
    if any(is_priority_item(item) for item in items):
        priority_items = [item for item in items if isinstance(item, dict)]
        if priority_items:
            rendered_items = "\n".join(render_priority_item(item, index) for index, item in enumerate(priority_items, start=1))
        else:
            rendered_items = "<p>No updates reported.</p>"
        return f"<h2>{esc(title)}</h2>\n{rendered_items}"
    if items:
        rendered_items = "\n".join(render_item(item if isinstance(item, dict) else {"summary": item}) for item in items)
    else:
        rendered_items = "<li>No updates reported.</li>"
    return f"<h2>{esc(title)}</h2>\n<ul>\n{rendered_items}\n</ul>"


def is_priority_section(section: Any) -> bool:
    if not isinstance(section, dict):
        return False
    title = text(section.get("title")).lower()
    items = section.get("items") or []
    return "重点问题" in title or any(is_priority_item(item) for item in items)


def render_overall_block(overall_summary: dict[str, Any], priority_section: dict[str, Any] | None) -> str:
    lines = [
        "<p><strong>【总体情况】</strong></p>",
        f"<p>1. {render_overall_summary(overall_summary)}</p>",
    ]
    if priority_section is not None:
        items = priority_section.get("items") or []
        priority_items = [item for item in items if isinstance(item, dict)]
        lines.append("<p>2. 重点问题：</p>")
        if priority_items:
            lines.extend(render_priority_item(item, index) for index, item in enumerate(priority_items, start=1))
        else:
            lines.append("<p>暂无重点问题。</p>")
    return "\n".join(lines)


def render_dashboard_screenshot(screenshot: dict[str, Any]) -> str:
    path = text(screenshot.get("path"))
    if not path:
        return ""
    alt = text(screenshot.get("alt"), "Dashboard screenshot")
    return (
        "<p>"
        f"<img src=\"{esc(path)}\" alt=\"{esc(alt)}\" "
        "style=\"max-width:100%;height:auto;border:0;\" />"
        "</p>"
    )


def render_image_placeholder(value: Any) -> str:
    if value is False or value is None:
        return ""
    label = text(value)
    if not label:
        label = "图片位置"
    return f"<p>{esc(label)}</p>"


def render_detail_link(payload: dict[str, Any]) -> str:
    detail = payload.get("detail_link")
    if isinstance(detail, dict):
        url = text(detail.get("url"))
        label = text(detail.get("label")) or url
    else:
        url = text(payload.get("detail_url"))
        label = text(payload.get("detail_label")) or url
    if not url:
        return ""
    return f"<p>详细数据可以查询飞书文档：<a href=\"{esc(url)}\">{esc(label)}</a></p>"


def render(payload: dict[str, Any]) -> dict[str, str]:
    team = text(payload.get("team"), "Team")
    period = report_period(payload)
    author = text(payload.get("author"))
    sections = payload.get("sections") or []
    if not isinstance(sections, list):
        sections = []
    overall_summary = payload.get("overall_summary")
    dashboard_screenshot = payload.get("dashboard_screenshot")
    image_placeholder = payload.get("image_placeholder")

    subject = text(payload.get("subject")) or f"【{period}】工单和客户反馈统计周报"

    priority_section = next((section for section in sections if is_priority_section(section)), None)
    remaining_sections = [section for section in sections if section is not priority_section]
    body_sections = []
    if isinstance(overall_summary, dict):
        body_sections.append(render_overall_block(overall_summary, priority_section if isinstance(priority_section, dict) else None))
    elif isinstance(priority_section, dict):
        body_sections.append(render_section(priority_section))
    if isinstance(dashboard_screenshot, dict):
        screenshot_html = render_dashboard_screenshot(dashboard_screenshot)
        if screenshot_html:
            body_sections.append(screenshot_html)
    elif image_placeholder is not None:
        placeholder_html = render_image_placeholder(image_placeholder)
        if placeholder_html:
            body_sections.append(placeholder_html)
    detail_link_html = render_detail_link(payload)
    if detail_link_html:
        body_sections.append(detail_link_html)
    body_sections.extend(render_section(section if isinstance(section, dict) else {"title": "Updates"}) for section in remaining_sections)
    rendered_sections = "\n".join(body_sections)
    if not rendered_sections:
        rendered_sections = render_section({"title": "Updates", "items": []})

    author_html = f"<p style=\"color:#666;\">Compiled by {esc(author)}</p>" if author else ""
    html_body = f"""<div>
{author_html}
{rendered_sections}
</div>"""

    preview_lines = [subject, period]
    if team and team != "Team":
        preview_lines.append(f"团队: {team}")
    if isinstance(overall_summary, dict):
        preview_lines.append(
            "总体情况: "
            f"{format_int(overall_summary.get('total_tickets'))} total, "
            f"{format_rate(overall_summary.get('pass_through_rate'))} pass-through"
        )
    if isinstance(dashboard_screenshot, dict) and text(dashboard_screenshot.get("path")):
        preview_lines.append(f"截图: {text(dashboard_screenshot.get('path'))}")
    elif image_placeholder is not None:
        preview_lines.append(f"图片: {text(image_placeholder, '图片位置')}")
    if text(payload.get("detail_url")):
        preview_lines.append(f"详情: {text(payload.get('detail_url'))}")
    for section in sections[:3]:
        if isinstance(section, dict):
            preview_lines.append(f"{text(section.get('title'), 'Updates')}: {len(section.get('items') or [])} item(s)")

    return {
        "subject": subject,
        "html_body": html_body,
        "text_preview": "\n".join(preview_lines),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="Path to normalized weekly report JSON, or '-' for stdin")
    args = parser.parse_args()

    raw = sys.stdin.read() if args.payload == "-" else Path(args.payload).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("Payload must be a JSON object.")
    print(json.dumps(render(payload), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
