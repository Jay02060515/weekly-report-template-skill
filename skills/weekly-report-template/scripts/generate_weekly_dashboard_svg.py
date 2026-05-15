#!/usr/bin/env python3
"""Generate a weekly customer-service dashboard SVG from normalized report data."""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import render_weekly_report


COLORS = [
    "#2db2f4",
    "#e17100",
    "#88d966",
    "#ffc73d",
    "#ff7a2f",
    "#7f93f0",
    "#4387e8",
    "#bd6bf3",
    "#85bd0f",
    "#35a66d",
    "#e34f73",
    "#7f67ff",
]


def text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def esc(value: Any) -> str:
    return html.escape(text(value), quote=True)


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(text(value)))
    except ValueError:
        return default


def current_workweek_label(today: date | None = None) -> str:
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return f"{monday:%Y/%m/%d} ~ {friday:%Y/%m/%d}"


def count_items(items: Any) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        label = text(item.get("label") or item.get("name") or item.get("category"))
        count = parse_int(item.get("count") or item.get("value"))
        if label and count > 0:
            result.append((label, count))
    return result


def percent_label(value: Any) -> str:
    return render_weekly_report.format_rate(value)


def wedge_path(cx: float, cy: float, r_outer: float, r_inner: float, start: float, end: float) -> str:
    large = 1 if end - start > math.pi else 0
    x1 = cx + r_outer * math.cos(start)
    y1 = cy + r_outer * math.sin(start)
    x2 = cx + r_outer * math.cos(end)
    y2 = cy + r_outer * math.sin(end)
    x3 = cx + r_inner * math.cos(end)
    y3 = cy + r_inner * math.sin(end)
    x4 = cx + r_inner * math.cos(start)
    y4 = cy + r_inner * math.sin(start)
    return (
        f"M {x1:.2f} {y1:.2f} "
        f"A {r_outer:.2f} {r_outer:.2f} 0 {large} 1 {x2:.2f} {y2:.2f} "
        f"L {x3:.2f} {y3:.2f} "
        f"A {r_inner:.2f} {r_inner:.2f} 0 {large} 0 {x4:.2f} {y4:.2f} Z"
    )


def render_svg(payload: dict[str, Any]) -> str:
    period = text(payload.get("date_range")) or text(payload.get("week_label")) or current_workweek_label()
    overall = payload.get("overall_summary") if isinstance(payload.get("overall_summary"), dict) else {}
    chart = payload.get("dashboard_chart") if isinstance(payload.get("dashboard_chart"), dict) else {}
    issue_counts = count_items(chart.get("issue_type_counts"))
    project_counts = count_items(chart.get("feishu_project_counts"))

    total = parse_int(overall.get("total_tickets"))
    pending = parse_int(chart.get("pending_count"))
    closed = parse_int(chart.get("closed_count"))
    rate = percent_label(overall.get("pass_through_rate"))

    max_count = max([count for _, count in issue_counts] or [1])
    y_top = 424
    y_bottom = 704
    plot_height = y_bottom - y_top
    bar_gap = 28
    bar_width = 42
    start_x = 134
    bar_step = 80 if len(issue_counts) <= 10 else max(54, int(790 / max(len(issue_counts), 1)))

    bars = []
    for idx, (label, count) in enumerate(issue_counts[:12]):
        x = start_x + idx * bar_step
        height = max(8, count / max_count * plot_height)
        y = y_bottom - height
        bars.append(
            f'<rect class="bar" x="{x}" y="{y:.1f}" width="{bar_width}" height="{height:.1f}" rx="8"/>'
            f'<text class="bar-label" x="{x + 15}" y="{y - 12:.1f}">{count}</text>'
            f'<text class="tiny" x="{x - 14}" y="748" transform="rotate(-48 {x - 14} 748)">{esc(label)}</text>'
        )

    grid = []
    grid_steps = 5
    for i in range(grid_steps + 1):
        y = y_bottom - i * (plot_height / grid_steps)
        value = round(max_count * i / grid_steps)
        grid.append(f'<line class="axis" x1="100" y1="{y:.1f}" x2="890" y2="{y:.1f}"/>')
        grid.append(f'<text class="tiny" x="68" y="{y + 5:.1f}">{value}</text>')

    pie_paths = []
    total_projects = sum(count for _, count in project_counts)
    if total_projects:
        angle = -math.pi / 2
        for idx, (_, count) in enumerate(project_counts):
            next_angle = angle + 2 * math.pi * count / total_projects
            pie_paths.append(f'<path d="{wedge_path(1254, 540, 112, 50, angle, next_angle)}" fill="{COLORS[idx % len(COLORS)]}"/>')
            angle = next_angle

    pie_labels = []
    label_positions = [
        (1406, 424), (1430, 512), (1400, 618), (1268, 694), (1110, 682), (1040, 600),
        (1022, 514), (1038, 430), (1168, 382), (1320, 382), (1460, 586), (1180, 734),
    ]
    for idx, (label, count) in enumerate(project_counts[:12]):
        x, y = label_positions[idx % len(label_positions)]
        color = COLORS[idx % len(COLORS)]
        pie_labels.append(f'<circle cx="{x - 16}" cy="{y - 5}" r="6" fill="{color}"/><text class="small" x="{x}" y="{y}">{esc(label)}：{count}</text>')

    legend = []
    for idx, (label, _) in enumerate(project_counts[:5]):
        x = 1030 + idx * 104
        legend.append(f'<circle cx="{x}" cy="758" r="7" fill="{COLORS[idx % len(COLORS)]}"/><text class="legend" x="{x + 16}" y="764">{esc(label)}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="860" viewBox="0 0 1600 860">
  <defs>
    <style>
      .bg {{ fill: #eaf6ff; }}
      .card {{ fill: #a7cdf6; }}
      .panel {{ fill: #bfdefc; }}
      .title {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 42px; font-weight: 800; fill: #172033; }}
      .subtitle {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 18px; fill: #4b7fae; }}
      .h2 {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 27px; font-weight: 800; fill: #0e4e94; }}
      .label {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 20px; font-weight: 650; fill: #1d5b95; }}
      .small {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 16px; fill: #2e72ad; }}
      .tiny {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 14px; fill: #4388ca; }}
      .kpi {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 72px; font-weight: 900; fill: #055d72; }}
      .kpi-blue {{ fill: #101b8e; }}
      .kpi-green {{ fill: #35b400; }}
      .kpi-dark {{ fill: #182035; }}
      .axis {{ stroke: #8bb7df; stroke-width: 1; opacity: .75; }}
      .bar {{ fill: #438ede; }}
      .bar-label {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 16px; fill: #357fd0; font-weight: 700; }}
      .legend {{ font-family: "PingFang SC","Microsoft YaHei",Arial,sans-serif; font-size: 16px; fill: #316da4; }}
    </style>
  </defs>
  <rect class="bg" width="1600" height="860"/>
  <text class="title" x="40" y="64">2026年周客户服务统计看板</text>
  <text class="subtitle" x="42" y="94">{esc(period)}</text>

  <rect class="card" x="42" y="120" width="350" height="160" rx="24"/>
  <text class="label" x="78" y="176">总工单数</text>
  <text class="kpi" x="78" y="246">{total}</text>

  <rect class="card" x="420" y="120" width="350" height="160" rx="24"/>
  <text class="label" x="456" y="176">跟进中/待回复</text>
  <text class="kpi kpi-blue" x="456" y="246">{pending}</text>

  <rect class="card" x="798" y="120" width="350" height="160" rx="24"/>
  <text class="label" x="834" y="176" fill="#20a000">已关闭</text>
  <text class="kpi kpi-green" x="834" y="246">{closed}</text>

  <rect class="card" x="1176" y="120" width="350" height="160" rx="24"/>
  <text class="label" x="1212" y="176">透传率</text>
  <text class="kpi kpi-dark" x="1212" y="246">{esc(rate)}</text>

  <rect class="panel" x="42" y="318" width="910" height="482" rx="24"/>
  <text class="h2" x="74" y="368">本周 CSM 处理各类问题工单数</text>
  <text class="small" x="64" y="400">数量</text>
  {''.join(grid)}
  {''.join(bars)}
  <text class="small" x="433" y="786">问题类型</text>

  <rect class="panel" x="990" y="318" width="568" height="482" rx="24"/>
  <text class="h2" x="1022" y="368">本周提交各类问题的飞书项目数</text>
  {''.join(pie_paths)}
  <circle cx="1254" cy="540" r="50" fill="#bfdefc"/>
  <text class="label" x="1254" y="536" text-anchor="middle">项目</text>
  <text class="label" x="1254" y="564" text-anchor="middle">{total_projects}</text>
  {''.join(pie_labels)}
  {''.join(legend)}
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="Path to normalized weekly report JSON, or '-' for stdin")
    parser.add_argument("--output", "-o", required=True, help="Output SVG path")
    args = parser.parse_args()

    raw = sys.stdin.read() if args.payload == "-" else Path(args.payload).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("Payload must be a JSON object.")
    Path(args.output).write_text(render_svg(payload), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
