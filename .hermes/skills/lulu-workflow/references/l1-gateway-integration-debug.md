# L1 网关集成调试全记录 (2026-06-12)

## 时间线

| 时间 | 事件 | 问题 |
|------|------|------|
| 19:13 | 第一次改 gateway/run.py，加 L1 注入 | Import 路径错误：`hermes_agent.agent.router` |
| 19:15 | 网关首次崩溃 | `ModuleNotFoundError: No module named 'hermes_agent'` |
| 19:16 | 修复 import → `from agent.router import router` | 编译通过 |
| 19:16 | systemd 重启网关 | L1 日志不出现（debug 级别太低） |
| 19:18 | 发现两个网关同时运行 | PM2 resurrect + systemd 冲突 |
| 19:23-19:26 | 查日志分析 L1 不出现原因 | `logger.debug` 被过滤 |
| 19:26 | 改为 `logger.warning` | 网关拉起来了 |
| 19:27 | systemd journal 显示 | `[L1] FAILED: 'MessageEvent' object has no attribute 'metadata'` |
| 19:30 | 修复 `event.metadata['l1_route']` → `event.l1_route` | |
| 19:30 | systemctl restart → 网关挂了 | user D-Bus 崩溃 |
| 19:37 | 用户手动拉起 gateway | L1 日志出现：`simple → hermes` ✅ |
| 19:46 | 切 PM2 独管网关 | systemd 已 disable |
| 19:53-20:06 | L1 日志验证 | 多个消息正确分类 |
| 20:06 | 用户发现误分类：`为什么` 句被判 `deployment` | 查路由逻辑 |
| 20:09+ | 优化 L1 逻辑 | 发现是 pycache 过期 |

## 4个根因总结

| # | 问题 | 表现 | 修复 |
|---|------|------|------|
| 1 | Import 路径错误 | `ModuleNotFoundError: hermes_agent` | `from agent.router import router` |
| 2 | `event.metadata` 不存在 | `AttributeError` 被 try/except 吞掉 | `event.l1_route = value` |
| 3 | systemd + PM2 双管家 | 无限重启循环（77次） | disable systemd，只用 PM2 |
| 4 | pycache 过期 | 源码改了但网关跑旧版本 | 清 `__pycache__` 后重启 |

## 关键诊断命令

```bash
# 查看谁在管网关
pm2 list | grep hermes-gateway
systemctl --user status hermes-gateway
ps aux | grep "[h]ermes gateway"

# 看 L1 日志
grep "L1 route" /root/.hermes/logs/gateway.log | tail -20

# 本地测试路由
cd /root/.hermes/hermes-agent && python3 -c "
from agent.router import route_message
r = route_message('测试消息')
print(r['intent'], '→', r['handler'])
"

# 修复 pycache
find /root/.hermes/hermes-agent -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
```

## MessageEvent 结构

`MessageEvent` 是 `@dataclass`，定义在 `gateway/platforms/base.py:1412`：
```python
class MessageEvent:
    text: str
    message_type: MessageType = MessageType.TEXT
    source: SessionSource = None
    raw_message: Any = None
    message_id: Optional[str] = None
    platform_update_id: Optional[int] = None
    media_urls: List[str] = field(default_factory=list)
    media_types: List[str] = field(default_factory=list)
    reply_to_message_id: Optional[str] = None
    reply_to_text: Optional[str] = None
    auto_skill: Optional[str | list[str]] = None
    channel_prompt: Optional[str] = None
    channel_context: Optional[str] = None
    internal: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
```

**没有 `metadata` 字段**。需要扩展时用动态属性 `event.xxx = value`。
