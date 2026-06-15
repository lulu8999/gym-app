# WeChat 图片识别调试记录（2026-06-09）

## 症状
微信发图后 agent 无响应/超时，最终回复"看不到图"

## 调试过程

### Step 1: 检查 Weixin 是否收到图
```
# gateway.log
[Weixin] inbound from=xxx type=dm media=1  ← media=1 表示收到图片 ✅
```

### Step 2: 确认 downstream routing
```
# gateway.log — 路由判定
Image routing: text (mode=text). Pre-analyzing 1 image(s) via vision_analyze.
```
- `text` 模式：走 `vision_analyze` 预分析，非模型原生看图
- 触发条件：`auxiliary.vision.provider` 非空时 `_explicit_aux_vision_override` 返回 True

### Step 3: vision_analyze 超时
```
# agent.log — 约 6 分钟后
Auxiliary vision (async): transient transport error; retrying once on the same provider before fallback: Request timed out.
```
- 超时原因：`auxiliary.vision.base_url` 和 `api_key_env` 为空

### Step 4: 修复配置后仍 401
```
Fix applied → aux.vision.base_url + api_key_env set → restart → vision_analyze still 401
```
- 根因：`agent/auxiliary_client.py` 的 `_resolve_task_provider_model()` 只读 `api_key` 字段，不读 `api_key_env`
- `.env` 未在当前 agent 进程加载，`os.getenv("XIAOMI_API_KEY")` 返回 None

### Step 5: 最终修复
1. 同时设置 `auxiliary.vision.api_key` + `auxiliary.vision.api_key_env`
2. 热补丁代码（见 trap #18）支持 `api_key_env` 解析

## 关键结论
- 微信能收图（`media=1`），不是通道级别问题
- 超时 ≠ key 损坏
- agent 进程不读取 `.env`，必须 `api_key` 直写
- 网关进程读取 `.env`，可正常用 `api_key_env`