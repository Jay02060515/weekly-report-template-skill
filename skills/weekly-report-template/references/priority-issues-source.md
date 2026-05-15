# Priority Issues Source

Use this reference for the second section of the weekly report email.

## Default Source

Feishu Wiki/Base URL:

```text
https://guanceyun.feishu.cn/wiki/UjjowLjWjiY2nWk7MgZchtbyn8Z?table=tblczuC0hyPSnOMj&view=vewQx72054
```

URL parts:

| Part | Value | Use |
| --- | --- | --- |
| Wiki token | `UjjowLjWjiY2nWk7MgZchtbyn8Z` | Resolve to the real Base token with `lark-cli wiki spaces get_node`. |
| Table ID | `tblczuC0hyPSnOMj` | Use as `--table-id`. |
| View ID | `vewQx72054` | Use as `--view-id` so the report follows the configured weekly view. |

## Required View Filter

Before extracting priority issues from the configured view, make sure the view filter is:

```text
开始日期 等于 本周
```

Use that same current-week view for priority issue extraction. If the view is not filtered to the current week, update or ask the user to update it before producing the final template.

## Required Fields

| Purpose | Base field name |
| --- | --- |
| Customer name | `客户名称` |
| Issue text | `反馈内容（简要描述）` |
| Conclusion text | `结论（简要描述或链接）` |
| Priority flag | `重点问题` |

## Extraction Rule

Read records from the configured view and keep only rows where `重点问题` is exactly `是`.

Recommended command pattern after resolving the Wiki token:

```bash
lark-cli base +record-list --as user \
  --base-token <resolved_base_token> \
  --table-id tblczuC0hyPSnOMj \
  --view-id vewQx72054 \
  --field-id 客户名称 \
  --field-id '反馈内容（简要描述）' \
  --field-id '结论（简要描述或链接）' \
  --field-id 重点问题 \
  --offset 0 \
  --limit 200 \
  --format json
```

If the response has `has_more=true`, continue paging until all rows in the view are checked.

## Normalized Items

Convert each retained row to:

```json
{
  "customer": "客户名称",
  "issue": "反馈内容（简要描述）",
  "conclusion": "结论（简要描述或链接）"
}
```

Place these items under item 2 in `【总体情况】`. The rendered email must use this structure:

```text
2. 重点问题：
(1) 客户名称
Issue: 反馈内容
Conclusion: 结论
```

Keep customer names in source order unless the user asks to sort. Do not rewrite the issue or conclusion unless the user explicitly requests polishing.
