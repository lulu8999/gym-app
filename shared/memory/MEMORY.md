# MEMORY.md - Long-Term Memory

## 关于 Lulu

- 叫我 **Lulu**，不需要客套话
- 南京，东八区
- 江苏警官学院学生
- 论文：多模态话语分析视角下中国微短剧的跨文化传播——以ReelShort为例

## 用户规则

1. 不动 C 盘系统文件 | 2. 不动个人文档（删改前先问）
3. 清理缓存/temp/log 前确认范围 | 4. 先检查再改配置
5. 每次新任务换新对话，不堆在同一会话

## 技术环境

### 本机（Windows）
- Windows 10.0.26200 (x64), Node 24.16.0
- Predator SSD GM7 M.2 1TB + KINGSTON 512GB
- C盘空间紧张（~12%）

### VPS（110.40.178.179）
- OpenCloudOS, 运行另一个 OpenClaw + Claude Code
- DeepSeek 后端通过 LiteLLM 代理（localhost:41111，PM2 管理）
- Claude Code 快捷命令：`claude-code-ds`
- DeepSeek 余额 ¥10.00（06-02），累计消耗 ~58M input / 0.9M output，费用 ¥11.91

## VPS Cron 定时任务

| 时间 | 任务 | 收件人 |
|------|------|--------|
| 09:00 Daily | deepseek-balance-check | Lulu WeChat |
| 09:00 Mon-Fri | stock-daily-verify | Lulu WeChat |
| 10:00 Mon-Fri | stock-morning-report | Lulu → 师父+老爹 |
| 15:30 Mon-Fri | stock-market-report | Lulu → 师父+老爹 |
| 15:30 Daily | daily-memory-summary | Lulu WeChat |
| */20 min | check-user-messages | Weixin |
| */20 min | gateway-watchdog | 静默（异常才通知） |

## VPS 关键配置

### API Key
- 当前 DeepSeek key：`sk-43b…112a`
- Kimi key：`/root/.kimi_key`，仅图片识别用
- 默认模型：`deepseek/deepseek-v4-flash`
- 旧 rightcodes provider 已移除

### 企业微信
- wecom.lulugame.fun → CF Tunnel → localhost:18800（PM2）
- corpId: ww815119bb08398d37, agentId: 1000002
- IP 白名单：110.40.178.179
- 自动注册：未知用户首次发消息自动创建 profile 并绑定
- Lulu WeChat chat_id: `o9cq80-Ct2fnApV5l3YGq1e2gWLQ@im.wechat`

### 股票分析系统
- `/root/stock_analyzer/` — data_fetcher, analyzer, reporter, fund_advisor, user_manager
- 多用户系统：admin 7权限 vs user 4权限
- ADMIN_IDS 硬编码：`['lulu', 'KuHai']`，多层防御绕过 profile.json
- 用户：徐昕（师父）、陆伟峰（老爹）、KuHai（Lulu别名）
- 持仓：中银上海金ETF联接C，成本¥1,100

### 管理面板
- admin.lulugame.fun → CF Tunnel → localhost:5000（gunicorn + systemd）
- Monitor 页面：系统状态、API健康、token用量、cron一览

### Web 终端
- term.lulugame.fun → CF Tunnel（Node.js + express + xterm.js + node-pty）
- Basic Auth：admin / 20040422lht，PM2 管理

### 运维调优
- 压缩 + memoryFlush 已开：会话超 10MB 自动触发压实
- wecom-chat-sync 每5→20分钟，check-user-messages 每10→20分钟
- 报告纯文字，先发 Lulu 再转发
- thinking 模式：medium（不支持 adaptive）

### Agent 自动压缩
- 开启 compaction + memoryFlush
- 超 10MB 自动触发，压实前跑记忆萃取
- 关键内容写进 memory/，旧上下文压缩成摘要

### VPS 已知问题
- memory_search 偶发卡死（131s+）
- 部分 cron timeout（30s）
- deepseek-balance-check 有时出错，待排查

## 重要事件

### 2026-05-30 本机
- 修复会话锁文件死锁
- 帮改论文：封面页眉横线去除、封面导出、图表数据提取
- 设置开机自启：gateway + 浏览器仪表盘

### 2026-05-31 本机
- 新建 auto-updater skill，接入 gateway.cmd 开机检查
- gateway.cmd 启动前加 auto-update 后台检测，不阻塞启动

### VPS 搭建记录（05-31 → 06-02）
- 搭建 OpenClaw + LiteLLM + Claude Code 环境
- 上线企业微信（05-31），管理面板（06-01）
- Claude Code + cc-switch 部署（06-02）
- Web 终端搭建（06-02）
- API Key 全面更换（旧 key 失效，切到 `sk-43b…112a`）
- 清理 45MB 旧轨迹文件，同步 5 个 skill 到 VPS
- 06-02 所有 VPS 服务已暂停

### 工作流程规则
- Plan-then-Execute 是至高规则
- 我负责聊天/协调/验证，Claude Code 负责终端实操
- 后台报错自己先排查修复，修完再解释
- 不准把 Lulu 个人信息套到别人头上
- 别人的信息就是别人的，没说要用的东西不准乱套
- 上下文不足时清理冗余或开新会话

## Memo

- python-docx 已装，pip 可用
- 未来要做微信小游戏、网页、小程序开发
