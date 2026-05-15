# Dashboard Chart Source

Use this reference when generating the weekly dashboard chart for the email body.

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
| View ID | `vewQx72054` | Use as `--view-id`. |

## Required View Filter

Before generating the chart, make sure the view filter is:

```text
开始日期 等于 本周
```

Use this current-week view for every chart metric.

## Required Fields

Read these fields from the weekly view:

| Purpose | Base field name |
| --- | --- |
| Status KPI | `状态` |
| Issue type bar chart | `问题类型` |

Recommended command:

```bash
lark-cli base +record-list --as user \
  --base-token <resolved_base_token> \
  --table-id tblczuC0hyPSnOMj \
  --view-id vewQx72054 \
  --field-id 状态 \
  --field-id 问题类型 \
  --offset 0 \
  --limit 200 \
  --format json
```

If `has_more=true`, continue paging until all current-week rows are included.

## Normalization Rules

- `dashboard_chart.pending_count`: count rows where `状态` is `跟进中` or `待回复`.
- `dashboard_chart.closed_count`: count rows where `状态` is `已关闭` or `已解决`.
- `dashboard_chart.issue_type_counts`: count all current-week rows by `问题类型`.
- `dashboard_chart.feishu_project_counts`: count rows where `状态` is `已提交飞书项目`, grouped by `问题类型`.
- Keep categories in descending count order. For ties, keep source or stable field-option order if known.
- If a row has no `问题类型`, either skip it from the chart or group it as `未分类`; mention the assumption.

## Generate Chart

Use:

```bash
python3 scripts/generate_weekly_dashboard_svg.py payload.json --output weekly-dashboard.svg
```

Add the generated file to the normalized payload before rendering:

```json
{
  "dashboard_chart": {
    "path": "./weekly-dashboard.svg",
    "alt": "2026年周客户服务统计看板",
    "pending_count": 6,
    "closed_count": 30,
    "issue_type_counts": [
      {"label": "监控器", "count": 8}
    ],
    "feishu_project_counts": [
      {"label": "指标", "count": 2}
    ]
  }
}
```

The generated SVG must not include the bottom customer-feedback detail table or the top-right Feishu support badge.
