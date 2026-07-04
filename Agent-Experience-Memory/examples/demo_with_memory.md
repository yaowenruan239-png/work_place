# Demo：使用经验记忆后的成功案例

## 用户问题

请帮我画销售额随时间变化的趋势图。

## CSV 字段

```text
date, amount, region
```

## 检索到的经验

```text
生成图表前必须检查字段名
```

经验提醒 Agent：生成图表前必须先检查实际字段名，不要基于用户自然语言描述编造列名。

## 使用经验记忆后的 Agent 行为

Agent 不再直接猜测字段名，而是先检查 CSV schema。

检查后发现：

- 存在时间字段：`date`
- 不存在字段：`sales_amount`
- 真实销售额字段是：`amount`

## 正确工具调用

```text
plot_chart(x="date", y="amount")
```

## 成功结果

成功生成销售额随时间变化的趋势图。

## 改进点

经验记忆在任务执行前提供了约束，让 Agent 先检查 schema，再选择真实字段，从而避免重复出现 `ColumnNotFound` 错误。
