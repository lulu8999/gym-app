#!/usr/bin/env python3
"""
Hermes Compress - RTK风格的输出压缩插件
自动识别命令类型，压缩输出60-90%，保留关键信息

用法：
  # 命令行模式
  git status | python hermes-compress.py
  
  # Python模块模式
  from hermes_compress import compress
  result = compress(git_status_output, cmd_type="git-status")
"""

import sys
import os
import re
import argparse
from typing import List, Tuple, Optional

__version__ = "1.0.0"
__all__ = ["compress", "OutputCompressor"]

class OutputCompressor:
    """输出压缩引擎"""
    
    def __init__(self, max_line_length: int = 200, max_lines: int = 500):
        self.max_line_length = max_line_length
        self.max_lines = max_lines
    
    def compress(self, text: str, cmd_type: str = None) -> str:
        """压缩文本输出
        
        Args:
            text: 要压缩的文本
            cmd_type: 命令类型，可选值：
                - git-status, git-diff, git-log
                - docker, docker-images
                - grep, find, ls, env, log
                - generic (默认，自动检测)
        
        Returns:
            压缩后的文本
        """
        if not text or not text.strip():
            return text
        
        # 如果没有指定命令类型，自动检测
        if not cmd_type:
            cmd_type = self._detect_command_type(text)
        
        # 根据命令类型选择压缩策略
        compressors = {
            "git-status": self._compress_git_status,
            "git-diff": self._compress_git_diff,
            "git-log": self._compress_git_log,
            "docker": self._compress_docker,
            "docker-images": self._compress_docker_images,
            "grep": self._compress_grep,
            "find": self._compress_find,
            "ls": self._compress_ls,
            "env": self._compress_env,
            "log": self._compress_log,
        }
        
        compressor = compressors.get(cmd_type, self._compress_generic)
        return compressor(text)
    
    def _detect_command_type(self, text: str) -> str:
        """自动检测命令类型"""
        # 检测git status
        if "On branch" in text or "Changes to be committed" in text:
            return "git-status"
        
        # 检测git diff
        if text.startswith("diff --git") or ("@@" in text and "---" in text and "+++" in text):
            return "git-diff"
        
        # 检测git log
        if re.search(r'^[a-f0-9]{7,40}\s', text, re.MULTILINE):
            return "git-log"
        
        # 检测docker ps
        if "CONTAINER ID" in text and "IMAGE" in text:
            return "docker"
        
        # 检测docker images
        if "REPOSITORY" in text and "TAG" in text and "IMAGE ID" in text:
            return "docker-images"
        
        # 检测grep（文件:行号:内容模式）
        if re.search(r'^[^:]+:\d+:', text, re.MULTILINE):
            return "grep"
        
        # 检测find（路径模式）
        if re.search(r'^\./', text, re.MULTILINE) or re.search(r'^/', text, re.MULTILINE):
            return "find"
        
        # 检测ls（权限模式）
        if re.search(r'^[d-][rwx-]{9}', text, re.MULTILINE):
            return "ls"
        
        # 检测env（KEY=value模式）
        if re.search(r'^[A-Z_]+=', text, re.MULTILINE):
            return "env"
        
        # 检测log（时间戳模式）
        if re.search(r'^\d{4}-\d{2}-\d{2}', text, re.MULTILINE):
            return "log"
        
        return "generic"
    
    def _compress_git_status(self, text: str) -> str:
        """压缩git status输出"""
        lines = text.split('\n')
        result = []
        
        branch_info = ""
        staged_files = []
        unstaged_files = []
        untracked_files = []
        
        in_staged = False
        in_unstaged = False
        in_untracked = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # 提取分支信息
            if stripped.startswith("On branch"):
                branch_info = stripped
                continue
            
            # 提取ahead/behind信息
            if "Your branch is" in stripped:
                branch_info += " " + stripped
                continue
            
            # 检测区域
            if "Changes to be committed" in stripped:
                in_staged = True
                in_unstaged = False
                in_untracked = False
                continue
            elif "Changes not staged for commit" in stripped:
                in_staged = False
                in_unstaged = True
                in_untracked = False
                continue
            elif "Untracked files" in stripped:
                in_staged = False
                in_unstaged = False
                in_untracked = True
                continue
            
            # 提取文件
            if stripped.startswith("new file:") or stripped.startswith("modified:") or stripped.startswith("deleted:"):
                file_name = stripped.split(":")[-1].strip()
                if in_staged:
                    staged_files.append(file_name)
                elif in_unstaged:
                    unstaged_files.append(file_name)
                continue
            
            # 提取untracked文件
            if in_untracked and not stripped.startswith("("):
                file_name = stripped
                untracked_files.append(file_name)
                continue
        
        # 构建压缩输出
        if branch_info:
            result.append(branch_info)
        
        if staged_files:
            result.append(f"Staged ({len(staged_files)}): {', '.join(staged_files[:5])}")
            if len(staged_files) > 5:
                result.append(f"  ... and {len(staged_files) - 5} more")
        
        if unstaged_files:
            result.append(f"Unstaged ({len(unstaged_files)}): {', '.join(unstaged_files[:5])}")
            if len(unstaged_files) > 5:
                result.append(f"  ... and {len(unstaged_files) - 5} more")
        
        if untracked_files:
            result.append(f"Untracked ({len(untracked_files)}): {', '.join(untracked_files[:10])}")
            if len(untracked_files) > 10:
                result.append(f"  ... and {len(untracked_files) - 10} more")
        
        return '\n'.join(result)
    
    def _compress_git_diff(self, text: str) -> str:
        """压缩git diff输出"""
        lines = text.split('\n')
        result = []
        
        current_file = ""
        insertions = 0
        deletions = 0
        files = []
        
        for line in lines:
            # 提取文件名
            if line.startswith("diff --git"):
                if current_file:
                    files.append((current_file, insertions, deletions))
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[3][2:]  # 去掉 b/ 前缀
                insertions = 0
                deletions = 0
                continue
            
            # 统计insertions/deletions
            if line.startswith("+") and not line.startswith("+++"):
                insertions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
        
        # 添加最后一个文件
        if current_file:
            files.append((current_file, insertions, deletions))
        
        # 构建输出
        if files:
            total_insertions = sum(i for _, i, _ in files)
            total_deletions = sum(d for _, _, d in files)
            result.append(f"{len(files)} files changed, +{total_insertions} -{total_deletions}")
            for file_name, ins, dels in files:
                result.append(f"{file_name} | +{ins} -{dels}")
        
        return '\n'.join(result)
    
    def _compress_git_log(self, text: str) -> str:
        """压缩git log输出"""
        lines = text.split('\n')
        result = []
        
        for line in lines[:20]:  # 只显示最近20条
            if not line.strip():
                continue
            # 简化hash，只保留前7位
            if re.match(r'^[a-f0-9]{40}', line):
                line = line[:7] + line[40:]
            result.append(line)
        
        if len(lines) > 20:
            result.append(f"... {len(lines) - 20} more commits")
        
        return '\n'.join(result)
    
    def _compress_docker(self, text: str) -> str:
        """压缩docker ps输出"""
        lines = text.split('\n')
        result = []
        
        # 跳过表头
        data_lines = [l for l in lines if l.strip() and not l.startswith("CONTAINER ID")]
        
        if not data_lines:
            return "No running containers"
        
        for line in data_lines:
            parts = line.split()
            if len(parts) >= 7:
                container_id = parts[0][:12]  # 短ID
                image = parts[1]
                status = ' '.join(parts[4:6])  # Up X hours
                name = parts[-1]
                result.append(f"{name} | {image} | {status}")
        
        return '\n'.join(result)
    
    def _compress_docker_images(self, text: str) -> str:
        """压缩docker images输出"""
        lines = text.split('\n')
        result = []
        
        # 跳过表头
        data_lines = [l for l in lines if l.strip() and not l.startswith("REPOSITORY")]
        
        for line in data_lines:
            parts = line.split()
            if len(parts) >= 5:
                repo = parts[0]
                tag = parts[1]
                size = parts[-1]
                result.append(f"{repo}:{tag} | {size}")
        
        return '\n'.join(result)
    
    def _compress_grep(self, text: str) -> str:
        """压缩grep输出"""
        lines = text.split('\n')
        result = []
        
        # 按文件分组
        file_groups = {}
        for line in lines:
            if not line.strip():
                continue
            
            # 提取文件名和行号
            match = re.match(r'^([^:]+):(\d+):', line)
            if match:
                file_name = match.group(1)
                line_number = match.group(2)
                content = line[match.end():].strip()
                
                if file_name not in file_groups:
                    file_groups[file_name] = []
                file_groups[file_name].append(f"{line_number}: {content[:80]}")
        
        # 构建输出
        for file_name, matches in file_groups.items():
            result.append(f"{file_name} ({len(matches)} matches):")
            for match in matches[:3]:  # 只显示前3个匹配
                result.append(f"  {match}")
            if len(matches) > 3:
                result.append(f"  ... and {len(matches) - 3} more")
        
        return '\n'.join(result)
    
    def _compress_find(self, text: str) -> str:
        """压缩find输出"""
        lines = text.split('\n')
        result = []
        
        # 按目录分组
        dir_groups = {}
        for line in lines:
            if not line.strip():
                continue
            
            # 提取目录和文件名
            if '/' in line:
                parts = line.rsplit('/', 1)
                if len(parts) == 2:
                    dir_name = parts[0] if parts[0] else '.'
                    file_name = parts[1]
                    
                    if dir_name not in dir_groups:
                        dir_groups[dir_name] = []
                    dir_groups[dir_name].append(file_name)
        
        # 构建输出
        for dir_name, files in dir_groups.items():
            result.append(f"{dir_name}/ ({len(files)} files):")
            for file in files[:5]:  # 只显示前5个文件
                result.append(f"  {file}")
            if len(files) > 5:
                result.append(f"  ... and {len(files) - 5} more")
        
        return '\n'.join(result)
    
    def _compress_ls(self, text: str) -> str:
        """压缩ls输出"""
        lines = text.split('\n')
        result = []
        
        # 如果是ls -l格式
        if re.search(r'^[d-][rwx-]{9}', text, re.MULTILINE):
            for line in lines:
                if not line.strip():
                    continue
                
                # 提取文件名
                parts = line.split()
                if len(parts) >= 9:
                    file_name = parts[8]
                    file_type = "d" if parts[0][0] == 'd' else "f"
                    result.append(f"{file_type} {file_name}")
        else:
            # 普通ls，直接返回文件名
            for line in lines:
                if line.strip():
                    result.append(line.strip())
        
        return '\n'.join(result)
    
    def _compress_env(self, text: str) -> str:
        """压缩env输出"""
        lines = text.split('\n')
        result = []
        
        # 按类型分组
        groups = {
            "PATH": [],
            "Language/Runtime": [],
            "Cloud/Services": [],
            "Tools": [],
            "Other": []
        }
        
        for line in lines:
            if not line.strip():
                continue
            
            # 提取KEY和VALUE
            match = re.match(r'^([A-Z_]+)=(.*)', line)
            if match:
                key = match.group(1)
                value = match.group(2)
                
                # 过滤敏感变量
                if any(sensitive in key.lower() for sensitive in ["token", "key", "secret", "password", "auth"]):
                    value = "***"
                
                # 截断长值
                if len(value) > 100:
                    value = value[:100] + "..."
                
                # 按类型分组
                if key == "PATH":
                    groups["PATH"].append(f"PATH ({len(value.split(':'))} entries)")
                elif any(keyword in key.lower() for keyword in ["lang", "locale", "python", "node", "npm"]):
                    groups["Language/Runtime"].append(f"{key}={value}")
                elif any(keyword in key.lower() for keyword in ["docker", "aws", "cloud", "hermes"]):
                    groups["Cloud/Services"].append(f"{key}={value}")
                elif any(keyword in key.lower() for keyword in ["terminal", "shell", "editor"]):
                    groups["Tools"].append(f"{key}={value}")
                else:
                    groups["Other"].append(f"{key}={value}")
        
        # 构建输出
        for group_name, items in groups.items():
            if items:
                result.append(f"{group_name}:")
                for item in items:
                    result.append(f"  {item}")
        
        return '\n'.join(result)
    
    def _compress_log(self, text: str) -> str:
        """压缩日志输出"""
        lines = text.split('\n')
        result = []
        
        # 统计日志级别
        level_counts = {"ERROR": 0, "WARN": 0, "INFO": 0, "DEBUG": 0}
        
        # 去重连续相同行
        prev_line = None
        duplicate_count = 0
        duplicate_start = None
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # 统计日志级别
            for level in level_counts:
                if level in line:
                    level_counts[level] += 1
            
            # 去重连续相同行
            if line == prev_line:
                duplicate_count += 1
                continue
            
            if duplicate_count > 0:
                result.append(f"  ... repeated {duplicate_count} times")
                duplicate_count = 0
            
            prev_line = line
            result.append(line)
        
        # 添加统计
        stats = [f"{level}: {count}" for level, count in level_counts.items() if count > 0]
        if stats:
            result.insert(0, "Log levels: " + ", ".join(stats))
        
        # 限制行数
        if len(result) > self.max_lines:
            result = result[:self.max_lines] + [f"... {len(lines) - self.max_lines} more lines"]
        
        return '\n'.join(result)
    
    def _compress_generic(self, text: str) -> str:
        """通用压缩"""
        lines = text.split('\n')
        result = []
        
        # 截断长行
        for line in lines:
            if len(line) > self.max_line_length:
                line = line[:self.max_line_length] + "..."
            result.append(line)
        
        # 去掉重复空行
        prev_line = None
        cleaned = []
        for line in result:
            if line.strip() == "" and prev_line == "":
                continue
            cleaned.append(line)
            prev_line = line.strip()
        
        # 限制行数
        if len(cleaned) > self.max_lines:
            cleaned = cleaned[:self.max_lines] + [f"... {len(lines) - self.max_lines} more lines"]
        
        return '\n'.join(cleaned)

# 便捷函数
def compress(text: str, cmd_type: str = None, max_line_length: int = 200, max_lines: int = 500) -> str:
    """压缩文本输出
    
    Args:
        text: 要压缩的文本
        cmd_type: 命令类型（git-status, git-diff, docker, grep, find, ls, env, log）
        max_line_length: 最大行长度
        max_lines: 最大行数
    
    Returns:
        压缩后的文本
    
    Example:
        >>> from hermes_compress import compress
        >>> result = compress(git_status_output, cmd_type="git-status")
    """
    compressor = OutputCompressor(max_line_length, max_lines)
    return compressor.compress(text, cmd_type)

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Hermes Compress - RTK风格的输出压缩插件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  git status | python hermes-compress.py
  python hermes-compress.py --input /tmp/output.txt
  python hermes-compress.py --type git-status --stats
        """
    )
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--type", "-t", help="命令类型", 
                       choices=["git-status", "git-diff", "git-log", "docker", "docker-images", 
                               "grep", "find", "ls", "env", "log", "generic"])
    parser.add_argument("--max-line-length", "-l", type=int, default=200, help="最大行长度")
    parser.add_argument("--max-lines", "-m", type=int, default=500, help="最大行数")
    parser.add_argument("--stats", "-s", action="store_true", help="显示压缩统计")
    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")
    
    args = parser.parse_args()
    
    # 读取输入
    if args.input:
        try:
            with open(args.input, 'r') as f:
                input_text = f.read()
        except FileNotFoundError:
            print(f"错误: 文件 '{args.input}' 不存在", file=sys.stderr)
            sys.exit(1)
    else:
        # 从stdin读取
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        input_text = sys.stdin.read()
    
    # 压缩输出
    compressed_text = compress(input_text, args.type, args.max_line_length, args.max_lines)
    
    # 输出结果
    print(compressed_text)
    
    # 显示统计
    if args.stats:
        original_lines = len(input_text.split('\n'))
        compressed_lines = len(compressed_text.split('\n'))
        reduction = (1 - compressed_lines / original_lines) * 100 if original_lines > 0 else 0
        print(f"\n压缩统计:", file=sys.stderr)
        print(f"  原始: {original_lines} 行", file=sys.stderr)
        print(f"  压缩后: {compressed_lines} 行", file=sys.stderr)
        print(f"  压缩率: {reduction:.1f}%", file=sys.stderr)

if __name__ == "__main__":
    main()