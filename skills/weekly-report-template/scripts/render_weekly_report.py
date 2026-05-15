#!/usr/bin/env python3
"""Render normalized weekly report JSON into an email subject and HTML body."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date, datetime, timedelta
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


def count_items(items: Any) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        label = text(item.get("label") or item.get("name") or item.get("category"))
        count = int(parse_number(item.get("count") or item.get("value"), default=0.0))
        if label and count > 0:
            result.append((label, count))
    return result


def render_metric_card(label: str, value: str, color: str = "#075985") -> str:
    return (
        '<td style="width:25%;padding:0 6px 12px 0;vertical-align:top;">'
        '<div style="background:#f8fbff;border:1px solid #dce8f7;border-radius:14px;padding:14px 16px;">'
        f'<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">{esc(label)}</div>'
        f'<div style="font-size:30px;font-weight:800;line-height:1.15;color:{color};">{esc(value)}</div>'
        '</div>'
        '</td>'
    )


def render_issue_rows(issue_counts: list[tuple[str, int]]) -> str:
    if not issue_counts:
        return '<div style="font-size:14px;color:#6b7280;">暂无问题类型数据。</div>'
    max_count = max(count for _, count in issue_counts)
    rows = []
    for label, count in issue_counts[:10]:
        width = max(12, int(count / max_count * 100))
        rows.append(
            '<tr>'
            f'<td style="width:100px;padding:7px 10px 7px 0;font-size:13px;color:#334155;line-height:1.4;">{esc(label)}</td>'
            '<td style="padding:7px 10px 7px 0;">'
            '<div style="height:11px;background:#d9ebff;border-radius:999px;overflow:hidden;">'
            f'<div style="width:{width}%;height:11px;background:#3b82d6;border-radius:999px;"></div>'
            '</div>'
            '</td>'
            f'<td style="width:28px;padding:7px 0;text-align:right;font-size:13px;font-weight:700;color:#0f172a;">{count}</td>'
            '</tr>'
        )
    return (
        '<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;width:100%;">'
        + ''.join(rows)
        + '</table>'
    )


def render_project_chips(project_counts: list[tuple[str, int]]) -> str:
    if not project_counts:
        return '<div style="font-size:14px;color:#6b7280;">暂无飞书项目提交数据。</div>'
    palette = ["#e0f2fe", "#fff7ed", "#f0fdf4", "#fffbeb", "#fef2f2", "#eef2ff", "#f5f3ff", "#ecfdf5"]
    text_palette = ["#0369a1", "#c2410c", "#15803d", "#b45309", "#b91c1c", "#3730a3", "#6d28d9", "#047857"]
    chips = []
    for idx, (label, count) in enumerate(project_counts[:10]):
        chips.append(
            f'<span style="display:inline-block;margin:0 8px 10px 0;padding:8px 11px;border-radius:999px;'
            f'background:{palette[idx % len(palette)]};color:{text_palette[idx % len(text_palette)]};'
            f'font-size:13px;line-height:1.1;font-weight:600;">{esc(label)}：{count}</span>'
        )
    total = sum(count for _, count in project_counts)
    return (
        f'<div style="margin:0 0 12px;font-size:14px;color:#475569;">本周共提交 '
        f'<strong style="font-size:24px;color:#075985;">{total}</strong> 个飞书项目。</div>'
        + ''.join(chips)
    )


def render_dashboard_chart(chart: dict[str, Any], overall_summary: dict[str, Any] | None, period: str) -> str:
    overall = overall_summary or {}
    total = format_int(overall.get("total_tickets"))
    pending = format_int(chart.get("pending_count"))
    closed = format_int(chart.get("closed_count"))
    rate = format_rate(overall.get("pass_through_rate"))
    issue_counts = count_items(chart.get("issue_type_counts"))
    project_counts = count_items(chart.get("feishu_project_counts"))
    return (
        '<div style="background:#eaf6ff;border-radius:16px;padding:18px 18px 20px;margin:0;">'
        f'<div style="font-size:22px;font-weight:800;color:#172033;margin:0 0 2px;">2026年周客户服务统计看板</div>'
        f'<div style="font-size:13px;color:#2f70aa;margin:0 0 18px;">{esc(period)}</div>'
        '<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="border-collapse:collapse;width:100%;">'
        '<tr>'
        f'{render_metric_card("总工单数", total)}'
        f'{render_metric_card("跟进中/待回复", pending, "#1726a0")}'
        f'{render_metric_card("已关闭", closed, "#1fb400")}'
        f'{render_metric_card("透传率", rate, "#172033")}'
        '</tr>'
        '</table>'
        '<div style="background:#bfdbfe;border-radius:14px;padding:16px 18px;margin:4px 0 14px;">'
        '<div style="font-size:17px;font-weight:800;color:#0e4e94;margin:0 0 12px;">本周 CSM 处理各类问题工单数</div>'
        f'{render_issue_rows(issue_counts)}'
        '</div>'
        '<div style="background:#bfdbfe;border-radius:14px;padding:16px 18px;">'
        '<div style="font-size:17px;font-weight:800;color:#0e4e94;margin:0 0 12px;">本周提交飞书项目数</div>'
        f'{render_project_chips(project_counts)}'
        '</div>'
        '</div>'
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


def generated_time_label(payload: dict[str, Any]) -> str:
    configured = text(payload.get("generated_time"))
    if configured:
        return configured
    return f"{datetime.now().strftime('%Y-%m-%d %H:%M')}（Asia/Shanghai）"


def plain_overall_summary(summary: dict[str, Any]) -> str:
    total = int(parse_number(summary.get("total_tickets", 0)))
    ticket_platform = int(parse_number(summary.get("ticket_platform_count", 0)))
    message_feedback = summary.get("message_platform_feedback_count")
    if message_feedback is None:
        message_feedback = max(total - ticket_platform, 0)
    return (
        f"本周总体工单{format_int(total)}个，总体透传率 {format_rate(summary.get('pass_through_rate'))}。"
        f"其中，工单平台产生{format_int(ticket_platform)}个，各消息平台用户反馈{format_int(message_feedback)}个。"
    )


def render_priority_cards(priority_section: dict[str, Any] | None) -> str:
    items = priority_section.get("items") if isinstance(priority_section, dict) else []
    if not isinstance(items, list):
        items = []
    priority_items = [item for item in items if isinstance(item, dict)]
    if not priority_items:
        return (
            '<div style="padding:14px 16px;background:#f8fbff;border:1px solid #dce8f7;'
            'border-radius:12px;font-size:14px;line-height:1.8;color:#4b5563;">暂无重点问题。</div>'
        )
    cards = []
    for index, item in enumerate(priority_items, start=1):
        customer = text(item.get("customer"), f"重点问题 {index}")
        issue = text(item.get("issue"), "无反馈内容")
        conclusion = text(item.get("conclusion"), "无结论")
        cards.append(
            '<div style="margin:0 0 12px;padding:14px 16px;background:#ffffff;border:1px solid #e5edf6;'
            'border-radius:12px;">'
            f'<div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:8px;">({index}) {esc(customer)}</div>'
            f'<div style="font-size:14px;line-height:1.75;color:#374151;"><strong>Issue:</strong> {rich(issue)}</div>'
            f'<div style="font-size:14px;line-height:1.75;color:#374151;margin-top:4px;"><strong>Conclusion:</strong> {rich(conclusion)}</div>'
            '</div>'
        )
    return "".join(cards)


def render_section_shell(title: str, body: str, padding_bottom: int = 0) -> str:
    return (
        f'<div style="padding:26px 32px {padding_bottom}px;">'
        f'<h2 style="margin:0 0 14px;font-size:18px;line-height:1.4;color:#0f172a;">{esc(title)}</h2>'
        f'{body}'
        '</div>'
    )


def render_detail_footer(payload: dict[str, Any]) -> str:
    detail = payload.get("detail_link")
    if isinstance(detail, dict):
        url = text(detail.get("url"))
        label = text(detail.get("label"), "查看详细数据")
    else:
        url = text(payload.get("detail_url"))
        label = text(payload.get("detail_label"), "查看详细数据")
    if not url:
        return ""
    return (
        '<div style="padding:28px 32px 34px;">'
        f'<a href="{esc(url)}" style="display:inline-block;padding:12px 18px;background:#1557c8;'
        f'color:#ffffff !important;text-decoration:none;border-radius:10px;font-size:14px;font-weight:700;">{esc(label)}</a>'
        '</div>'
    )


def render(payload: dict[str, Any]) -> dict[str, str]:
    team = text(payload.get("team"), "Team")
    period = report_period(payload)
    author = text(payload.get("author"))
    sections = payload.get("sections") or []
    if not isinstance(sections, list):
        sections = []
    overall_summary = payload.get("overall_summary")
    dashboard_chart = payload.get("dashboard_chart")
    dashboard_screenshot = payload.get("dashboard_screenshot")
    image_placeholder = payload.get("image_placeholder")

    subject = text(payload.get("subject")) or f"【{period}】工单和客户反馈统计周报"

    priority_section = next((section for section in sections if is_priority_section(section)), None)
    remaining_sections = [section for section in sections if section is not priority_section]

    body_sections = [
        '<div style="background:linear-gradient(135deg,#0f4fbf 0%,#2f7cf4 100%);color:#ffffff;padding:28px 32px 24px;">'
        '<div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.84;margin-bottom:10px;">WEEKLY BRIEF</div>'
        '<h1 style="margin:0 0 10px;font-size:28px;line-height:1.2;font-weight:700;">工单和客户反馈统计周报</h1>'
        '<p style="margin:0;font-size:14px;line-height:1.7;color:rgba(255,255,255,0.92);">'
        '本周客户服务工单与各消息平台反馈已汇总如下；本邮件保留需要优先关注的总体情况、重点问题和问题分布。'
        '</p>'
        '</div>',
        '<div style="background:#f8fbff;border-bottom:1px solid #e5edf6;padding:18px 32px;'
        'font-size:13px;line-height:1.9;color:#4b5563;">'
        f'<strong style="color:#0f172a;">统计周期：</strong>{esc(period)}<br>'
        f'<strong style="color:#0f172a;">生成时间：</strong>{esc(generated_time_label(payload))}'
        '</div>',
    ]

    if isinstance(overall_summary, dict):
        body_sections.append(
            render_section_shell(
                "一眼结论",
                '<div style="margin:0;padding:14px 16px;background:#f8fbff;border:1px solid #dce8f7;'
                f'border-radius:12px;font-size:15px;line-height:1.9;color:#111827;">{esc(plain_overall_summary(overall_summary))}</div>',
            )
        )
    elif isinstance(priority_section, dict):
        body_sections.append(render_section_shell("一眼结论", '<div style="font-size:14px;color:#4b5563;">暂无总体统计。</div>'))

    body_sections.append(render_section_shell("重点问题", render_priority_cards(priority_section if isinstance(priority_section, dict) else None)))

    if isinstance(dashboard_chart, dict):
        chart_html = render_dashboard_chart(dashboard_chart, overall_summary if isinstance(overall_summary, dict) else None, period)
        if chart_html:
            body_sections.append(render_section_shell("核心指标", chart_html))
    elif isinstance(dashboard_screenshot, dict):
        screenshot_html = render_dashboard_screenshot(dashboard_screenshot)
        if screenshot_html:
            body_sections.append(render_section_shell("核心指标", screenshot_html))
    elif image_placeholder is not None:
        placeholder_html = render_image_placeholder(image_placeholder)
        if placeholder_html:
            body_sections.append(render_section_shell("核心指标", placeholder_html))

    detail_link_html = render_detail_link(payload)
    body_sections.extend(render_section(section if isinstance(section, dict) else {"title": "Updates"}) for section in remaining_sections)
    body_sections.append(render_detail_footer(payload))
    rendered_sections = "\n".join(part for part in body_sections if part)
    if not rendered_sections:
        rendered_sections = render_section({"title": "Updates", "items": []})

    author_html = f"<p style=\"color:#666;\">Compiled by {esc(author)}</p>" if author else ""
    html_body = f"""<div style="margin:0;padding:28px 16px;background:#f3f6fb;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif;color:#1f2937;">
<div style="max-width:760px;margin:0 auto;background:#ffffff;border:1px solid #dbe5f0;border-radius:18px;overflow:hidden;box-shadow:0 12px 36px rgba(15,23,42,0.08);">
{author_html}
{rendered_sections}
</div>
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
    if isinstance(dashboard_chart, dict) and text(dashboard_chart.get("path")):
        preview_lines.append(f"图表: {text(dashboard_chart.get('path'))}")
    elif isinstance(dashboard_screenshot, dict) and text(dashboard_screenshot.get("path")):
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
