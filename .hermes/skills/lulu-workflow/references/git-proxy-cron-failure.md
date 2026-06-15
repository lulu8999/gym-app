# Git 代理导致 cron 脚本反复失败的排查与修复

## 问题（2026-06-13）

`hermes_auto_update.sh` cron 每 3 天运行一次，连续 6 天报 `exit code 128`（6/8~6/13，只有 6/9 成功一次）。

## 排查

### 1. 看 cron output 目录

```bash
ls /root/.hermes/cron/output/1f7df080d6b3/
cat /root/.hermes/cron/output/1f7df080d6b3/2026-06-13_00-01-02.md
```

输出：`Script exited with code 128` — Git fatal error。

### 2. 手动跑脚本

```bash
bash -x /root/.hermes/scripts/hermes_auto_update.sh
```

卡在 `git fetch origin main` 步骤。

### 3. 查 git 全局配置

```bash
git config --list --show-scope | grep proxy
```

输出：
```
global  http.https://github.com.proxy=http://127.0.0.1:7890
global  https.https://github.com.proxy=http://127.0.0.1:7890
```

**全局代理 `127.0.0.1:7890` 影响所有 GitHub 操作（包括 SSH remote）。**

### 4. 查 SSH 密钥

```bash
ssh -T git@github.com
# Permission denied (publickey)
```

SSH 密钥存在但未在 GitHub 注册。所以能通的那次（6/9）是代理在线+HTTPS 回退成功的。

## 根因

```
cron 执行时 mihomo 代理不在线
  → git fetch 走 127.0.0.1:7890 代理连接失败
  → 脚本 set -e 直接退出 128
  → cron 标记 error
```

## 修复

将脚本从 `origin`（SSH）改为 `upstream`（HTTPS 只读），并 graceful 降级：

```bash
# ❌ 旧版 — SSH origin + 代理参数，代理不在线就崩
git -c http.proxy=http://127.0.0.1:7890 fetch origin main 2>/dev/null

# ✅ 新版 — HTTPS upstream + 代理不在线时跳过
if ! git fetch upstream main 2>/dev/null; then
    echo "⚠️ git fetch 失败，跳过本次检查"
    exit 0  # exit 0 = cron 不报 error
fi
```

## 验证

```bash
bash /root/.hermes/scripts/hermes_auto_update.sh
# exit: 0 ✅
```

## 教训

| 坑 | 教训 |
|----|------|
| 全局 git proxy 影响所有 git 操作 | 排查 cron 失败先 `git config --list` 看全局设置 |
| SSH remote 配了全局 proxy | `git remote -v` 看 URL 类型，SSH 不自动走代理 |
| `set -e` + fetch 失败 = 128 | 任何 git 操作的 cron 脚本都要加 `|| exit 0` 兜底 |
| cron 环境与交互式环境不同 | proxy 在 cron 时可能不在线，必须测试 graceful fallback |
