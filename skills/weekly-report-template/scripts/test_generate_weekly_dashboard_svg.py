#!/usr/bin/env python3
"""Smoke tests for the weekly dashboard SVG generator."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_weekly_dashboard_svg


class GenerateWeeklyDashboardSvgTest(unittest.TestCase):
    def test_generates_svg_with_latest_metrics_and_without_feishu_badge(self) -> None:
        payload = {
            "date_range": "2026/05/11 ~ 2026/05/15",
            "overall_summary": {
                "total_tickets": 45,
                "pass_through_rate": "0.051282051",
                "ticket_platform_count": 5,
            },
            "dashboard_chart": {
                "pending_count": 6,
                "closed_count": 30,
                "issue_type_counts": [
                    {"label": "监控器", "count": 8},
                    {"label": "日志", "count": 6},
                ],
                "feishu_project_counts": [
                    {"label": "指标", "count": 2},
                    {"label": "日志", "count": 1},
                ],
            },
        }

        svg = generate_weekly_dashboard_svg.render_svg(payload)

        self.assertIn("2026年周客户服务统计看板", svg)
        self.assertIn(">45<", svg)
        self.assertIn(">6<", svg)
        self.assertIn(">30<", svg)
        self.assertIn("5.13%", svg)
        self.assertIn("监控器", svg)
        self.assertIn("指标", svg)
        self.assertNotIn("飞书多维表格", svg)
        self.assertNotIn("客户服务问题反馈汇总", svg)

    def test_writes_svg_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "payload.json"
            output_path = Path(tmpdir) / "dashboard.svg"
            payload_path.write_text(json.dumps({"overall_summary": {"total_tickets": 1}}, ensure_ascii=False), encoding="utf-8")

            with unittest.mock.patch.object(
                sys,
                "argv",
                ["generate_weekly_dashboard_svg.py", str(payload_path), "--output", str(output_path)],
            ):
                generate_weekly_dashboard_svg.main()

            self.assertTrue(output_path.exists())
            self.assertIn("<svg", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
