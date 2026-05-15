# Weekly Report Template Skill

一个用于生成周报邮件模板的 Codex Skill。它会从飞书/Lark Sheets 和多维表格 Base 中读取本周数据，整理总体工单统计、重点客户问题、详细数据链接，并输出可复制到邮箱里的邮件主题和正文模板。

这个 Skill 只负责生成邮件内容，不会打开邮箱、创建草稿或发送邮件。看板截图位置会保留为 `图片位置`，方便你自己截图后手动粘贴。

Codex skill for generating weekly report email templates from Feishu/Lark Sheets and Base data.

## 安装

使用下面的 GitHub 目录链接安装：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/Jay02060515/weekly-report-template-skill/tree/main/skills/weekly-report-template
```

安装后重启 Codex，让新的 Skill 生效。

## 使用场景

- 从飞书多维表格读取本周客户服务统计数据
- 统计本周总体工单数、工单平台数量、消息平台反馈数量和透传率
- 提取标记为重点问题的客户反馈
- 生成周报邮件主题和正文模板
- 保留 `图片位置`，用于手动粘贴看板截图

## Skill 路径

```text
skills/weekly-report-template
```
