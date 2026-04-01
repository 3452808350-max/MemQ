#!/usr/bin/env python3
"""
测试 Kimi CLI 集成
"""

import subprocess
import sys

def test_kimi_status():
    """测试 Kimi CLI 状态"""
    print("🧪 测试 1: 检查 Kimi CLI 状态...\n")
    
    result = subprocess.run(
        ["kimi", "--version"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ Kimi CLI 版本：{result.stdout.strip()}\n")
        return True
    else:
        print(f"❌ Kimi CLI 未正常工作\n")
        return False

def test_kimi_simple_task():
    """测试简单任务"""
    print("🧪 测试 2: 执行简单任务...\n")
    
    task = "写一个 Python 函数，计算两个数的和"
    
    result = subprocess.run(
        ["kimi", task],
        capture_output=True,
        text=True,
        timeout=60,
        cwd="/home/kyj/.openclaw/workspace"
    )
    
    if result.returncode == 0:
        print("✅ 任务执行成功\n")
        print("输出预览:")
        print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        return True
    else:
        print(f"❌ 任务执行失败：{result.stderr}\n")
        return False

def test_controller_status():
    """测试控制器"""
    print("🧪 测试 3: 检查控制器...\n")
    
    result = subprocess.run(
        ["python3", "kimi_controller.py", "--status"],
        capture_output=True,
        text=True,
        cwd="/home/kyj/.openclaw/workspace"
    )
    
    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(f"❌ 控制器异常：{result.stderr}\n")
        return False

def main():
    print("=" * 60)
    print("🚀 OpenClaw + Kimi CLI 集成测试")
    print("=" * 60)
    print()
    
    tests = [
        ("Kimi CLI 状态", test_kimi_status),
        ("控制器状态", test_controller_status),
        # ("简单任务", test_kimi_simple_task),  # 需要 API 配额，可选
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {name} 测试异常：{e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"\n📊 测试结果：{passed} 通过，{failed} 失败\n")
    
    if failed == 0:
        print("🎉 所有测试通过！Kimi CLI 已准备好与 OpenClaw 集成！\n")
        return 0
    else:
        print("⚠️  部分测试失败，请检查配置\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
