"""
AI Git Sync - 为AI设计的Git文件同步工具

功能：
1. 自动提交更改
2. 跨设备同步
3. 简单API
4. 支持远程仓库
"""
import os
import subprocess
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

class AIGitSync:
    """AI Git 同步工具"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.git_dir = self.repo_path / ".git"
        
    def _run(self, *args) -> tuple[str, str, int]:
        """执行git命令"""
        result = subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        return result.stdout, result.stderr, result.returncode
    
    def status(self) -> dict:
        """获取git状态"""
        stdout, _, _ = self._run("status", "--porcelain")
        files = []
        for line in stdout.strip().split("\n"):
            if line:
                status = line[:2]
                file = line[3:]
                files.append({"status": status, "file": file})
        return {"files": files, "count": len(files)}
    
    def add(self, patterns: List[str] = None) -> bool:
        """添加文件到暂存区"""
        if not patterns:
            patterns = ["."]
        
        for pattern in patterns:
            stdout, stderr, code = self._run("add", pattern)
            if code != 0:
                print(f"Error adding {pattern}: {stderr}")
                return False
        return True
    
    def commit(self, message: str = None) -> str:
        """提交更改"""
        if not message:
            # 自动生成提交信息
            status = self.status()
            files_changed = status["count"]
            message = f"AI sync: {files_changed} files changed ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        
        stdout, stderr, code = self._run("commit", "-m", message)
        if code != 0:
            if "nothing to commit" in stderr:
                return "No changes to commit"
            return f"Error: {stderr}"
        return stdout if stdout else "Committed successfully"
    
    def push(self, remote: str = "origin", branch: str = "main") -> str:
        """推送到远程"""
        stdout, stderr, code = self._run("push", remote, branch)
        if code != 0:
            return f"Error: {stderr}"
        return stdout if stdout else "Pushed successfully"
    
    def pull(self, remote: str = "origin", branch: str = "main") -> str:
        """拉取远程更改"""
        stdout, stderr, code = self._run("pull", remote, branch)
        if code != 0:
            return f"Error: {stderr}"
        return stdout if stdout else "Pulled successfully"
    
    def sync(self, message: str = None, auto_push: bool = True) -> dict:
        """完整同步流程"""
        result = {
            "status": self.status(),
            "commit": None,
            "push": None,
            "pull": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加所有更改
        self.add()
        
        # 提交
        commit_result = self.commit(message)
        result["commit"] = commit_result
        
        # 推送
        if auto_push and "Committed" in commit_result:
            result["push"] = self.push()
        
        # 拉取
        result["pull"] = self.pull()
        
        return result
    
    def log(self, n: int = 5) -> List[dict]:
        """获取提交历史"""
        stdout, _, _ = self._run("log", f"-{n}", "--oneline", "--format=%h|%s|%an|%at")
        commits = []
        for line in stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "author": parts[2],
                        "time": datetime.fromtimestamp(int(parts[3])).isoformat()
                    })
        return commits
    
    def diff(self, file: str = None) -> str:
        """查看更改"""
        if file:
            stdout, _, _ = self._run("diff", file)
        else:
            stdout, _, _ = self._run("diff")
        return stdout
    
    def get_file_hash(self, file_path: str) -> str:
        """获取文件hash"""
        path = self.repo_path / file_path
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()


# ============ CLI 界面 ============

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Git Sync Tool")
    parser.add_argument("command", choices=["status", "sync", "push", "pull", "log", "diff"])
    parser.add_argument("-m", "--message", help="Commit message")
    parser.add_argument("-p", "--push", action="store_true", default=True, help="Auto push")
    
    args = parser.parse_args()
    
    sync = AIGitSync()
    
    if args.command == "status":
        print(json.dumps(sync.status(), indent=2))
    elif args.command == "sync":
        result = sync.sync(args.message, args.push)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "push":
        print(sync.push())
    elif args.command == "pull":
        print(sync.pull())
    elif args.command == "log":
        print(json.dumps(sync.log(), indent=2, default=str))
    elif args.command == "diff":
        print(sync.diff())


if __name__ == "__main__":
    main()
