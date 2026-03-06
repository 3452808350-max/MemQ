# @file: errors.py
# @module: openclaw.core.memory.errors
# @purpose: "Define memory-related error codes and exceptions"
# @ai_maintained: true
# @version: "1.0.0"
# @test_coverage: 0.95

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# @enum: ErrorSeverity
# @ai_readable: true
# @purpose: "Error severity levels"
class ErrorSeverity(str, Enum):
    """
    @value: CRITICAL - System cannot continue
    @value: ERROR - Function unavailable but system can continue
    @value: WARNING - Need attention but function normal
    @value: INFO - Informational message
    """
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

# @error: MEMORY_STORE_FAILED
# @code: "MEM-001"
# @severity: "error"
# @ai_fixable: true
# @fix_suggestion: "Check database connection and retry, or increase storage limit"
class MemoryStoreError(Exception):
    """@purpose: Memory storage failed"""
    
    error_code: str = "MEM-001"
    severity: ErrorSeverity = ErrorSeverity.ERROR
    ai_fixable: bool = True
    ai_suggestion: str = "Check database connection and retry"

# @error: MEMORY_RETRIEVAL_FAILED
# @code: "MEM-002"
# @severity: "error"
# @ai_fixable: true
# @fix_suggestion: "Check if key exists and database is accessible"
class MemoryRetrievalError(Exception):
    """@purpose: Memory retrieval failed"""
    
    error_code: str = "MEM-002"
    severity: ErrorSeverity = ErrorSeverity.ERROR
    ai_fixable: bool = True
    ai_suggestion: str = "Check if key exists and database is accessible"

# @error: MEMORY_SEARCH_FAILED
# @code: "MEM-003"
# @severity: "error"
# @ai_fixable: false
class MemorySearchError(Exception):
    """@purpose: Memory search failed"""
    
    error_code: str = "MEM-003"
    severity: ErrorSeverity = ErrorSeverity.ERROR
    ai_fixable: bool = False

# @error: MEMORY_COMPRESSION_FAILED
# @code: "MEM-004"
# @severity: "warning"
# @ai_fixable: true
# @fix_suggestion: "Try manual compression or increase max_tokens limit"
class MemoryCompressionError(Exception):
    """@purpose: Memory compression failed"""
    
    error_code: str = "MEM-004"
    severity: ErrorSeverity = ErrorSeverity.WARNING
    ai_fixable: bool = True
    ai_suggestion: str = "Try manual compression or increase max_tokens limit"

# @error: MEMORY_NOT_INITIALIZED
# @code: "MEM-005"
# @severity: "critical"
# @ai_fixable: true
# @fix_suggestion: "Call initialize() method before using MemoryManager"
class MemoryNotInitializedError(Exception):
    """@purpose: Memory manager not initialized"""
    
    error_code: str = "MEM-005"
    severity: ErrorSeverity = ErrorSeverity.CRITICAL
    ai_fixable: bool = True
    ai_suggestion: str = "Call initialize() method before using MemoryManager"

# @function: get_error_definition
# @purpose: "Get error definition by error code"
# @input: error_code: str
# @output: Dict[str, Any]
# @ai_testable: true
def get_error_definition(error_code: str) -> Optional[Dict[str, Any]]:
    """@purpose: Get error definition by code"""
    
    error_registry: Dict[str, Dict[str, Any]] = {
        "MEM-001": {
            "code": "MEM-001",
            "severity": ErrorSeverity.ERROR,
            "message": "Memory storage failed",
            "ai_fixable": True,
            "ai_suggestion": "Check database connection and retry"
        },
        "MEM-002": {
            "code": "MEM-002",
            "severity": ErrorSeverity.ERROR,
            "message": "Memory retrieval failed",
            "ai_fixable": True,
            "ai_suggestion": "Check if key exists and database is accessible"
        },
        "MEM-003": {
            "code": "MEM-003",
            "severity": ErrorSeverity.ERROR,
            "message": "Memory search failed",
            "ai_fixable": False
        },
        "MEM-004": {
            "code": "MEM-004",
            "severity": ErrorSeverity.WARNING,
            "message": "Memory compression failed",
            "ai_fixable": True,
            "ai_suggestion": "Try manual compression or increase max_tokens limit"
        },
        "MEM-005": {
            "code": "MEM-005",
            "severity": ErrorSeverity.CRITICAL,
            "message": "Memory manager not initialized",
            "ai_fixable": True,
            "ai_suggestion": "Call initialize() method before using MemoryManager"
        }
    }
    
    return error_registry.get(error_code)
