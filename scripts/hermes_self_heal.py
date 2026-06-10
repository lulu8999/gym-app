#!/usr/bin/env python3
"""
Hermes 自愈系统 — 备份、监控、自动恢复

运行方式：
  python3 hermes_self_heal.py backup     # 手动备份
  python3 hermes_self_heal.py check      # 健康检查 + 自动恢复
  python3 hermes_self_heal.py restore    # 从最新备份恢复

cron 定时调用 check 模式，有问题自动修，修不好才报用户。
"""
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

# ── 配置 ─────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
BACKUP_DIR = HERMES_HOME / "backups"
MAX_BACKUPS = 5

# 需要备份的路径（相对于 HERMES_HOME）
BACKUP_PATHS = [
    "config.yaml",
    ".env",
    "access.yaml",
    "plugins/",
    "skills/",
    "cron/",
    "scripts/",
]

# 冷却期（秒）— 同一服务被重启后，N 秒内不再重启
RESTART_COOLDOWN = 120
_last_restart: dict[str, float] = {}

# 标记文件：上次检查时各服务的状态快照，用于判断状态是否真的变了
_STATUS_FILE = HERMES_HOME / ".self_heal_last_state.json"

# PM2 服务名 → 对应端口
SERVICES = {
    "hermes-gateway": {"port": 8645, "type": "tcp"},
    "hermes-dashboard": {"port": 9119, "type": "tcp"},
    "openclaw-gateway": {"port": 9000, "type": "tcp"},
    "location-server": {"port": 9803, "type": "tcp"},
    "litellm-proxy": {"port": 41111, "type": "tcp"},
}


# ── 工具函数 ──────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_cmd(cmd: list, timeout: int = 15) -> tuple[int, str]:
    """执行命令，返回 (exit_code, stdout+stderr)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError:
        return -2, "COMMAND_NOT_FOUND"


def port_listening(port: int) -> bool:
    code, out = run_cmd(["ss", "-tlnp"])
    return f":{port}" in out


def pm2_status(name: str) -> str:
    """返回 'online', 'stopped', 'errored', 或 'not_found'"""
    code, out = run_cmd(["pm2", "show", name])
    if code != 0:
        return "not_found"
    # 去除 ANSI 颜色转义码
    import re
    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', out)
    # 用更精确的方式匹配状态行
    for line in clean.splitlines():
        line = line.strip()
        if line.startswith("│ status") and "│" in line[10:]:
            parts = line.split("│")
            if len(parts) >= 3:
                status = parts[2].strip()
                if status in ("online", "stopped", "errored"):
                    return status
    return "unknown"


# ── 备份 ──────────────────────────────────────────────────────────

def do_backup() -> bool:
    """创建完整备份，返回是否成功"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"hermes_backup_{ts}.tar.gz"

    # 轮转旧备份
    existing = sorted(BACKUP_DIR.glob("hermes_backup_*.tar.gz"))
    while len(existing) >= MAX_BACKUPS:
        existing[0].unlink()
        existing = existing[1:]

    try:
        with tarfile.open(backup_path, "w:gz") as tar:
            for rel in BACKUP_PATHS:
                src = HERMES_HOME / rel
                if src.exists():
                    tar.add(src, arcname=rel)
        # 同时存一份 PM2 进程列表
        run_cmd(["pm2", "save"])
        log(f"备份完成: {backup_path}")
        return True
    except Exception as e:
        log(f"备份失败: {e}")
        return False


def latest_backup() -> Path | None:
    existing = sorted(BACKUP_DIR.glob("hermes_backup_*.tar.gz"))
    return existing[-1] if existing else None


def do_restore() -> bool:
    """从最新备份恢复"""
    bk = latest_backup()
    if not bk:
        log("没有可用备份")
        return False
    try:
        with tarfile.open(bk, "r:gz") as tar:
            tar.extractall(path=HERMES_HOME)
        log(f"已从 {bk.name} 恢复")
        return True
    except Exception as e:
        log(f"恢复失败: {e}")
        return False


# ── 健康检查 ──────────────────────────────────────────────────────

def check_all() -> list[dict]:
    """检查所有服务，返回问题列表"""
    issues = []

    # 1. 检查 PM2 是否在运行
    code, _ = run_cmd(["pm2", "list"])
    if code != 0:
        issues.append({"service": "pm2", "problem": "pm2_daemon_not_running"})
        return issues  # PM2 挂了就不用查具体的了

    # 2. 检查各个服务
    for name, cfg in SERVICES.items():
        status = pm2_status(name)
        port_ok = port_listening(cfg["port"]) if cfg.get("port") else None

        if status != "online":
            issues.append({
                "service": name,
                "problem": f"status={status}",
                "expected_port": cfg["port"],
            })
        elif port_ok is False:
            issues.append({
                "service": name,
                "problem": "process_online_but_port_not_listening",
                "expected_port": cfg["port"],
            })

    # 3. 检查配置文件存在
    cfg_path = HERMES_HOME / "config.yaml"
    if not cfg_path.exists():
        issues.append({"service": "config", "problem": "config.yaml_missing"})

    return issues


def _in_cooldown(name: str) -> bool:
    """检查服务是否还在冷却期内"""
    last = _last_restart.get(name, 0)
    elapsed = time.time() - last
    if elapsed < RESTART_COOLDOWN:
        log(f"{name} 在冷却期内（还剩 {int(RESTART_COOLDOWN - elapsed)}s），跳过重启")
        return True
    return False


def _save_state(issues: list[dict]):
    """保存本次检查结果，下次对比用"""
    try:
        state = {
            "timestamp": time.time(),
            "issues": [
                {"service": i["service"], "problem": i.get("problem", "")}
                for i in issues
            ],
        }
        with open(_STATUS_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def _is_repeated_issue(service: str, problem: str, old_issues: list[dict]) -> bool:
    """判断同一个问题上次检查是否存在"""
    for iss in old_issues:
        if iss.get("service") == service and iss.get("problem") == problem:
            return True
    return False


def fix_issues(issues: list[dict]) -> tuple[bool, list[str]]:
    """尝试修复问题，返回 (全部修好了吗, 修复记录)"""
    fixes = []
    all_ok = True

    # 读上一次的状态（用于判断是否是重复问题）
    old_issues = []
    try:
        with open(_STATUS_FILE) as f:
            old_state = json.load(f)
        old_issues = old_state.get("issues", [])
    except Exception:
        pass

    # 再保存本次问题（给下一次用）
    _save_state(issues)

    for iss in issues:
        svc = iss["service"]
        problem = iss.get("problem", "")

        # 端口未监听但进程 online → 可能是 transient，跳过不重启
        if problem == "process_online_but_port_not_listening":
            log(f"{svc} 进程在线但端口暂未监听，可能是启动中，跳过重启")
            fixes.append(f"{svc}_port_not_ready_skipped")
            continue

        # 检查是否同一个问题反复出现
        if _is_repeated_issue(svc, problem, old_issues):
            log(f"{svc} 的问题已持续存在（上次也有），跳过本次重启，留给下次检查")
            fixes.append(f"{svc}_persistent_issue_skipped")
            all_ok = False
            continue

        if svc == "pm2":
            log("PM2 daemon 挂了，尝试启动…")
            code, out = run_cmd(["pm2", "resurrect"], timeout=10)
            if code != 0:
                log(f"PM2 resurrect 失败: {out}")
                # 最后手段：从备份恢复 PM2 dump
                dump = HERMES_HOME / "backups" / "pm2_dump.json"
                if dump.exists():
                    shutil.copy(dump, Path.home() / ".pm2" / "dump.pm2")
                    run_cmd(["pm2", "resurrect"], timeout=10)
            fixes.append(f"pm2_daemon_restarted")
            all_ok = False  # 要再检查一轮
            continue

        if svc == "config":
            log("config.yaml 缺失，尝试从备份恢复…")
            if do_restore():
                fixes.append("config_restored_from_backup")
            else:
                fixes.append("config_restore_FAILED")
                all_ok = False
            continue

        # 检查冷却期
        if _in_cooldown(svc):
            fixes.append(f"{svc}_in_cooldown_skipped")
            all_ok = False
            continue

        # 重启 PM2 服务
        log(f"尝试重启 {svc}…")
        _last_restart[svc] = time.time()
        code, out = run_cmd(["pm2", "restart", svc], timeout=30)
        if code != 0:
            log(f"pm2 restart {svc} 失败: {out}")
            # 第二次尝试：停掉再启动
            run_cmd(["pm2", "stop", svc], timeout=10)
            time.sleep(2)
            code, out = run_cmd(["pm2", "start", svc], timeout=30)
            if code != 0:
                fixes.append(f"{svc}_restart_FAILED")
                all_ok = False
                continue

        time.sleep(5)
        # 验证端口
        port = iss.get("expected_port")
        if port and not port_listening(port):
            log(f"{svc} 重启后端口 {port} 仍未监听，尝试从备份恢复配置后重试…")
            if do_restore():
                run_cmd(["pm2", "restart", svc], timeout=30)
                time.sleep(5)
                if port and port_listening(port):
                    fixes.append(f"{svc}_fixed_via_config_restore")
                else:
                    fixes.append(f"{svc}_unfixable")
                    all_ok = False
            else:
                fixes.append(f"{svc}_unfixable")
                all_ok = False
        else:
            fixes.append(f"{svc}_restarted_ok")

    return all_ok, fixes


# ── 主入口 ────────────────────────────────────────────────────────

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "check"

    if action == "backup":
        ok = do_backup()
        sys.exit(0 if ok else 1)

    elif action == "restore":
        ok = do_restore()
        sys.exit(0 if ok else 1)

    elif action == "check":
        # 先备份（每天自动一次）
        do_backup()

        issues = check_all()

        if not issues:
            # 一切正常 → 静默退出（不输出任何内容）
            return

        # 有问题 → 尝试修复
        log(f"检测到 {len(issues)} 个问题，开始修复…")
        all_fixed, fixes = fix_issues(issues)

        if all_fixed:
            # 修好了 → 也静默，不打扰用户
            return

        # 修不好 → 输出报告，cron 会发给 KuHai
        log("=" * 50)
        log("⚠️ 自愈失败，以下问题未能修复:")
        for f in fixes:
            if "FAILED" in f or "unfixable" in f:
                log(f"  ✗ {f}")
        log("=" * 50)
        log("请手动检查服务器状态")
        sys.exit(1)

    else:
        print(f"用法: {sys.argv[0]} [backup|check|restore]")
        sys.exit(1)


if __name__ == "__main__":
    main()
