# Spreadsheet Contract

Use this reference when reading Feishu spreadsheet rows for a weekly report email.

## Minimum Required Fields

At least one column must identify the reporting period, and at least one column must contain report content.

Recommended headers:

| Normalized field | Preferred headers | Notes |
| --- | --- | --- |
| `week` | 周次, Week, week_label, 报告周期 | Use for weekly filtering. |
| `date` | 日期, Date, 更新时间, update_date | Use when week is absent; derive the week from date. |
| `owner` | 负责人, Owner, 成员, 姓名, Name | Used for grouping and attribution. |
| `project` | 项目, Project, 模块, 主题 | Optional but useful for scanning. |
| `completed` | 本周完成, 完成事项, Done, This Week | Main content for the "This Week" section. |
| `next` | 下周计划, 计划, Next Week, Plan | Main content for the "Next Week" section. |
| `risk` | 风险, 阻塞, Blocker, Risk, 问题 | Main content for the "Risks and Blockers" section. |
| `status` | 状态, Status, 进度 | Preserve if available. |
| `impact` | 影响, 价值, Impact, Outcome | Preserve if available. |
| `link` | 链接, Link, URL, 相关文档 | Convert to an HTML link if present. |

## Filtering Rules

Prefer explicit user input for the target week. If absent, default to the current local week and state that assumption.

Filter rows in this order:

1. Match `week` or reporting-period column exactly when present.
2. Otherwise, include rows whose `date` falls within the requested Monday-to-Friday work week.
3. Otherwise, include non-empty rows and warn that no period column was found.

## Normalization Rules

- Ignore fully empty rows.
- Trim whitespace in every text field.
- Split multi-line cells into separate bullet items when they contain distinct tasks.
- Preserve source links, ticket IDs, and document URLs.
- Do not invent completion status, owner, metrics, or risks.
- If a row has no owner, use `Unassigned` and mention the gap in the final response.
- If a section has no content, render a short neutral placeholder such as `No updates reported.`

## Grouping Guidance

Default grouping:

1. Group by `project` when most rows have a project.
2. Otherwise group by `owner`.
3. Otherwise keep source row order.

For leadership-facing reports, prefer concise project grouping. For team-internal reports, owner grouping is usually easier to follow.
