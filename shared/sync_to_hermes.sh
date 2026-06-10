#!/bin/bash
# sync_memory.sh — 从 Hermes 共享目录同步记忆/技能到本地
# 放在 VPS 上，Hermes 调用这个来读取 OpenClaw 的数据

SHARED_DIR="/root/shared"
LOCAL_MEMORY_DIR="/root/.hermes/shared_memory"

mkdir -p "$LOCAL_MEMORY_DIR"

echo "=== 同步时间: $(date) ==="

# 1. 把 OpenClaw 的记忆复制到 Hermes 可读的位置
if [ -f "$SHARED_DIR/memory/MEMORY.md" ]; then
    cp "$SHARED_DIR/memory/MEMORY.md" "$LOCAL_MEMORY_DIR/"
    echo "✅ 已同步 MEMORY.md"
fi

# 2. 把 OpenClaw 的技能复制过来
if ls "$SHARED_DIR/skills/"*.md 1>/dev/null 2>&1; then
    cp "$SHARED_DIR/skills/"*.md "$LOCAL_MEMORY_DIR/"
    echo "✅ 已同步 skills"
fi

# 3. 读取任务结果
if ls "$SHARED_DIR/tasks/"*.md 1>/dev/null 2>&1; then
    echo ""
    echo "=== 待处理任务 ==="
    cat "$SHARED_DIR/tasks/"*.md
fi

echo "=== 完成 ==="
