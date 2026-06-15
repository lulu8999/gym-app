#!/usr/bin/env python3
"""
Hermes Compress - RTK风格的输出压缩插件
自动识别命令类型，压缩输出60-90%，保留关键信息
"""

import sys
import re
import argparse
from typing import List, Tuple

class OutputCompressor:
    """输出压缩引擎"""
    
    def __init__(self, max_line_length: int = 200, max_lines: int = 500):
        self.max_line_length = max_line_length
        self.max_lines = max_lines
    
    def compress(self, text: str, cmd_type: str = None) -> str:
        """压缩文本输出"""
        if not text.strip():
            return text
        
        # 如果没有指定命令类型，自动检测
        if not cmd_type:
            cmd_type = self._detect_command_type(text)
        
        # 根据命令类型选择压缩策略
        if cmd_type == "git-status":
            return self._compress_git_status(text)
        elif cmd_type == "git-diff":
            return self._compress_git_diff(text)
        elif cmd_type == "docker":
            return self._compress_docker(text)
        elif cmd_type == "grep":
            return self._compress_grep(text)
        elif cmd_type == "find":
            return self._compress_find(text)
        elif cmd_type == "ls":
            return self._compress_ls(text)
        elif cmd_type == "env":
            return self._compress_env(text)
        elif cmd_type == "log":
            return self._compress_log(text)
        else:
            return self._compress_generic(text)
    
    def _detect_command_type(self, text: str) -> str:
        """自动检测命令类型"""
        # 检测git status
        if "On branch" in text or "Changes to be committed" in text:
            return "git-status"
        
        # 检测git diff
        if text.startswith("diff --git") or "@@" in text:
            return "git-diff"
        
        # 检测docker
        if "CONTAINER ID" in text or "IMAGE" in text:
            return "docker"
        
        # 检测grep（文件:行号:内容模式）
        if re.search(r'^[^:]+:\d+:', text, re.MULTILINE):
            return "grep"
        
        # 检测find（路径模式）
        if re.search(r'^\./', text, re.MULTILINE):
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
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 提取分支信息
            if line.startswith("On branch"):
                branch_info = line
                continue
            
            # 提取ahead/behind信息
            if "Your branch is" in line:
                branch_info += " " + line
                continue
            
            # 提取staged文件
            if line.startswith("new file:") or line.startswith("modified:"):
                file_name = line.split(":")[-1].strip()
                if "Changes to be committed" in text:
                    staged_files.append(file_name)
                else:
                    unstaged_files.append(file_name)
                continue
            
            # 提取unstaged文件
            if line.startswith("modified:") or line.startswith("deleted:"):
                file_name = line.split(":")[-1].strip()
                unstaged_files.append(file_name)
                continue
            
            # 提取untracked文件
            if line.startswith("??"):
                file_name = line.split()[-1] if len(line.split()) > 1 else line[3:]
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
        
        for line in lines:
            # 提取文件名
            if line.startswith("diff --git"):
                if current_file:
                    result.append(f"{current_file} | +{insertions} -{deletions}")
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
            result.append(f"{current_file} | +{insertions} -{deletions}")
        
        # 添加统计
        total_insertions = sum(int(r.split('+')[1].split(' ')[0]) for r in result if '|' in r)
        total_deletions = sum(int(r.split('-')[-1]) for r in result if '|' in r)
        result.insert(0, f"{len([r for r in result if '|' in r])} files changed, +{total_insertions} -{total_deletions}")
        
        return '\n'.join(result)
    
    def _compress_docker(self, text: str) -> str:
        """压缩docker输出"""
        lines = text.split('\n')
        result = []
        
        # 如果是docker ps
        if "CONTAINER ID" in text:
            for line in lines[1:]:  # 跳过表头
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 7:
                    container_id = parts[0][:12]  # 短ID
                    image = parts[1]
                    status = parts[4]
                    ports = parts[6] if len(parts) > 6 else ""
                    name = parts[-1]
                    result.append(f"{name} | {image} | {status} | {ports}")
        
        # 如果是docker images
        elif "REPOSITORY" in text:
            for line in lines[1:]:  # 跳过表头
                if not line.strip():
                    continue
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
        
        for line in lines:
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
        for line in result:
            if line.strip() == "" and prev_line == "":
                continue
            prev_line = line
        
        # 限制行数
        if len(result) > self.max_lines:
            result = result[:self.max_lines] + [f"... {len(lines) - self.max_lines} more lines"]
        
        return '\n'.join(result)

def main():
    parser = argparse.ArgumentParser(description="Hermes Compress - RTK风格的输出压缩插件")
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--type", "-t", help="命令类型", 
                       choices=["git-status", "git-diff", "docker", "grep", "find", "ls", "env", "log", "generic"])
    parser.add_argument("--max-line-length", "-l", type=int, default=200, help="最大行长度")
    parser.add_argument("--max-lines", "-m", type=int, default=500, help="最大行数")
    parser.add_argument("--stats", "-s", action="store_true", help="显示压缩统计")
    
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
            print("用法: echo 'content' | python hermes-compress.py", file=sys.stderr)
            print("或: python hermes-compress.py --input /tmp/output.txt", file=sys.stderr)
            sys.exit(1)
        input_text = sys.stdin.read()
    
    # 压缩输出
    compressor = OutputCompressor(args.max_line_length, args.max_lines)
    compressed_text = compressor.compress(input_text, args.type)
    
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