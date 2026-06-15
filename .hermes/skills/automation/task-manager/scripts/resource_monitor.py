#!/usr/bin/env python3
"""
系统资源监控器
监控 CPU、内存、进程数，支持智能调度决策
"""

import psutil
import time
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ResourceStatus:
    """资源状态"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    active_tasks: int
    timestamp: float

    @property
    def can_accept_new_task(self) -> bool:
        """是否可以接受新任务"""
        return (
            self.cpu_percent < 50 and
            self.memory_percent < 70 and
            self.active_tasks < 3
        )

    @property
    def health_score(self) -> int:
        """健康度评分（0-100）"""
        score = 100
        # CPU 扣分
        if self.cpu_percent > 50:
            score -= int((self.cpu_percent - 50) * 1.5)
        # 内存扣分
        if self.memory_percent > 70:
            score -= int((self.memory_percent - 70) * 2)
        # 任务数扣分
        score -= self.active_tasks * 15
        return max(0, score)

    def __str__(self) -> str:
        return (
            f"CPU: {self.cpu_percent:.1f}% | "
            f"内存: {self.memory_percent:.1f}% ({self.memory_available_mb:.0f}MB) | "
            f"活跃任务: {self.active_tasks} | "
            f"健康度: {self.health_score}"
        )


class ResourceMonitor:
    """资源监控器"""

    def __init__(self):
        self.history: list[ResourceStatus] = []
        self.max_history = 100

    def get_current_status(self, active_tasks: int = 0) -> ResourceStatus:
        """获取当前资源状态"""
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()

        status = ResourceStatus(
            cpu_percent=cpu,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / 1024 / 1024,
            active_tasks=active_tasks,
            timestamp=time.time()
        )

        # 保存历史
        self.history.append(status)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        return status

    def get_average_status(self, seconds: int = 60) -> Optional[ResourceStatus]:
        """获取过去 N 秒的平均状态"""
        cutoff = time.time() - seconds
        recent = [h for h in self.history if h.timestamp > cutoff]

        if not recent:
            return None

        return ResourceStatus(
            cpu_percent=sum(h.cpu_percent for h in recent) / len(recent),
            memory_percent=sum(h.memory_percent for h in recent) / len(recent),
            memory_available_mb=sum(h.memory_available_mb for h in recent) / len(recent),
            active_tasks=recent[-1].active_tasks,  # 使用最新的任务数
            timestamp=time.time()
        )

    def wait_for_resources(
        self,
        target_cpu: float = 50,
        target_memory: float = 70,
        timeout: int = 300,
        check_interval: int = 5
    ) -> bool:
        """
        等待资源可用

        Returns:
            True: 资源可用
            False: 超时
        """
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_current_status()
            if status.cpu_percent < target_cpu and status.memory_percent < target_memory:
                return True
            time.sleep(check_interval)
        return False


if __name__ == '__main__':
    # 测试
    monitor = ResourceMonitor()
    status = monitor.get_current_status(active_tasks=1)
    print(f"当前状态: {status}")
    print(f"可接受新任务: {status.can_accept_new_task}")
