# Weekly Report Template Skill

一个用于生成周报邮件模板的 Codex Skill。它会从飞书/Lark Sheets 和多维表格 Base 中读取本周数据，整理总体工单统计、重点客户问题、详细数据链接，并输出一封完整 HTML 周报邮件。

默认情况下，这个 Skill 会生成邮件内容，不会打开邮箱、创建草稿或发送邮件。若你明确要求发送，它会先展示完整预览、收件人、抄送人和主题；只有你回复确认发送后，才会通过阿里企业邮箱 SMTP 发出。

Codex skill for generating weekly report email templates from Feishu/Lark Sheets and Base data, with optional confirmed SMTP sending through Aliyun Enterprise Mail.

## 安装

使用下面的 GitHub 目录链接安装：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --url https://github.com/Jay02060515/weekly-report-template-skill/tree/main/skills/weekly-report-template
```

安装后重启 Codex，让新的 Skill 生效。

首次使用 SMTP 发送前，Codex 会引导你配置发件邮箱、To、CC、BCC，并询问是否保存为本机默认值。选择保存后，下次你只需要说“帮我写本周周报邮件”，预览确认后即可发送。

密码不要写进仓库、Skill 文件或对话里。推荐把阿里企业邮箱三方客户端安全密码保存到 macOS Keychain，发送脚本会自动读取。

## 使用场景

- 从飞书多维表格读取本周客户服务统计数据
- 统计本周总体工单数、工单平台数量、消息平台反馈数量和透传率
- 提取标记为重点问题的客户反馈
- 生成周报邮件主题和正文模板
- 根据最新本周数据绘制周报看板图，并放入邮件正文
- 可选：在确认后通过阿里企业邮箱 SMTP 发送邮件

## 首次发送配置

第一次发送时，如果没有默认收件配置，Codex 应该向你确认：

- 发件邮箱：例如 `name@example.com`
- To：收件人邮箱，多个用逗号分隔
- CC：抄送邮箱，可为空
- BCC：密送邮箱，可为空
- 发件人显示名：例如 `客户服务周报`
- 是否保存为本机默认值

如果你选择保存为默认值，Codex 会在本机安装目录创建：

```text
references/local-smtp-defaults.md
```

这个文件只保存非秘密配置，例如：

```bash
export ALIMAIL_SMTP_USER="你的完整邮箱地址"
export ALIMAIL_DEFAULT_TO="收件人邮箱，多个用逗号分隔"
export ALIMAIL_DEFAULT_CC="抄送邮箱，可为空"
export ALIMAIL_DEFAULT_BCC=""
export ALIMAIL_FROM_NAME="发件人显示名"
```

这个文件已被 `.gitignore` 忽略，不应该提交到 GitHub。

## 密码保存位置

推荐把阿里企业邮箱三方客户端安全密码保存到 macOS Keychain：

```bash
security add-generic-password -a "$USER" -s "ALIMAIL_SMTP_PASSWORD" -w
```

执行后输入密码，终端不会回显。测试是否保存成功：

```bash
security find-generic-password -a "$USER" -s "ALIMAIL_SMTP_PASSWORD" >/dev/null && echo "已保存"
```

以后发送脚本会优先读取环境变量 `ALIMAIL_SMTP_PASSWORD`，读不到时自动从 Keychain 读取 `ALIMAIL_SMTP_PASSWORD`。不要把密码写进 `local-smtp-defaults.md`、仓库、日志或对话里。

如果要更换密码：

```bash
security delete-generic-password -a "$USER" -s "ALIMAIL_SMTP_PASSWORD"
security add-generic-password -a "$USER" -s "ALIMAIL_SMTP_PASSWORD" -w
```

默认 SMTP 配置：

```text
ALIMAIL_SMTP_HOST=smtp.qiye.aliyun.com
ALIMAIL_SMTP_PORT=465
```

发送时的安全流程：

1. Codex 先生成周报邮件草稿预览。
2. Codex 展示 To、CC、BCC、Subject 和正文摘要。
3. 用户明确回复确认发送后，Codex 才会调用 SMTP 发送。
4. 没有确认时，发送脚本只会 dry-run，不会发出邮件。

## Skill 路径

```text
skills/weekly-report-template
```
