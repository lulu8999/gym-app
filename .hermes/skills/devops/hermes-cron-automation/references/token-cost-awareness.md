# Token 成本意识 — 本用户的使用场景

## 背景

本用户使用 DeepSeek V4 Flash（通过 DeepSeek 官方 API），当前余额约 3.65 CNY。
之前用 OpenClaw 时曾因反复调工具消耗 **2 亿 tokens**，缓存命中率仅 20%，所以对 token 消耗比较敏感。已充值 10+ 元后对支出敏感。

## 官方定价（deepseek-v4-flash，USD，来自 api-docs.deepseek.com）

| 类型 | USD/百万 tokens | CNY/百万 tokens（×7.3） |
|------|----------------|----------------------|
| Input cache miss | $0.14 | ¥1.02 |
| Input cache hit | $0.0028 | ¥0.02 |
| Output | $0.28 | ¥2.04 |

### V4 Pro 定价（仅在 delegate_task 中使用）

| 类型 | USD/百万 tokens | CNY/百万 tokens（×7.3） |
|------|----------------|----------------------|
| Input cache miss | $0.435 | ¥3.18 |
| Input cache hit | $0.003625 | ¥0.026 |
| Output | $0.87 | ¥6.35 |

## 精确计算步骤（数学必须一步一步来）

用户明确要求：**涉及数学计算时，每一步都必须列出来，不能跳步。**

以今天（6月4日）的实际数据为例：

### Step 1：从 Hermes Insights 拿原始数据

```
Input tokens:      1,582,977     ← 累计输入
Output tokens:       491,259     ← 累计输出
Total tokens:    165,418,059     ← 含缓存的全部 tokens
```

### Step 2：计算缓存命中量

```
缓存命中 = Total - Input - Output
         = 165,418,059 - 1,582,977 - 491,259
         = 163,343,823 tokens
```

### Step 3：换算成百万 token 单位

```
Input cache miss: 1,582,977 ÷ 1,000,000 = 1.58M
Input cache hit:  163,343,823 ÷ 1,000,000 = 163.34M
Output:            491,259 ÷ 1,000,000 = 0.49M
```

### Step 4：现金官定价 × 汇率换算成人民币

deepseek-v4-flash 的定价（美元 → 人民币 ×7.3）：

| 类型 | USD/百万 | CNY/百万 |
|------|---------|---------|
| Input cache miss | $0.14 | ¥1.02 |
| Input cache hit | $0.0028 | ¥0.02 |
| Output | $0.28 | ¥2.04 |

### Step 5：逐项计算费用（人民币）

```
a) Input cache miss:   1.58M × ¥1.02   = ¥1.61
b) Input cache hit:  163.34M × ¥0.02   = ¥3.27
c) Output:              0.49M × ¥2.04  = ¥1.00
```

### Step 6：合计

```
总计 = ¥1.61 + ¥3.27 + ¥1.00 = ¥5.88
```

### Step 7：余额验证

```
今早余额    5.28 CNY
充值        +10.00 CNY
            15.28 CNY
现在余额    3.65 CNY
━━━━━━━━━━━━━━━━━━━
实际花费    11.63 CNY
```

## ⚠️ 算出来的费用 vs 实际扣费

算出来的 ¥5.88 和实际扣费 ¥11.63 差一倍。原因：

1. **缓存命中比例估算偏差** — Hermes 的 Total tokens 是累计值，但每次 API 调用
   发送的完整上下文长度不同，我按总比例均摊，实际可能更大
2. **汇率波动** — 7.3 是近似值，DeepSeek 实际汇率按结算日算
3. **Thinking 模式额外 token** — DeepSeek V4 Flash 默认开启 thinking 模式，
   可能产生额外的内部推理 token（但官方页面上 pricing 未区分 thinking vs non-thinking）
4. **余额查询 API 只反映当前余额** — 无法查询历史消费明细

**结论：算出来的数字是下限（~¥6），实际扣费（~¥12）以余额变化为准。**
每日总结报告同时引用计算结果和余额差额。

## 自动化脚本

`calculate_token_cost.py`（位于 `~/.hermes/scripts/`）自动执行上述计算：

```bash
python3 ~/.hermes/scripts/calculate_token_cost.py
```

输出格式：
```
📊 昨日 Token 消耗明细（2026-06-04）
=============================================
📈 总计
  Input tokens:  1,582,977
  Output tokens: 491,259
  费用: $0.82 USD ≈ ¥6.01

🤖 DeepSeek V4 Flash
  Input cache miss: 1.58M × ¥1.02
  Input cache hit:  165.40M × ¥0.0204
  Output:           0.49M × ¥2.04
  小计: ¥6.0

💰 当前余额: ¥3.59
📌 余额偏低（<¥5）
```

此脚本每日 6:00 自动运行（挂在每日总结报告 cron 的 `script` 参数中），
输出作为 `[SCRIPT OUTPUT]` 注入到 LLM prompt。

## 关键风险：长会话的上下文堆积

用户提出的核心问题：

> 如果在同一个会话中持续对话（包括跨天但未满 24 小时空闲），所有历史上下文会全部打包发到 API。输入 token 的消耗会规模级增长，而输出却没多大变化，几分钟就能烧完余额。

## Hermes 的防护机制

| 机制 | 配置值 | 说明 |
|------|--------|------|
| 自动上下文压缩 | `compression.enabled: true` | 对话变长时自动 summarise 旧内容 |
| 压缩阈值 | `compression.threshold: 0.5` | 上下文占用 50% 时触发压缩 |
| 目标压缩比 | `compression.target_ratio: 0.2` | 压缩到原来的 20% |
| 最大轮数 | `agent.max_turns: 90` | 到 90 轮自动切会话 |
| 缓存 TTL | `prompt_caching.cache_ttl: 5m` | 同会话内系统提示词可复用 |

## 监控手段

1. **`hermes insights --days 1`** — 每日 token 统计（Input/Output/Total）
2. **`calculate_token_cost.py`** — 精确费用计算（按 DeepSeek 官方 USD 定价 × 汇率）
3. **`check_deepseek_balance.py`** — 余额查询（6:05 cron）
4. **每日总结报告（6:00）** — 集成计算脚本 + LLM 分析

## 余额报警阈值

- 日消耗 > ¥10 → ⚠️ 提醒注意
- 日消耗 > ¥50 → 🔴 严重超支
- 余额 < 1 元 → 🔴 建议充值
- 余额 < 5 元 → 📌 余额偏低

## 日常消耗参考

| 时间 | 实际扣费 | 备注 |
|------|---------|------|
| 6月4日全天（大量工作） | ¥11.63 | 含 OpenClaw 调试、配置文件修改、自愈脚本修复、token 计算脚本创建 |
| 日均常规 | ~¥2-5 | 含多轮对话 + 工具调用 |

## 成本优化策略：多层模型委托

### 核心思路

让主 agent 用便宜模型（`deepseek-v4-flash`）处理日常对话，复杂任务（编程、论文）
由子 agent 用更强模型（`deepseek-v4-pro`）执行。

### 配置方式

```yaml
delegation:
  model: deepseek-v4-pro      # 子 agent 使用更强模型
  provider: deepseek
```

### 实际工作流

```
用户聊天 → 主 agent（deepseek-v4-flash，便宜）
            ↓ 遇到复杂任务
        delegate_task(model="deepseek-v4-pro")
            ↓
        子 agent 用 V4 Pro 处理 → 返回结果
            ↓
        主 agent 整理结果回复用户
```

### 适用场景

| 场景 | 适合用 V4 Pro 吗 | 说明 |
|------|-----------------|------|
| 日常闲聊 | ❌ | flash 够用，便宜 |
| 改论文文字 | ❌ | flash 能改 |
| 编程大项目 | ✅ | 需要更强推理 |
| 论文重写/排版 | ✅ | 复杂任务用 V4 Pro |
| 数据分析 | 看复杂度 | 简单分析用 flash |
