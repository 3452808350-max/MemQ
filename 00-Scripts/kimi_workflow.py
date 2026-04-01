#!/usr/bin/env python3
"""
Kimi 自动化工作流

工作流：Kimi 写代码 → 自动测试 → 保存记忆 → 发送通知

使用示例:
    python3 kimi_workflow.py "实现用户登录功能"
    python3 kimi_workflow.py --project /path/to/project "添加 API 端点"
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

class KimiWorkflow:
    """Kimi 自动化工作流控制器"""
    
    def __init__(self, workdir: str = None, timeout: int = 300):
        self.workdir = workdir or "/home/kyj/.openclaw/workspace"
        self.timeout = timeout
        self.log_file = Path(self.workdir) / "kimi_workflow.log"
        self.memory_file = Path(self.workdir) / "memory" / "workflow_memories.json"
        
    def log(self, stage: str, message: str, data: Dict = None):
        """记录工作流日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "message": message,
            "data": data or {}
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")
        
        print(f"[{stage}] {message}")
    
    def step1_kimi_code(self, task: str) -> bool:
        """步骤 1: Kimi 编写代码"""
        self.log("STEP1", f"🚀 Kimi 开始编写代码：{task}")
        
        try:
            cmd = ["kimi", task]
            result = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=False,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                self.log("STEP1", "✅ Kimi 完成代码编写", {"success": True})
                return True
            else:
                self.log("STEP1", "❌ Kimi 代码编写失败", {"success": False, "error": result.stderr})
                return False
                
        except subprocess.TimeoutExpired:
            self.log("STEP1", "⏰ Kimi 代码编写超时", {"success": False})
            return False
        except Exception as e:
            self.log("STEP1", f"💥 Kimi 代码编写异常：{e}", {"success": False})
            return False
    
    def step2_auto_test(self, test_command: str = None) -> bool:
        """步骤 2: 自动测试"""
        self.log("STEP2", "🧪 开始自动测试")
        
        # 自动检测测试命令
        if not test_command:
            if Path(self.workdir / "pytest.ini").exists() or Path(self.workdir / "tests").exists():
                test_command = "pytest -v"
            elif Path(self.workdir / "package.json").exists():
                test_command = "npm test"
            elif Path(self.workdir / "Makefile").exists():
                test_command = "make test"
            else:
                self.log("STEP2", "⚠️  未找到测试配置，跳过测试", {"skipped": True})
                return True
        
        try:
            self.log("STEP2", f"执行测试命令：{test_command}")
            
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=self.workdir,
                capture_output=False,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self.log("STEP2", "✅ 测试通过", {"success": True})
                return True
            else:
                self.log("STEP2", "❌ 测试失败", {"success": False, "error": result.stderr})
                return False
                
        except subprocess.TimeoutExpired:
            self.log("STEP2", "⏰ 测试超时", {"success": False})
            return False
        except Exception as e:
            self.log("STEP2", f"💥 测试异常：{e}", {"success": False})
            return False
    
    def step3_save_memory(self, task: str, result: str) -> bool:
        """步骤 3: 保存记忆到 LanceDB"""
        self.log("STEP3", "🧠 保存记忆到 LanceDB")
        
        try:
            # 准备记忆内容
            memory_text = f"Kimi 完成了任务：{task}\n结果：{result}"
            
            # 使用 OpenClaw memory_store 工具
            memory_entry = {
                "text": memory_text,
                "category": "fact",
                "scope": "global",
                "importance": 0.7,
                "tags": ["kimi", "workflow", "code-task"],
                "metadata": {
                    "task": task,
                    "timestamp": datetime.now().isoformat(),
                    "workflow": "kimi-auto"
                }
            }
            
            # 保存到本地记忆文件（作为 LanceDB 的补充）
            with open(self.memory_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(memory_entry, ensure_ascii=False) + "\n")
            
            self.log("STEP3", "✅ 记忆已保存", {
                "success": True,
                "text": memory_text[:100]
            })
            
            return True
            
        except Exception as e:
            self.log("STEP3", f"❌ 保存记忆失败：{e}", {"success": False})
            return False
    
    def step4_send_notification(self, task: str, success: bool) -> bool:
        """步骤 4: 发送 Telegram 通知"""
        self.log("STEP4", "📱 发送通知")
        
        try:
            status = "✅ 成功" if success else "❌ 失败"
            message = f"""
🤖 Kimi 工作流完成

📝 任务：{task}
📊 状态：{status}
⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            # 使用 OpenClaw message 工具发送
            notification_file = Path(self.workdir) / "pending_notifications.json"
            notification = {
                "channel": "telegram",
                "message": message.strip(),
                "timestamp": datetime.now().isoformat()
            }
            
            with open(notification_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(notification, ensure_ascii=False) + "\n")
            
            self.log("STEP4", "✅ 通知已加入队列", {"success": True})
            return True
            
        except Exception as e:
            self.log("STEP4", f"❌ 发送通知失败：{e}", {"success": False})
            return False
    
    def run(self, task: str, skip_test: bool = False, test_command: str = None) -> bool:
        """
        运行完整工作流
        
        工作流:
        1. Kimi 编写代码
        2. 自动测试（可选）
        3. 保存记忆
        4. 发送通知
        """
        print("=" * 60)
        print("🚀 Kimi 自动化工作流")
        print("=" * 60)
        print(f"📂 工作目录：{self.workdir}")
        print(f"📝 任务：{task}")
        print("=" * 60)
        print()
        
        self.log("WORKFLOW", f"开始工作流：{task}")
        
        # 步骤 1: Kimi 编写代码
        step1_success = self.step1_kimi_code(task)
        print()
        
        # 步骤 2: 自动测试（可选）
        if step1_success and not skip_test:
            step2_success = self.step2_auto_test(test_command)
        else:
            step2_success = skip_test or step1_success
            self.log("STEP2", "⏭️  跳过测试")
        print()
        
        # 步骤 3: 保存记忆
        result_summary = "成功完成" if step1_success else "失败"
        step3_success = self.step3_save_memory(task, result_summary)
        print()
        
        # 步骤 4: 发送通知
        overall_success = step1_success and step2_success
        step4_success = self.step4_send_notification(task, overall_success)
        print()
        
        # 总结
        print("=" * 60)
        if overall_success:
            print("🎉 工作流成功完成！")
        else:
            print("⚠️  工作流部分失败，请检查日志")
        print("=" * 60)
        
        self.log("WORKFLOW", f"工作流完成：{'成功' if overall_success else '失败'}")
        
        return overall_success


def main():
    parser = argparse.ArgumentParser(
        description="Kimi 自动化工作流"
    )
    parser.add_argument(
        "task",
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
        help="Kimi 超时时间（秒）"
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="跳过自动测试"
    )
    parser.add_argument(
        "--test-command",
        help="自定义测试命令"
    )
    
    args = parser.parse_args()
    
    workflow = KimiWorkflow(
        workdir=args.project,
        timeout=args.timeout
    )
    
    success = workflow.run(
        task=args.task,
        skip_test=args.skip_test,
        test_command=args.test_command
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
