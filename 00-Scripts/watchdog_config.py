#!/usr/bin/env python3
"""
OpenClaw Watchdog 配置编辑器

用法：
    python3 watchdog_config.py set check_interval 60
    python3 watchdog_config.py get check_interval
    python3 watchdog_config.py show
"""

import json
import sys
from pathlib import Path

CONFIG_FILE = Path.home() / ".openclaw" / "watchdog_config.json"

DEFAULT_CONFIG = {
    "check_interval_seconds": 30,
    "max_restart_attempts": 3,
    "restart_delay_seconds": 5,
    "gateway_port": 18789,
    "gateway_host": "127.0.0.1",
    "telegram_notify": True,
    "log_level": "INFO"
}


def load_config():
    """加载配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✓ 配置已保存到 {CONFIG_FILE}")


def cmd_show():
    """显示配置"""
    config = load_config()
    print("当前配置：")
    for key, value in config.items():
        print(f"  {key}: {value}")


def cmd_get(key):
    """获取配置值"""
    config = load_config()
    if key in config:
        print(config[key])
    else:
        print(f"❌ 未知配置项：{key}", file=sys.stderr)
        sys.exit(1)


def cmd_set(key, value):
    """设置配置值"""
    config = load_config()
    
    # 类型转换
    if key in ["check_interval_seconds", "max_restart_attempts", "restart_delay_seconds", "gateway_port"]:
        value = int(value)
    elif key == "telegram_notify":
        value = value.lower() in ["true", "yes", "1"]
    
    config[key] = value
    save_config(config)
    print(f"✓ {key} = {value}")


def cmd_reset():
    """重置配置"""
    save_config(DEFAULT_CONFIG)
    print("✓ 配置已重置为默认值")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  watchdog_config.py show              # 显示配置")
        print("  watchdog_config.py get <key>         # 获取配置值")
        print("  watchdog_config.py set <key> <value> # 设置配置值")
        print("  watchdog_config.py reset             # 重置配置")
        print("")
        print("配置项:")
        for key, value in DEFAULT_CONFIG.items():
            print(f"  {key}: {value} (默认)")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "show":
        cmd_show()
    elif command == "get":
        if len(sys.argv) < 3:
            print("❌ 缺少配置项名称", file=sys.stderr)
            sys.exit(1)
        cmd_get(sys.argv[2])
    elif command == "set":
        if len(sys.argv) < 4:
            print("❌ 缺少参数", file=sys.stderr)
            sys.exit(1)
        cmd_set(sys.argv[2], sys.argv[3])
    elif command == "reset":
        cmd_reset()
    else:
        print(f"❌ 未知命令：{command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
