# auxiliary_client.py 代码补丁：_resolve_task_provider_model 支持 api_key_env

## 问题

`_resolve_task_provider_model()`（`agent/auxiliary_client.py:4698`）只读取任务的 `api_key` 字段，不读取 `api_key_env`：

```python
# 只读 api_key，不读 api_key_env
cfg_api_key = str(task_config.get("api_key", "")).strip() or None
```

这意味着 `auxiliary.vision` 配置中 `api_key_env: XIAOMI_API_KEY` 永远不会被解析——函数返回的 api_key 始终为 None。

## 补丁内容

在 `auxiliary_client.py:4698-4699` 之间插入：

```python
cfg_api_key = str(task_config.get("api_key", "")).strip() or None
# ↓ 新增：fallback 到 api_key_env
if not cfg_api_key:
    cfg_api_key_env = str(task_config.get("api_key_env", "")).strip() or None
    if cfg_api_key_env:
        cfg_api_key = os.getenv(cfg_api_key_env, "").strip() or None
cfg_api_mode = str(task_config.get("api_mode", "")).strip() or None
```

## 生效范围

| 调用方 | 路径 | 是否受影响 |
|--------|------|-----------|
| `vision_analyze` 工具（agent 会话） | `vision_tools.py:978` → `async_call_llm` | ✅ 走这个函数 |
| `_enrich_message_with_vision`（网关） | `gateway/run.py:11618` → `vision_analyze_tool` | ✅ 同上 |
| `call_llm`（同步路径） | `auxiliary_client.py:4022` | ✅ 同上 |

## 注意事项

**即使打了这个补丁，agent 进程仍可能返回 401** —— 因为 `os.getenv("XIAOMI_API_KEY")` 在 agent 会话中返回 None（agent 不加载 .env）。

**完整修复方案：同时设 `api_key` 和 `api_key_env`**

```bash
# api_key_env 给网关进程（启动时加载 .env）
hermes config set auxiliary.vision.api_key_env XIAOMI_API_KEY
# api_key 给 agent 进程（直接从 config 读取）
hermes config set auxiliary.vision.api_key "sk-真实key值"
```

补丁是一个保障——当 `api_key` 被清空时，网关进程还能从 env 拿到 key。

## 补丁持久性

Hermes 更新（`git pull`）可能覆盖此补丁，因为 `auxiliary_client.py` 是源码文件。更新后需重新检查补丁是否还在：

```bash
grep -n "api_key_env" /root/.hermes/hermes-agent/agent/auxiliary_client.py
# 如果找不到补丁那两行 → 重新打
```

补丁代码（可脚本化）：
```bash
cd /root/.hermes/hermes-agent
# 检查补丁是否已在
grep -q "if not cfg_api_key:" agent/auxiliary_client.py && echo "补丁已存在" || echo "补丁丢失，需重新应用"
```