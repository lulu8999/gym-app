# CLI 会话 `pre_llm_call` 钩子未触发诊断

## 发现时间
2026-06-13 20:00

## 触发场景
用户在 CLI 终端（VPS 直连）中连续发问，内容涉及工作流程差异：
1. "不要原盘文件"
2. "为什么感觉你跟微信的hermes的工作流程不一样"
3. "你现在这个终端上也有意图路由吗"
4. "那不是还有l123插件吗"

## 诊断证据

```bash
# 路由日志最后一条
tail -1 /root/.hermes/plugins/l123/recent_routes.log
# → [2026-06-13T19:52:11] complex/complex: [L1:complex|4步|你连到win上去...]

# 当前时间
date "+%H:%M"
# → 20:00

# 插件配置存在
grep "l123" /root/.hermes/config.yaml
# → plugins.enabled: [..., "l123"]
```

**结论**：19:52 之后的 8 分钟、4 条消息无任何 L1 路由记录。

## 可能根源

| 可能性 | 概率 | 依据 |
|--------|:----:|------|
| CLI 会话启动 < 插件加载 | 高 | 会话在 19:51 U盘任务开始，插件钩子可能错过已运行会话 |
| Hermes CLI 不走 `pre_llm_call` | 中 | Hermes 插件框架的钩子机制可能只对 Gateway 线程生效，CLI 模式 Agent 直连 LLM 不触发钩子 |
| 插件热加载未绑定 | 低 | 检查 `gateway.log` 无 L123 错误日志 |

## 验证步骤

1. 新建 CLI 会话（`/new` 或新窗口），发测试消息，检查 `recent_routes.log` 是否有新增
2. 重启网关后重复步骤 1
3. 如仍无记录 → 确认 Hermes CLI Agent 类是否注册了 `pre_llm_call` 钩子

## 修复方向

如果 Hermes CLI 确实不支持 `pre_llm_call` 钩子：
- 在 Agent 消息处理入口处直接注入 L1 路由逻辑（不走插件钩子链）
- 或在 CLI 模式的 `run_agent.py` 中硬编码调用 L1 router