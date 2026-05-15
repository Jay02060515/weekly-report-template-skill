# Weekly Report Template Skill

一个用于生成周报邮件模板的 Codex Skill。它会从飞书/Lark Sheets 和多维表格 Base 中读取本周数据，整理总体工单统计、重点客户问题、详细数据链接，并输出可复制到邮箱里的邮件主题和正文模板。

默认情况下，这个 Skill 会生成邮件内容和一张基于最新飞书数据绘制的周报看板图，不会打开邮箱、创建草稿或发送邮件。若你明确要求发送，并且已经配置好阿里企业邮箱 SMTP 环境变量，它也可以先展示邮件草稿预览，在你确认收件人、主题和正文后通过 SMTP 发送。

Codex skill for generating weekly report email templates from Feishu/Lark Sheets and Base data, with optional confirmed SMTP sending through Aliyun Enterprise Mail.

## 安装

使用下面的 GitHub 目录链接安装：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/Jay02060515/weekly-report-template-skill/tree/main/skills/weekly-report-template
```

安装后重启 Codex，让新的 Skill 生效。

首次使用 SMTP 发送前，Codex 会提示你在本机配置发件邮箱、SMTP 密码、默认收件人等信息。不要把 SMTP 密码写进仓库、Skill 文件或对话里；建议只通过本机环境变量提供。

## 使用场景

- 从飞书多维表格读取本周客户服务统计数据
- 统计本周总体工单数、工单平台数量、消息平台反馈数量和透传率
- 提取标记为重点问题的客户反馈
- 生成周报邮件主题和正文模板
- 根据最新本周数据绘制周报看板图，并放入邮件正文
- 可选：在确认后通过阿里企业邮箱 SMTP 发送邮件

## SMTP 发送配置

发送邮件前，需要用户在本机配置环境变量。下面是模板，请替换成自己的信息：

```bash
export ALIMAIL_SMTP_USER="你的完整邮箱地址"
export ALIMAIL_SMTP_PASSWORD="三方客户端安全密码"
export ALIMAIL_DEFAULT_TO="收件人邮箱"
export ALIMAIL_DEFAULT_CC="抄送邮箱"
export ALIMAIL_DEFAULT_BCC=""
export ALIMAIL_FROM_NAME="发件人显示名"
```

默认 SMTP 配置：

```text
ALIMAIL_SMTP_HOST=smtp.qiye.aliyun.com
ALIMAIL_SMTP_PORT=465
```

SMTP 密码建议使用阿里企业邮箱的三方客户端安全密码。不要把密码写进仓库、Skill 文件或对话里。

发送时的安全流程：

1. Codex 先生成周报邮件草稿预览。
2. Codex 展示 To、CC、BCC、Subject 和正文摘要。
3. 用户明确回复确认发送后，Codex 才会调用 SMTP 发送。
4. 没有确认时，发送脚本只会 dry-run，不会发出邮件。

## Skill 路径

```text
skills/weekly-report-template
```
