#!/usr/bin/env python3
"""
Kimi CLI 控制器 - 让 OpenClaw 控制 Kimi CLI

使用方法:
    python3 kimi_controller.py "任务描述"
    python3 kimi_controller.py --project /path/to/project "任务描述"
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

class KimiController:
    def __init__(self, workdir=None, timeout=300):
        self.workdir = workdir or os.getcwd()
        self.timeout = timeout
        self.kimi_cmd = "kimi"
        
        # 验证 Kimi CLI 已安装
        if not self._check_kimi_installed():
            print("❌ Kimi CLI 未安装，请先运行：curl -LsSf https://code.kimi.com/install.sh | bash")
            sys.exit(1)
    
    def _check_kimi_installed(self):
        """检查 Kimi CLI 是否已安装"""
        try:
            result = subprocess.run(
                ["which", self.kimi_cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _log_task(self, task, status="pending"):
        """记录任务到日志"""
        log_file = Path(self.workdir) / "kimi_tasks.log"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "status": status,
            "workdir": self.workdir
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def execute(self, task, interactive=False):
        """
        执行 Kimi CLI 任务
        
        Args:
            task: 任务描述
            interactive: 是否交互式运行
        
        Returns:
            dict: 执行结果
        """
        print(f"🚀 开始执行 Kimi 任务...\n")
        print(f"📂 工作目录：{self.workdir}")
        print(f"📝 任务：{task}\n")
        print("=" * 60)
        
        self._log_task(task, "running")
        
        try:
            # 构建命令
            if interactive:
                cmd = [self.kimi_cmd]
            else:
                cmd = [self.kimi_cmd, task]
            
            # 执行
            result = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=False,  # 直接输出到终端
                text=True,
                timeout=self.timeout
            )
            
            # 记录结果
            if result.returncode == 0:
                self._log_task(task, "completed")
                print("\n✅ 任务完成！")
            else:
                self._log_task(task, "failed")
                print(f"\n❌ 任务失败，退出码：{result.returncode}")
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "task": task
            }
            
        except subprocess.TimeoutExpired:
            self._log_task(task, "timeout")
            print(f"\n⏰ 任务超时（{self.timeout}秒）")
            return {
                "success": False,
                "error": "timeout",
                "task": task
            }
        except Exception as e:
            self._log_task(task, "error")
            print(f"\n💥 执行错误：{e}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    def init_project(self):
        """初始化项目（生成 AGENTS.md）"""
        print("📋 初始化项目，生成 AGENTS.md...\n")
        return self.execute("/init", interactive=True)
    
    def check_status(self):
        """检查 Kimi CLI 状态"""
        try:
            result = subprocess.run(
                [self.kimi_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"✅ Kimi CLI 版本：{result.stdout.strip()}")
            return True
        except Exception as e:
            print(f"❌ 检查失败：{e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Kimi CLI 控制器 - OpenClaw 集成"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="任务描述"
    )
    parser.add_argument(
        "--project", "-p",
        default="/home/kyj/.openclaw/workspace",
        help="项目目录"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=300,
        help="超时时间（秒）"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互式运行"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="初始化项目"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="检查状态"
    )
    
    args = parser.parse_args()
    
    controller = KimiController(
        workdir=args.project,
        timeout=args.timeout
    )
    
    if args.status:
        controller.check_status()
    elif args.init:
        controller.init_project()
    elif args.task:
        controller.execute(args.task, interactive=args.interactive)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
