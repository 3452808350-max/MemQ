# @file: agent.py
# @module: openclaw.core.agent
# @purpose: "Define AI-First Agent system"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# @enum: AgentMode
# @ai_readable: true
class AgentMode(str, Enum):
    """
    @value: AUTONOMOUS - Full autonomous mode
    @value: HUMAN_IN_LOOP - Human approval required
    @value: SUPERVISED - Human supervised
    """
    AUTONOMOUS = "autonomous"
    HUMAN_IN_LOOP = "human_in_loop"
    SUPERVISED = "supervised"

# @schema: AgentCapability
# @ai_readable: true
@dataclass
class AgentCapability:
    """@purpose: Agent capability definition"""
    
    # @field: name
    # @type: str
    name: str
    
    # @field: description
    # @type: str
    description: str
    
    # @field: parameters
    # @type: Dict[str, Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # @field: required_permissions
    # @type: List[str]
    required_permissions: List[str] = field(default_factory=list)

# @schema: AgentConfig
# @ai_readable: true
@dataclass
class AgentConfig:
    """@purpose: Agent configuration"""
    
    # @field: name
    # @type: str
    # @required: true
    name: str
    
    # @field: description
    # @type: str
    # @default: ""
    description: str = ""
    
    # @field: mode
    # @type: AgentMode
    # @default: HUMAN_IN_LOOP
    mode: AgentMode = AgentMode.HUMAN_IN_LOOP
    
    # @field: capabilities
    # @type: List[AgentCapability]
    capabilities: List[AgentCapability] = field(default_factory=list)
    
    # @field: system_prompt
    # @type: str
    system_prompt: str = "You are a helpful AI assistant."
    
    # @field: max_iterations
    # @type: int
    # @default: 10
    max_iterations: int = 10
    
    # @field: timeout_seconds
    # @type: int
    # @default: 300
    timeout_seconds: int = 300

# @class: Agent
# @purpose: "AI-First Agent implementation"
# @dependencies: ["AgentConfig", "AgentCapability"]
# @ai_testable: true
class Agent:
    """
    @summary: AI-First Agent with explicit capabilities
    
    @features:
      - Explicit capability declaration
      - Mode-based execution
      - Tool integration
      - Context awareness
    """
    
    # @attribute: config
    # @type: AgentConfig
    config: AgentConfig
    
    # @attribute: capabilities
    # @type: Dict[str, AgentCapability]
    capabilities: Dict[str, AgentCapability]
    
    # @constructor
    def __init__(self, config: AgentConfig):
        """@purpose: Initialize agent"""
        self.config = config
        self.capabilities = {
            cap.name: cap
            for cap in config.capabilities
        }
    
    # @function: can_execute
    # @purpose: "Check if agent can execute action"
    # @input: action: str, context: Dict[str, Any]
    # @output: bool
    # @ai_testable: true
    def can_execute(self, action: str, context: Dict[str, Any]) -> bool:
        """
        @summary: Check execution permission
        
        @steps:
          1. Check mode
          2. Check capabilities
          3. Check permissions
          4. Return decision
        """
        
        # @step: 1
        if self.config.mode == AgentMode.SUPERVISED:
            return False
        
        # @step: 2
        if action not in self.capabilities:
            return False
        
        # @step: 3
        cap = self.capabilities[action]
        # Check permissions (simplified)
        
        # @step: 4
        return True
    
    # @function: execute
    # @purpose: "Execute action"
    # @input: action: str, input_data: Dict[str, Any]
    # @output: Dict[str, Any]
    # @raises: PermissionError, TimeoutError
    # @ai_testable: true
    async def execute(
        self,
        action: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """@purpose: Execute action"""
        
        if not self.can_execute(action, input_data):
            raise PermissionError(f"Cannot execute {action}")
        
        # Execute action (simplified)
        result = {
            "action": action,
            "status": "success",
            "data": {}
        }
        
        return result
    
    # @function: get_capabilities
    # @purpose: "Get agent capabilities"
    # @output: List[Dict[str, Any]]
    # @ai_testable: true
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """@purpose: Get capabilities list"""
        
        return [
            {
                "name": cap.name,
                "description": cap.description,
                "parameters": cap.parameters
            }
            for cap in self.capabilities.values()
        ]
