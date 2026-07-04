# Demo：没有经验记忆时的失败案例

## 用户问题

请帮我画销售额随时间变化的趋势图。

## CSV 字段

```text
date, amount, region
```

## 没有经验记忆时的 Agent 行为

Agent 没有先检查 CSV schema，也没有确认真实字段名，而是根据用户问题中的“销售额”猜测数据中存在 `sales_amount` 字段。

## 错误工具调用

```text
plot_chart(x="date", y="sales_amount")
```

## 失败结果

```text
ColumnNotFound: column sales_amount not found
```

## 问题原因

Agent 在生成图表前没有先检查 schema，直接基于自然语言描述编造了不存在的字段名。实际 CSV 中的销售额字段是 `amount`，不是 `sales_amount`。
