---
name: Token Budget Guard
slug: token-budget-guard
version: 1.0.0
description: "Before every action, estimate token consumption and check against budget. Stop if near limit."
metadata:
  priority: max
  enabled: true
---

## Token Budget Guard（最高优先级）

每次行动前估算 token 消耗并检查预算上限。

## 规则

1. **估算**：根据上下文长度、模型、操作复杂度估算本轮 token
2. **检查**：用轻量方式获取当前消耗（缓存优先，不调完整 status）
3. **判断**：
   - 当前 + 估算 ≥ 500K → 立即终止，报告当前已完成的进度
   - 在预算内 → 输出简报继续

## 简报格式
```
[TokenGuard] 当前: XXX / 500K | 本轮: ~XK | 余量: XXX | ✅
```

## 例外
- 仅 `NO_REPLY` 可跳过
- 其他所有回复均需执行
