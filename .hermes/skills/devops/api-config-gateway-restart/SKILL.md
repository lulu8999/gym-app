---
name: api-config-gateway-restart
description: 安全配置新API/切换模型 + 正常重启网关的标准流程，杜绝强杀进程和擅自操作
---

# API 配置 + 网关重启标准流程

## 适用场景
- 添加新的 API Key
- 切换模型 provider
- 修改 API 配置（base_url, model 等）
- 需要重启 Hermes Gateway

## API 配置铁律

**加 API Key 必须遵循完整流程：**

1. **先搜 config.yaml 全文件确认无残留旧 key/重复配置**（`model:` 段 + `providers:` 段可能有同名配置，`auxiliary:` 段也可能有冗余 key 引用）
2. **列完整参数**（provider/model/api_key/base_url）→ 给 Lulu 确认
3. **拿到肯定答复后** → 直接写入 config.yaml，**禁止用 api_key_env 间接引用**
4. **写入后 grep 确认仅一处配置 + 无残留旧 key**
5. **curl 测试 API 通不通**
6. **都通过后再问 Lulu 是否重启网关**

**禁止直接改 .env 绕过确认流程。**
> 所有步骤都必须先列清参数 → 发 Lulu 确认 → 得到肯定答复 → 再动手。

## Provider 类型选择（2026-06-13 修正）

**所有 OpenAI 兼容 API 统一用 `provider: openai`。**

| API 类型 | provider 值 | 示例 |
|----------|------------|------|
| 所有 OpenAI 兼容 API | `openai` | MiMo、千帆、DeepSeek、中转站等 |

> ⚠️ `provider: custom` 已废弃 — Gateway 不认识此值，会静默忽略（`unknown config keys ignored: provider`），导致 provider 配置完全失效。
>
> ⚠️ 2026-06-13 实测：千帆和 DeepSeek 从 `provider: custom` 改为 `provider: openai` 后，API 200 通过，Gateway 无警告。

---

## Step 1: 搜全文件 + 列完整参数给 Lulu 确认（**必须先搜+列，不能擅自改**）

### 1a. 全文件搜索防残留

```bash
# 同时搜 providers 段和 model 段，排查同名配置
grep -n "要配的模型名" ~/.hermes/config.yaml
# 如果有多个匹配 → 必须先清理旧配置再配新的
```

### 1b. 检查 auxiliary 段

```bash
grep -n "要配的模型名前缀\|要用的base_url" ~/.hermes/config.yaml
# auxiliary.vision 等段可能有冗余的 api_key_env 或旧 key，一并清理
```

### 1c. 列完整参数给 Lulu 确认

把所有参数一次性列全，格式示例：

```yaml
新增/修改 [provider名]（如 xiaomi-mimo）：

- **provider**: openai  # ⚠️ 必须 openai，不是 custom！
- **default_model**: xxx
- **api_key**: sk-xxx（直接写完整值，不要用 env 间接引用）
- **base_url**: https://xxx.com/v1
- **models**: '["model1","model2"]'

**常见陷阱：**
- ⚠️ 千帆 coding 计划的模型名固定为 `qianfan-code-latest`（服务端智能路由），`model.default` 必须写这个，不要写具体模型名如 `glm-5.1`
- ⚠️ 千帆 coding 计划的 endpoint 是 `/v2/coding` 而非标准 `/v2/chat/completions`
- ⚠️ `provider: custom` 已被 Gateway 弃用 — 所有 OpenAI 兼容 API 统一用 `provider: openai`
- ⚠️ `api_key_env` 不可靠 — 必须直接写 `api_key: 完整key`
- ⚠️ **Key 截断陷阱**：终端显示的 key 可能被截断为 `sk-xxx...yyy`（字面 `...`），写入后就废了。必须从 `.env` 或用 Python 逐字符提取完整 key
- ⚠️ **`auxiliary.vision` 等辅助段**也可能有冗余的 key 引用（如多余的 `api_key_env`），改 provider 配置时必须一并检查清理

等待 Lulu 回复说"搞/行/可以" → 再进 Step 1.5。

---

## Step 1.5: 执行前教训验证（Lulu 明确要求）

**Lulu 明确要求**：改配置前必须先回顾所有已知教训，验证当前配置是否已修复所有踩过的坑，确认没问题才能动手。

### 1.5a. 从历史记录提取教训清单

通过 session_search 搜索历史会话获取教训。

### 1.5b. 验证清单（逐个检查）

用以下模板逐项验证：

```
========== 预执行验证报告 ==========
[✅/❌] 教训①: api_key_env 已清除（不应出现在当前配置中）
[✅/❌] 教训②: key_env 已清除（不应存在）
[✅/❌] 教训③: auxiliary 段冗余 api_key_env 已清理
[✅/❌] 教训④: api_key 直接写入（不是 env 间接引用）
[✅/❌] 教训⑤: 全文件唯一性（grep 确认无重复配置）
[✅/❌] 教训⑥: .env 未误删（不影响其他功能）
========================================
状态总结：X/Y 通过，Z 未通过
```

实际检查命令：

```bash
grep -n "api_key_env\|key_env" ~/.hermes/config.yaml    # 查间接引用
grep -c "实际Key前10字符" ~/.hermes/config.yaml          # 查唯一性
grep "XIAOMI_API_KEY" ~/.hermes/.env                     # 查 .env 完好
```

### 1.5c. 汇报并等待确认

把验证报告发给 Lulu，等他说"进入/继续/搞" → 再进 Step 2。

---

## Step 2: 修改配置

确认后：

1. **API Key 直接写入 config.yaml 的 providers 段**，不要用 api_key_env 间接引用
   ```yaml
   # providers 段直接写 key
   xiaomi-mimo:
     api_key: sk-实际Key
     provider: openai    # OpenAI 兼容用 openai
     base_url: https://api.xiaomimimo.com/v1
     default_model: mimo-v2.5-pro
     models: '["mimo-v2-flash","mimo-v2-pro","mimo-v2.5","mimo-v2.5-pro"]'
   ```
2. **删除 providers 段中残留的 `api_key_env` 和 `key_env` 字段**（如果存在）
3. **清理 auxiliary 段中冗余的 `api_key_env`**（如 `auxiliary.vision` 中既有直接 `api_key` 又有 `api_key_env`，删后者）
4. **验证 YAML 格式正确：**
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('/root/.hermes/config.yaml')); print('YAML OK')"
   ```
5. **验证 Key 已写入磁盘且仅一处：**
   ```bash
   grep -c "Key前20字符" ~/.hermes/config.yaml
   # 应返回期望的引用次数（非冗余配置时通常为 1 或 2）
   ```
6. **检查未知 key 警告：** 重启后查日志确认无 `unknown config keys ignored` 警告
   ```bash
   journalctl --user-unit=hermes-gateway --since "1 min ago" --no-pager | grep "unknown config"
   # 应无输出
   ```

> ⚠️ **铁律：禁用 api_key_env 间接引用，Key 必须直接写在 config.yaml 里。**
> ⚠️ **检查 auxiliary.vision 等辅助段是否有冗余 key_env，一并清理。**

---

## Step 3: 重启网关（**必须先问 Lulu 是否同意**）

**重启前必须问 Lulu**，说清楚"网关重启后大概断连几秒微信"。Lulu同意后才执行。

### ❌ 绝对禁止的做法
- 直接 `kill -9` 网关进程 — 硬断微信
- `kill -15` 也不可以用 — 用户明确说过不要杀进程
- 任何 `kill` 命令都不行
- **同时用 systemd 和 PM2 管网关** — 两个 init 系统抢同一端口，会造成无限重启循环（2026-06-12：PM2 崩溃 77 次，systemd 也在反复拉起）

### ✅ 正确的重启方式

**首选：PM2（Lulu 偏好，已在管其他 7 个服务）**

用 `pm2 resurrect` 恢复所有进程（网关包含在内）。但重启前必须：
1. ✅ 先停 systemd 侧网关：`systemctl --user stop hermes-gateway`
2. ✅ 然后 `systemctl --user disable hermes-gateway` 防止自动复活
3. ✅ 最后 `pm2 resurrect` 一把拉起

**方式 A：PM2 管理（推荐）**
```bash
# 确保只有一个管家
systemctl --user stop hermes-gateway
systemctl --user disable hermes-gateway
pm2 resurrect   # 从 dump.pm2 恢复进程
```

**方式 B：纯 systemd（仅在 user D-Bus 正常时可用）**
```bash
systemctl --user stop hermes-gateway
sleep 5
systemctl --user start hermes-gateway
```
⚠️ 注意：如果 user D-Bus 崩了（`Failed to connect to bus`），此方式不可用。

**方式 C：直接脚本启动（最后手段）**
```bash
bash /root/run-hermes-gateway.sh
```

### 🔴 从网关内部会话无法重启（2026-06-15 确认）

`hermes gateway restart` 如果从**网关进程内的会话**执行（如微信/企微对话中发的命令），会返回：

```
✗ Refusing to restart the gateway from inside the gateway process.
This command was blocked to prevent restart loops.
Use `hermes gateway restart` from a shell outside the running gateway.
```

**这是安全机制，不是 bug。**

**解决办法**：告知用户网关已改好配置，用户需要：
1. **启动新会话**（旧的用 `/new` 或等它自然结束）
2. 或从外部终端执行 `hermes gateway restart`

改完 `model.default` 后新配置不会立即在当前会话生效，需要等网关重启后新会话才用新模型。

### 快速切模型（不改 provider 和 Key 的简单场景）

用 `hermes config set` 一行搞定：

```bash
hermes config set model.default mimo-v2.5-pro-ultraspeed
```

比手动编辑 YAML 安全——Hermes CLI 自己写文件，不会格式出错。适用于：
- 同一 provider 内切换模型（如 `mimo-v2.5-pro` → `mimo-v2.5-pro-ultraspeed`）
- 不需改 API Key / base_url 的简单场景

### 🔴 双网关冲突陷阱（2026-06-12 血泪教训）

**症状**：
- PM2 显示网关反复崩溃（restart count 飙到 77+）
- 每个进程存活不到 1 秒
- 错误日志只有废弃警告，没有 Python 异常

**根因**：systemd 和 PM2 同时试图管理同一个网关。systemd 停了进程，PM2 立刻拉新进程，systemd 的 `Restart=always` 又拉另一个，两个抢端口互相杀。

**诊断命令**：
```bash
# 查看谁在管网关
pm2 list | grep hermes-gateway
systemctl --user status hermes-gateway
ps aux | grep "[h]ermes gateway"
# 出现两个进程 PID → 双网关冲突
```

**解决**：选一个管家（推荐 PM2），彻底禁用另一个：
```bash
systemctl --user stop hermes-gateway
systemctl --user disable hermes-gateway
# 然后只用 PM2
pm2 resurrect
```

### API 清理与恢复流程

**删除 API 时**：
1. 明确询问删除范围：
   - 仅删除 config.yaml 中的 providers 配置
   - 仅删除 .env 中的 API Key
   - 两者都删除
2. 确认是否影响其他功能（delegation、tts、stt 等）
3. 记录删除的内容，便于后续恢复

**恢复 API 时**：
1. 先检查 config.yaml 中是否还有相关配置引用
2. 按标准流程添加 API Key 到 .env
3. 按标准流程配置 providers/model 段
4. 重启网关前必须问 Lulu

---

## Step 4: 验证新模型生效

1. 发一条消息检查是否用新模型正常响应
2. **检查未知 key 警告**：
   ```bash
   journalctl --user-unit=hermes-gateway --since "1 min ago" --no-pager | grep "unknown config"
   # 应无输出 — 如果有，说明 config.yaml 有不被识别的 key（如 providers 段的 provider: custom）
   ```
3. 如果报 401：
   - 检查日志是否有 `unknown config keys ignored: provider`
   - 检查 config.yaml 的 providers 段是否有 `provider: custom`（需要删除）
   - curl 直测排除 Hermes 配置问题

---

## 🔴 pycache 陷阱：源码改了但网关没生效

**症状**：修改了 `gateway/run.py` 或 `agent/router.py` 源码，用 `python3 -m py_compile` 验证通过，重启网关后代码却跑旧版本。

**根因**：Python `.pyc` 缓存文件比源码旧或编译时间戳混乱，导致 import 时加载了缓存的旧字节码。

**诊断**：
```bash
# 对比源文件和缓存文件修改时间
stat gateway/run.py agent/__pycache__/router.cpython-311.pyc
# .pyc 比 .py 旧 → 缓存过期
```

**正确做法**：改网关源码后**必须清 pycache 再重启**：
```bash
find /root/.hermes/hermes-agent -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
# 然后再重启网关
pm2 resurrect
```

**2026-06-12 教训**：L1 路由代码逻辑正确（本地 `python3 -c` 测试通过），但网关日志显示错误分类。清 pycache 后重启，立即正确。**从此改网关源码 → 清 pycache → 重启 三步缺一不可。**

---

## 🔴 网关源码修改安全流程（修改 gateway/run.py 专用）

---

## 🔑 Claude Code / LiteLLM 专用 Key 更新流程

**场景**：更新 DeepSeek API Key（或 Claude Code 后端用到的任何 Key）。LiteLLM 代理运行在 PM2，Claude Code 通过 `localhost:41111` 连接。

### 🔴 三重陷阱（2026-06-12 血泪教训）

**陷阱 1：两个地方都要改**
- `/root/.claude-code-litellm/.env` — LiteLLM 读 `DEEPSEEK_API_KEY`
- `/root/.claude/settings.json` — Claude Code 自己的 `apiKey` 字段，会被传给 LiteLLM
- 只改其中一个 → 另一个还是旧 Key → 401

**陷阱 2：工具输出掩码损坏 .env**
- `sed` / `echo` 等命令的输出被 Hermes 工具掩码（`***`）替换
- 导致 .env 内容变成字面 `DEEPSEEK_API_KEY=***` — 真正的 Key 丢失
- ✅ 正确做法：用 Python 代码直接写文件，不要经过 shell 命令

**陷阱 3：PM2 需要 `--update-env`**
- `pm2 restart litellm-proxy` — 不刷新环境变量，旧 Key 残留
- ✅ `pm2 restart litellm-proxy --update-env`
- ⚠️ 更稳妥：先 `export DEEPSEEK_API_KEY=...` 在当前 shell，再 `pm2 restart --update-env`

### ✅ 正确流程

```python
# Step 1: 用 Python 写入 .env（避免工具掩码）
from hermes_tools import terminal
key = "sk-实际的Key"
with open('/root/.claude-code-litellm/.env', 'w') as f:
    f.write(f'DEEPSEEK_API_KEY={key}\n')

# Step 2: 更新 settings.json
import json
c = json.load(open('/root/.claude/settings.json'))
c['apiKey'] = key
json.dump(c, open('/root/.claude/settings.json', 'w'), indent=4)

# Step 3: 重启 LiteLLM（强制刷新环境变量）
# 注意：需要在 shell 里先 export Key 再 pm2 restart --update-env
# 或者用 start.sh 的 source 机制
```

### 验证

```bash
# 健康检查
curl -s http://localhost:41111/health | python3 -m json.tool | grep healthy
# 应全部 healthy，unhealthy_count=0
```

---

## 参考关联

- `custom-provider-setup` — 各类 provider 的详细配置陷阱
- `gateway-administration` — 网关管理的完整文档（包括"NEVER kill"原则）
- `service-watchdog-management` — 看门狗管理

## 参考资料

- 📕 `references/platform-model-resolution.md` — 各平台（weixin/telegram等）的模型解析规则：网关平台使用 config.yaml 默认模型，CLI `--global` 覆盖不影响平台会话。排查"平台不回复"的必备背景知识。
- 📕 `references/mimo-provider.md` — MiMo（小米）Provider 配置参数、可用模型列表、视觉能力配置、常见问题排查。
- 📕 `references/env-cleanup-procedure.md` — `.env` 文件清理标准流程（备份→提取活跃变量→验证），适用于切换配置方式或重构后清理冗余。
- 📕 `references/three-phase-cleanup.md` — 三阶段 API 配置清理模式（Key 截断修复 → Provider 字段修复 → .env 瘦身），2026-06-13 经多次重启/报错后验证有效的系统化修复顺序。
