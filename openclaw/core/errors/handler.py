# @file: handler.py
# @module: openclaw.core.errors.handler
# @purpose: "Handle errors with AI-fixable suggestions"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

# @enum: ErrorSeverity
# @ai_readable: true
class ErrorSeverity(str, Enum):
    """
    @value: CRITICAL - System cannot continue
    @value: ERROR - Function unavailable
    @value: WARNING - Need attention
    @value: INFO - Informational
    """
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

# @schema: ErrorContext
# @ai_readable: true
@dataclass
class ErrorContext:
    """@purpose: Structured error context"""
    
    # @field: error_code
    # @type: str
    error_code: str
    
    # @field: severity
    # @type: ErrorSeverity
    severity: ErrorSeverity
    
    # @field: message
    # @type: str
    message: str
    
    # @field: details
    # @type: Dict[str, Any]
    details: Dict[str, Any]
    
    # @field: recoverable
    # @type: bool
    recoverable: bool
    
    # @field: ai_suggestion
    # @type: Optional[str]
    ai_suggestion: Optional[str] = None
    
    # @field: retryable
    # @type: bool
    retryable: bool = False

# @class: ErrorHandler
# @purpose: "Handle errors with AI-fixable suggestions"
# @ai_testable: true
class ErrorHandler:
    """
    @summary: Structured error handler
    
    @features:
      - Structured error codes
      - AI-fixable suggestions
      - Error categorization
      - Error statistics
    """
    
    # @attribute: error_registry
    # @type: Dict[str, Dict[str, Any]]
    _error_registry: Dict[str, Dict[str, Any]]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize error handler"""
        
        self._error_registry = {
            "MEM-001": {
                "code": "MEM-001",
                "severity": ErrorSeverity.ERROR,
                "message": "Memory storage failed",
                "recoverable": True,
                "ai_suggestion": "Check database connection and retry"
            },
            "CFG-001": {
                "code": "CFG-001",
                "severity": ErrorSeverity.ERROR,
                "message": "Configuration validation failed",
                "recoverable": True,
                "ai_suggestion": "Check configuration file format and values"
            },
            "LLM-001": {
                "code": "LLM-001",
                "severity": ErrorSeverity.ERROR,
                "message": "LLM API error",
                "recoverable": True,
                "ai_suggestion": "Check API key and network connection"
            }
        }
    
    # @function: handle
    # @purpose: "Handle error and return structured context"
    # @input: error: Exception, context: Dict[str, Any]
    # @output: ErrorContext
    # @ai_testable: true
    async def handle(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> ErrorContext:
        """
        @summary: Handle error
        
        @steps:
          1. Extract error code
          2. Get error definition
          3. Create ErrorContext
          4. Return structured error
        """
        
        # @step: 1
        error_code = self._extract_error_code(error)
        
        # @step: 2
        definition = self._get_error_definition(error_code)
        
        # @step: 3
        error_context = ErrorContext(
            error_code=error_code,
            severity=definition.get('severity', ErrorSeverity.ERROR),
            message=definition.get('message', str(error)),
            details={
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "context": context
            },
            recoverable=definition.get('recoverable', False),
            ai_suggestion=definition.get('ai_suggestion')
        )
        
        # @step: 4
        return error_context
    
    # @function: get_suggestion
    # @purpose: "Get AI recovery suggestion"
    # @input: error_code: str
    # @output: Optional[str]
    # @ai_testable: true
    async def get_suggestion(self, error_code: str) -> Optional[str]:
        """@purpose: Get recovery suggestion"""
        
        definition = self._get_error_definition(error_code)
        return definition.get('ai_suggestion')
    
    # @function: _extract_error_code
    # @purpose: "Extract error code from exception"
    # @input: error: Exception
    # @output: str
    # @private: true
    def _extract_error_code(self, error: Exception) -> str:
        """@purpose: Extract error code"""
        
        if hasattr(error, 'error_code'):
            return error.error_code
        
        # Map exception types to error codes
        error_type_map = {
            'ConnectionError': 'NET-001',
            'TimeoutError': 'NET-002',
            'ValidationError': 'CFG-001',
            'FileNotFoundError': 'SYS-001',
        }
        
        return error_type_map.get(type(error).__name__, 'UNK-001')
    
    # @function: _get_error_definition
    # @purpose: "Get error definition from registry"
    # @input: error_code: str
    # @output: Dict[str, Any]
    # @private: true
    def _get_error_definition(self, error_code: str) -> Dict[str, Any]:
        """@purpose: Get error definition"""
        
        return self._error_registry.get(error_code, {
            "code": error_code,
            "severity": ErrorSeverity.ERROR,
            "message": f"Unknown error: {error_code}",
            "recoverable": False
        })
