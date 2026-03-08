# @file: subagent.py
# @module: openclaw.core.agent.subagent
# @purpose: "Subagent system for multi-agent collaboration"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import uuid

# @enum: AgentState
# @ai_readable: true
class AgentState(str, Enum):
    """
    @value: IDLE - Agent is idle
    @value: WORKING - Agent is working
    @value: WAITING - Agent is waiting
    @value: ERROR - Agent has error
    """
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"

# @schema: SubAgentConfig
# @ai_readable: true
@dataclass
class SubAgentConfig:
    """@purpose: Subagent configuration"""
    
    # @field: name
    # @type: str
    name: str
    
    # @field: description
    # @type: str
    description: str = ""
    
    # @field: skills
    # @type: List[str]
    skills: List[str] = field(default_factory=list)
    
    # @field: max_iterations
    # @type: int
    # @default: 10
    max_iterations: int = 10
    
    # @field: timeout
    # @type: int
    # @default: 300
    timeout: int = 300  # seconds

# @class: SubAgent
# @purpose: "Subagent implementation"
# @ai_testable: true
class SubAgent:
    """
    @summary: Subagent for task execution
    
    @features:
      - Task execution
      - Skill usage
      - State management
      - Timeout protection
    """
    
    # @attribute: config
    # @type: SubAgentConfig
    config: SubAgentConfig
    
    # @attribute: state
    # @type: AgentState
    state: AgentState
    
    # @attribute: current_task
    # @type: Optional[str]
    current_task: Optional[str]
    
    # @attribute: skills
    # @type: Dict[str, Callable]
    skills: Dict[str, Callable]
    
    # @constructor
    def __init__(self, config: SubAgentConfig):
        """@purpose: Initialize subagent"""
        
        self.config = config
        self.state = AgentState.IDLE
        self.current_task = None
        self.skills = {}
    
    # @function: register_skill
    # @purpose: "Register skill"
    # @input: name: str, skill: Callable
    # @side_effects: ["Add skill to skills"]
    # @ai_testable: true
    def register_skill(self, name: str, skill: Callable) -> None:
        """@purpose: Register skill"""
        
        self.skills[name] = skill
    
    # @function: execute
    # @purpose: "Execute task"
    # @input: task: str, context: Optional[Dict[str, Any]]
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        @summary: Execute task
        
        @steps:
          1. Set state to WORKING
          2. Execute task
          3. Handle result
          4. Update state
        """
        
        # @step: 1
        self.state = AgentState.WORKING
        self.current_task = task
        
        try:
            # @step: 2
            result = await self._execute_task(task, context or {})
            
            # @step: 3-4
            self.state = AgentState.IDLE
            self.current_task = None
            
            return {
                "success": True,
                "result": result,
                "agent": self.config.name
            }
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.current_task = None
            
            return {
                "success": False,
                "error": str(e),
                "agent": self.config.name
            }
    
    # @function: _execute_task
    # @purpose: "Internal task execution"
    # @input: task: str, context: Dict[str, Any]
    # @output: Any
    # @private: true
    # @async: true
    async def _execute_task(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Any:
        """@purpose: Execute task internally"""
        
        # Simple task execution
        # In real implementation, this would use LLM
        return await self._process_task(task, context)
    
    # @function: _process_task
    # @purpose: "Process task using skills"
    # @input: task: str, context: Dict[str, Any]
    # @output: Any
    # @private: true
    # @async: true
    async def _process_task(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Any:
        """@purpose: Process task"""
        
        # Use skills to process task
        # This is a simplified implementation
        return {
            "task": task,
            "context": context,
            "skills_used": list(self.skills.keys())
        }
    
    # @function: get_status
    # @purpose: "Get agent status"
    # @output: Dict[str, Any]
    # @ai_testable: true
    def get_status(self) -> Dict[str, Any]:
        """@purpose: Get status"""
        
        return {
            "name": self.config.name,
            "state": self.state.value,
            "current_task": self.current_task,
            "skills": list(self.skills.keys())
        }

# @class: SubAgentCoordinator
# @purpose: "Coordinate multiple subagents"
# @ai_testable: true
class SubAgentCoordinator:
    """
    @summary: Coordinate multiple subagents
    
    @features:
      - Agent management
      - Task distribution
      - Result aggregation
      - Error handling
    """
    
    # @attribute: agents
    # @type: Dict[str, SubAgent]
    agents: Dict[str, SubAgent]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize coordinator"""
        
        self.agents = {}
    
    # @function: add_agent
    # @purpose: "Add subagent"
    # @input: agent: SubAgent
    # @side_effects: ["Add agent to agents"]
    # @ai_testable: true
    def add_agent(self, agent: SubAgent) -> None:
        """@purpose: Add agent"""
        
        self.agents[agent.config.name] = agent
    
    # @function: remove_agent
    # @purpose: "Remove subagent"
    # @input: name: str
    # @output: bool
    # @ai_testable: true
    def remove_agent(self, name: str) -> bool:
        """@purpose: Remove agent"""
        
        if name in self.agents:
            del self.agents[name]
            return True
        return False
    
    # @function: distribute_task
    # @purpose: "Distribute task to agents"
    # @input: task: str, agent_names: Optional[List[str]]
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def distribute_task(
        self,
        task: str,
        agent_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        @summary: Distribute task
        
        @steps:
          1. Select agents
          2. Distribute task
          3. Collect results
          4. Aggregate results
        """
        
        # @step: 1
        if agent_names:
            agents = [
                self.agents[name]
                for name in agent_names
                if name in self.agents
            ]
        else:
            agents = list(self.agents.values())
        
        if not agents:
            return {
                "success": False,
                "error": "No agents available"
            }
        
        # @step: 2-3
        tasks = [
            agent.execute(task, {"agent": agent.config.name})
            for agent in agents
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # @step: 4
        return {
            "success": True,
            "results": results,
            "agents_used": len(agents)
        }
    
    # @function: get_status
    # @purpose: "Get coordinator status"
    # @output: Dict[str, Any]
    # @ai_testable: true
    def get_status(self) -> Dict[str, Any]:
        """@purpose: Get status"""
        
        return {
            "total_agents": len(self.agents),
            "agents": {
                name: agent.get_status()
                for name, agent in self.agents.items()
            }
        }

# @class: AgentFactory
# @purpose: "Create subagents"
# @ai_testable: true
class AgentFactory:
    """@summary: Agent factory"""
    
    # @function: create_agent
    # @purpose: "Create subagent from config"
    # @input: config: SubAgentConfig
    # @output: SubAgent
    # @ai_testable: true
    @staticmethod
    def create_agent(config: SubAgentConfig) -> SubAgent:
        """@purpose: Create agent"""
        
        return SubAgent(config)
    
    # @function: create_default_agents
    # @purpose: "Create default agent set"
    # @output: List[SubAgent]
    # @ai_testable: true
    @staticmethod
    def create_default_agents() -> List[SubAgent]:
        """@purpose: Create default agents"""
        
        configs = [
            SubAgentConfig(
                name="researcher",
                description="Research and information gathering",
                skills=["search", "analyze"]
            ),
            SubAgentConfig(
                name="coder",
                description="Code writing and modification",
                skills=["code", "debug"]
            ),
            SubAgentConfig(
                name="writer",
                description="Content writing",
                skills=["write", "edit"]
            ),
            SubAgentConfig(
                name="reviewer",
                description="Code and content review",
                skills=["review", "validate"]
            )
        ]
        
        return [
            AgentFactory.create_agent(config)
            for config in configs
        ]
