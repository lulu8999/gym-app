---
name: iot-security-research
title: IoT 设备安全调研与文档生成
description: 对 IoT 设备（尤其 BLE 智能门锁）进行安全调研：收集品牌/协议/加密方式，分析安全等级与逆向可行性，生成结构化 PDF 报告。
category: research
trigger: 用户需要对 IoT 设备进行安全调研，分析 BLE/无线协议，或生成安全技术报告
dependencies: [weasyprint]
---

# IoT 设备安全调研与文档生成

用于快速调研 IoT 产品（如智能门锁）的 BLE 协议、加密机制、安全漏洞，并输出结构化 PDF 报告。

## 工作流

### Step 1: 批量调研（用 delegate_task）
当需要覆盖多个品牌时，使用 `delegate_task` 并行搜索：

```python
# 示例：委托子 agent 进行全品牌搜索
delegate_task(
    goal="搜索各品牌智能门锁的BLE通信协议和加密方式",
    context=f"覆盖品牌包括：TTLock、小米米家、涂鸦、August...",
    toolsets=["web"]
)
```

单品牌调研直接用 `web_search` 分次搜索即可。

### Step 2: 格式转换（HTML + WeasyPrint → PDF）
使用 WeasyPrint 从 HTML 生成 PDF（比 fpdf2/reportlab 更适合复杂表格和结构化文档）：

```bash
# 将含 CSS 样式的 HTML 转为 PDF
weasyprint report.html report.pdf 2>&1
```

**⚠️ WeasyPrint 坑点：**
- Noto Sans CJK SC 不支持 emoji（⭐🔐✅❌ 等会报 notdef 警告）。解决方案：**用纯文本替代** emoji，如 `[高]` 代替 `⭐⭐⭐`，用文字标签代替图标
- 字体系列设置：`font-family: "Noto Sans CJK SC", "Noto Sans SC", sans-serif;`
- 中文字体需通过 `fc-list :lang=zh` 确认系统已安装

### Step 3: 三层次安全分析（用户偏好）
用户爱问"为什么"，解释安全问题时要分三个层次：

1. **技术层**：加密强度、密钥存储方案（ARM TrustZone vs SE）、是否有 CVE 或已知攻击
2. **法律层**：DMCA 第 1201 条反规避条款、商业秘密法
3. **经济层**：逆向投入产出比、安全元件破解成本

### Step 4: 品牌对比模板
使用统一的评估维度：

| 维度 | 说明 |
|:----|:----|
| 无线协议 | BLE 版本、有无 WiFi/Z-Wave |
| 加密方式 | AES-128/256、TLS、安全芯片 |
| 配对方式 | JustWorks / Passkey Entry / Bonding / 安全芯片认证 |
| API 开放度 | 开放 SDK / 付费 API / 封闭 |
| 安全评级 | 5 级制（从明文到安全元件） |
| 破解友好度 | 从"极低"到"极高" |

## 三层分级策略（用户总结）

不是所有锁都能逆向。答疑时按三层分法解释：

| 层级 | 代表品牌 | 破解难度 | 推荐策略 |
|:----|:---------|:-------:|:---------|
| 高端（2000+） | 米家/德施曼/Schlage | 🚫 不可 BLE 破解 | 监控路线（只读广播）/ 物理方案 |
| 中端（800-2000） | TTLock/涂鸦 | ⚠️ 需先配对提取 eKey | 抓包分析 → ESP32 复用 |
| 廉价（300-800） | 淘宝公模 | ✅ 直连 | ESP32 写 Characteristic |

### 监控路线 vs 破解路线（用户常混淆）

```
监控路线（被动）              破解路线（主动）
- 只读广播数据                - 连接 GATT Service
- 检测门状态/电量             - 尝试写入开锁指令
- 不写指令，无法律风险        - 有法律风险
- 所有锁都可做                - 高端锁不可行
```

**特别提醒**：监控收到的广播数据和破解所需的加密密钥是两回事。广播里的密文没有密钥就是废数据。

## 参考资料

- `references/ble-lock-brand-database.md` — 13 个品牌加密方式速查
- `references/weasyprint-font-tips.md` — 中文 PDF 字体配置
- `references/lock-tier-analysis.md` — 三层分级分析 + 物理方案 + 推荐项目路径

## 相关技能

- `chinese-document-generation` — fpdf2/reportlab 方式（适合简单 PDF）
- `l123-l1` — 概念性 Q&A 拦截（避免因门锁问题调 DeepSeek）
- 本技能走 WeasyPrint（适合复杂表格/排版）
