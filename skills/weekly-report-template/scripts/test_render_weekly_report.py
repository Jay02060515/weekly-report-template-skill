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

        self.assertIn("本周总结", result["html_body"])
        self.assertIn("本周客户服务共处理", result["html_body"])
        self.assertIn("总工单：36", result["html_body"])
        self.assertIn("工单平台产生", result["html_body"])
        self.assertIn("工单平台：8", result["html_body"])
        self.assertIn("消息平台：28", result["html_body"])
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
        self.assertIn(f'href="{escaped_url}"', result["html_body"])
        self.assertIn("查看详细数据", result["html_body"])
        self.assertIn("图片: 图片位置", result["text_preview"])

    def test_renders_generated_dashboard_as_html_before_placeholder(self) -> None:
        result = render_weekly_report.render(
            {
                "date_range": "2026/05/11 ~ 2026/05/15",
                "image_placeholder": "图片位置",
                "overall_summary": {
                    "total_tickets": 36,
                    "pass_through_rate": "5.56%",
                    "ticket_platform_count": 8,
                },
                "dashboard_chart": {
                    "path": "./weekly-dashboard.svg",
                    "alt": "看板图",
                    "pending_count": 6,
                    "closed_count": 30,
                    "issue_type_counts": [{"label": "监控器", "count": 8}],
                    "feishu_project_counts": [{"label": "指标", "count": 2}],
                },
            }
        )

        self.assertIn("本周 CSM 处理各类问题工单数", result["html_body"])
        self.assertIn("本周提交飞书项目数", result["html_body"])
        self.assertNotIn('<img src="./weekly-dashboard.svg"', result["html_body"])
        self.assertNotIn("<p>图片位置</p>", result["html_body"])
        self.assertIn("图表: ./weekly-dashboard.svg", result["text_preview"])


if __name__ == "__main__":
    unittest.main()
