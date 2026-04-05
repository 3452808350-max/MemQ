#!/usr/bin/env python3
"""
Team Mode 状态管理器
解决 subagent 和主 session 响应冲突问题
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

STATE_FILE = ".agent-state.json"


class TeamModeManager:
    """管理 Team Mode 状态，确保主 Session 和 Subagent 不会冲突响应"""
    
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self._ensure_state_file()
    
    def _ensure_state_file(self):
        """确保状态文件存在"""
        if not os.path.exists(self.state_file):
            self._save_state({
                "lastResponse": {},
                "teamMode": {
                    "active": False,
                    "startTime": None,
                    "endTime": None,
                    "subagents": [],
                    "taskDescription": None
                }
            })
    
    def _load_state(self) -> Dict[str, Any]:
        """加载状态"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"lastResponse": {}, "teamMode": {"active": False}}
    
    def _save_state(self, state: Dict[str, Any]):
        """保存状态"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def start(self, task_description: str, subagent_count: int = 0):
        """启动 Team Mode"""
        state = self._load_state()
        state["teamMode"] = {
            "active": True,
            "startTime": datetime.now().isoformat(),
            "endTime": None,
            "subagentCount": subagent_count,
            "completed": [],
            "taskDescription": task_description
        }
        self._save_state(state)
        print(f"[TeamMode] Started: {task_description}")
    
    def complete(self):
        """完成 Team Mode"""
        state = self._load_state()
        state["teamMode"]["active"] = False
        state["teamMode"]["endTime"] = datetime.now().isoformat()
        self._save_state(state)
        print("[TeamMode] Completed")
    
    def is_active(self) -> bool:
        """检查是否处于 Team Mode"""
        state = self._load_state()
        return state.get("teamMode", {}).get("active", False)
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return self._load_state().get("teamMode", {})
    
    def should_respond_to_message(self, message_id: str) -> bool:
        """
        判断是否应该响应此消息
        避免重复响应和冲突
        """
        state = self._load_state()
        
        # 检查是否已响应过
        last = state.get("lastResponse", {})
        if last.get("messageId") == message_id:
            return False
        
        # Team Mode 期间，只有汇总消息可以响应
        if state.get("teamMode", {}).get("active"):
            # 检查是否是取消命令
            return False
        
        return True
    
    def record_response(self, message_id: str, content: str, responder: str = "main"):
        """记录响应，用于去重"""
        state = self._load_state()
        state["lastResponse"] = {
            "messageId": message_id,
            "timestamp": datetime.now().isoformat(),
            "responder": responder,
            "contentPreview": content[:100] if content else ""
        }
        self._save_state(state)
    
    def mark_subagent_complete(self, subagent_id: str):
        """标记 subagent 完成"""
        state = self._load_state()
        if "completed" not in state["teamMode"]:
            state["teamMode"]["completed"] = []
        state["teamMode"]["completed"].append({
            "id": subagent_id,
            "time": datetime.now().isoformat()
        })
        self._save_state(state)


# 便捷函数
def is_team_mode_active() -> bool:
    """检查是否处于 Team Mode"""
    return TeamModeManager().is_active()


def start_team_mode(task: str, subagent_count: int = 0):
    """启动 Team Mode"""
    TeamModeManager().start(task, subagent_count)


def complete_team_mode():
    """完成 Team Mode"""
    TeamModeManager().complete()


def get_team_status() -> Dict[str, Any]:
    """获取 Team Mode 状态"""
    return TeamModeManager().get_status()


if __name__ == "__main__":
    # 测试
    manager = TeamModeManager()
    
    print("Testing TeamModeManager...")
    
    # 测试启动
    manager.start("Test task", 3)
    assert manager.is_active() == True
    print("✓ Start works")
    
    # 测试状态
    status = manager.get_status()
    assert status["active"] == True
    assert status["taskDescription"] == "Test task"
    print("✓ Status works")
    
    # 测试响应检查
    assert manager.should_respond_to_message("msg1") == False  # Team mode active
    print("✓ Should respond check works")
    
    # 测试完成
    manager.complete()
    assert manager.is_active() == False
    print("✓ Complete works")
    
    # 测试响应记录
    manager.record_response("msg2", "Test response")
    assert manager.should_respond_to_message("msg2") == False
    print("✓ Response recording works")
    
    print("\nAll tests passed!")
