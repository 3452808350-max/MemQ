#!/usr/bin/env python3
"""
Kimi Wire模式封装 - 结构化双向通信

用于OpenClaw与Kimi CLI的集成
基于JSON-RPC 2.0协议

使用方式:
    from kimi_wire import KimiWireClient
    
    client = KimiWireClient()
    result = client.prompt("分析茅台的技术面")
    print(result['text'])
"""
import subprocess
import json
import threading
import queue
import uuid
import re
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


class MessageType(Enum):
    """Wire消息类型"""
    TURN_BEGIN = "TurnBegin"
    TURN_END = "TurnEnd"
    STEP_BEGIN = "StepBegin"
    STEP_END = "StepEnd"
    THINK = "ThinkPart"
    TEXT = "TextPart"
    CONTENT = "ContentPart"
    STATUS_UPDATE = "StatusUpdate"
    TOOL_CALL = "ToolCallPart"
    ERROR = "ErrorPart"


@dataclass
class WireEvent:
    """Wire事件"""
    type: str
    payload: Dict[str, Any]
    
    def get_text(self) -> Optional[str]:
        """获取文本内容"""
        if self.type in ("TextPart", "ContentPart"):
            return self.payload.get("text")
        return None


@dataclass
class WireResult:
    """Wire会话结果"""
    success: bool
    text: str = ""
    thoughts: List[str] = field(default_factory=list)
    events: List[WireEvent] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)
    status: str = "finished"
    error: Optional[str] = None


class KimiWireClient:
    """
    Kimi Wire模式客户端
    
    通过stdin/stdout与kimi --wire进程进行JSON-RPC通信
    """
    
    def __init__(
        self,
        agent_file: str = None,
        work_dir: str = "/home/kyj/.openclaw/workspace",
        timeout: int = 300
    ):
        """
        初始化Wire客户端
        
        Args:
            agent_file: Agent配置文件路径
            work_dir: 工作目录
            timeout: 默认超时时间(秒)
        """
        self.agent_file = agent_file or "/home/kyj/.openclaw/workspace/kimi-dss-agent/dss-agent.yaml"
        self.work_dir = work_dir
        self.timeout = timeout
        
        self._process = None
        self._reader_thread = None
        self._response_queue = queue.Queue()
        self._event_queue = queue.Queue()
        self._pending_requests: Dict[str, queue.Queue] = {}
        
    def start(self):
        """启动Kimi Wire进程"""
        cmd = ["kimi", "--wire"]
        if self.agent_file:
            cmd.extend(["--agent-file", self.agent_file])
        
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.work_dir
        )
        
        # 启动读取线程
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        
        # 发送initialize
        self._initialize()
    
    def stop(self):
        """停止Wire进程"""
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None
    
    def _read_loop(self):
        """读取stdout的循环"""
        while self._process and self._process.poll() is None:
            try:
                line = self._process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    msg = json.loads(line)
                    self._handle_message(msg)
                except json.JSONDecodeError:
                    continue
                    
            except Exception:
                break
    
    def _handle_message(self, msg: Dict):
        """处理接收到的消息"""
        # 检查是否是响应
        if "id" in msg:
            msg_id = msg["id"]
            if msg_id in self._pending_requests:
                self._pending_requests[msg_id].put(msg)
            else:
                self._response_queue.put(msg)
        
        # 检查是否是事件/请求
        if msg.get("method") == "event":
            event = WireEvent(
                type=msg["params"].get("type"),
                payload=msg["params"].get("payload", {})
            )
            self._event_queue.put(event)
        
        elif msg.get("method") == "request":
            # Agent请求（如审批、工具调用）
            self._handle_request(msg)
    
    def _handle_request(self, msg: Dict):
        """处理Agent的请求（审批、工具调用等）"""
        request_type = msg["params"].get("type")
        payload = msg["params"].get("payload", {})
        
        # 自动批准常见操作
        if request_type == "ApprovalRequest":
            # 自动批准
            response = {
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {
                    "request_id": payload.get("id"),
                    "response": "approve"
                }
            }
            self._send(response)
        
        elif request_type == "ToolCallRequest":
            # 外部工具调用 - 这里可以扩展
            tool_name = payload.get("name")
            # 默认返回成功
            response = {
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {
                    "tool_call_id": payload.get("id"),
                    "return_value": {"success": True}
                }
            }
            self._send(response)
    
    def _send(self, msg: Dict):
        """发送消息到进程"""
        if self._process and self._process.stdin:
            self._process.stdin.write(json.dumps(msg) + "\n")
            self._process.stdin.flush()
    
    def _initialize(self) -> Dict:
        """初始化握手"""
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": str(uuid.uuid4()),
            "params": {
                "protocol_version": "1.6",
                "client": {
                    "name": "dss-wire-client",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "supports_question": True,
                    "supports_plan_mode": False
                }
            }
        }
        
        return self._send_request(init_request)
    
    def _send_request(self, request: Dict, timeout: int = None) -> Dict:
        """发送请求并等待响应"""
        request_id = request["id"]
        response_queue = queue.Queue()
        self._pending_requests[request_id] = response_queue
        
        self._send(request)
        
        try:
            return response_queue.get(timeout=timeout or self.timeout)
        except queue.Empty:
            return {"error": "Timeout"}
        finally:
            del self._pending_requests[request_id]
    
    def prompt(self, user_input: str, timeout: int = None) -> WireResult:
        """
        发送用户输入并运行Agent轮次
        
        Args:
            user_input: 用户输入
            timeout: 超时时间
            
        Returns:
            WireResult对象
        """
        if not self._process:
            self.start()
        
        request = {
            "jsonrpc": "2.0",
            "method": "prompt",
            "id": str(uuid.uuid4()),
            "params": {
                "user_input": user_input
            }
        }
        
        # 收集事件
        events = []
        texts = []
        thoughts = []
        token_usage = {}
        
        # 发送请求
        response = self._send_request(request, timeout=timeout or self.timeout)
        
        # 收集事件直到轮次结束
        start_time = time.time()
        while True:
            try:
                event = self._event_queue.get(timeout=1)
                events.append(event)
                
                if event.type == "TextPart":
                    text = event.payload.get("text", "")
                    if text:
                        texts.append(text)
                
                elif event.type == "ThinkPart":
                    thought = event.payload.get("think", "")
                    if thought:
                        thoughts.append(thought)
                
                elif event.type == "StatusUpdate":
                    token_usage = event.payload.get("token_usage", {})
                
                elif event.type == "TurnEnd":
                    break
                    
            except queue.Empty:
                if time.time() - start_time > (timeout or self.timeout):
                    break
        
        result = response.get("result", {})
        
        return WireResult(
            success=response.get("error") is None,
            text="\n".join(texts),
            thoughts=thoughts,
            events=events,
            token_usage=token_usage,
            status=result.get("status", "unknown"),
            error=response.get("error")
        )
    
    def steer(self, user_input: str) -> bool:
        """
        在轮次进行中注入用户消息
        
        Args:
            user_input: 注入的消息
            
        Returns:
            是否成功
        """
        request = {
            "jsonrpc": "2.0",
            "method": "steer",
            "id": str(uuid.uuid4()),
            "params": {
                "user_input": user_input
            }
        }
        
        response = self._send_request(request)
        return response.get("result", {}).get("status") == "steered"
    
    def cancel(self):
        """取消当前轮次"""
        request = {
            "jsonrpc": "2.0",
            "method": "cancel",
            "id": str(uuid.uuid4()),
            "params": {}
        }
        self._send_request(request)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


# 便捷函数
def run_kimi_wire(prompt: str, agent_file: str = None, timeout: int = 300) -> WireResult:
    """
    快捷运行Kimi Wire
    
    Args:
        prompt: 用户输入
        agent_file: Agent配置文件
        timeout: 超时时间
        
    Returns:
        WireResult对象
    """
    with KimiWireClient(agent_file=agent_file, timeout=timeout) as client:
        return client.prompt(prompt)


# 命令行入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python kimi_wire.py \"你的问题\"")
        sys.exit(1)
    
    prompt_text = sys.argv[1]
    result = run_kimi_wire(prompt_text)
    
    if result.success:
        print(result.text)
        if result.token_usage:
            print(f"\n--- Token使用: {result.token_usage} ---", file=sys.stderr)
    else:
        print(f"错误: {result.error}", file=sys.stderr)
        sys.exit(1)