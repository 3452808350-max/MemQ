#!/usr/bin/env python3
"""
OpenClaw AI 自检 Agent
独立于 OpenClaw 的自我检查和自我修复系统
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List

class SelfCheckAgent:
    """AI 自检 Agent"""
    
    def __init__(self):
        self.checks = []
        self.results = {}
        self.report_path = "/home/kyj/.openclaw/workspace/self_check_report.json"
    
    def add_check(self, name: str, check_func, critical: bool = True):
        """添加检查项"""
        self.checks.append({
            'name': name,
            'func': check_func,
            'critical': critical
        })
    
    def check_filesystem(self) -> Dict:
        """检查文件系统"""
        result = {
            'name': '文件系统',
            'status': 'ok',
            'issues': []
        }
        
        # 检查 workspace 目录
        workspace = "/home/kyj/.openclaw/workspace"
        if not os.path.exists(workspace):
            result['status'] = 'error'
            result['issues'].append(f"Workspace 不存在：{workspace}")
            return result
        
        # 检查磁盘空间
        stat = os.statvfs(workspace)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if free_gb < 5:
            result['status'] = 'warning'
            result['issues'].append(f"磁盘空间不足：{free_gb:.1f}GB")
        
        # 检查关键文件
        critical_files = [
            "openclaw/core/memory/embedding.py",
            "openclaw/tests/test_benchmark.py",
            "dss_v4.py"
        ]
        
        for f in critical_files:
            path = os.path.join(workspace, f)
            if not os.path.exists(path):
                result['status'] = 'error'
                result['issues'].append(f"关键文件缺失：{f}")
        
        result['free_space_gb'] = free_gb
        return result
    
    def check_dependencies(self) -> Dict:
        """检查依赖"""
        result = {
            'name': '依赖检查',
            'status': 'ok',
            'issues': []
        }
        
        # 检查 Python 包
        required_packages = [
            'transformers',
            'torch',
            'modelscope',
            'pytest'
        ]
        
        for pkg in required_packages:
            try:
                __import__(pkg)
            except ImportError:
                result['status'] = 'error'
                result['issues'].append(f"缺少依赖：{pkg}")
        
        return result
    
    def check_tests(self) -> Dict:
        """检查测试"""
        result = {
            'name': '测试检查',
            'status': 'ok',
            'issues': []
        }
        
        # 检查测试文件
        test_files = [
            "openclaw/tests/test_benchmark.py",
            "openclaw/tests/test_load.py",
            "openclaw/tests/test_integration.py"
        ]
        
        for f in test_files:
            path = os.path.join("/home/kyj/.openclaw/workspace", f)
            if not os.path.exists(path):
                result['status'] = 'warning'
                result['issues'].append(f"测试文件缺失：{f}")
        
        return result
    
    def check_memory(self) -> Dict:
        """检查记忆系统"""
        result = {
            'name': '记忆系统',
            'status': 'ok',
            'issues': []
        }
        
        # 检查模型文件
        model_path = "/home/kyj/.cache/modelscope/hub/models/BAAI/bge-large-zh-v1.5"
        if not os.path.exists(model_path):
            result['status'] = 'error'
            result['issues'].append(f"模型文件缺失：{model_path}")
        
        return result
    
    def run_all_checks(self) -> Dict:
        """运行所有检查"""
        print("=" * 80)
        print("🔍 OpenClaw AI 自检")
        print("=" * 80)
        print("")
        
        # 添加检查项
        self.add_check('文件系统', self.check_filesystem)
        self.add_check('依赖检查', self.check_dependencies)
        self.add_check('测试检查', self.check_tests)
        self.add_check('记忆系统', self.check_memory)
        
        # 运行检查
        for check in self.checks:
            print(f"检查：{check['name']}...", end=" ")
            result = check['func']()
            self.results[check['name']] = result
            
            if result['status'] == 'ok':
                print("✅ OK")
            elif result['status'] == 'warning':
                print("⚠️  WARNING")
            else:
                print("❌ ERROR")
            
            for issue in result.get('issues', []):
                print(f"   - {issue}")
        
        print("")
        
        # 生成报告
        self.generate_report()
        
        return self.results
    
    def generate_report(self):
        """生成检查报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'summary': {
                'total': len(self.checks),
                'ok': sum(1 for r in self.results.values() if r['status'] == 'ok'),
                'warning': sum(1 for r in self.results.values() if r['status'] == 'warning'),
                'error': sum(1 for r in self.results.values() if r['status'] == 'error')
            }
        }
        
        # 保存报告
        with open(self.report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print("=" * 80)
        print("📊 检查报告")
        print("=" * 80)
        print(f"总检查项：{report['summary']['total']}")
        print(f"✅ 正常：{report['summary']['ok']}")
        print(f"⚠️  警告：{report['summary']['warning']}")
        print(f"❌ 错误：{report['summary']['error']}")
        print("")
        print(f"报告已保存：{self.report_path}")

# 运行自检
if __name__ == "__main__":
    agent = SelfCheckAgent()
    agent.run_all_checks()
