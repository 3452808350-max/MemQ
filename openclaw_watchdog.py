#!/usr/bin/env python3
"""
OpenClaw Watchdog - 独立监控和自动修复 Agent

功能：
1. 监控 Gateway 健康状态
2. 自动检测并修复常见问题
3. 崩溃时自动重启
4. 发送通知到 Telegram

运行方式：
- systemd 服务（推荐）
- cron 定时任务
- 独立守护进程
"""

import os
import sys
import json
import time
import socket
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import signal

# 配置
CONFIG = {
    "check_interval_seconds": 30,      # 检查间隔
    "max_restart_attempts": 3,          # 最大重启尝试次数
    "restart_delay_seconds": 5,         # 重启延迟
    "gateway_port": 18789,              # Gateway 端口
    "gateway_host": "127.0.0.1",        # Gateway 主机
    "log_file": "~/.openclaw/watchdog.log",
    "state_file": "~/.openclaw/watchdog_state.json",
    "telegram_notify": True,            # 是否发送 Telegram 通知
}

# 日志设置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser(CONFIG["log_file"])),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class OpenClawWatchdog:
    """OpenClaw 看门狗"""
    
    def __init__(self):
        self.home = Path.home() / ".openclaw"
        self.state_file = Path(CONFIG["state_file"]).expanduser()
        self.restart_count = 0
        self.last_restart_time = 0
        self.running = True
        
        # 设置信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """处理停止信号"""
        logger.info(f"收到信号 {signum}，正在停止...")
        self.running = False
    
    def load_state(self) -> Dict:
        """加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载状态失败：{e}")
        return {"restart_count": 0, "last_restart": None}
    
    def save_state(self, state: Dict):
        """保存状态"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"保存状态失败：{e}")
    
    def check_port(self, port: int = None) -> bool:
        """检查端口是否被监听"""
        port = port or CONFIG["gateway_port"]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((CONFIG["gateway_host"], port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"检查端口失败：{e}")
            return False
    
    def check_gateway_process(self) -> Optional[int]:
        """检查 Gateway 进程，返回 PID 或 None"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "openclaw.*gateway"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = [int(p) for p in result.stdout.strip().split('\n') if p.isdigit()]
                return pids[0] if pids else None
            return None
        except Exception as e:
            logger.error(f"检查进程失败：{e}")
            return None
    
    def check_gateway_health(self) -> Dict:
        """
        检查 Gateway 健康状态
        返回：{"status": "ok|error|dead", "details": {...}}
        """
        health = {
            "status": "ok",
            "details": {
                "port_listening": False,
                "process_running": False,
                "config_valid": False,
                "error": None
            }
        }
        
        # 1. 检查端口
        health["details"]["port_listening"] = self.check_port()
        
        # 2. 检查进程
        pid = self.check_gateway_process()
        health["details"]["process_running"] = pid is not None
        health["details"]["process_pid"] = pid
        
        # 3. 检查配置
        config_file = self.home / "openclaw.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    json.load(f)
                health["details"]["config_valid"] = True
            except Exception as e:
                health["details"]["config_valid"] = False
                health["details"]["config_error"] = str(e)
        else:
            health["details"]["config_valid"] = False
            health["details"]["config_error"] = "配置文件不存在"
        
        # 4. 判断状态
        if not health["details"]["port_listening"] and not health["details"]["process_running"]:
            health["status"] = "dead"
            health["details"]["error"] = "Gateway 未运行"
        elif not health["details"]["port_listening"] and health["details"]["process_running"]:
            health["status"] = "error"
            health["details"]["error"] = "进程存在但端口未监听（可能卡死）"
        elif not health["details"]["config_valid"]:
            health["status"] = "error"
            health["details"]["error"] = "配置文件无效"
        
        return health
    
    def kill_gateway(self) -> bool:
        """停止 Gateway 进程"""
        try:
            pids = []
            result = subprocess.run(
                ["pgrep", "-f", "openclaw.*gateway"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                pids = [int(p) for p in result.stdout.strip().split('\n') if p.isdigit()]
            
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    logger.info(f"已发送 SIGTERM 到进程 {pid}")
                except ProcessLookupError:
                    pass
            
            # 等待进程退出
            time.sleep(2)
            
            # 如果还在，强制杀死
            result = subprocess.run(
                ["pgrep", "-f", "openclaw.*gateway"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                pids = [int(p) for p in result.stdout.strip().split('\n') if p.isdigit()]
                for pid in pids:
                    os.kill(pid, signal.SIGKILL)
                    logger.warning(f"已强制杀死进程 {pid}")
            
            return True
        except Exception as e:
            logger.error(f"停止 Gateway 失败：{e}")
            return False
    
    def start_gateway(self) -> bool:
        """启动 Gateway"""
        try:
            # 使用 systemd 启动（如果已安装）
            systemd_service = "/etc/systemd/user/openclaw-gateway.service"
            if Path(systemd_service).exists() or Path("/etc/systemd/system/openclaw-gateway.service").exists():
                subprocess.run(
                    ["systemctl", "--user", "start", "openclaw-gateway"],
                    timeout=10
                )
                logger.info("已通过 systemd 启动 Gateway")
                return True
            
            # 否则直接启动
            env = os.environ.copy()
            env["OPENCLAW_HOME"] = str(self.home)
            
            subprocess.Popen(
                ["openclaw", "gateway"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env
            )
            logger.info("已直接启动 Gateway")
            return True
        except Exception as e:
            logger.error(f"启动 Gateway 失败：{e}")
            return False
    
    def restart_gateway(self) -> bool:
        """重启 Gateway"""
        logger.info("正在重启 Gateway...")
        
        # 检查重启频率限制
        now = time.time()
        if now - self.last_restart_time < 60:  # 1 分钟内不重复重启
            logger.warning("重启过于频繁，跳过")
            return False
        
        # 停止
        logger.info("停止 Gateway...")
        self.kill_gateway()
        time.sleep(2)
        
        # 启动
        logger.info("启动 Gateway...")
        success = self.start_gateway()
        
        if success:
            self.last_restart_time = now
            self.restart_count += 1
            state = self.load_state()
            state["restart_count"] = self.restart_count
            state["last_restart"] = datetime.now().isoformat()
            self.save_state(state)
            logger.info(f"Gateway 重启成功（总重启次数：{self.restart_count}）")
        else:
            logger.error("Gateway 重启失败")
        
        return success
    
    def fix_common_issues(self) -> List[str]:
        """修复常见问题"""
        fixed = []
        
        # 1. 清理僵尸进程
        pids = self.check_gateway_process()
        if pids and not self.check_port():
            logger.info("检测到僵尸进程，正在清理...")
            self.kill_gateway()
            fixed.append("清理僵尸进程")
        
        # 2. 修复配置权限
        config_file = self.home / "openclaw.json"
        if config_file.exists():
            try:
                os.chmod(config_file, 0o600)
                fixed.append("修复配置权限")
            except Exception as e:
                logger.warning(f"修复权限失败：{e}")
        
        # 3. 清理锁文件
        lock_file = self.home / "gateway.lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
                fixed.append("清理锁文件")
            except Exception as e:
                logger.warning(f"清理锁文件失败：{e}")
        
        return fixed
    
    def send_notification(self, message: str):
        """发送通知（Telegram）"""
        if not CONFIG["telegram_notify"]:
            return
        
        try:
            # 使用 openclaw message 命令发送
            subprocess.run(
                ["openclaw", "message", "send", "--target", "self", "--message", message],
                timeout=10,
                capture_output=True
            )
            logger.info(f"通知已发送：{message}")
        except Exception as e:
            logger.warning(f"发送通知失败：{e}")
    
    def run_check_cycle(self):
        """执行一次检查周期"""
        logger.info("执行健康检查...")
        
        # 检查健康
        health = self.check_gateway_health()
        logger.info(f"健康状态：{health['status']} - {health['details']}")
        
        if health["status"] == "ok":
            # 一切正常，重置重启计数
            if self.restart_count > 0:
                self.restart_count = max(0, self.restart_count - 1)
                state = self.load_state()
                state["restart_count"] = self.restart_count
                self.save_state(state)
            return
        
        # 发现问题，尝试修复
        logger.warning(f"发现问题：{health['details'].get('error', '未知')}")
        
        # 尝试修复常见问题
        fixed = self.fix_common_issues()
        if fixed:
            logger.info(f"已修复：{fixed}")
        
        # 如果需要重启
        if health["status"] in ["dead", "error"]:
            if self.restart_count < CONFIG["max_restart_attempts"]:
                success = self.restart_gateway()
                if success:
                    self.send_notification(
                        f"🔧 OpenClaw Watchdog\n\n"
                        f"Gateway 已自动重启\n"
                        f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"重启次数：{self.restart_count}"
                    )
                else:
                    self.send_notification(
                        f"⚠️ OpenClaw Watchdog\n\n"
                        f"Gateway 重启失败\n"
                        f"错误：{health['details'].get('error', '未知')}\n"
                        f"请手动检查"
                    )
            else:
                logger.error("重启次数过多，停止自动重启")
                self.send_notification(
                    f"🚨 OpenClaw Watchdog\n\n"
                    f"Gateway 重启失败次数过多（{self.restart_count}次）\n"
                    f"需要手动干预"
                )
    
    def run(self):
        """主运行循环"""
        logger.info("=" * 50)
        logger.info("OpenClaw Watchdog 启动")
        logger.info(f"检查间隔：{CONFIG['check_interval_seconds']}秒")
        logger.info(f"最大重启次数：{CONFIG['max_restart_attempts']}")
        logger.info("=" * 50)
        
        # 加载状态
        state = self.load_state()
        self.restart_count = state.get("restart_count", 0)
        logger.info(f"历史重启次数：{self.restart_count}")
        
        # 主循环
        while self.running:
            try:
                self.run_check_cycle()
            except Exception as e:
                logger.error(f"检查周期出错：{e}")
            
            # 等待下次检查
            for _ in range(CONFIG["check_interval_seconds"]):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("Watchdog 已停止")


def main():
    """入口函数"""
    watchdog = OpenClawWatchdog()
    watchdog.run()


if __name__ == "__main__":
    main()
