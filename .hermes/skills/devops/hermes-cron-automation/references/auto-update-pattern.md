# Git 自动更新 no_agent 脚本模式

用于 Hermes 自身或项目的 git 自动更新。利用 no_agent 脚本的特性：
- **无更新时静默退出（空 stdout → 不投递）**
- **有更新时输出更新信息（非空 stdout → 投递）**

## 脚本模板

```bash
#!/usr/bin/env bash
# auto_update.sh — 自动检查并拉取 git 更新
set -e
cd /path/to/repo

# 1. 获取当前版本
CURRENT=$(git describe --tags 2>/dev/null || git rev-parse --short HEAD)

# 2. 用代理 fetch
git -c http.proxy=http://127.0.0.1:7890 -c https.proxy=http://127.0.0.1:7890 fetch origin main 2>/dev/null

# 3. 比较本地和远端
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0  # 无更新，静默退出
fi

# 4. 有更新：暂存本地改动 → pull → 恢复
git stash push -m "auto-update-stash" 2>/dev/null || true
git pull --rebase origin main 2>/dev/null
git stash pop 2>/dev/null || true

# 5. 输出更新信息（no_agent 投递）
NEW=$(git describe --tags 2>/dev/null || git rev-parse --short HEAD)
echo "🔄 已自动更新：$CURRENT → $NEW"
```

## 注意事项

- 脚本放在 `~/.hermes/scripts/`，cron 用相对文件名引用
- `set -e` 确保 fetch/pull 失败时脚本退出，不产生误报
- `stash push/pop` 保存本地未提交的改动，pull 后恢复
- 代理设置根据实际环境调整（mihomo 默认 127.0.0.1:7890）
- 确认 `git log --oneline -1` 命令可用（bare repo 不能直接使用）
