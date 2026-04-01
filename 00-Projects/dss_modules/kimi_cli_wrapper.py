"""
Kimi CLI 集成模块
用于在OpenClaw中调用Kimi CLI
"""
import subprocess
import json
import os
import time

class KimiCLI:
    """Kimi CLI 包装器"""
    
    def __init__(self, work_dir=None):
        self.work_dir = work_dir or os.getcwd()
        self.kimi_path = "/home/kyj/.local/bin/kimi"
        
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            result = subprocess.run(
                [self.kimi_path, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.work_dir
            )
            # 检查是否有登录提示
            return "LLM not set" not in result.stderr
        except:
            return False
    
    def run_command(self, prompt: str, timeout: int = 300) -> str:
        """
        运行Kimi CLI命令
        
        注意: 需要交互式终端登录
        """
        if not self.is_logged_in():
            return "错误: Kimi CLI未登录，请在终端运行 'kimi' 然后 '/login'"
        
        try:
            # 使用-c选项发送命令
            result = subprocess.run(
                [self.kimi_path, "-c", prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
                input="\n"  # 模拟回车
            )
            return result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return "错误: 命令超时"
        except Exception as e:
            return f"错误: {e}"
    
    def analyze_code(self, file_path: str) -> str:
        """分析代码文件"""
        prompt = f"请分析以下代码文件 {file_path}，给出优化建议："
        return self.run_command(prompt)
    
    def generate_code(self, task: str) -> str:
        """生成代码"""
        prompt = f"请用Python实现以下功能：{task}"
        return self.run_command(prompt)


# 使用示例
if __name__ == "__main__":
    kimi = KimiCLI("/home/kyj/.openclaw/workspace")
    
    if kimi.is_logged_in():
        print("Kimi CLI已登录")
        # result = kimi.generate_code("快速排序函数")
        # print(result)
    else:
        print("请先登录: kimi /login")
