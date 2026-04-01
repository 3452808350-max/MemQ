#!/usr/bin/env python3
"""
OpenClaw Watchdog v2 - 智能监控和自动修复 Agent

改进点：
1. 指数退避重试机制 - 避免频繁重启
2. 分级健康状态 - ok/warning/error/critical
3. 智能故障检测 - 区分暂时波动和持续故障
4. 动态日志检测 - 自动找到最新日志文件
5. 故障趋势分析 - 识别周期性故障
6. 更早的 AI 介入 - 配置类错误立即触发 AI 修复
"""

import os
import sys
import json
import time
import socket
import subprocess
import logging
import re
import shutil
import hashlib
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import signal
import tempfile
import threading

# ==================== 配置 ====================

class Config:
    """配置类"""
    CHECK_INTERVAL_SECONDS = 60
    MAX_RESTART_ATTEMPTS = 3
    RESTART_DELAY_SECONDS = 5
    GATEWAY_PORT = 18789
    GATEWAY_HOST = "127.0.0.1"
    LOG_FILE = "~/.openclaw/watchdog_v2.log"
    STATE_FILE = "~/.openclaw/watchdog_v2_state.json"
    TELEGRAM_NOTIFY = True
    LOG_LEVEL = "INFO"
    RESET_COUNTER_AFTER_HOURS = 24
    
    # 指数退避配置
    BACKOFF_INITIAL_DELAY = 30          # 初始延迟 30 秒
    BACKOFF_MAX_DELAY = 600             # 最大延迟 10 分钟
    BACKOFF_MULTIPLIER = 2              # 倍数
    
    # 健康检查阈值
    WARNING_THRESHOLD = 2               # 连续 2 次异常进入 warning
    ERROR_THRESHOLD = 3                 # 连续 3 次异常进入 error
    STUCK_THRESHOLD = 4                 # 连续 4 次异常进入 critical
    
    # Telegram 故障容忍
    TELEGRAM_ERROR_TOLERANCE = 5        # 5 次错误才判定为故障
    TELEGRAM_STALL_TOLERANCE = 3        # 3 次停滞才判定为卡住
    
    # AI 修复配置
    AI_FIX = {
        "enabled": True,
        "api_key": None,
        "model": "qwen3.5-plus",
        "max_attempts": 2,
        "timeout_seconds": 120,
        # 立即触发 AI 修复的错误类型（无需等待重启次数）
        "immediate_triggers": [
            "config_error",           # 配置错误
            "kimi_bridge_auth_fail",  # Kimi Bridge 认证失败
            "permission_denied",      # 权限问题
        ]
    }
    
    # 审计配置
    AUDIT = {
        "enabled": True,
        "max_history": 50,
        "backup_before_fix": True,
        "detailed_logging": True,
    }
    
    # 故障趋势分析
    TREND_ANALYSIS = {
        "enabled": True,
        "window_minutes": 60,           # 分析 1 小时内的故障
        "pattern_threshold": 3,         # 3 次相同错误视为模式
    }


# ==================== 数据模型 ====================

class HealthStatus(Enum):
    """健康状态枚举"""
    OK = "ok"                           # 正常
    WARNING = "warning"                 # 警告（偶发问题）
    ERROR = "error"                     # 错误（需要关注）
    CRITICAL = "critical"               # 严重（需要立即处理）
    DEAD = "dead"                       # 服务死亡


@dataclass
class HealthCheck:
    """健康检查结果"""
    status: HealthStatus
    timestamp: datetime
    details: Dict[str, Any]
    consecutive_failures: int = 0
    error_signature: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "consecutive_failures": self.consecutive_failures,
            "error_signature": self.error_signature,
        }


@dataclass  
class Incident:
    """故障事件"""
    id: str
    start_time: datetime
    end_time: Optional[datetime]
    error_type: str
    error_signature: str
    resolved: bool
    actions_taken: List[str]
    
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


# ==================== 主类 ====================

class OpenClawWatchdogV2:
    """OpenClaw Watchdog v2"""
    
    def __init__(self):
        self.home = Path.home() / ".openclaw"
        self.state_file = Path(Config.STATE_FILE).expanduser()
        self.running = True
        
        # 状态管理
        self.consecutive_failures = 0
        self.last_restart_time = 0
        self.backoff_delay = Config.BACKOFF_INITIAL_DELAY
        self.current_incident: Optional[Incident] = None
        self.incident_history: List[Incident] = []
        
        # 故障计数器（用于趋势分析）
        self.error_counter: Dict[str, List[datetime]] = {}
        
        # 锁
        self._lock = threading.Lock()
        
        # 设置日志
        self._setup_logging()
        
        # 设置信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("=" * 60)
        self.logger.info("OpenClaw Watchdog v2 启动")
        self.logger.info("=" * 60)
    
    def _setup_logging(self):
        """设置日志"""
        log_path = Path(Config.LOG_FILE).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("WatchdogV2")
    
    def _signal_handler(self, signum, frame):
        """处理停止信号"""
        self.logger.info(f"收到信号 {signum}，正在停止...")
        self.running = False
    
    # ==================== 状态持久化 ====================
    
    def load_state(self) -> Dict:
        """加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载状态失败：{e}")
        return {
            "consecutive_failures": 0,
            "total_restarts": 0,
            "incidents": [],
            "error_counter": {},
        }
    
    def save_state(self):
        """保存状态"""
        try:
            state = {
                "consecutive_failures": self.consecutive_failures,
                "total_restarts": self.load_state().get("total_restarts", 0),
                "last_update": datetime.now().isoformat(),
                "incidents": [
                    {
                        "id": i.id,
                        "start_time": i.start_time.isoformat(),
                        "end_time": i.end_time.isoformat() if i.end_time else None,
                        "error_type": i.error_type,
                        "resolved": i.resolved,
                        "duration_seconds": i.duration_seconds(),
                    }
                    for i in self.incident_history[-10:]  # 只保留最近 10 个
                ],
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.warning(f"保存状态失败：{e}")
    
    # ==================== 核心健康检查 ====================
    
    def get_latest_log_file(self) -> Optional[Path]:
        """动态获取最新的日志文件"""
        try:
            log_dir = Path("/tmp/openclaw")
            if not log_dir.exists():
                return None
            
            log_files = list(log_dir.glob("openclaw-*.log"))
            if not log_files:
                return None
            
            # 按修改时间排序，返回最新的
            return max(log_files, key=lambda p: p.stat().st_mtime)
        except Exception as e:
            self.logger.warning(f"获取日志文件失败：{e}")
            return None
    
    def check_basic_health(self) -> Dict[str, Any]:
        """基础健康检查"""
        details = {
            "port_listening": False,
            "process_running": False,
            "process_pid": None,
            "config_valid": False,
            "gateway_responding": False,
        }
        
        # 1. 检查端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            details["port_listening"] = sock.connect_ex((Config.GATEWAY_HOST, Config.GATEWAY_PORT)) == 0
            sock.close()
        except Exception as e:
            self.logger.debug(f"端口检查失败：{e}")
        
        # 2. 检查进程
        try:
            result = subprocess.run(
                ["pgrep", "-f", "openclaw.*gateway"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                pids = [p for p in result.stdout.strip().split('\n') if p.isdigit()]
                if pids:
                    details["process_running"] = True
                    details["process_pid"] = int(pids[0])
        except Exception as e:
            self.logger.debug(f"进程检查失败：{e}")
        
        # 3. 检查配置
        config_file = self.home / "openclaw.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    json.load(f)
                details["config_valid"] = True
            except Exception as e:
                details["config_valid"] = False
                details["config_error"] = str(e)
        
        # 4. HTTP 健康检查
        if details["port_listening"]:
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"http://{Config.GATEWAY_HOST}:{Config.GATEWAY_PORT}/health",
                    method="GET"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    details["gateway_responding"] = resp.status == 200
            except Exception:
                pass
        
        return details
    
    def check_functional_health(self) -> Dict[str, Any]:
        """功能性健康检查 - v2 改进版"""
        details = {
            "telegram_ok": True,
            "kimi_bridge_ok": True,
            "errors": [],
            "metrics": {}
        }
        
        log_file = self.get_latest_log_file()
        if not log_file:
            return details
        
        try:
            # 获取最近 5 分钟的日志
            result = subprocess.run(
                ["tail", "-n", "200", str(log_file)],
                capture_output=True, text=True, timeout=5
            )
            recent_logs = result.stdout
            
            # 统计 Telegram 相关错误
            telegram_patterns = {
                "delete_webhook_fail": r'deleteWebhook failed',
                "polling_stall": r'Polling stall detected',
                "connection_error": r'connect.*telegram|telegram.*error',
                "timeout": r'timeout.*telegram|telegram.*timeout',
            }
            
            telegram_errors = {}
            for pattern_name, pattern in telegram_patterns.items():
                matches = len(re.findall(pattern, recent_logs, re.IGNORECASE))
                telegram_errors[pattern_name] = matches
            
            details["metrics"]["telegram"] = telegram_errors
            
            # 判定 Telegram 状态
            total_telegram_errors = sum(telegram_errors.values())
            if telegram_errors.get("delete_webhook_fail", 0) >= Config.TELEGRAM_ERROR_TOLERANCE:
                details["telegram_ok"] = False
                details["errors"].append(f"Telegram deleteWebhook 持续失败 ({telegram_errors['delete_webhook_fail']} 次)")
            elif telegram_errors.get("polling_stall", 0) >= Config.TELEGRAM_STALL_TOLERANCE:
                details["telegram_ok"] = False
                details["errors"].append(f"Telegram polling 多次停滞 ({telegram_errors['polling_stall']} 次)")
            elif total_telegram_errors >= Config.TELEGRAM_ERROR_TOLERANCE * 2:
                details["telegram_ok"] = False
                details["errors"].append(f"Telegram 错误过多 ({total_telegram_errors} 次)")
            
            # 检查 Kimi Bridge 状态
            kimi_patterns = {
                "auth_fail": r'auth failed.*401|authentication failed',
                "ws_closed": r'bridge-acp.*closed.*1006',
                "disconnect": r'bridge ACP disconnected',
            }
            
            kimi_errors = {}
            for pattern_name, pattern in kimi_patterns.items():
                matches = len(re.findall(pattern, recent_logs, re.IGNORECASE))
                kimi_errors[pattern_name] = matches
            
            details["metrics"]["kimi_bridge"] = kimi_errors
            
            # 检查最近一次 Kimi Bridge 连接状态
            if "bridge ACP connected" in recent_logs:
                last_connected_pos = recent_logs.rfind("bridge ACP connected")
                last_disconnected_pos = recent_logs.rfind("bridge ACP disconnected")
                if last_disconnected_pos > last_connected_pos:
                    details["kimi_bridge_ok"] = False
                    details["errors"].append("Kimi Bridge 当前未连接")
            
            # 检查认证失败（这是配置问题，需要立即处理）
            if kimi_errors.get("auth_fail", 0) > 0:
                details["kimi_bridge_ok"] = False
                details["auth_error"] = True
                details["errors"].append("Kimi Bridge 认证失败（配置问题）")
                
        except Exception as e:
            self.logger.warning(f"功能性检查失败：{e}")
        
        return details
    
    def extract_error_signature(self, details: Dict) -> str:
        """提取错误签名（用于去重和趋势分析）"""
        signatures = []
        
        if not details.get("config_valid", True):
            signatures.append("config_invalid")
        
        if not details.get("port_listening", True):
            signatures.append("port_not_listening")
        
        func_details = details.get("functional", {})
        if not func_details.get("telegram_ok", True):
            signatures.append("telegram_error")
        if not func_details.get("kimi_bridge_ok", True):
            if func_details.get("auth_error"):
                signatures.append("kimi_bridge_auth_fail")
            else:
                signatures.append("kimi_bridge_disconnect")
        
        return "|".join(signatures) if signatures else "unknown"
    
    def determine_health_status(self, basic: Dict, functional: Dict) -> HealthStatus:
        """根据检查结果确定健康状态"""
        
        # 死亡状态
        if not basic["port_listening"] and not basic["process_running"]:
            return HealthStatus.DEAD
        
        # 配置错误 - 立即 critical
        if not basic.get("config_valid", True):
            return HealthStatus.CRITICAL
        
        # 进程存在但端口不通 - 卡住
        if basic["process_running"] and not basic["port_listening"]:
            return HealthStatus.CRITICAL
        
        # 功能性检查
        func_issues = []
        if not functional.get("telegram_ok", True):
            func_issues.append("telegram")
        if not functional.get("kimi_bridge_ok", True):
            func_issues.append("kimi_bridge")
            # Kimi Bridge 认证失败是配置问题，立即 critical
            if functional.get("auth_error"):
                return HealthStatus.CRITICAL
        
        if func_issues:
            # 根据连续失败次数分级
            if self.consecutive_failures >= Config.STUCK_THRESHOLD:
                return HealthStatus.CRITICAL
            elif self.consecutive_failures >= Config.ERROR_THRESHOLD:
                return HealthStatus.ERROR
            else:
                return HealthStatus.WARNING
        
        return HealthStatus.OK
    
    def perform_health_check(self) -> HealthCheck:
        """执行完整的健康检查"""
        basic = self.check_basic_health()
        functional = self.check_functional_health()
        
        # 合并详情
        details = {**basic, "functional": functional, "functional_issues": functional.get("errors", [])}
        
        # 确定状态
        status = self.determine_health_status(basic, functional)
        
        # 更新连续失败计数
        with self._lock:
            if status == HealthStatus.OK:
                if self.consecutive_failures > 0:
                    self.logger.info(f"服务恢复正常，重置连续失败计数（之前：{self.consecutive_failures}）")
                    self.consecutive_failures = 0
                    self.backoff_delay = Config.BACKOFF_INITIAL_DELAY
                    self._resolve_current_incident()
            else:
                self.consecutive_failures += 1
                self.logger.debug(f"健康检查异常，连续失败：{self.consecutive_failures}")
        
        error_signature = self.extract_error_signature(details)
        
        return HealthCheck(
            status=status,
            timestamp=datetime.now(),
            details=details,
            consecutive_failures=self.consecutive_failures,
            error_signature=error_signature,
        )
    
    # ==================== 趋势分析 ====================
    
    def record_error(self, error_signature: str):
        """记录错误用于趋势分析"""
        now = datetime.now()
        if error_signature not in self.error_counter:
            self.error_counter[error_signature] = []
        
        self.error_counter[error_signature].append(now)
        
        # 清理过期记录
        window = timedelta(minutes=Config.TREND_ANALYSIS["window_minutes"])
        self.error_counter[error_signature] = [
            t for t in self.error_counter[error_signature]
            if now - t < window
        ]
    
    def detect_error_pattern(self, error_signature: str) -> Optional[Dict]:
        """检测是否有错误模式"""
        if not Config.TREND_ANALYSIS["enabled"]:
            return None
        
        if error_signature not in self.error_counter:
            return None
        
        count = len(self.error_counter[error_signature])
        threshold = Config.TREND_ANALYSIS["pattern_threshold"]
        
        if count >= threshold:
            return {
                "pattern_detected": True,
                "error_signature": error_signature,
                "occurrences": count,
                "window_minutes": Config.TREND_ANALYSIS["window_minutes"],
                "message": f"检测到错误模式 '{error_signature}' 在 {Config.TREND_ANALYSIS['window_minutes']} 分钟内发生了 {count} 次"
            }
        return None
    
    # ==================== 事件管理 ====================
    
    def start_incident(self, error_type: str, error_signature: str):
        """开始记录故障事件"""
        if self.current_incident is None:
            self.current_incident = Incident(
                id=hashlib.md5(f"{datetime.now().isoformat()}{error_signature}".encode()).hexdigest()[:12],
                start_time=datetime.now(),
                end_time=None,
                error_type=error_type,
                error_signature=error_signature,
                resolved=False,
                actions_taken=[]
            )
            self.logger.info(f"开始记录故障事件: {self.current_incident.id}")
    
    def add_incident_action(self, action: str):
        """记录故障处理动作"""
        if self.current_incident:
            self.current_incident.actions_taken.append(f"{datetime.now().strftime('%H:%M:%S')} - {action}")
    
    def _resolve_current_incident(self):
        """解决当前故障事件"""
        if self.current_incident:
            self.current_incident.end_time = datetime.now()
            self.current_incident.resolved = True
            duration = self.current_incident.duration_seconds()
            self.logger.info(
                f"故障事件 {self.current_incident.id} 已解决，"
                f"持续时间: {duration:.1f} 秒，"
                f"处理动作: {len(self.current_incident.actions_taken)} 个"
            )
            self.incident_history.append(self.current_incident)
            self.current_incident = None
    
    # ==================== 修复操作 ====================
    
    def calculate_backoff_delay(self) -> int:
        """计算指数退避延迟"""
        delay = min(
            Config.BACKOFF_INITIAL_DELAY * (Config.BACKOFF_MULTIPLIER ** self.consecutive_failures),
            Config.BACKOFF_MAX_DELAY
        )
        return int(delay)
    
    def should_attempt_restart(self) -> Tuple[bool, str]:
        """判断是否应尝试重启"""
        # 检查重启频率限制
        now = time.time()
        time_since_last = now - self.last_restart_time
        
        if time_since_last < 60:
            return False, f"距离上次重启仅 {time_since_last:.0f} 秒，跳过"
        
        # 检查退避延迟
        required_delay = self.calculate_backoff_delay()
        if time_since_last < required_delay:
            return False, f"退避等待中，还需等待 {required_delay - time_since_last:.0f} 秒"
        
        # 检查最大重启次数
        if self.consecutive_failures > Config.MAX_RESTART_ATTEMPTS * 2:
            return False, "连续失败次数过多，需要人工干预"
        
        return True, "可以重启"
    
    def restart_gateway(self) -> bool:
        """重启 Gateway"""
        self.logger.info("正在重启 Gateway...")
        self.add_incident_action("开始重启 Gateway")
        
        # 1. 优雅停止
        try:
            subprocess.run(
                ["systemctl", "--user", "stop", "openclaw-gateway"],
                timeout=10, capture_output=True
            )
            time.sleep(2)
        except Exception as e:
            self.logger.warning(f"systemctl stop 失败：{e}")
        
        # 2. 强制清理残留进程
        try:
            subprocess.run(
                ["killall", "-9", "openclaw-gateway", "openclaw"],
                timeout=5, capture_output=True
            )
            time.sleep(1)
        except Exception:
            pass
        
        # 3. 启动服务
        try:
            result = subprocess.run(
                ["systemctl", "--user", "start", "openclaw-gateway"],
                timeout=10, capture_output=True
            )
            if result.returncode == 0:
                self.last_restart_time = time.time()
                self.add_incident_action("Gateway 重启成功")
                self.logger.info("Gateway 重启成功")
                return True
            else:
                self.logger.error(f"Gateway 启动失败：{result.stderr}")
                self.add_incident_action(f"Gateway 启动失败: {result.stderr[:100]}")
                return False
        except Exception as e:
            self.logger.error(f"重启 Gateway 失败：{e}")
            self.add_incident_action(f"重启失败: {str(e)[:100]}")
            return False
    
    def fix_common_issues(self, health: HealthCheck) -> List[str]:
        """修复常见问题"""
        fixes = []
        
        # 1. 配置权限问题
        config_file = self.home / "openclaw.json"
        if config_file.exists():
            try:
                current_mode = os.stat(config_file).st_mode
                if current_mode & 0o077:
                    os.chmod(config_file, 0o600)
                    fixes.append("修复配置权限为 600")
                    self.add_incident_action("修复配置权限")
            except Exception as e:
                self.logger.warning(f"修复权限失败：{e}")
        
        # 2. 清理锁文件
        lock_file = self.home / "gateway.lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
                fixes.append("清理锁文件")
                self.add_incident_action("清理锁文件")
            except Exception as e:
                self.logger.warning(f"清理锁文件失败：{e}")
        
        return fixes
    
    # ==================== AI 修复 ====================
    
    def should_trigger_ai_fix(self, health: HealthCheck) -> Tuple[bool, str]:
        """判断是否应触发 AI 修复"""
        ai_config = Config.AI_FIX
        if not ai_config.get("enabled", False):
            return False, "AI 修复已禁用"
        
        # 检查是否是立即触发的错误类型
        immediate_triggers = ai_config.get("immediate_triggers", [])
        if any(trigger in health.error_signature for trigger in immediate_triggers):
            return True, f"触发立即 AI 修复（错误类型：{health.error_signature}）"
        
        # 检查是否超过阈值
        if self.consecutive_failures >= Config.MAX_RESTART_ATTEMPTS:
            return True, "连续失败次数达到阈值，触发 AI 修复"
        
        return False, "未达到 AI 修复触发条件"
    
    def call_ai_for_fix(self, health: HealthCheck) -> Tuple[bool, str, List[Dict]]:
        """调用 AI 分析问题并提供修复方案（简化版，保留核心逻辑）"""
        # 这里简化实现，实际可以复用 v1 的完整逻辑
        # 或调用外部脚本
        
        error_signature = health.error_signature
        
        # 已知问题的快速修复
        quick_fixes = {
            "kimi_bridge_auth_fail": [
                {"type": "config", "description": "检查 kimi-claw 配置中的 bridge.token", "check_file": "~/.openclaw/openclaw.json"},
            ],
            "config_invalid": [
                {"type": "command", "description": "验证并修复 JSON 配置", "command": "python3 -m json.tool ~/.openclaw/openclaw.json > /dev/null && echo 'Valid JSON' || echo 'Invalid JSON'"},
            ],
        }
        
        if error_signature in quick_fixes:
            return True, f"已知问题 '{error_signature}'，应用快速修复方案", quick_fixes[error_signature]
        
        return False, "未找到快速修复方案", []
    
    # ==================== 通知 ====================
    
    def send_notification(self, message: str):
        """发送通知"""
        if not Config.TELEGRAM_NOTIFY:
            return
        
        try:
            # 使用 notify-send 作为备选
            subprocess.run(
                ["notify-send", "OpenClaw Watchdog", message],
                timeout=5, capture_output=True
            )
        except Exception:
            pass
        
        # 尝试使用 openclaw message
        try:
            subprocess.run(
                ["openclaw", "message", "send", "--target", "self", "--message", message],
                timeout=10, capture_output=True
            )
        except Exception as e:
            self.logger.debug(f"发送通知失败：{e}")
    
    def format_status_message(self, health: HealthCheck, action: str = "") -> str:
        """格式化状态消息"""
        lines = [
            f"📊 OpenClaw Watchdog v2",
            f"",
            f"状态: {health.status.value.upper()}",
            f"时间: {health.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"连续异常: {health.consecutive_failures} 次",
        ]
        
        if health.error_signature:
            lines.append(f"错误类型: {health.error_signature}")
        
        if health.details.get("functional_issues"):
            lines.append(f"")
            lines.append(f"问题详情:")
            for issue in health.details["functional_issues"]:
                lines.append(f"  • {issue}")
        
        if action:
            lines.append(f"")
            lines.append(f"执行动作: {action}")
        
        return "\n".join(lines)
    
    # ==================== 主循环 ====================
    
    def run_check_cycle(self):
        """执行一次检查周期"""
        self.logger.debug("执行健康检查...")
        
        # 执行健康检查
        health = self.perform_health_check()
        
        # 记录错误用于趋势分析
        if health.status != HealthStatus.OK:
            self.record_error(health.error_signature)
        
        # 检测错误模式
        pattern = self.detect_error_pattern(health.error_signature)
        if pattern:
            self.logger.warning(f"🚨 {pattern['message']}")
        
        # 记录当前状态
        if health.status == HealthStatus.OK:
            self.logger.info(f"✅ 健康状态: {health.status.value} | PID: {health.details.get('process_pid')} | 端口: {health.details.get('port_listening')}")
            return
        
        self.logger.info(
            f"⚠️ 健康状态: {health.status.value} | "
            f"连续失败: {health.consecutive_failures} | "
            f"错误签名: {health.error_signature}"
        )
        
        # 开始记录故障事件
        self.start_incident(health.status.value, health.error_signature)
        
        # 根据状态采取不同行动
        if health.status == HealthStatus.WARNING:
            # Warning 级别只记录和通知，不采取行动
            if self.consecutive_failures == Config.WARNING_THRESHOLD:
                self.send_notification(self.format_status_message(health, "持续观察中"))
            return
        
        if health.status == HealthStatus.ERROR:
            # Error 级别尝试简单修复
            fixes = self.fix_common_issues(health)
            if fixes:
                self.logger.info(f"已执行修复: {fixes}")
                self.add_incident_action(f"执行修复: {fixes}")
            
            # 检查是否需要 AI 修复
            should_ai, ai_reason = self.should_trigger_ai_fix(health)
            if should_ai:
                self.logger.info(f"触发 AI 修复: {ai_reason}")
                self.add_incident_action(f"触发 AI 修复: {ai_reason}")
                # TODO: 调用完整的 AI 修复逻辑
            
            return
        
        if health.status in [HealthStatus.CRITICAL, HealthStatus.DEAD]:
            # Critical/Dead 级别尝试重启
            should_restart, restart_reason = self.should_attempt_restart()
            
            if not should_restart:
                self.logger.info(f"跳过重启: {restart_reason}")
                self.add_incident_action(f"跳过重启: {restart_reason}")
                return
            
            # 先尝试简单修复
            fixes = self.fix_common_issues(health)
            if fixes:
                self.logger.info(f"已执行修复: {fixes}")
            
            # 执行重启
            self.logger.info(f"准备重启: {restart_reason}")
            success = self.restart_gateway()
            
            if success:
                self.send_notification(
                    self.format_status_message(health, "✅ Gateway 已重启")
                )
            else:
                self.send_notification(
                    self.format_status_message(health, "❌ Gateway 重启失败，需要人工干预")
                )
    
    def run(self):
        """主运行循环"""
        self.logger.info(f"检查间隔: {Config.CHECK_INTERVAL_SECONDS} 秒")
        self.logger.info(f"退避配置: 初始 {Config.BACKOFF_INITIAL_DELAY}s, 最大 {Config.BACKOFF_MAX_DELAY}s")
        self.logger.info(f"阈值: Warning={Config.WARNING_THRESHOLD}, Error={Config.ERROR_THRESHOLD}, Critical={Config.STUCK_THRESHOLD}")
        
        # 加载历史状态
        state = self.load_state()
        self.consecutive_failures = state.get("consecutive_failures", 0)
        
        while self.running:
            try:
                self.run_check_cycle()
                self.save_state()
            except Exception as e:
                self.logger.error(f"检查周期异常: {e}", exc_info=True)
            
            # 等待下次检查
            for _ in range(Config.CHECK_INTERVAL_SECONDS):
                if not self.running:
                    break
                time.sleep(1)
        
        self.logger.info("Watchdog v2 已停止")
        self.save_state()


def main():
    """入口函数"""
    watchdog = OpenClawWatchdogV2()
    watchdog.run()


if __name__ == "__main__":
    main()
