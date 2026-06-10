#!/usr/bin/env python3
"""
上下文看门狗 — 检测当前会话 token 消耗是否过多
超阈值时输出提醒文本，cron job 会把它推送给 Lulu
"""
import sqlite3
import os
import sys
import json

DB_PATH = os.path.expanduser("~/.hermes/state.db")

# 阈值设置（tokens）
WARN_THRESHOLD = 400_000    # 40万 token 提醒
CRIT_THRESHOLD = 800_000    # 80万 token 强烈提醒

# 通知冷却（秒）— 同一会话避免重复提醒
COOLDOWN_FILE = os.path.expanduser("~/.hermes/.context_watchdog_cooldown")
COOLDOWN_SECONDS = 3600  # 1小时


def get_active_sessions():
    """获取所有活跃（未结束）的会话"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT id, source, model, 
               input_tokens, output_tokens, cache_read_tokens,
               message_count, tool_call_count,
               started_at
        FROM sessions 
        WHERE ended_at IS NULL 
        ORDER BY started_at DESC
    """)
    sessions = cursor.fetchall()
    conn.close()
    return sessions


def check_cooldown(session_id):
    """检查是否在冷却期内"""
    if not os.path.exists(COOLDOWN_FILE):
        return False
    try:
        with open(COOLDOWN_FILE, "r") as f:
            data = json.load(f)
        last_warn = data.get(session_id, 0)
        import time
        return (time.time() - last_warn) < COOLDOWN_SECONDS
    except:
        return False


def set_cooldown(session_id):
    """设置冷却时间"""
    import time
    data = {}
    if os.path.exists(COOLDOWN_FILE):
        try:
            with open(COOLDOWN_FILE, "r") as f:
                data = json.load(f)
        except:
            pass
    data[session_id] = time.time()
    with open(COOLDOWN_FILE, "w") as f:
        json.dump(data, f)


def main():
    sessions = get_active_sessions()
    
    if not sessions:
        print("[SILENT]")
        return
    
    warnings = []
    
    for sid, source, model, input_t, output_t, cache_t, msg_count, tool_count, started in sessions:
        total = input_t + output_t
        
        if total < WARN_THRESHOLD:
            continue
        
        # 检查冷却
        if check_cooldown(sid):
            continue
        
        # 计算预估费用（MiMo v2.5 定价）
        # Input: $0.40/M = ¥2.92/M, Output: $2.00/M = ¥14.60/M
        input_cost = input_t * 2.92 / 1_000_000
        output_cost = output_t * 14.60 / 1_000_000
        total_cost = input_cost + output_cost
        
        level = "🔴 严重" if total >= CRIT_THRESHOLD else "⚠️ 注意"
        
        warnings.append({
            "session_id": sid,
            "source": source,
            "model": model,
            "input_tokens": input_t,
            "output_tokens": output_t,
            "total_tokens": total,
            "message_count": msg_count,
            "total_cost": total_cost,
            "level": level,
        })
    
    if not warnings:
        print("[SILENT]")
        return
    
    # 输出提醒
    lines = ["📊 **上下文监控提醒**\n"]
    
    for w in warnings:
        lines.append(f"{w['level']} 会话 `{w['session_id']}`")
        lines.append(f"- 来源: {w['source']} | 模型: {w['model']}")
        lines.append(f"- Input: {w['input_tokens']:,} | Output: {w['output_tokens']:,}")
        lines.append(f"- 消息数: {w['message_count']} | 预估费用: ¥{w['total_cost']:.2f}")
        
        if w['total_tokens'] >= CRIT_THRESHOLD:
            lines.append(f"- 💸 上下文已经很大了，每轮对话都在烧钱！")
        else:
            lines.append(f"- 📌 上下文在增长，考虑开新会话省点钱～")
        
        # 设置冷却
        set_cooldown(w['session_id'])
    
    lines.append("")
    lines.append("要不要开新会话清一下上下文？回复「开新会话」就行～")
    
    print("\n".join(lines))


if __name__ == "__main__":
    main()
