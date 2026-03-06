# @file: schemas.py
# @module: openclaw.core.config.schemas
# @purpose: "Define configuration schemas"
# @ai_maintained: true
# @version: "1.0.0"
# @test_coverage: 0.95

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum

# @enum: LogLevel
# @ai_readable: true
class LogLevel(str, Enum):
    """
    @value: DEBUG - Debug level logging
    @value: INFO - Info level logging
    @value: WARNING - Warning level logging
    @value: ERROR - Error level logging
    @value: CRITICAL - Critical level logging
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# @schema: LLMConfig
# @ai_readable: true
class LLMConfig(BaseModel):
    """
    @field: provider - LLM provider name
    @field: model - Model name
    @field: api_key - API key (optional)
    @field: base_url - Base URL for API
    @field: temperature - Temperature (0.0-2.0)
    @field: max_tokens - Maximum tokens
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True
    )
    
    # @field: provider
    # @type: Literal["openai", "anthropic", "minimax", "qwen", "kimi"]
    # @required: true
    provider: Literal["openai", "anthropic", "minimax", "qwen", "kimi"] = Field(
        default="minimax",
        description="LLM provider"
    )
    
    # @field: model
    # @type: str
    # @required: true
    # @default: "minimax-cn/MiniMax-M2.5"
    model: str = Field(
        default="minimax-cn/MiniMax-M2.5",
        description="Model name"
    )
    
    # @field: api_key
    # @type: Optional[str]
    # @default: None
    api_key: Optional[str] = Field(
        default=None,
        description="API key",
        json_schema_extra={"sensitive": True}
    )
    
    # @field: base_url
    # @type: Optional[str]
    # @default: None
    base_url: Optional[str] = Field(default=None)
    
    # @field: temperature
    # @type: float
    # @default: 0.7
    # @range: [0.0, 2.0]
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0
    )
    
    # @field: max_tokens
    # @type: int
    # @default: 2000
    # @range: [1, 128000]
    max_tokens: int = Field(
        default=2000,
        ge=1,
        le=128000
    )

# @schema: AgentConfig
# @ai_readable: true
class AgentConfig(BaseModel):
    """
    @field: name - Agent name
    @field: description - Agent description
    @field: model - LLM configuration
    @field: tools - List of tool names
    @field: system_prompt - System prompt
    """
    
    model_config = ConfigDict(validate_assignment=True)
    
    # @field: name
    # @type: str
    # @required: true
    name: str = Field(
        description="Agent name",
        min_length=1,
        max_length=64
    )
    
    # @field: description
    # @type: str
    # @default: ""
    description: str = Field(default="")
    
    # @field: llm
    # @type: LLMConfig
    # @default: LLMConfig()
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # @field: tools
    # @type: List[str]
    # @default: []
    tools: List[str] = Field(default_factory=list)
    
    # @field: system_prompt
    # @type: str
    # @default: "You are a helpful AI assistant."
    system_prompt: str = Field(
        default="You are a helpful AI assistant.",
        description="System prompt"
    )

# @schema: OpenClawConfig
# @ai_readable: true
class OpenClawConfig(BaseModel):
    """
    @field: app_name - Application name
    @field: version - Version string
    @field: debug - Debug mode flag
    @field: log_level - Logging level
    @field: llm - LLM configuration
    @field: agents - Agent configurations
    @field: plugins - Plugin list
    """
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        validate_assignment=True,
        extra="forbid"
    )
    
    # @field: app_name
    # @type: str
    # @default: "OpenClaw"
    app_name: str = Field(default="OpenClaw")
    
    # @field: version
    # @type: str
    # @default: "1.0.0"
    version: str = Field(default="1.0.0")
    
    # @field: debug
    # @type: bool
    # @default: False
    debug: bool = Field(default=False)
    
    # @field: log_level
    # @type: LogLevel
    # @default: LogLevel.INFO
    log_level: LogLevel = Field(default=LogLevel.INFO)
    
    # @field: llm
    # @type: LLMConfig
    # @default: LLMConfig()
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # @field: agents
    # @type: Dict[str, AgentConfig]
    # @default: {}
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    
    # @field: plugins
    # @type: List[str]
    # @default: []
    plugins: List[str] = Field(default_factory=list)
    
    # @validator: agents
    @field_validator('agents')
    @classmethod
    def validate_agents(cls, v: Dict[str, AgentConfig]) -> Dict[str, AgentConfig]:
        """@purpose: Validate agent configurations"""
        
        if not v:
            v["default"] = AgentConfig(name="default")
        
        return v
    
    # @function: export_schema
    # @purpose: "Export JSON Schema for AI generation"
    # @output: Dict[str, Any]
    def export_schema(self) -> Dict[str, Any]:
        """@purpose: Export JSON Schema"""
        return self.model_json_schema()
    
    # @function: validate_all
    # @purpose: "Validate all configurations"
    # @output: List[str]
    def validate_all(self) -> List[str]:
        """@purpose: Validate and return errors"""
        
        errors = []
        try:
            self.model_validate(self.model_dump())
        except Exception as e:
            errors.append(str(e))
        
        return errors
