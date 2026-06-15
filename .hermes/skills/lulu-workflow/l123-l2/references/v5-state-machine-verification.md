# L2 v5.0 状态机端到端验证记录

## 2026-06-12 新闻爬虫任务（3 步骤，严格逐步执行）

### L1 路由
```
gateway.log: L1 route: coding → claude_code | is_complex=1
```

### L2 DeepSeek 拆分
```
gateway.log: L2 plan: 3 steps | handler=claude_code
gateway.log: L2 plan injected: 3 steps appended to message
```

### 执行计划
```
Step 1: [claude_code] 移除健身网页和DNS配置
Step 2: [openclaw] 编写爬虫脚本爬取今日头条热门新闻
Step 3: [claude_code] 将新闻汇总生成图片
```

### 执行过程
| 步骤 | 状态 | 工具调用 | 耗时 |
|:---|:---:|:---|:---:|
| Step 1 | ✅ | terminal (systemctl stop/disable, rm -rf, cron remove) | ~2min |
| Step 2 | ✅ | delegate_task (openclaw) | ~3min |
| Step 3 | ✅ | delegate_task (claude_code) | ~2min |

### 铁律指令（注入到 agent context）
```
[L2 执行框架 — 🔴铁律，违反则任务失败]
强制规则：
  1. 每轮只执行一个步骤，禁止同时执行多个
  2. 当前步骤完成并验证后，才能进入下一步
  3. 禁止跳过、合并、重排步骤
  4. 每步执行完输出「[L2] Step N 完成 — 简述结果」
  5. 全部完成后调用 orchestrator.summarize() 生成汇总
```

### 关键：与旧版 v4.0 的区别
| | v4.0（健身网页） | v5.0（新闻爬虫） |
|:---|:---|:---|
| 注入文本 | "请严格按此计划逐步执行" | "🔴铁律，违反则任务失败" |
| Step 3+4+5 | 合并为一次 delegate_task | 不允许合并 |
| 步骤验证 | 无状态机约束 | next_step() → 执行 → mark_done() |
| 汇总 | 手动汇总 | orchestrator.summarize() |

### 图片生成三次迭代（体现了经验教训价值）
| # | 问题 | 修复 | 耗时 |
|:---|:---|:---|:---:|
| ① | 中文全方块 | 加载 Noto Sans CJK SC | +2min |
| ② | emoji 变方块 | _safe_text() 过滤 | +2min |
| ③ | 符号遗漏 | 完整 Unicode 范围正则 | +2min |

### 经验教训
- 状态机指令必须用"铁律"而非"请"，否则 agent 会随意跳步
- 图片生成必须在第一步就探测中文字体，不能依赖默认
- 每次任务完成后必须输出经验教训总结（已写入 lulu-workflow §十）
