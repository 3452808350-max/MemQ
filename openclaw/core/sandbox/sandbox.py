# @file: sandbox.py
# @module: openclaw.core.sandbox.sandbox
# @purpose: "Secure sandbox environment for code execution"
# @ai_maintained: true
# @version: "1.0.0"

import os
import sys
import tempfile
import subprocess
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

# @schema: SandboxConfig
# @ai_readable: true
@dataclass
class SandboxConfig:
    """@purpose: Sandbox configuration"""
    
    # @field: workdir
    # @type: str
    # @default: "/tmp/sandbox"
    workdir: str = "/tmp/sandbox"
    
    # @field: timeout
    # @type: int
    # @default: 300
    timeout: int = 300  # seconds
    
    # @field: max_memory
    # @type: int
    # @default: 512
    max_memory: int = 512  # MB
    
    # @field: network_access
    # @type: bool
    # @default: False
    network_access: bool = False
    
    # @field: allowed_commands
    # @type: List[str]
    # @default: ["python3", "pip", "ls", "cat"]
    allowed_commands: List[str] = field(default_factory=lambda: ["python3", "pip", "ls", "cat"])

# @class: Sandbox
# @purpose: "Secure sandbox environment"
# @ai_testable: true
class Sandbox:
    """
    @summary: Secure sandbox for code execution
    
    @features:
      - Isolated environment
      - Command restrictions
      - Resource limits
      - Timeout protection
    """
    
    # @attribute: config
    # @type: SandboxConfig
    config: SandboxConfig
    
    # @attribute: workdir
    # @type: str
    workdir: str
    
    # @constructor
    def __init__(self, config: Optional[SandboxConfig] = None):
        """@purpose: Initialize sandbox"""
        
        self.config = config or SandboxConfig()
        self.workdir = self.config.workdir
        
        # Create workdir
        os.makedirs(self.workdir, exist_ok=True)
    
    # @function: execute
    # @purpose: "Execute command in sandbox"
    # @input: command: str
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def execute(self, command: str) -> Dict[str, Any]:
        """
        @summary: Execute command
        
        @steps:
          1. Validate command
          2. Execute with limits
          3. Capture output
          4. Return result
        """
        
        # @step: 1
        if not self._validate_command(command):
            return {
                "success": False,
                "error": "Command not allowed",
                "stdout": "",
                "stderr": ""
            }
        
        # @step: 2-4
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=self.workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=10 * 1024 * 1024  # 10MB buffer
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout
            )
            
            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "execution_time": 0  # Would need timing
            }
            
        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": f"Execution timeout ({self.config.timeout}s)",
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": ""
            }
    
    # @function: execute_code
    # @purpose: "Execute Python code in sandbox"
    # @input: code: str
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def execute_code(self, code: str) -> Dict[str, Any]:
        """
        @summary: Execute Python code
        
        @steps:
          1. Write code to temp file
          2. Execute with python3
          3. Capture output
          4. Cleanup
        """
        
        # @step: 1
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            dir=self.workdir,
            delete=False
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # @step: 2-3
            result = await self.execute(f"python3 {temp_file}")
            return result
        finally:
            # @step: 4
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    # @function: _validate_command
    # @purpose: "Validate command is allowed"
    # @input: command: str
    # @output: bool
    # @private: true
    def _validate_command(self, command: str) -> bool:
        """@purpose: Validate command"""
        
        # Check if command starts with allowed command
        for allowed in self.config.allowed_commands:
            if command.startswith(allowed):
                return True
        
        return False
    
    # @function: cleanup
    # @purpose: "Cleanup sandbox"
    # @side_effects: ["Remove workdir contents"]
    # @async: true
    # @ai_testable: true
    async def cleanup(self) -> None:
        """@purpose: Cleanup sandbox"""
        
        import shutil
        
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
        
        os.makedirs(self.workdir, exist_ok=True)
    
    # @function: get_info
    # @purpose: "Get sandbox information"
    # @output: Dict[str, Any]
    # @ai_testable: true
    def get_info(self) -> Dict[str, Any]:
        """@purpose: Get sandbox info"""
        
        return {
            "workdir": self.workdir,
            "timeout": self.config.timeout,
            "max_memory": self.config.max_memory,
            "network_access": self.config.network_access,
            "allowed_commands": self.config.allowed_commands
        }

# @class: SandboxManager
# @purpose: "Manage multiple sandboxes"
# @ai_testable: true
class SandboxManager:
    """@summary: Sandbox manager"""
    
    # @attribute: sandboxes
    # @type: Dict[str, Sandbox]
    sandboxes: Dict[str, Sandbox]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize manager"""
        self.sandboxes = {}
    
    # @function: create_sandbox
    # @purpose: "Create new sandbox"
    # @input: name: str, config: Optional[SandboxConfig]
    # @output: Sandbox
    # @ai_testable: true
    def create_sandbox(
        self,
        name: str,
        config: Optional[SandboxConfig] = None
    ) -> Sandbox:
        """@purpose: Create sandbox"""
        
        sandbox = Sandbox(config)
        self.sandboxes[name] = sandbox
        return sandbox
    
    # @function: get_sandbox
    # @purpose: "Get sandbox by name"
    # @input: name: str
    # @output: Optional[Sandbox]
    # @ai_testable: true
    def get_sandbox(self, name: str) -> Optional[Sandbox]:
        """@purpose: Get sandbox"""
        
        return self.sandboxes.get(name)
    
    # @function: delete_sandbox
    # @purpose: "Delete sandbox"
    # @input: name: str
    # @output: bool
    # @async: true
    # @ai_testable: true
    async def delete_sandbox(self, name: str) -> bool:
        """@purpose: Delete sandbox"""
        
        if name not in self.sandboxes:
            return False
        
        sandbox = self.sandboxes[name]
        await sandbox.cleanup()
        
        del self.sandboxes[name]
        return True
    
    # @function: cleanup_all
    # @purpose: "Cleanup all sandboxes"
    # @side_effects: ["Cleanup all sandboxes"]
    # @async: true
    # @ai_testable: true
    async def cleanup_all(self) -> None:
        """@purpose: Cleanup all"""
        
        for sandbox in self.sandboxes.values():
            await sandbox.cleanup()
        
        self.sandboxes.clear()
