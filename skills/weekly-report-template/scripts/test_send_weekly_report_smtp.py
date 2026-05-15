#!/usr/bin/env python3
"""Smoke tests for the SMTP weekly report sender."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import send_weekly_report_smtp


def sample_payload() -> dict[str, object]:
    return {
        "date_range": "2026/05/11 ~ 2026/05/15",
        "image_placeholder": "图片位置",
        "overall_summary": {
            "total_tickets": 36,
            "pass_through_rate": "5.56%",
            "ticket_platform_count": 8,
        },
    }


class SendWeeklyReportSmtpTest(unittest.TestCase):
    def run_main(self, argv: list[str], env: dict[str, str]) -> str:
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, "argv", argv):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                send_weekly_report_smtp.main()
            return buffer.getvalue()

    def test_dry_run_does_not_connect_to_smtp(self) -> None:
        with TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "payload.json"
            payload_path.write_text(json.dumps(sample_payload(), ensure_ascii=False), encoding="utf-8")

            with mock.patch("smtplib.SMTP_SSL") as smtp:
                output = self.run_main(
                    [
                        "send_weekly_report_smtp.py",
                        str(payload_path),
                        "--to",
                        "team@example.com",
                    ],
                    {"ALIMAIL_SMTP_USER": "sender@example.com"},
                )

            smtp.assert_not_called()
            summary = json.loads(output)
            self.assertFalse(summary["sent"])
            self.assertEqual(summary["to"], ["team@example.com"])
            self.assertIn("工单和客户反馈统计周报", summary["subject"])

    def test_confirm_send_uses_smtp_ssl(self) -> None:
        with TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "payload.json"
            payload_path.write_text(json.dumps(sample_payload(), ensure_ascii=False), encoding="utf-8")

            smtp_instance = mock.Mock()
            smtp_context = mock.Mock()
            smtp_context.__enter__ = mock.Mock(return_value=smtp_instance)
            smtp_context.__exit__ = mock.Mock(return_value=False)
            with mock.patch("smtplib.SMTP_SSL", return_value=smtp_context) as smtp_ssl:
                output = self.run_main(
                    [
                        "send_weekly_report_smtp.py",
                        str(payload_path),
                        "--to",
                        "team@example.com,owner@example.com",
                        "--cc",
                        "cc@example.com",
                        "--bcc",
                        "hidden@example.com",
                        "--confirm-send",
                    ],
                    {
                        "ALIMAIL_SMTP_USER": "sender@example.com",
                        "ALIMAIL_SMTP_PASSWORD": "secret",
                    },
                )

            smtp_ssl.assert_called_once_with("smtp.qiye.aliyun.com", 465, timeout=20)
            smtp_instance.login.assert_called_once_with("sender@example.com", "secret")
            recipients = smtp_instance.sendmail.call_args.args[1]
            self.assertEqual(recipients, ["team@example.com", "owner@example.com", "cc@example.com", "hidden@example.com"])
            summary = json.loads(output)
            self.assertTrue(summary["sent"])

    def test_dry_run_uses_default_recipients_from_env(self) -> None:
        with TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "payload.json"
            payload_path.write_text(json.dumps(sample_payload(), ensure_ascii=False), encoding="utf-8")

            output = self.run_main(
                [
                    "send_weekly_report_smtp.py",
                    str(payload_path),
                ],
                {
                    "ALIMAIL_SMTP_USER": "sender@example.com",
                    "ALIMAIL_DEFAULT_TO": "team@example.com,owner@example.com",
                    "ALIMAIL_DEFAULT_CC": "cc@example.com",
                },
            )

            summary = json.loads(output)
            self.assertEqual(summary["to"], ["team@example.com", "owner@example.com"])
            self.assertEqual(summary["cc"], ["cc@example.com"])
            self.assertFalse(summary["sent"])

    def test_confirm_send_requires_password(self) -> None:
        with TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "payload.json"
            payload_path.write_text(json.dumps(sample_payload(), ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                self.run_main(
                    [
                        "send_weekly_report_smtp.py",
                        str(payload_path),
                        "--to",
                        "team@example.com",
                        "--confirm-send",
                    ],
                    {"ALIMAIL_SMTP_USER": "sender@example.com"},
                )

            self.assertIn("ALIMAIL_SMTP_PASSWORD", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
