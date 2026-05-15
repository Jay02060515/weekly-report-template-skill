# Overall Summary Source

Use this reference for the first section of the weekly report email.

## Default Source

Feishu Wiki/Base dashboard URL:

```text
https://guanceyun.feishu.cn/wiki/UjjowLjWjiY2nWk7MgZchtbyn8Z?table=blkDixQ8FhptY5sJ
```

URL parts:

| Part | Value | Use |
| --- | --- | --- |
| Wiki token | `UjjowLjWjiY2nWk7MgZchtbyn8Z` | Resolve to the real Base token with `lark-cli wiki spaces get_node`. |
| Dashboard ID | `blkDixQ8FhptY5sJ` | Dashboard containing the visible weekly metrics. |
| Detail table ID | `tblczuC0hyPSnOMj` | Source detail table: `📋客户服务统计表`. |
| Weekly view ID | `vewQx72054` | Weekly filtered view to count current-week records. |
| Rate table ID | `tblWJRUGUHotjTfp` | Source table: `2026透传率计算表`. |

## Required View Filter

Before reading weekly records from:

```text
https://guanceyun.feishu.cn/wiki/UjjowLjWjiY2nWk7MgZchtbyn8Z?table=tblczuC0hyPSnOMj&view=vewQx72054
```

make sure the view filter is:

```text
开始日期 等于 本周
```

Use this current-week filter for all weekly counts. If the visible view is not filtered this way, update or ask the user to update the view/filter before generating the report; do not silently use an unfiltered or differently filtered view.

## Required Values

| Normalized field | Source |
| --- | --- |
| `total_tickets` | Count records in `tblczuC0hyPSnOMj` using view `vewQx72054`. |
| `pass_through_rate` | Read field `透传率/周` from table `tblWJRUGUHotjTfp`. |
| `ticket_platform_count` | Count records in weekly view where `来源类型` is `工单`. |
| `message_platform_feedback_count` | Calculate `total_tickets - ticket_platform_count`. |

## Extraction Commands

Resolve the Wiki token first:

```bash
lark-cli wiki spaces get_node --as user --params '{"token":"UjjowLjWjiY2nWk7MgZchtbyn8Z"}'
```

Then count total records and ticket-platform records from the weekly view:

```bash
lark-cli base +record-list --as user \
  --base-token <resolved_base_token> \
  --table-id tblczuC0hyPSnOMj \
  --view-id vewQx72054 \
  --field-id 来源类型 \
  --offset 0 \
  --limit 200 \
  --format json
```

If `has_more=true`, continue paging and add counts across pages. Count a record as ticket-platform generated when `来源类型` equals `工单`.

Read weekly pass-through rate:

```bash
lark-cli base +record-list --as user \
  --base-token <resolved_base_token> \
  --table-id tblWJRUGUHotjTfp \
  --field-id '透传率/周' \
  --offset 0 \
  --limit 20 \
  --format json
```

Use the first non-empty `透传率/周` value unless the user specifies a different calculation row. Values may be returned as decimal strings, for example `0.051282051`; render as a percentage with two decimal places.

## Normalized Object

```json
{
  "total_tickets": 36,
  "pass_through_rate": 0.0556,
  "ticket_platform_count": 8
}
```

Derive `message_platform_feedback_count` during rendering as:

```text
total_tickets - ticket_platform_count
```

## Email Format

Render as the first item under `【总体情况】`:

```text
【总体情况】
1. 本周总体工单36个，总体透传率 5.56%，其中工单平台产生8个，各消息平台的用户反馈28个。
```

Do not invent missing values. If any required value is unavailable, produce the final template only after either recovering the value from another configured source or asking the user for that value.
