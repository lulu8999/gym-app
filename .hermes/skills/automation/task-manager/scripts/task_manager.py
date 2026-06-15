#!/usr/bin/env python3
"""
后台任务管理器
支持任务队列、智能调度、状态跟踪
"""

import json
import time
import uuid
import subprocess
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable, Dict
from threading import Thread, Lock
import queue

from resource_monitor import ResourceMonitor, ResourceStatus


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"          # 等待中
    QUEUED = "queued"            # 已入队
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


class TaskType(Enum):
    """任务类型"""
    CODE = "code"                # 编程任务 - 交给 Claude
    ANALYSIS = "analysis"        # 分析任务 - 我来做
    DOCUMENT = "document"        # 文档处理 - 自动化工具
    COMMAND = "command"          # 命令执行 - 后台进程


@dataclass
class Task:
    """任务定义"""
    id: str
    type: TaskType
    title: str
    description: str
    command: Optional[str] = None  # 需要执行的命令
    script: Optional[str] = None   # 需要执行的脚本路径
    priority: int = 5              # 1-10，数字越小越优先
    created_at: float = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    output_file: Optional[str] = None
    notify_on_complete: bool = True

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            'type': self.type.value,
            'status': self.status.value,
            'created_at_str': datetime.fromtimestamp(self.created_at).strftime('%Y-%m-%d %H:%M:%S')
        }


class TaskManager:
    """任务管理器"""

    def __init__(self, data_dir: str = '~/.hermes/task_manager'):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.queue: queue.PriorityQueue = queue.PriorityQueue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.monitor = ResourceMonitor()

        self.lock = Lock()
        self.running = False
        self.scheduler_thread: Optional[Thread] = None

        # 回调函数
        self.on_task_complete: Optional[Callable[[Task], None]] = None
        self.on_task_failed: Optional[Callable[[Task], None]] = None

        # 加载已保存的任务
        self._load_tasks()

    def _load_tasks(self):
        """加载已保存的任务"""
        tasks_file = self.data_dir / 'tasks.json'
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 恢复任务状态...
            except:
                pass

    def _save_tasks(self):
        """保存任务状态"""
        tasks_file = self.data_dir / 'tasks.json'
        with self.lock:
            all_tasks = {
                **{k: v.to_dict() for k, v in self.active_tasks.items()},
                **{k: v.to_dict() for k, v in self.completed_tasks.items()}
            }
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(all_tasks, f, ensure_ascii=False, indent=2)

    def submit_task(
        self,
        task_type: TaskType,
        title: str,
        description: str,
        command: Optional[str] = None,
        script: Optional[str] = None,
        priority: int = 5,
        notify: bool = True
    ) -> Task:
        """
        提交新任务

        Returns:
            创建的任务对象
        """
        task = Task(
            id=str(uuid.uuid4())[:8],
            type=task_type,
            title=title,
            description=description,
            command=command,
            script=script,
            priority=priority,
            notify_on_complete=notify
        )

        # 检查资源
        status = self.monitor.get_current_status(len(self.active_tasks))

        if status.can_accept_new_task:
            # 立即执行
            task.status = TaskStatus.RUNNING
            with self.lock:
                self.active_tasks[task.id] = task
            self._start_task(task)
        else:
            # 放入队列
            task.status = TaskStatus.QUEUED
            self.queue.put((priority, time.time(), task))
            print(f"任务 {task.id} 已入队（等待资源）")

        self._save_tasks()
        return task

    def _start_task(self, task: Task):
        """启动任务"""
        task.started_at = time.time()
        task.status = TaskStatus.RUNNING

        # 根据任务类型选择执行方式
        if task.type == TaskType.CODE:
            self._run_code_task(task)
        elif task.type == TaskType.COMMAND:
            self._run_command_task(task)
        elif task.type == TaskType.SCRIPT:
            self._run_script_task(task)
        else:
            # 其他类型需要外部处理
            pass

    def _run_command_task(self, task: Task):
        """运行命令任务"""
        def run():
            try:
                result = subprocess.run(
                    task.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=1800  # 30分钟超时
                )
                task.result = result.stdout
                if result.returncode != 0:
                    task.error = result.stderr
                    task.status = TaskStatus.FAILED
                    if self.on_task_failed:
                        self.on_task_failed(task)
                else:
                    task.status = TaskStatus.COMPLETED
                    if self.on_task_complete:
                        self.on_task_complete(task)

            except subprocess.TimeoutExpired:
                task.error = "任务超时"
                task.status = TaskStatus.FAILED
                if self.on_task_failed:
                    self.on_task_failed(task)
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                if self.on_task_failed:
                    self.on_task_failed(task)
            finally:
                task.completed_at = time.time()
                with self.lock:
                    if task.id in self.active_tasks:
                        self.completed_tasks[task.id] = self.active_tasks.pop(task.id)
                self._save_tasks()
                self._process_queue()

        thread = Thread(target=run, daemon=True)
        thread.start()

    def _run_code_task(self, task: Task):
        """运行代码任务（通过 claude-code-ds）"""
        # 这里需要调用 Claude Code CLI
        # 暂时用占位符
        task.result = "Claude Code 任务已提交，等待完成"
        self._save_tasks()

    def _process_queue(self):
        """处理队列中的任务"""
        status = self.monitor.get_current_status(len(self.active_tasks))

        while status.can_accept_new_task and not self.queue.empty():
            try:
                priority, _, task = self.queue.get_nowait()
                task.status = TaskStatus.RUNNING
                with self.lock:
                    self.active_tasks[task.id] = task
                self._start_task(task)
                status = self.monitor.get_current_status(len(self.active_tasks))
            except queue.Empty:
                break

    def get_status(self) -> dict:
        """获取管理器状态"""
        resource = self.monitor.get_current_status(len(self.active_tasks))
        return {
            'resource': resource,
            'active_count': len(self.active_tasks),
            'queued_count': self.queue.qsize(),
            'completed_count': len(self.completed_tasks),
            'can_accept': resource.can_accept_new_task
        }

    def list_tasks(self) -> List[Task]:
        """列出所有任务"""
        with self.lock:
            return list(self.active_tasks.values()) + list(self.completed_tasks.values())

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self.lock:
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
        return None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        # 仅支持取消等待中的任务
        # TODO: 实现真正的取消机制
        return False


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取全局任务管理器"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


if __name__ == '__main__':
    # 测试
    tm = get_task_manager()

    # 添加测试任务
    task = tm.submit_task(
        task_type=TaskType.COMMAND,
        title="测试任务",
        description="echo hello",
        command="echo 'Hello from background task' && sleep 2",
        priority=1
    )

    print(f"创建任务: {task.id}")
    print(f"状态: {task.status.value}")

    # 等待完成
    time.sleep(3)

    task = tm.get_task(task.id)
    print(f"最终状态: {task.status.value}")
    print(f"结果: {task.result}")
