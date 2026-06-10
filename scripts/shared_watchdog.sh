#!/bin/bash
# shared_watchdog.sh — 监测 /root/shared/ 目录变化，零 token 消耗
# 配合 cronjob no_agent=True 使用，有新内容时自动通知

SHARED_DIR="/root/shared"
STATE_FILE="/root/.hermes/.shared_watchdog_state"

# 生成当前目录状态指纹
current_hash=$(find "$SHARED_DIR" -type f \( -name "*.md" -o -name "*.json" \) -newer "$STATE_FILE" 2>/dev/null | wc -l)

# 首次运行，初始化状态文件
if [ ! -f "$STATE_FILE" ]; then
    date +%s > "$STATE_FILE"
    exit 0
fi

# 检查是否有新文件
if [ "$current_hash" -gt 0 ]; then
    echo "📥 共享目录有新内容："
    echo ""
    
    # 列出新/修改的文件
    find "$SHARED_DIR" -type f \( -name "*.md" -o -name "*.json" \) -newer "$STATE_FILE" | while read f; do
        rel_path="${f#$SHARED_DIR/}"
        echo "  📄 $rel_path"
    done
    
    echo ""
    echo "--- 目录分类 ---"
    
    # 检查 tasks/ 目录
    new_tasks=$(find "$SHARED_DIR/tasks" -type f -name "*.md" -newer "$STATE_FILE" 2>/dev/null | wc -l)
    if [ "$new_tasks" -gt 0 ]; then
        echo "  📋 新任务: $new_tasks 个"
        echo ""
        echo "=== 任务内容 ==="
        find "$SHARED_DIR/tasks" -type f -name "*.md" -newer "$STATE_FILE" | while read t; do
            echo "--- $(basename "$t") ---"
            cat "$t"
            echo ""
        done
    fi
    
    # 检查 memory/ 目录
    new_memory=$(find "$SHARED_DIR/memory" -type f -name "*.md" -newer "$STATE_FILE" 2>/dev/null | wc -l)
    if [ "$new_memory" -gt 0 ]; then
        echo "  🧠 新记忆: $new_memory 个"
    fi
    
    # 检查 skills/ 目录
    new_skills=$(find "$SHARED_DIR/skills" -type f -name "*.md" -newer "$STATE_FILE" 2>/dev/null | wc -l)
    if [ "$new_skills" -gt 0 ]; then
        echo "  🔧 新技能: $new_skills 个"
    fi
    
    # 自动执行同步
    if [ -f "$SHARED_DIR/sync_to_hermes.sh" ]; then
        bash "$SHARED_DIR/sync_to_hermes.sh" 2>/dev/null
    fi
    
    echo ""
    echo "✅ 同步完成"
fi

# 更新状态时间戳
date +%s > "$STATE_FILE"
