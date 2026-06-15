#!/usr/bin/env python3
"""
任务完成通知系统
支持多种通知方式：企微、文件、日志
"""

import json
import time
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from task_manager import Task, TaskStatus


@dataclass
class NotificationConfig:
    """通知配置"""
    wecom_enabled: bool = True
    wecom_channel: str = "wecom:LuHaiTian"  # 默认发给自己
    file_enabled: bool = True
    log_enabled: bool = True


class TaskNotifier:
    """
    任务通知器
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self.log_dir = Path('~/.hermes/task_manager/notifications').expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def notify_task_complete(self, task: Task):
        """任务完成通知"""
        if not task.notify_on_complete:
            return

        message = self._format_complete_message(task)

        # 企微通知
        if self.config.wecom_enabled:
            self._send_wecom(message)

        # 保存到文件
        if self.config.file_enabled:
            self._save_to_file(task, message)

        # 记录日志
        if self.config.log_enabled:
            self._log_notification(task, message)

    def notify_task_failed(self, task: Task):
        """任务失败通知"""
        message = self._format_failed_message(task)

        if self.config.wecom_enabled:
            self._send_wecom(message, is_error=True)

        if self.config.file_enabled:
            self._save_to_file(task, message, suffix='_failed')

        if self.config.log_enabled:
            self._log_notification(task, message, level='ERROR')

    def notify_progress(self, task: Task, progress: str):
        """任务进度通知（仅保存日志，不发送）"""
        if self.config.log_enabled:
            self._log_progress(task, progress)

    def _format_complete_message(self, task: Task) -> str:
        """格式化完成消息"""
        duration = ""
        if task.started_at and task.completed_at:
            secs = task.completed_at - task.started_at
            if secs < 60:
                duration = f"{secs:.0f}秒"
            elif secs < 3600:
                duration = f"{secs/60:.1f}分钟"
            else:
                duration = f"{secs/3600:.1f}小时"

        msg = f"""
✅ 后台任务完成

任务: {task.title}
类型: {task.type.value}
耗时: {duration}

"""
        if task.result:
            # 结果截断
            result_preview = task.result[:500] + "..." if len(task.result) > 500 else task.result
            msg += f"结果摘要:\n{result_preview}\n\n"

        if task.output_file:
            msg += f"输出位置: {task.output_file}\n"

        return msg.strip()

    def _format_failed_message(self, task: Task) -> str:
        """格式化失败消息"""
        msg = f"""
❌ 后台任务失败

任务: {task.title}
类型: {task.type.value}
错误: {task.error or '未知错误'}

请检查任务详情或重试。
"""
        return msg.strip()

    def _send_wecom(self, message: str, is_error: bool = False):
        """发送企微消息"""
        try:
            # 尝试使用 Hermes 的 send_message 工具
            # 这里需要通过子进程或者文件触发
            # 暂时用日志记录
            self._log_wecom_attempt(message, is_error)
        except Exception as e:
            print(f"企微发送失败: {e}")

    def _save_to_file(self, task: Task, message: str, suffix: str = ''):
        """保存到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{task.id}{suffix}_{timestamp}.txt"
        filepath = self.log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(message)
            f.write("\n\n")
            f.write("=" * 50)
            f.write("\n\n任务详情:\n")
            f.write(json.dumps(task.to_dict(), ensure_ascii=False, indent=2))

    def _log_notification(self, task: Task, message: str, level: str = 'INFO'):
        """记录日志"""
        log_file = self.log_dir / 'notifications.log'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{level}] Task {task.id}: {task.title}\n")
            f.write(f"  Status: {task.status.value}\n")
            if level == 'ERROR':
                f.write(f"  Error: {task.error}\n")
            f.write("\n")

    def _log_progress(self, task: Task, progress: str):
        """记录进度"""
        log_file = self.log_dir / 'progress.log'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {task.id}: {progress}\n")

    def _log_wecom_attempt(self, message: str, is_error: bool):
        """记录企微发送尝试"""
        log_file = self.log_dir / 'wecom_attempts.log'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {'[ERROR]' if is_error else '[INFO]}\n")
            f.write(f"{message[:200]}...\n\n")


# 全局通知器
_notifier: Optional[TaskNotifier] = None


def get_notifier() -> TaskNotifier:
    """获取全局通知器"""
    global _notifier
    if _notifier is None:
        _notifier = TaskNotifier()
    return _notifier


if __name__ == '__main__':
    # 测试
    from task_manager import Task, TaskType

    notifier = get_notifier()

    task = Task(
        id="test-001",
        type=TaskType.CODE,
        title="测试任务",
        description="这是一个测试",
        status=TaskStatus.COMPLETED,
        result="测试结果正常\n所有功能已实现"
    )
    task.started_at = time.time() - 120
    task.completed_at = time.time()

    notifier.notify_task_complete(task)
    print("通知测试完成")
