# Token 费用精准计算

## 原则：用余额差值，不用估算

DeepSeek 的实际计费受缓存命中率、thinking 模式等多个因素影响，
**不要估缓存命中率或猜汇率来算费用**——唯一精确的方式是余额减法。

## 脚本位置

`/root/.hermes/scripts/calculate_token_cost.py`

挂在每日总结 cron（6:00）作为 `script`，其输出注入到 LLM prompt。

## 工作原理

```
第一次运行（6月4日）
  → 记录当日余额 ¥3.32 到 .cost_state.json

第二天运行（6月5日 6:00）
  → 读昨日余额 ¥3.32
  → 查当前余额 ¥1.50
  → 精确花费 = 3.32 - 1.50 = ¥1.82
  → 输出到报告
  → 保存今日余额（给明天用）
```

## 输出示例

```
Token 消耗明细（2026-06-05）

1. 实际花费（余额差值法）
   昨日余额:   ¥3.32
   今日余额:   ¥1.50
   ━━━━━━━━━━━━━━━━━━━━━━━━
   实际花费:   ¥1.82

2. Token 用量参考（Hermes Insights）
   会话: 12  工具调用: 378
   Input:  1.60M tokens
   Output: 504.8K tokens
   V4 Flash: 169.99M tokens

   定价参考（/1M tokens，USD→CNY）:
   V4 Flash:
     Input miss: $0.14 (¥1.02)
     Input hit:  $0.0028 (¥0.02)
     Output:     $0.28 (¥2.04)

余额: ¥1.50
余额偏低（<¥5）
```

## 状态文件

`/root/.hermes/scripts/.cost_state.json`

```json
{
  "last_balance": 3.32,
  "last_date": "2026-06-04"
}
```

- 只在日期变化时更新（每天第一次运行记录当日余额）
- 同一天多次运行不会覆盖基准

## 相关 cron

| Job | 时间 | 脚本 |
|-----|------|------|
| 每日总结报告 | 6:00 | `calculate_token_cost.py` (script) + LLM prompt |
| DeepSeek 余额日报 | 6:05 | `check_deepseek_balance.py` (no_agent，纯余额) |

## 注意

- `write_file` 工具会自动将 `sk-xxx` 格式的 API Key 替换为 `***`，
  因此含 Key 的脚本修改必须用 `sed`/Python 写文件，不走 `write_file`
- `hermes insights --days 1` 返回的是截至当前时刻的近 1 天数据，
  不是自然日。但余额差值是精准的自然日消耗
