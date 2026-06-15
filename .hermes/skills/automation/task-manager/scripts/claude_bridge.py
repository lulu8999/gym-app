#!/usr/bin/env python3
"""
Claude Code 桥接器
负责与 Claude Code CLI 的通信，把编程任务交给 Claude 处理
"""

import subprocess
import json
import time
import os
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

from task_manager import Task, TaskStatus


@dataclass
class ClaudeTaskConfig:
    """Claude 任务配置"""
    workdir: Optional[str] = None
    files: Optional[list] = None
    timeout: int = 1800  # 30分钟
    approve_all: bool = True  # 是否自动批准


class ClaudeBridge:
    """
    Claude Code 桥接
    负责把编程任务发给 Claude，并跟踪进度
    """

    def __init__(self):
        self.claude_cmd = 'claude-code-ds'
        self.check_claude_available()

    def check_claude_available(self) -> bool:
        """检查 Claude Code 是否可用"""
        try:
            result = subprocess.run(
                ['which', self.claude_cmd],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    def submit_task(
        self,
        task: Task,
        config: Optional[ClaudeTaskConfig] = None,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[Task], None]] = None
    ) -> bool:
        """
        提交任务给 Claude

        Args:
            task: 任务对象
            config: Claude 配置
            on_progress: 进度回调
            on_complete: 完成回调

        Returns:
            是否成功提交
        """
        if not self.check_claude_available():
            task.error = "Claude Code 不可用"
            task.status = TaskStatus.FAILED
            return False

        config = config or ClaudeTaskConfig()

        # 构建 Claude 命令
        cmd_parts = [self.claude_cmd]

        if config.workdir:
            cmd_parts.extend(['--cwd', config.workdir])

        if config.approve_all:
            cmd_parts.append('--dangerously-skip-permissions')

        # 使用 -p 参数传递提示词
        prompt = self._build_prompt(task)
        cmd_parts.extend(['-p', prompt])

        # 运行 Claude
        def run_claude():
            try:
                if on_progress:
                    on_progress("开始执行 Claude Code...")

                # 创建输出目录
                output_dir = Path(f'~/.hermes/task_manager/outputs/{task.id}').expanduser()
                output_dir.mkdir(parents=True, exist_ok=True)

                # 记录开始时间
                start_time = time.time()

                result = subprocess.run(
                    cmd_parts,
                    capture_output=True,
                    text=True,
                    timeout=config.timeout,
                    cwd=config.workdir or os.getcwd()
                )

                # 记录结果
                end_time = time.time()

                # 保存输出
                stdout_file = output_dir / 'stdout.txt'
                stderr_file = output_dir / 'stderr.txt'
                meta_file = output_dir / 'meta.json'

                with open(stdout_file, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                with open(stderr_file, 'w', encoding='utf-8') as f:
                    f.write(result.stderr)

                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'task_id': task.id,
                        'command': ' '.join(cmd_parts),
                        'returncode': result.returncode,
                        'duration': end_time - start_time,
                        'timestamp': end_time
                    }, f, indent=2)

                # 更新任务状态
                task.output_file = str(output_dir)
                if result.returncode == 0:
                    task.status = TaskStatus.COMPLETED
                    task.result = result.stdout[:5000]  # 限制结果大小
                else:
                    task.status = TaskStatus.FAILED
                    task.error = result.stderr[:2000]

                if on_progress:
                    on_progress(f"任务完成，耗时 {end_time - start_time:.1f}s")

                if on_complete:
                    on_complete(task)

            except subprocess.TimeoutExpired:
                task.status = TaskStatus.FAILED
                task.error = f"任务超时（>{config.timeout}秒）"
                if on_complete:
                    on_complete(task)
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                if on_complete:
                    on_complete(task)

        # 启动后台线程
        import threading
        thread = threading.Thread(target=run_claude, daemon=True)
        thread.start()

        return True

    def _build_prompt(self, task: Task) -> str:
        """构建 Claude 提示词"""
        prompt = f"""
任务: {task.title}
描述: {task.description}

要求:
1. 详细记录你的思考过程
2. 所有修改都要有详细注释
3. 完成后汇报：做了什么、文件路径、如何验证
4. 如果遇到问题，先尝试解决，解决不了详细说明问题

开始执行。
"""
        return prompt.strip()


class TaskSplitter:
    """
    任务拆分器
    把大任务拆成多个小任务给不同的处理器
    """

    @staticmethod
    def analyze_task(description: str) -> dict:
        """
        分析任务类型

        Returns:
            {
                'type': 'code' | 'analysis' | 'document',
                'complexity': 1-10,
                'can_parallel': bool,
                'subtasks': list
            }
        """
        # 简单的关键词匹配
        description_lower = description.lower()

        result = {
            'type': 'analysis',
            'complexity': 5,
            'can_parallel': False,
            'subtasks': []
        }

        # 检测编程相关
        code_keywords = ['编程', '代码', '程序', 'python', 'javascript', '函数', '类', '开发']
        if any(kw in description_lower for kw in code_keywords):
            result['type'] = 'code'
            result['complexity'] = 7

        # 检测文档相关
        doc_keywords = ['文档', 'word', 'excel', 'ppt', 'pdf', 'markdown', '排版']
        if any(kw in description_lower for kw in doc_keywords):
            result['type'] = 'document'
            result['complexity'] = 4

        # 检测复杂度
        if '重构' in description or '架构' in description or '系统' in description:
            result['complexity'] = 9

        return result

    @staticmethod
    def split_for_claude(description: str) -> list:
        """
        拆分任务给 Claude

        如果任务太大，拆成多个子任务
        """
        analysis = TaskSplitter.analyze_task(description)

        if analysis['complexity'] <= 5:
            # 简单任务不需要拆分
            return [{
                'title': '执行任务',
                'description': description,
                'type': analysis['type']
            }]

        # 复杂任务需要先做计划
        return [{
            'title': '1. 制定计划',
            'description': f'先分析任务并制定详细实施计划。\n\n任务描述: {description}',
            'type': 'planning'
        }, {
            'title': '2. 执行任务',
            'description': '按照计划执行。计划会在上一步完成后提供。',
            'type': analysis['type'],
            'depends_on': 0
        }]


# 使用示例
def example_usage():
    """示例：使用 ClaudeBridge 提交编程任务"""
    from task_manager import Task, TaskType, TaskStatus

    # 创建任务
    task = Task(
        id="test-001",
        type=TaskType.CODE,
        title="创建用户管理系统",
        description="用Python创建一个简单的用户管理系统，包含注册、登录、信息修改功能"
    )

    # 创建桥接
    bridge = ClaudeBridge()

    # 提交任务
    def on_progress(msg):
        print(f"[进度] {msg}")

    def on_complete(task):
        print(f"[完成] 状态: {task.status.value}")
        if task.result:
            print(f"[结果] {task.result[:500]}")

    success = bridge.submit_task(
        task=task,
        config=ClaudeTaskConfig(workdir='/tmp/test_project'),
        on_progress=on_progress,
        on_complete=on_complete
    )

    if success:
        print("任务已提交给 Claude，后台执行中...")
    else:
        print("任务提交失败")


if __name__ == '__main__':
    # 测试
    bridge = ClaudeBridge()
    print(f"Claude 可用: {bridge.check_claude_available()}")
