# @file: manager.py
# @module: openclaw.core.config.manager
# @purpose: "Manage configuration loading and validation"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, Any, Optional
from pathlib import Path
import json
import yaml

from .schemas import OpenClawConfig, AgentConfig, LLMConfig

# @class: ConfigManager
# @purpose: "Manage configuration loading and validation"
# @ai_testable: true
class ConfigManager:
    """
    @summary: Configuration manager with validation
    
    @features:
      - Load from file (JSON/YAML)
      - Load from environment
      - Validate configuration
      - Export schema for AI
    """
    
    # @attribute: config
    # @type: OpenClawConfig
    config: OpenClawConfig
    
    # @constructor
    def __init__(self, config: OpenClawConfig):
        """@purpose: Initialize with configuration"""
        self.config = config
    
    # @function: from_file
    # @purpose: "Load configuration from file"
    # @input: path: str
    # @output: ConfigManager
    # @raises: FileNotFoundError, ValueError
    # @ai_testable: true
    @classmethod
    def from_file(cls, path: str) -> 'ConfigManager':
        """
        @summary: Load from file
        
        @steps:
          1. Read file
          2. Parse based on extension
          3. Validate
          4. Return ConfigManager
        """
        
        # @step: 1
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        # @step: 2
        if path.endswith('.json'):
            config_data = json.loads(data)
        elif path.endswith(('.yaml', '.yml')):
            config_data = yaml.safe_load(data)
        else:
            raise ValueError(f"Unsupported config format: {path}")
        
        # @step: 3
        config = OpenClawConfig.model_validate(config_data)
        
        # @step: 4
        return cls(config)
    
    # @function: from_env
    # @purpose: "Load configuration from environment"
    # @output: ConfigManager
    # @ai_testable: true
    @classmethod
    def from_env(cls) -> 'ConfigManager':
        """@purpose: Load from environment variables"""
        
        config = OpenClawConfig()
        return cls(config)
    
    # @function: create_default
    # @purpose: "Create default configuration"
    # @output: ConfigManager
    # @ai_testable: true
    @classmethod
    def create_default(cls) -> 'ConfigManager':
        """@purpose: Create default configuration"""
        
        config = OpenClawConfig()
        return cls(config)
    
    # @function: get
    # @purpose: "Get configuration value"
    # @input: key: str, default: Any
    # @output: Any
    # @ai_testable: true
    def get(self, key: str, default: Any = None) -> Any:
        """@purpose: Get configuration value"""
        
        keys = key.split('.')
        value = self.config.model_dump()
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    # @function: set
    # @purpose: "Set configuration value"
    # @input: key: str, value: Any
    # @side_effects: ["Update configuration"]
    # @ai_testable: true
    def set(self, key: str, value: Any) -> None:
        """@purpose: Set configuration value"""
        
        keys = key.split('.')
        config_dict = self.config.model_dump()
        
        current = config_dict
        for k in keys[:-1]:
            current = current.get(k, {})
        
        current[keys[-1]] = value
        
        # Update config
        self.config = OpenClawConfig.model_validate(config_dict)
    
    # @function: validate
    # @purpose: "Validate configuration"
    # @output: ValidationResult
    # @ai_testable: true
    def validate(self) -> 'ValidationResult':
        """@purpose: Validate configuration"""
        
        errors = self.config.validate_all()
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    # @function: export_schema
    # @purpose: "Export JSON Schema for AI generation"
    # @output: Dict[str, Any]
    # @ai_testable: true
    def export_schema(self) -> Dict[str, Any]:
        """@purpose: Export JSON Schema"""
        return self.config.export_schema()
    
    # @function: save
    # @purpose: "Save configuration to file"
    # @input: path: str
    # @side_effects: ["Create file"]
    # @ai_testable: true
    def save(self, path: str) -> None:
        """@purpose: Save to file"""
        
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = self.config.model_dump()
        
        if path.endswith('.json'):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
        elif path.endswith(('.yaml', '.yml')):
            with open(path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {path}")

# @schema: ValidationResult
# @ai_readable: true
class ValidationResult:
    """@purpose: Validation result structure"""
    
    # @field: is_valid
    # @type: bool
    is_valid: bool
    
    # @field: errors
    # @type: List[str]
    errors: List[str]
