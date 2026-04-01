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
import re
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import signal
import tempfile

# 默认配置
DEFAULT_CONFIG = {
    "check_interval_seconds": 60,      # 检查间隔（1 分钟）- 更频繁检查以更快发现问题
    "max_restart_attempts": 3,          # 最大重启尝试次数
    "restart_delay_seconds": 5,         # 重启延迟
    "gateway_port": 18789,              # Gateway 端口
    "gateway_host": "127.0.0.1",        # Gateway 主机
    "log_file": "~/.openclaw/watchdog.log",
    "state_file": "~/.openclaw/watchdog_state.json",
    "telegram_notify": True,            # 是否发送 Telegram 通知
    "log_level": "INFO",
    "reset_counter_after_hours": 24,    # 多少小时后自动重置重启计数器
    "ai_fix": {
        "enabled": True,                # 是否启用 AI 自动修复
        "api_key": None,                # API key，None 表示从配置文件读取
        "model": "kimi-k2.5",           # 使用的模型
        "max_attempts": 2,              # AI 修复最大尝试次数
        "timeout_seconds": 120,         # AI 调用超时时间
    },
    "audit": {
        "enabled": True,                # 是否启用审计日志
        "max_history": 50,              # 保留多少条历史记录
        "backup_before_fix": True,      # 修复前是否备份配置
        "detailed_logging": True,       # 是否记录详细日志
    }
}

# 配置文件路径
CONFIG_FILE = Path.home() / ".openclaw" / "watchdog_config.json"

def load_config():
    """从配置文件加载配置"""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"加载配置文件失败：{e}，使用默认配置")
    return config

# 加载配置
CONFIG = load_config()

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
        return {"restart_count": 0, "last_restart": None, "last_success_start": None}
    
    def save_state(self, state: Dict):
        """保存状态"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"保存状态失败：{e}")
    
    # ============ 审计日志功能 ============
    
    def get_audit_log_file(self) -> Path:
        """获取审计日志文件路径"""
        return self.home / "fix_audit_log.json"
    
    def load_audit_history(self) -> List[Dict]:
        """加载修复历史记录"""
        audit_file = self.get_audit_log_file()
        if audit_file.exists():
            try:
                with open(audit_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载审计日志失败：{e}")
        return []
    
    def save_audit_history(self, history: List[Dict]):
        """保存修复历史记录"""
        try:
            audit_file = self.get_audit_log_file()
            with open(audit_file, 'w') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存审计日志失败：{e}")
    
    def add_audit_record(self, record: Dict):
        """添加一条审计记录"""
        if not CONFIG.get("audit", {}).get("enabled", True):
            return
        
        history = self.load_audit_history()
        record["timestamp"] = datetime.now().isoformat()
        record["id"] = hashlib.md5(f"{record['timestamp']}{record.get('error_type', 'unknown')}".encode()).hexdigest()[:12]
        
        history.insert(0, record)  # 最新的在前面
        
        # 限制历史记录数量
        max_history = CONFIG.get("audit", {}).get("max_history", 50)
        if len(history) > max_history:
            history = history[:max_history]
        
        self.save_audit_history(history)
        logger.info(f"审计记录已保存: {record['id']}")
    
    def create_backup(self, reason: str) -> Optional[str]:
        """创建配置备份"""
        if not CONFIG.get("audit", {}).get("backup_before_fix", True):
            return None
        
        try:
            config_file = self.home / "openclaw.json"
            if not config_file.exists():
                return None
            
            backup_dir = self.home / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"openclaw.json.backup.{timestamp}.{reason}"
            backup_path = backup_dir / backup_name
            
            shutil.copy2(config_file, backup_path)
            
            # 清理旧备份（保留最近20个）
            backups = sorted(backup_dir.glob("openclaw.json.backup.*"), key=lambda p: p.stat().st_mtime, reverse=True)
            for old_backup in backups[20:]:
                old_backup.unlink()
            
            logger.info(f"配置已备份到: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.warning(f"创建备份失败：{e}")
            return None
    
    def rollback_changes(self, backup_path: str) -> bool:
        """回滚到备份配置"""
        try:
            config_file = self.home / "openclaw.json"
            backup = Path(backup_path)
            
            if not backup.exists():
                logger.error(f"备份文件不存在：{backup_path}")
                return False
            
            # 创建当前配置的应急备份
            emergency_backup = self.home / f"openclaw.json.emergency.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(config_file, emergency_backup)
            
            # 恢复备份
            shutil.copy2(backup, config_file)
            logger.info(f"配置已回滚到: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"回滚失败：{e}")
            return False
    
    def format_audit_summary(self, record: Dict) -> str:
        """格式化审计记录为易读文本"""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"修复记录 ID: {record.get('id', 'N/A')}")
        lines.append(f"时间: {record.get('timestamp', 'N/A')}")
        lines.append(f"{'='*60}")
        
        # 错误信息
        lines.append(f"\n📋 错误信息:")
        lines.append(f"  类型: {record.get('error_type', 'N/A')}")
        lines.append(f"  描述: {record.get('error_detail', 'N/A')}")
        
        # 健康状态
        health = record.get('health_status', {})
        if health:
            lines.append(f"\n🏥 健康状态:")
            lines.append(f"  状态: {health.get('status', 'N/A')}")
            details = health.get('details', {})
            for key, value in details.items():
                if key != 'error':
                    lines.append(f"  {key}: {value}")
        
        # AI 分析
        ai_analysis = record.get('ai_analysis', {})
        if ai_analysis:
            lines.append(f"\n🤖 AI 分析:")
            lines.append(f"  分析结果: {ai_analysis.get('analysis', 'N/A')}")
            lines.append(f"  置信度: {ai_analysis.get('confidence', 'N/A')}")
            lines.append(f"  原始响应: {ai_analysis.get('raw_response', 'N/A')[:200]}...")
        
        # 执行的操作
        lines.append(f"\n🔧 执行的操作:")
        operations = record.get('operations', [])
        if operations:
            for i, op in enumerate(operations, 1):
                status = "✅" if op.get('success') else "❌"
                lines.append(f"  {i}. {status} {op.get('description', 'N/A')}")
                if op.get('command'):
                    lines.append(f"     命令: {op.get('command')}")
                if op.get('output'):
                    lines.append(f"     输出: {op.get('output')[:200]}")
                if op.get('error'):
                    lines.append(f"     错误: {op.get('error')}")
        else:
            lines.append("  (无操作)")
        
        # 结果
        lines.append(f"\n📊 修复结果:")
        result = record.get('result', {})
        lines.append(f"  成功: {'✅ 是' if result.get('success') else '❌ 否'}")
        lines.append(f"  修复后状态: {result.get('final_status', 'N/A')}")
        lines.append(f"  备份路径: {record.get('backup_path', 'N/A')}")
        
        if result.get('error'):
            lines.append(f"  错误: {result.get('error')}")
        
        lines.append(f"\n{'='*60}\n")
        return '\n'.join(lines)
    
    # ============ 知识库功能 ============
    
    def get_knowledge_base_file(self) -> Path:
        """获取知识库文件路径"""
        kb_config = CONFIG.get("knowledge_base", {})
        kb_path = kb_config.get("file", "~/.openclaw/memory/fix_knowledge_base.json")
        return Path(kb_path).expanduser()
    
    def load_knowledge_base(self) -> List[Dict]:
        """加载知识库"""
        kb_file = self.get_knowledge_base_file()
        if kb_file.exists():
            try:
                with open(kb_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载知识库失败：{e}")
        return []
    
    def save_knowledge_base(self, knowledge_list: List[Dict]):
        """保存知识库"""
        try:
            kb_file = self.get_knowledge_base_file()
            kb_file.parent.mkdir(parents=True, exist_ok=True)
            with open(kb_file, 'w') as f:
                json.dump(knowledge_list, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存知识库失败：{e}")
    
    def extract_error_signature(self, error_detail: str) -> str:
        """提取错误签名（用于去重）"""
        # 移除时间戳、PID 等变化的部分
        signature = error_detail
        # 移除时间戳模式
        signature = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', '[TIME]', signature)
        # 移除 PID
        signature = re.sub(r'\(\d+\)', '(PID)', signature)
        # 移除临时文件名
        signature = re.sub(r'/tmp/[^\s]+', '/tmp/[TEMP]', signature)
        # 计算哈希
        return hashlib.md5(signature.encode()).hexdigest()[:16]
    
    def find_similar_knowledge(self, error_detail: str, knowledge_list: List[Dict]) -> Optional[Dict]:
        """查找相似的知识条目"""
        new_sig = self.extract_error_signature(error_detail)
        for entry in knowledge_list:
            if entry.get('error_signature') == new_sig:
                return entry
        return None
    
    def add_to_knowledge_base(self, audit_record: Dict) -> Optional[Dict]:
        """
        将成功的修复经验添加到知识库
        返回：添加的知识条目（如果是重复则返回 None）
        """
        kb_config = CONFIG.get("knowledge_base", {})
        if not kb_config.get("enabled", True):
            return None
        
        result = audit_record.get('result', {})
        if not result.get('success', False):
            return None
        
        knowledge_list = self.load_knowledge_base()
        
        # 提取关键信息
        error_detail = audit_record.get('error_detail', '')
        error_signature = self.extract_error_signature(error_detail)
        
        # 检查是否已存在相似条目
        existing = self.find_similar_knowledge(error_detail, knowledge_list)
        if existing:
            # 更新计数和时间
            existing['occurrence_count'] = existing.get('occurrence_count', 1) + 1
            existing['last_occurrence'] = datetime.now().isoformat()
            self.save_knowledge_base(knowledge_list)
            logger.info(f"知识库条目已更新（第 {existing['occurrence_count']} 次发生）: {existing.get('id')}")
            return None  # 返回 None 表示没有新增
        
        # 创建新条目
        ai_analysis = audit_record.get('ai_analysis', {})
        operations = audit_record.get('operations', [])
        
        knowledge_entry = {
            "id": audit_record.get('id', hashlib.md5(str(time.time()).encode()).hexdigest()[:12]),
            "created_at": datetime.now().isoformat(),
            "last_occurrence": datetime.now().isoformat(),
            "occurrence_count": 1,
            "error_type": audit_record.get('error_type', 'unknown'),
            "error_detail": error_detail,
            "error_signature": error_signature,
            "error_logs_preview": audit_record.get('error_logs_preview', '')[:1000],
            "root_cause": ai_analysis.get('analysis', '未知'),
            "solution": {
                "description": self._format_solution(operations),
                "operations": [
                    {
                        "type": op.get('type'),
                        "description": op.get('description'),
                        "command": op.get('command'),
                        "file_path": op.get('file_path')
                    }
                    for op in operations if op.get('success')
                ]
            },
            "prevention": self._generate_prevention_tips(ai_analysis.get('analysis', '')),
            "tags": self._extract_tags(error_detail, ai_analysis.get('analysis', ''))
        }
        
        knowledge_list.insert(0, knowledge_entry)
        
        # 限制数量
        max_entries = kb_config.get("max_entries", 100)
        if len(knowledge_list) > max_entries:
            knowledge_list = knowledge_list[:max_entries]
        
        self.save_knowledge_base(knowledge_list)
        logger.info(f"新知识库条目已添加: {knowledge_entry['id']}")
        
        # 保存到 openclaw memory（如果启用）
        if kb_config.get("save_to_openclaw", True):
            self._save_to_openclaw_memory(knowledge_entry)
        
        return knowledge_entry
    
    def _format_solution(self, operations: List[Dict]) -> str:
        """格式化解决方案描述"""
        if not operations:
            return "自动重启服务"
        
        descriptions = []
        for op in operations:
            if op.get('success'):
                desc = op.get('description', '')
                if desc:
                    descriptions.append(desc)
        
        return "; ".join(descriptions) if descriptions else "配置修复"
    
    def _generate_prevention_tips(self, analysis: str) -> List[str]:
        """根据分析生成预防建议"""
        tips = []
        
        analysis_lower = analysis.lower()
        
        if "config" in analysis_lower or "配置" in analysis:
            tips.append("修改配置前使用 `openclaw validate` 验证配置")
            tips.append("重要修改前备份配置文件")
        
        if "permission" in analysis_lower or "权限" in analysis:
            tips.append("检查文件权限设置")
            tips.append("使用 `chmod 600 ~/.openclaw/openclaw.json` 设置正确权限")
        
        if "model" in analysis_lower or "模型" in analysis:
            tips.append("添加新模型前检查 input 类型是否支持")
            tips.append("参考文档确认模型配置格式")
        
        if "port" in analysis_lower or "端口" in analysis:
            tips.append("检查端口是否被其他程序占用")
            tips.append("使用 `lsof -i :18789` 查看端口占用")
        
        if not tips:
            tips.append("定期备份配置")
            tips.append("关注 watchdog 日志预警")
        
        return tips
    
    def _extract_tags(self, error_detail: str, analysis: str) -> List[str]:
        """提取标签"""
        tags = []
        text = (error_detail + " " + analysis).lower()
        
        tag_mapping = {
            "config": ["配置错误", "config", "configuration"],
            "permission": ["权限", "permission", "access denied"],
            "network": ["网络", "端口", "port", "connection", "network"],
            "model": ["模型", "model", "ai", "provider"],
            "service": ["服务", "service", "gateway", "进程"],
            "resource": ["资源", "内存", "cpu", "oom", "memory"],
        }
        
        for tag, keywords in tag_mapping.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        
        return tags if tags else ["general"]
    
    def _save_to_openclaw_memory(self, knowledge_entry: Dict):
        """保存到 openclaw memory 目录"""
        try:
            memory_dir = self.home / "memory"
            memory_dir.mkdir(exist_ok=True)
            
            # 创建 Markdown 格式的知识文档
            filename = f"fix_knowledge_{knowledge_entry['id']}.md"
            filepath = memory_dir / filename
            
            content = f"""# 修复知识库条目

## 基本信息
- **ID**: {knowledge_entry['id']}
- **创建时间**: {knowledge_entry['created_at']}
- **发生次数**: {knowledge_entry['occurrence_count']}
- **标签**: {', '.join(knowledge_entry.get('tags', []))}

## 问题描述
**类型**: {knowledge_entry['error_type']}

**详细错误**:
```
{knowledge_entry['error_detail'][:500]}
```

## 根本原因
{knowledge_entry['root_cause']}

## 解决方案
{knowledge_entry['solution']['description']}

### 具体操作
"""
            
            for i, op in enumerate(knowledge_entry['solution']['operations'], 1):
                content += f"\n{i}. **{op.get('description', 'N/A')}**\n"
                if op.get('command'):
                    content += f"   ```bash\n   {op.get('command')}\n   ```\n"
                if op.get('file_path'):
                    content += f"   文件: `{op.get('file_path')}`\n"
            
            content += f"""
## 预防措施
"""
            for tip in knowledge_entry['prevention']:
                content += f"- {tip}\n"
            
            content += f"""
## 相关日志预览
```
{knowledge_entry.get('error_logs_preview', '无')[:500]}
```

---
*此条目由 OpenClaw Watchdog AI 修复系统自动生成*
"""
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            logger.info(f"知识已保存到 openclaw memory: {filepath}")
            
        except Exception as e:
            logger.warning(f"保存到 openclaw memory 失败：{e}")
    
    def format_knowledge_notification(self, entry: Dict) -> str:
        """格式化知识库通知"""
        lines = []
        lines.append(f"📚 新知识已记录到知识库")
        lines.append(f"")
        lines.append(f"📝 问题类型: {entry.get('error_type', 'N/A')}")
        lines.append(f"🔍 根本原因: {entry.get('root_cause', 'N/A')[:150]}...")
        lines.append(f"")
        lines.append(f"✅ 解决方案:")
        lines.append(f"{entry.get('solution', {}).get('description', 'N/A')}")
        lines.append(f"")
        lines.append(f"🏷️ 标签: {', '.join(entry.get('tags', []))}")
        lines.append(f"")
        lines.append(f"⚠️ 预防措施:")
        for tip in entry.get('prevention', [])[:3]:
            lines.append(f"  • {tip}")
        lines.append(f"")
        lines.append(f"💡 查看完整知识库:")
        lines.append(f"  python3 ~/.openclaw/workspace/openclaw-watchdog-ctl.py knowledge")
        
        return '\n'.join(lines)
    
    def check_and_reset_counter(self) -> bool:
        """
        检查是否需要自动重置重启计数器
        返回：是否执行了重置
        """
        state = self.load_state()
        last_restart_str = state.get("last_restart")
        reset_hours = CONFIG.get("reset_counter_after_hours", 24)
        
        if not last_restart_str or self.restart_count == 0:
            return False
        
        try:
            last_restart = datetime.fromisoformat(last_restart_str)
            elapsed_hours = (datetime.now() - last_restart).total_seconds() / 3600
            
            if elapsed_hours >= reset_hours:
                logger.info(f"距离上次重启已过 {elapsed_hours:.1f} 小时，自动重置计数器")
                self.restart_count = 0
                state["restart_count"] = 0
                self.save_state(state)
                return True
        except Exception as e:
            logger.warning(f"检查重置时间失败：{e}")
        
        return False
    
    def get_api_key(self) -> Optional[str]:
        """从 openclaw 配置中获取 API key"""
        try:
            config_file = self.home / "openclaw.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                # 尝试从 bailian 配置获取
                providers = data.get("models", {}).get("providers", {})
                if "bailian" in providers:
                    return providers["bailian"].get("apiKey")
                # 尝试其他 provider
                for name, provider in providers.items():
                    if "apiKey" in provider:
                        return provider["apiKey"]
        except Exception as e:
            logger.warning(f"获取 API key 失败：{e}")
        return None
    
    def get_ai_config(self) -> Tuple[str, str]:
        """获取 AI 配置（模型和 endpoint）"""
        try:
            config_file = self.home / "openclaw.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                providers = data.get("models", {}).get("providers", {})
                if "bailian" in providers:
                    provider = providers["bailian"]
                    base_url = provider.get("baseUrl", "https://coding.dashscope.aliyuncs.com/v1")
                    # 使用第一个可用模型
                    models = provider.get("models", [])
                    if models:
                        model = models[0].get("id", "qwen-max")
                    else:
                        model = "qwen-max"
                    return model, base_url
        except Exception as e:
            logger.warning(f"获取 AI 配置失败：{e}")
        # 默认值
        return "qwen-max", "https://coding.dashscope.aliyuncs.com/v1"
    
    def call_ai_for_fix(self, error_logs: str, health_status: Dict) -> Tuple[bool, str, List[Dict]]:
        """
        调用 AI 分析问题并提供修复方案
        返回：(成功, 分析结果, 修复操作列表)
        """
        try:
            import urllib.request
            import urllib.error
        except ImportError:
            logger.error("无法导入 urllib，AI 修复不可用")
            return False, "缺少 urllib 模块", []
        
        api_key = CONFIG.get("ai_fix", {}).get("api_key") or self.get_api_key()
        if not api_key:
            return False, "未找到 API key", []
        
        # 从 openclaw 配置获取模型和 endpoint
        model, base_url = self.get_ai_config()
        timeout = CONFIG.get("ai_fix", {}).get("timeout_seconds", 120)
        
        # 构建提示词
        prompt = f"""你是一位专业的系统运维工程师。OpenClaw Gateway 服务启动失败，请分析问题并提供修复方案。

## 健康检查结果
```json
{json.dumps(health_status, indent=2, ensure_ascii=False)}
```

## 最近错误日志
```
{error_logs[:3000]}
```

## 你的任务
1. 分析问题根本原因
2. 提供具体的修复操作（命令或配置修改）
3. 以 JSON 格式返回修复方案

## 返回格式
```json
{{
  "analysis": "问题分析摘要",
  "confidence": "high|medium|low",
  "fixes": [
    {{
      "type": "command|config|file",
      "description": "操作描述",
      "command": "如果是 command 类型，提供具体命令",
      "file_path": "如果是 file/config 类型，提供文件路径",
      "content": "如果是 file 类型，提供文件内容"
    }}
  ]
}}
```

注意：
- 只返回 JSON，不要其他解释
- 命令必须是可执行的 shell 命令
- 对于配置文件修改，提供完整的修改后内容
- 如果无法确定问题，返回 confidence: low 和空的 fixes"""

        try:
            # 构建请求
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的系统运维助手，擅长诊断和修复服务故障。只输出 JSON 格式的修复方案。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            
            # 构建请求 URL（使用阿里云的 dashscope）
            chat_url = f"{base_url}/chat/completions" if not base_url.endswith('/v1') else f"{base_url}/chat/completions"
            
            req = urllib.request.Request(
                chat_url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method="POST"
            )
            
            logger.info(f"正在调用 AI 分析 ({model})...")
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result["choices"][0]["message"]["content"]
                
                # 提取 JSON
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
                
                try:
                    fix_plan = json.loads(content)
                    fixes = fix_plan.get("fixes", [])
                    analysis = fix_plan.get("analysis", "无分析")
                    confidence = fix_plan.get("confidence", "low")
                    
                    logger.info(f"AI 分析完成：{analysis[:100]}...")
                    logger.info(f"置信度：{confidence}，建议修复操作：{len(fixes)} 个")
                    
                    return confidence != "low", analysis, fixes
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"AI 返回格式错误：{e}")
                    return False, f"返回格式错误：{content[:200]}", []
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
            logger.error(f"API 调用失败：{e.code} - {error_body[:500]}")
            return False, f"API 错误：{e.code}", []
        except Exception as e:
            logger.error(f"AI 调用失败：{e}")
            return False, str(e), []
    
    def apply_fixes_with_audit(self, fixes: List[Dict], audit_record: Dict) -> List[Dict]:
        """应用修复操作并记录审计日志"""
        operations = []
        
        for fix in fixes:
            fix_type = fix.get("type")
            description = fix.get("description", "未知操作")
            
            op_record = {
                "type": fix_type,
                "description": description,
                "success": False,
                "command": None,
                "output": None,
                "error": None,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                if fix_type == "command":
                    command = fix.get("command", "")
                    if command:
                        logger.info(f"执行修复命令：{description}")
                        op_record["command"] = command
                        result = subprocess.run(
                            command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        op_record["output"] = result.stdout
                        if result.returncode == 0:
                            op_record["success"] = True
                            logger.info(f"✅ 命令执行成功: {description}")
                        else:
                            op_record["error"] = result.stderr
                            logger.warning(f"❌ 命令执行失败: {description} - {result.stderr[:200]}")
                            
                elif fix_type == "config" or fix_type == "file":
                    file_path = fix.get("file_path", "")
                    content = fix.get("content", "")
                    
                    if file_path and content:
                        # 解析路径
                        if file_path.startswith("~/"):
                            file_path = os.path.expanduser(file_path)
                        
                        logger.info(f"写入配置文件：{file_path}")
                        op_record["file_path"] = file_path
                        op_record["content_preview"] = content[:500] if len(content) > 500 else content
                        
                        # 备份原文件
                        if os.path.exists(file_path):
                            backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            shutil.copy2(file_path, backup_path)
                            op_record["file_backup"] = backup_path
                        
                        # 写入新内容
                        with open(file_path, 'w') as f:
                            f.write(content)
                        
                        op_record["success"] = True
                        logger.info(f"✅ 配置已写入: {file_path}")
                        
            except Exception as e:
                op_record["error"] = str(e)
                logger.error(f"❌ 操作失败: {description} - {e}")
            
            operations.append(op_record)
        
        audit_record["operations"] = operations
        return operations
    
    def attempt_ai_fix(self, health_status: Dict) -> Tuple[bool, str, List[Dict], Dict]:
        """
        尝试使用 AI 自动修复问题（带完整审计）
        返回：(是否成功修复, 分析结果, 应用的操作列表, 审计记录)
        """
        # 初始化审计记录
        audit_record = {
            "type": "ai_fix",
            "error_type": health_status.get("status", "unknown"),
            "error_detail": health_status.get("details", {}).get("error", "未知错误"),
            "health_status": health_status,
            "ai_analysis": {},
            "operations": [],
            "result": {},
            "backup_path": None,
            "logs_collected": {}
        }
        
        if not CONFIG.get("ai_fix", {}).get("enabled", False):
            audit_record["result"] = {"success": False, "error": "AI 修复已禁用"}
            self.add_audit_record(audit_record)
            return False, "AI 修复已禁用", [], audit_record
        
        logger.info("=" * 60)
        logger.info("开始 AI 自动修复流程")
        logger.info("=" * 60)
        
        # 第1步：创建备份
        backup_path = self.create_backup("before_ai_fix")
        audit_record["backup_path"] = backup_path
        if backup_path:
            logger.info(f"✅ 配置已备份到: {backup_path}")
        
        # 第2步：收集错误日志
        error_logs = ""
        logs_collected = {}
        
        # 从 journalctl 获取
        try:
            result = subprocess.run(
                ["journalctl", "--user", "-u", "openclaw-gateway", "--since", "30 minutes ago", "--no-pager"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                error_logs += result.stdout[-5000:]
                logs_collected["journalctl"] = {"success": True, "length": len(result.stdout)}
            else:
                logs_collected["journalctl"] = {"success": False, "error": result.stderr}
        except Exception as e:
            logs_collected["journalctl"] = {"success": False, "error": str(e)}
            logger.warning(f"获取 journal 日志失败：{e}")
        
        # 从 openclaw 日志获取
        try:
            log_files = list(Path("/tmp/openclaw").glob("openclaw-*.log"))
            if log_files:
                latest = max(log_files, key=lambda p: p.stat().st_mtime)
                result = subprocess.run(
                    ["tail", "-n", "100", str(latest)],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    error_logs += "\n\n" + result.stdout
                    logs_collected["openclaw_log"] = {"success": True, "file": str(latest), "length": len(result.stdout)}
                else:
                    logs_collected["openclaw_log"] = {"success": False, "error": result.stderr}
            else:
                logs_collected["openclaw_log"] = {"success": False, "error": "未找到日志文件"}
        except Exception as e:
            logs_collected["openclaw_log"] = {"success": False, "error": str(e)}
            logger.warning(f"获取 openclaw 日志失败：{e}")
        
        audit_record["logs_collected"] = logs_collected
        audit_record["error_logs_preview"] = error_logs[:2000] if len(error_logs) > 2000 else error_logs
        
        # 第3步：调用 AI 分析
        logger.info("正在调用 AI 分析问题...")
        ai_success, analysis, fixes = self.call_ai_for_fix(error_logs, health_status)
        
        audit_record["ai_analysis"] = {
            "success": ai_success,
            "analysis": analysis,
            "fixes_count": len(fixes),
            "fixes": fixes,
            "raw_response": None  # 可在 call_ai_for_fix 中记录
        }
        
        if not ai_success or not fixes:
            logger.error("AI 无法提供有效修复方案")
            audit_record["result"] = {
                "success": False,
                "error": "AI 无法提供有效修复方案",
                "analysis": analysis
            }
            self.add_audit_record(audit_record)
            
            # 生成摘要
            summary = self.format_audit_summary(audit_record)
            logger.info(f"修复失败摘要：\n{summary}")
            
            return False, analysis, [], audit_record
        
        logger.info(f"AI 分析完成，建议 {len(fixes)} 个修复操作")
        logger.info(f"分析结果：{analysis}")
        
        # 第4步：应用修复操作
        logger.info("正在应用修复操作...")
        operations = self.apply_fixes_with_audit(fixes, audit_record)
        
        # 第5步：验证修复结果
        logger.info("等待修复生效...")
        time.sleep(2)
        new_health = self.check_gateway_health()
        
        if new_health["status"] == "ok":
            logger.info("✅ 修复成功！Gateway 已恢复正常")
            audit_record["result"] = {
                "success": True,
                "final_status": "ok",
                "message": "修复成功"
            }
            self.add_audit_record(audit_record)
            
            summary = self.format_audit_summary(audit_record)
            logger.info(f"修复成功摘要：\n{summary}")
            
            return True, analysis, operations, audit_record
        
        # 尝试重启 Gateway
        logger.info("修复后尝试重启 Gateway...")
        restart_success = self.restart_gateway()
        audit_record["restart_attempted"] = True
        audit_record["restart_success"] = restart_success
        
        if restart_success:
            time.sleep(3)
            final_health = self.check_gateway_health()
            audit_record["final_health"] = final_health
            
            if final_health["status"] == "ok":
                logger.info("✅ 修复并重启成功！Gateway 已恢复正常")
                audit_record["result"] = {
                    "success": True,
                    "final_status": "ok",
                    "message": "修复后重启成功"
                }
                self.add_audit_record(audit_record)
                
                summary = self.format_audit_summary(audit_record)
                logger.info(f"修复成功摘要：\n{summary}")
                
                return True, analysis + " (修复后重启成功)", operations, audit_record
            else:
                logger.error(f"❌ 重启后仍不正常: {final_health}")
                audit_record["result"] = {
                    "success": False,
                    "final_status": final_health.get("status"),
                    "error": "重启后仍不正常"
                }
        else:
            logger.error("❌ 重启 Gateway 失败")
            audit_record["result"] = {
                "success": False,
                "error": "重启 Gateway 失败"
            }
        
        # 记录失败的审计
        self.add_audit_record(audit_record)
        
        summary = self.format_audit_summary(audit_record)
        logger.error(f"修复失败摘要：\n{summary}")
        
        return False, analysis + " (修复未解决问题)", operations, audit_record
    
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
    
    def check_functional_health(self) -> Dict:
        """
        功能性健康检查 - 检查服务是否真的在工作
        """
        health = {
            "functional_ok": True,
            "issues": [],
            "details": {}
        }
        
        # 1. 检查最近的日志中是否有 Telegram 持续错误
        log_file = Path("/tmp/openclaw/openclaw-2026-03-13.log")
        if log_file.exists():
            try:
                # 获取最近 10 分钟的日志
                import subprocess
                result = subprocess.run(
                    ["tail", "-n", "100", str(log_file)],
                    capture_output=True, text=True, timeout=5
                )
                recent_logs = result.stdout
                
                # 检查是否有持续的 Telegram 错误
                telegram_errors = recent_logs.count('"subsystem":"telegram') + recent_logs.count('[telegram]')
                delete_webhook_errors = recent_logs.count('deleteWebhook failed')
                polling_stalls = recent_logs.count('Polling stall detected')
                
                health["details"]["telegram_error_count"] = telegram_errors
                health["details"]["delete_webhook_errors"] = delete_webhook_errors
                health["details"]["polling_stalls"] = polling_stalls
                
                # 如果有持续的 deleteWebhook 失败，判定为卡住
                if delete_webhook_errors >= 3:
                    health["functional_ok"] = False
                    health["issues"].append(f"Telegram deleteWebhook 持续失败 ({delete_webhook_errors} 次)")
                
                # 如果有多次 polling stall，判定为不稳定
                if polling_stalls >= 2:
                    health["functional_ok"] = False
                    health["issues"].append(f"Telegram polling 多次停滞 ({polling_stalls} 次)")
                    
            except Exception as e:
                logger.warning(f"检查日志失败: {e}")
        
        # 2. 检查 systemd 日志中的错误
        try:
            result = subprocess.run(
                ["journalctl", "--user", "-u", "openclaw-gateway", "--since", "10 minutes ago", "-q"],
                capture_output=True, text=True, timeout=5
            )
            journal_logs = result.stdout
            
            # 检查关键错误模式
            if "deleteWebhook failed" in journal_logs and journal_logs.count("deleteWebhook failed") >= 3:
                health["functional_ok"] = False
                health["issues"].append("检测到持续的 Telegram API 错误")
            
            if "polling stall detected" in journal_logs and journal_logs.count("polling stall") >= 2:
                health["functional_ok"] = False
                health["issues"].append("检测到多次 polling 停滞")
                
        except Exception as e:
            logger.warning(f"检查 journal 失败: {e}")
        
        return health
    
    def check_gateway_health(self) -> Dict:
        """
        检查 Gateway 健康状态
        返回：{"status": "ok|error|dead|stuck", "details": {...}}
        """
        health = {
            "status": "ok",
            "details": {
                "port_listening": False,
                "process_running": False,
                "config_valid": False,
                "functional_ok": True,
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
        
        # 4. 功能性健康检查
        functional = self.check_functional_health()
        health["details"]["functional_ok"] = functional["functional_ok"]
        health["details"]["functional_issues"] = functional["issues"]
        
        # 5. 判断状态
        if not health["details"]["port_listening"] and not health["details"]["process_running"]:
            health["status"] = "dead"
            health["details"]["error"] = "Gateway 未运行"
        elif not health["details"]["port_listening"] and health["details"]["process_running"]:
            health["status"] = "error"
            health["details"]["error"] = "进程存在但端口未监听（可能卡死）"
        elif not health["details"]["config_valid"]:
            health["status"] = "error"
            health["details"]["error"] = "配置文件无效"
        elif not health["details"]["functional_ok"]:
            # 新增：功能性故障状态
            health["status"] = "stuck"
            health["details"]["error"] = f"服务功能性故障: {'; '.join(functional['issues'])}"
        
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
            # 成功启动后立即重置计数器
            old_count = self.restart_count
            self.restart_count = 0
            state = self.load_state()
            state["restart_count"] = 0
            state["last_restart"] = datetime.now().isoformat()
            state["last_success_start"] = datetime.now().isoformat()
            self.save_state(state)
            if old_count > 0:
                logger.info(f"Gateway 重启成功，重启计数器已重置（之前：{old_count}）")
            else:
                logger.info("Gateway 重启成功")
        else:
            self.restart_count += 1
            state = self.load_state()
            state["restart_count"] = self.restart_count
            state["last_restart"] = datetime.now().isoformat()
            self.save_state(state)
            logger.error(f"Gateway 重启失败（当前计数：{self.restart_count}）")
        
        return success
    
    def fix_common_issues(self, health: Dict = None) -> List[str]:
        """修复常见问题"""
        fixed = []
        
        # 1. 清理僵尸进程
        pids = self.check_gateway_process()
        if pids and not self.check_port():
            logger.info("检测到僵尸进程，正在清理...")
            self.kill_gateway()
            fixed.append("清理僵尸进程")
        
        # 2. 如果检测到功能性卡住（stuck），强制重启
        if health and health.get("status") == "stuck":
            logger.info("检测到服务功能性卡住，需要强制重启...")
            logger.info(f"问题详情: {health.get('details', {}).get('error', '未知')}")
            self.kill_gateway()
            fixed.append("清理卡住的服务进程")
            
            # 短暂等待确保端口释放
            time.sleep(3)
        
        # 3. 修复配置权限
        config_file = self.home / "openclaw.json"
        if config_file.exists():
            try:
                os.chmod(config_file, 0o600)
                fixed.append("修复配置权限")
            except Exception as e:
                logger.warning(f"修复权限失败：{e}")
        
        # 4. 清理锁文件
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
        
        # 首先检查是否需要自动重置计数器
        if self.restart_count >= CONFIG["max_restart_attempts"]:
            if self.check_and_reset_counter():
                self.send_notification(
                    "🔄 OpenClaw Watchdog\n\n"
                    f"重启计数器已自动重置（{CONFIG['reset_counter_after_hours']}小时规则）\n"
                    f"将继续尝试恢复 Gateway"
                )
        
        # 检查健康
        health = self.check_gateway_health()
        functional_status = "功能性正常" if health['details'].get('functional_ok', True) else f"功能性故障: {health['details'].get('functional_issues', [])}"
        logger.info(f"健康状态：{health['status']} - {health['details'].get('error', '正常')} | {functional_status}")
        
        if health["status"] == "ok":
            # 一切正常，重置重启计数（完全重置而非递减）
            if self.restart_count > 0:
                logger.info(f"服务运行正常，重置重启计数器（之前：{self.restart_count}）")
                self.restart_count = 0
                state = self.load_state()
                state["restart_count"] = 0
                self.save_state(state)
            return
        
        # 发现问题，尝试修复
        logger.warning(f"发现问题：{health['details'].get('error', '未知')}")
        
        # 尝试修复常见问题（传递 health 以便处理 stuck 状态）
        fixed = self.fix_common_issues(health)
        if fixed:
            logger.info(f"已修复：{fixed}")
        
        # 如果需要重启（包括 dead, error 和新增的 stuck 状态）
        if health["status"] in ["dead", "error", "stuck"]:
            if self.restart_count < CONFIG["max_restart_attempts"]:
                status_emoji = "🔧" if health["status"] != "stuck" else "🔄"
                status_text = "已自动重启" if health["status"] != "stuck" else "已自动重启（修复卡住问题）"
                
                success = self.restart_gateway()
                if success:
                    self.send_notification(
                        f"{status_emoji} OpenClaw Watchdog\n\n"
                        f"Gateway {status_text}\n"
                        f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"状态：{health['status']}\n"
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
                # 重启次数过多，尝试 AI 自动修复
                ai_fix_config = CONFIG.get("ai_fix", {})
                ai_fix_attempted = self.load_state().get("ai_fix_attempted", False)
                
                if ai_fix_config.get("enabled", False) and not ai_fix_attempted:
                    logger.warning("重启次数过多，尝试 AI 自动修复...")
                    self.send_notification(
                        f"🤖 OpenClaw Watchdog\n\n"
                        f"Gateway 重启失败 {self.restart_count} 次\n"
                        f"正在尝试 AI 自动修复..."
                    )
                    
                    # 执行 AI 修复（带完整审计）
                    fixed, analysis, operations, audit_record = self.attempt_ai_fix(health)
                    
                    # 记录已尝试 AI 修复
                    state = self.load_state()
                    state["ai_fix_attempted"] = True
                    state["ai_fix_time"] = datetime.now().isoformat()
                    state["ai_fix_result"] = "success" if fixed else "failed"
                    state["ai_analysis"] = analysis
                    state["last_audit_id"] = audit_record.get("id")
                    self.save_state(state)
                    
                    # 构建详细通知
                    error_detail = health.get("details", {}).get("error", "未知错误")
                    ops_summary = []
                    for i, op in enumerate(operations[:5], 1):
                        status = "✅" if op.get("success") else "❌"
                        ops_summary.append(f"{i}. {status} {op.get('description', 'N/A')}")
                    
                    if fixed:
                        logger.info(f"AI 修复成功：{analysis}")
                        self.restart_count = 0  # 重置计数器
                        state["restart_count"] = 0
                        state["last_success_start"] = datetime.now().isoformat()
                        self.save_state(state)
                        
                        # 添加到知识库
                        kb_entry = self.add_to_knowledge_base(audit_record)
                        
                        # 生成审计日志文件路径
                        audit_file = self.get_audit_log_file()
                        
                        # 构建基础通知
                        notification = (
                            f"✅ OpenClaw Watchdog - AI 修复成功\n\n"
                            f"📝 问题原因：\n{error_detail}\n\n"
                            f"🤖 AI 分析：\n{analysis[:300]}\n\n"
                            f"🔧 执行操作 ({len(operations)} 个)：\n" + "\n".join(ops_summary) + "\n\n"
                        )
                        
                        # 如果有新知识条目，添加知识库信息
                        if kb_entry:
                            kb_config = CONFIG.get("knowledge_base", {})
                            if kb_config.get("notify_user", True):
                                notification += (
                                    f"📚 知识库记录：\n"
                                    f"  新知识已记录，ID: {kb_entry.get('id')}\n"
                                    f"  标签: {', '.join(kb_entry.get('tags', []))}\n\n"
                                    f"⚠️ 预防建议：\n"
                                )
                                for tip in kb_entry.get('prevention', [])[:3]:
                                    notification += f"  • {tip}\n"
                                notification += "\n"
                        
                        notification += (
                            f"📄 详细日志：{audit_file}\n"
                            f"记录 ID：{audit_record.get('id', 'N/A')}"
                        )
                        
                        self.send_notification(notification)
                        
                        # 单独发送知识库通知（如果配置了）
                        if kb_entry:
                            kb_config = CONFIG.get("knowledge_base", {})
                            if kb_config.get("save_to_openclaw", True):
                                kb_notification = self.format_knowledge_notification(kb_entry)
                                self.send_notification(kb_notification)
                    else:
                        logger.error(f"AI 修复失败：{analysis}")
                        
                        # 生成审计日志文件路径
                        audit_file = self.get_audit_log_file()
                        
                        # 构建失败原因分析
                        fail_reasons = []
                        if not operations:
                            fail_reasons.append("• AI 未提供可执行的操作")
                        else:
                            failed_ops = [op for op in operations if not op.get("success")]
                            if failed_ops:
                                fail_reasons.append(f"• {len(failed_ops)} 个操作执行失败")
                        
                        # 尝试获取更详细的错误
                        final_error = audit_record.get("result", {}).get("error", "未知")
                        
                        self.send_notification(
                            f"❌ OpenClaw Watchdog - AI 修复失败\n\n"
                            f"📝 问题原因：\n{error_detail}\n\n"
                            f"🤖 AI 分析：\n{analysis[:300]}\n\n"
                            f"⚠️ 失败原因：\n" + "\n".join(fail_reasons) + f"\n• {final_error}\n\n"
                            f"🔧 尝试的操作 ({len(operations)} 个)：\n" + "\n".join(ops_summary) + "\n\n"
                            f"📄 详细日志：{audit_file}\n"
                            f"记录 ID：{audit_record.get('id', 'N/A')}\n\n"
                            f"💡 建议：\n"
                            f"1. 查看详细日志了解失败原因\n"
                            f"2. 手动修复问题\n"
                            f"3. 使用 openclaw-watchdog-ctl.py reset 重置计数器"
                        )
                else:
                    logger.error("重启次数过多，停止自动重启")
                    reason = "AI 修复已禁用" if not ai_fix_config.get("enabled", False) else "AI 修复已尝试但未成功"
                    self.send_notification(
                        f"🚨 OpenClaw Watchdog\n\n"
                        f"Gateway 重启失败次数过多（{self.restart_count}次）\n"
                        f"{reason}\n"
                        f"需要手动干预"
                    )
    
    def run(self):
        """主运行循环"""
        logger.info("=" * 50)
        logger.info("OpenClaw Watchdog 启动")
        logger.info(f"检查间隔：{CONFIG['check_interval_seconds']}秒（含功能性健康检查）")
        logger.info(f"最大重启次数：{CONFIG['max_restart_attempts']}")
        logger.info(f"检测项目：进程、端口、配置、Telegram API 状态、Polling 状态")
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
