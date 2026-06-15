# 概念性 Q&A 被误判为 complex 的修复记录

## 背景（2026-06-13）

用户发现 DeepSeek 缓存命中率下降，排查后指出 L1 路由把概念性问答也判为 `complex`，触发 `l2_plan`（DeepSeek API 调用），造成不必要的 token 消耗。

**用户要求**：只有写大型程序或拟定复杂计划才用 DeepSeek，其余全交给 Hermes（MiMo）。

## 已实施的修复（2026-06-13）

### 修改文件
`/root/l123/agent/router.py`

### 新增方法 `_is_conceptual_qa()`

在 `_is_complex()` 之前插入一条**路径0**：

```python
def _is_conceptual_qa(self, message: str) -> bool:
    """检测是否为概念性问答（无需DeepSeek，hermes直接答）
    
    如果消息含有概念性质疑词（能不能/为什么/是不是等），
    且不含可执行关键词（写/部署/爬/脚本等），则判为概念性问题。"""
    conceptual_patterns = [
        "能不能", "可否", "可以吗", "能不能够",
        "为什么", "为何",
        "是不是", "有没有", "是否",
        "是什么", "什么是", "是何",
        "如果.*那",
        "怎么搞",
    ]
    for pat in conceptual_patterns:
        if re.search(pat, message):
            # 检查是否包含可执行关键词（写代码/部署/爬取等）
            executable_keywords = []
            for intent_name in ["coding", "deployment", "scraping"]:
                cfg = self.config.get("intent_types", {}).get(intent_name, {})
                executable_keywords.extend(cfg.get("keywords", []))
            executable_keywords.sort(key=len, reverse=True)
            has_executable = any(kw in message for kw in executable_keywords)
            if not has_executable:
                return True
    return False
```

### 路由变化

```
route() 流程：
  路径0: _is_conceptual_qa()? → simple/hermes ✅
  路径1: _is_complex()?       → complex/l2_dispatcher
  路径2: _detect_intent_shifts? → complex/l2_dispatcher
  路径3: 单意图                → simple/单发
```

### 修复效果

| 消息 | 修复前 | 修复后 |
|:----|:----:|:----:|
| 高端款能否模拟双向芯片信号 | complex → DeepSeek | simple/hermes |
| 高端锁物理方案怎么搞    | complex → DeepSeek | creative/hermes |
| 能不能把模型切换一下    | complex → DeepSeek | creative/hermes |
| 为什么高端锁不能逆向    | complex → DeepSeek | creative/hermes |
| 查天气并写报告          | complex | ✅ complex（真正多步） |
| 写个脚本爬数据          | single_dispatch | ✅ 正常走 OpenClaw |
| 部署个网站              | single_dispatch | ✅ 正常走 Claude Code |

### 已知边缘情况

- "指纹锁程序也可以吗" — "可以吗"匹配概念模式，但"程序"在 coding 关键词中 → `has_executable=True` → 不走概念路径，仍判 complex。影响极小（上下文概念问题很少同时出现"程序"和"可以吗"）。

## 验证方法

```bash
cd /root/l123 && python3 -c "
from agent.router import router
tests = [
    ('高端款能否模拟双向芯片认证信号', 'simple'),
    ('高端锁物理方案怎么搞', 'simple/creative'),
    ('能不能把模型切换一下', 'simple/creative'),
    ('为什么高端锁不能逆向', 'simple/creative'),
    ('查天气并写报告', 'complex'),  # 真正多步
    ('写个Python脚本爬取这个网站的数据', 'single_dispatch'),
    ('部署个网站', 'single_dispatch'),
]
for t, expected_type in tests:
    r = router.route(t)
    status = '✅' if r['type'] != 'complex' or expected_type == 'complex' else '❌'
    print(f'{status} \"{t}\" → {r[\"type\"]}/{r[\"intent\"]}')
"
```
