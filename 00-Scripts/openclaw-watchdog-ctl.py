#!/usr/bin/env python3
"""
OpenClaw Watchdog 控制器

用法:
    python3 openclaw-watchdog-ctl.py status      # 查看状态
    python3 openclaw-watchdog-ctl.py start       # 启动 v2
    python3 openclaw-watchdog-ctl.py stop        # 停止
    python3 openclaw-watchdog-ctl.py restart     # 重启
    python3 openclaw-watchdog-ctl.py logs        # 查看日志
    python3 openclaw-watchdog-ctl.py analyze     # 分析故障趋势
    python3 openclaw-watchdog-ctl.py upgrade     # 升级到 v2
    python3 openclaw-watchdog-ctl.py rollback    # 回滚到 v1
"""

import os
import sys
import json
import subprocess
import signal
from pathlib import Path
from datetime import datetime, timedelta

WORKSPACE = Path.home() / ".openclaw" / "workspace"
PID_FILE = WORKSPACE / "watchdog.pid"
V1_SCRIPT = WORKSPACE / "openclaw_watchdog.py"
V2_SCRIPT = WORKSPACE / "openclaw_watchdog_v2.py"

def get_pid() -> int:
    """获取 watchdog PID"""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except:
            pass
    return 0

def save_pid(pid: int):
    """保存 PID"""
    PID_FILE.write_text(str(pid))

def is_running(pid: int) -> bool:
    """检查进程是否在运行"""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except:
        return False

def get_version() -> str:
    """获取当前运行的版本"""
    pid = get_pid()
    if not is_running(pid):
        return "stopped"
    
    try:
        # 检查进程命令行
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "args="],
            capture_output=True, text=True
        )
        cmdline = result.stdout.strip()
        if "v2" in cmdline:
            return "v2"
        return "v1"
    except:
        return "unknown"

def cmd_status():
    """查看状态"""
    pid = get_pid()
    version = get_version()
    
    print("=" * 50)
    print("OpenClaw Watchdog 状态")
    print("=" * 50)
    
    if version == "stopped":
        print("状态: 🔴 已停止")
    else:
        print(f"状态: 🟢 运行中")
        print(f"版本: {version.upper()}")
        print(f"PID: {pid}")
        
        # 显示运行时间
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "etime="],
                capture_output=True, text=True
            )
            print(f"运行时间: {result.stdout.strip()}")
        except:
            pass
    
    # 显示状态文件
    state_file = Path.home() / ".openclaw" / f"watchdog_{version}_state.json"
    if state_file.exists() and version != "stopped":
        try:
            with open(state_file) as f:
                state = json.load(f)
            print(f"\n统计信息:")
            print(f"  连续失败: {state.get('consecutive_failures', 0)}")
            print(f"  总重启次数: {state.get('total_restarts', 0)}")
            if state.get('incidents'):
                print(f"  最近故障: {len(state['incidents'])} 次")
        except:
            pass
    
    # 显示日志路径
    print(f"\n日志文件:")
    if version == "v2":
        print(f"  {Path.home() / '.openclaw' / 'watchdog_v2.log'}")
    else:
        print(f"  {Path.home() / '.openclaw' / 'watchdog.log'}")
    
    print("=" * 50)

def cmd_start(version: str = "v2"):
    """启动 watchdog"""
    current = get_version()
    if current != "stopped":
        print(f"Watchdog {current.upper()} 已在运行 (PID: {get_pid()})")
        return
    
    script = V2_SCRIPT if version == "v2" else V1_SCRIPT
    if not script.exists():
        print(f"错误: 脚本不存在 {script}")
        return
    
    print(f"启动 Watchdog {version.upper()}...")
    
    # 后台启动
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    save_pid(proc.pid)
    print(f"已启动，PID: {proc.pid}")
    
    # 等待确认
    import time
    time.sleep(1)
    if is_running(proc.pid):
        print("✅ 启动成功")
    else:
        print("❌ 启动可能失败，请检查日志")

def cmd_stop():
    """停止 watchdog"""
    pid = get_pid()
    version = get_version()
    
    if version == "stopped":
        print("Watchdog 未在运行")
        return
    
    print(f"停止 Watchdog {version.upper()} (PID: {pid})...")
    
    try:
        os.kill(pid, signal.SIGTERM)
        
        # 等待停止
        import time
        for _ in range(10):
            if not is_running(pid):
                break
            time.sleep(0.5)
        
        if is_running(pid):
            print("强制终止...")
            os.kill(pid, signal.SIGKILL)
        
        PID_FILE.unlink(missing_ok=True)
        print("✅ 已停止")
    except Exception as e:
        print(f"停止失败: {e}")

def cmd_restart(version: str = "v2"):
    """重启 watchdog"""
    cmd_stop()
    import time
    time.sleep(1)
    cmd_start(version)

def cmd_logs(lines: int = 50, version: str = None):
    """查看日志"""
    if version is None:
        version = get_version()
    
    if version == "stopped":
        version = "v2"  # 默认查看 v2 日志
    
    log_file = Path.home() / ".openclaw" / (f"watchdog_{version}.log" if version == "v2" else "watchdog.log")
    
    if not log_file.exists():
        print(f"日志文件不存在: {log_file}")
        return
    
    print(f"\n=== {log_file} (最近 {lines} 行) ===\n")
    subprocess.run(["tail", "-n", str(lines), str(log_file)])

def cmd_analyze():
    """分析故障趋势"""
    print("=" * 60)
    print("OpenClaw Watchdog 故障趋势分析")
    print("=" * 60)
    
    # 分析 v2 状态文件
    state_file = Path.home() / ".openclaw" / "watchdog_v2_state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
            
            incidents = state.get('incidents', [])
            if incidents:
                print(f"\n📊 最近 {len(incidents)} 次故障事件:")
                print("-" * 60)
                
                for inc in incidents[-5:]:
                    duration = inc.get('duration_seconds', 0)
                    print(f"\nID: {inc['id']}")
                    print(f"  时间: {inc['start_time'][:19]}")
                    print(f"  类型: {inc['error_type']}")
                    print(f"  持续: {duration:.1f} 秒")
                    print(f"  解决: {'✅' if inc['resolved'] else '❌'}")
            else:
                print("\n✅ 最近没有记录到故障事件")
        except Exception as e:
            print(f"分析失败: {e}")
    else:
        print("\n⚠️ 没有找到 v2 状态文件")
    
    # 分析日志中的模式
    log_file = Path.home() / ".openclaw" / "watchdog_v2.log"
    if log_file.exists():
        try:
            result = subprocess.run(
                ["grep", "-E", "健康状态:|错误签名:", str(log_file)],
                capture_output=True, text=True
            )
            
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                errors = {}
                for line in lines:
                    if "错误签名:" in line:
                        sig = line.split("错误签名:")[-1].strip()
                        errors[sig] = errors.get(sig, 0) + 1
                
                if errors:
                    print(f"\n📈 错误频率统计:")
                    print("-" * 60)
                    for sig, count in sorted(errors.items(), key=lambda x: -x[1]):
                        print(f"  {count:3d} 次: {sig}")
        except:
            pass
    
    print("\n" + "=" * 60)

def cmd_upgrade():
    """升级到 v2"""
    print("升级到 Watchdog v2...")
    
    # 检查 v2 脚本是否存在
    if not V2_SCRIPT.exists():
        print(f"错误: v2 脚本不存在 {V2_SCRIPT}")
        return
    
    # 停止旧版本
    cmd_stop()
    
    # 备份 v1 配置
    config = Path.home() / ".openclaw" / "watchdog_config.json"
    if config.exists():
        backup = config.with_suffix('.json.v1_backup')
        backup.write_text(config.read_text())
        print(f"✅ 配置已备份到: {backup}")
    
    # 启动 v2
    import time
    time.sleep(1)
    cmd_start("v2")
    
    print("\n🎉 升级完成!")
    print("提示: v2 的主要改进包括")
    print("  - 指数退避机制，避免频繁重启")
    print("  - 分级健康状态 (ok/warning/error/critical)")
    print("  - 智能故障检测，区分暂时波动和持续故障")
    print("  - 动态日志检测，自动找到最新日志")
    print("  - 故障趋势分析")

def cmd_rollback():
    """回滚到 v1"""
    print("回滚到 Watchdog v1...")
    
    cmd_stop()
    
    import time
    time.sleep(1)
    cmd_start("v1")
    
    print("✅ 已回滚到 v1")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    commands = {
        "status": cmd_status,
        "start": lambda: cmd_start("v2"),
        "stop": cmd_stop,
        "restart": lambda: cmd_restart("v2"),
        "logs": lambda: cmd_logs(int(sys.argv[2]) if len(sys.argv) > 2 else 50),
        "analyze": cmd_analyze,
        "upgrade": cmd_upgrade,
        "rollback": cmd_rollback,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
