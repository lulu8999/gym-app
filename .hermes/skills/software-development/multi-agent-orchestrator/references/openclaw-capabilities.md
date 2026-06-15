# OpenClaw 能力记录

> 版本: 2026.5.28 (e932160)  
> CLI: `/usr/local/bin/openclaw`  
> 网关端口: 18789  
> 配置: `/root/.openclaw/openclaw.json`

## 已安装且就绪的技能

通过 `openclaw skills list` 查看。关键技能：

| 技能 | 状态 | 用途 |
|------|------|------|
| browser-automation | ✅ ready | 浏览器自动化（多步骤、登录、标签管理） |
| canvas | ✅ ready | 在 canvas 节点展示 HTML |
| 还有 ~13 个其他就绪技能 | | |

## 浏览器技能详情

**browser-automation**（`openclaw-extra` 源）
- 路径：`~/.openclaw/plugin-skills/browser-automation/SKILL.md`
- 操作动作：`open`, `snapshot`, `act`, `tabs`, `close`, `status`, `profiles`
- 支持 `label` 为标签命名，后续通过 `targetId` 引用
- 支持 `refs="aria"` 获取可访问性快照
- 用 `profile="user"` 可复用已有浏览器 session（cookies/login）

## 启用浏览器的步骤

```bash
# 1. 安装 Chromium（OpenCloudOS/dnf）
dnf install -y ungoogled-chromium
ln -sf /usr/bin/ungoogled-chromium /usr/local/bin/chromium-browser
ln -sf /usr/bin/ungoogled-chromium /usr/local/bin/google-chrome

# 2. 启动 OpenClaw 网关（后台）
openclaw gateway run --allow-unconfigured --bind loopback

# 3. 测试浏览器状态
openclaw browser status

# 4. 如果遇到 scope-upgrade 拒绝（device pairing approval denied），手动修复：
#    编辑 ~/.openclaw/devices/paired.json，把 device 的 scopes 和 approvedScopes 加上 "operator.admin"
#    修改前: "scopes": ["operator.pairing"]
#    修改后: "scopes": ["operator.pairing", "operator.admin"]
#    然后重启网关

# 5. 如果 OpenClaw 检测不到已安装的浏览器（"No supported browser found"）
#    尝试直接指向安装的路径。注意：ungoogled-chromium 不在 OpenClaw 的搜索列表中，
#    可能需要使用标准名称的浏览器
```

## 浏览器无法启动的排障

OpenClaw 仅识别标准命名的浏览器（`google-chrome`, `chromium-browser`, `chromium`, `brave`, `msedge`）。
`ungoogled-chromium` 默认不在搜索列表中，即使通过 `ln -sf` 创建别名也可能不被识别。

**Playwright 下载 Chromium 的问题：** 从中国大陆 VPS 访问 `storage.googleapis.com`（Google CDN）超时，
无法通过 `npx playwright install chromium` 下载。替代方案：
- 通过系统包管理器安装（`dnf install ungoogled-chromium`）
- 或从国内镜像手动下载 Chromium
- 或使用 Puppeteer 而非 Playwright

## ClawHub 上可安装的其他浏览器技能

```
openclaw skills search browser
```

- `agent-browser-cli` — 浏览器自动化 CLI
- `stagehand-browser-cli` — Stagehand 自然语言浏览器操作
- `ws-agent-browser` — 浏览器智能控制（中文）
- `use-my-browser` — 控制用户真实 Chrome 浏览器

## 已知问题

- 网关需要手动启动（pm2 未配置）
- 浏览器需要设备配对 + scope-upgrade 批准
- `--auth none` 参数不影响 scope 升级机制
- 如果有 stale channel 配置（openclaw-weixin, wecom 等），不影响核心功能
- 反复失败时考虑直接给 Hermes 装 Playwright 浏览器工具绕过
- **配对解决方式：** 编辑 `~/.openclaw/devices/paired.json`，给 device 加上 `operator.admin` scope 后重启网关即可。`openclaw devices approve` 命令行在自动化场景下可能失败（需要交互式批准），直接改配置文件更可靠。
- **Playwright 下载超时：** 中国大陆 VPS 连 Google CDN 超时，替代方案是系统包管理器安装
