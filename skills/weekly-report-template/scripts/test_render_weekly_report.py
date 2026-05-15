#!/usr/bin/env python3
"""Smoke tests for the weekly report renderer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_weekly_report


class RenderWeeklyReportTest(unittest.TestCase):
    def test_renders_summary_with_common_feishu_number_shapes(self) -> None:
        result = render_weekly_report.render(
            {
                "team": "客户服务",
                "date_range": "2026/05/11 ~ 2026/05/15",
                "overall_summary": {
                    "total_tickets": "36个",
                    "pass_through_rate": "5.56%",
                    "ticket_platform_count": "8.0",
                },
            }
        )

        self.assertIn("本周总体工单36个", result["html_body"])
        self.assertIn("工单平台产生8个", result["html_body"])
        self.assertIn("用户反馈28个", result["html_body"])
        self.assertIn("团队: 客户服务", result["text_preview"])

    def test_escapes_user_supplied_html(self) -> None:
        result = render_weekly_report.render(
            {
                "date_range": "2026/05/11 ~ 2026/05/15",
                "sections": [
                    {
                        "title": "This Week",
                        "items": [
                            {
                                "project": "<script>alert(1)</script>",
                                "summary": "Fixed <b>unsafe</b> text",
                            }
                        ],
                    }
                ],
            }
        )

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", result["html_body"])
        self.assertIn("Fixed &lt;b&gt;unsafe&lt;/b&gt; text", result["html_body"])

    def test_renders_manual_image_placeholder_and_detail_link(self) -> None:
        url = "https://guanceyun.feishu.cn/wiki/UjjowLjWjiY2nWk7MgZchtbyn8Z?table=tblczuC0hyPSnOMj&view=vewQx72054"
        result = render_weekly_report.render(
            {
                "date_range": "2026/05/11 ~ 2026/05/15",
                "image_placeholder": "图片位置",
                "detail_url": url,
                "overall_summary": {
                    "total_tickets": 36,
                    "pass_through_rate": "5.56%",
                    "ticket_platform_count": 8,
                },
                "sections": [
                    {
                        "title": "Priority Customer Issues",
                        "items": [
                            {
                                "customer": "吉利",
                                "issue": "指标无法正常采集",
                                "conclusion": "已说明问题根因。",
                            }
                        ],
                    }
                ],
            }
        )

        self.assertIn("<p>图片位置</p>", result["html_body"])
        escaped_url = url.replace("&", "&amp;")
        self.assertIn(f'<a href="{escaped_url}">{escaped_url}</a>', result["html_body"])
        self.assertIn("图片: 图片位置", result["text_preview"])

    def test_renders_generated_dashboard_chart_before_placeholder(self) -> None:
        result = render_weekly_report.render(
            {
                "date_range": "2026/05/11 ~ 2026/05/15",
                "image_placeholder": "图片位置",
                "dashboard_chart": {"path": "./weekly-dashboard.svg", "alt": "看板图"},
            }
        )

        self.assertIn('<img src="./weekly-dashboard.svg" alt="看板图"', result["html_body"])
        self.assertNotIn("<p>图片位置</p>", result["html_body"])
        self.assertIn("图表: ./weekly-dashboard.svg", result["text_preview"])


if __name__ == "__main__":
    unittest.main()
