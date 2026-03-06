# @file: validator.py
# @module: openclaw.tools.validator
# @purpose: "Validate AI metadata completeness"
# @ai_maintained: true
# @version: "1.0.0"
# @test_coverage: 0.95

from typing import Dict, List, Any
from pathlib import Path
from .parser import AICodeParser, FileMetadata

# @class: CodeValidator
# @purpose: "Validate AI metadata completeness"
# @ai_testable: true
class CodeValidator:
    """
    @summary: Validate AI-optimized code metadata
    
    @features:
      - Check required metadata
      - Validate schema definitions
      - Check function signatures
      - Generate validation report
    """
    
    # @attribute: parser
    # @type: AICodeParser
    parser: AICodeParser
    
    # @attribute: required_file_metadata
    # @type: List[str]
    _required_file_metadata: List[str] = [
        'module',
        'purpose',
        'ai_maintained',
        'version'
    ]
    
    # @attribute: required_function_metadata
    # @type: List[str]
    _required_function_metadata: List[str] = [
        'purpose',
        'input',
        'output'
    ]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize validator"""
        self.parser = AICodeParser()
    
    # @function: validate_file
    # @purpose: "Validate single file"
    # @input: file_path: str
    # @output: ValidationResult
    # @ai_testable: true
    def validate_file(self, file_path: str) -> 'ValidationResult':
        """
        @summary: Validate file metadata
        
        @steps:
          1. Parse file
          2. Check file-level metadata
          3. Check schemas
          4. Check functions
          5. Check errors
          6. Generate report
        """
        
        result = ValidationResult(file=file_path)
        
        # @step: 1
        try:
            metadata = self.parser.parse_file(file_path)
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
            return result
        
        # @step: 2
        self._validate_file_metadata(metadata, result)
        
        # @step: 3
        self._validate_schemas(metadata, result)
        
        # @step: 4
        self._validate_functions(metadata, result)
        
        # @step: 5
        self._validate_errors(metadata, result)
        
        # @step: 6
        result.valid = len(result.errors) == 0
        result.score = self._calculate_score(result)
        
        return result
    
    # @function: validate_directory
    # @purpose: "Validate all files in directory"
    # @input: dir_path: str
    # @output: List[ValidationResult]
    # @ai_testable: true
    def validate_directory(self, dir_path: str) -> List['ValidationResult']:
        """@purpose: Validate directory of files"""
        
        path = Path(dir_path)
        files = list(path.glob("*.py"))
        
        results = []
        for file in files:
            if file.name.startswith('_'):
                continue
            
            result = self.validate_file(str(file))
            results.append(result)
        
        return results
    
    # @function: _validate_file_metadata
    # @purpose: "Validate file-level metadata"
    # @input: metadata: FileMetadata, result: ValidationResult
    # @side_effects: ["Update result.errors"]
    # @private: true
    def _validate_file_metadata(self, metadata: FileMetadata, result: 'ValidationResult') -> None:
        """@purpose: Validate file metadata"""
        
        for field in self._required_file_metadata:
            value = getattr(metadata, field, None)
            
            if value is None or value == '' or value == 0.0:
                result.errors.append(f"Missing required file metadata: @{field}")
    
    # @function: _validate_schemas
    # @purpose: "Validate schema definitions"
    # @input: metadata: FileMetadata, result: ValidationResult
    # @side_effects: ["Update result.errors"]
    # @private: true
    def _validate_schemas(self, metadata: FileMetadata, result: 'ValidationResult') -> None:
        """@purpose: Validate schemas"""
        
        for schema in metadata.schemas:
            if not schema.purpose:
                result.errors.append(f"Schema {schema.name} missing @purpose")
    
    # @function: _validate_functions
    # @purpose: "Validate function metadata"
    # @input: metadata: FileMetadata, result: ValidationResult
    # @side_effects: ["Update result.errors"]
    # @private: true
    def _validate_functions(self, metadata: FileMetadata, result: 'ValidationResult') -> None:
        """@purpose: Validate functions"""
        
        for func in metadata.functions:
            for field in self._required_function_metadata:
                value = getattr(func, field, '')
                
                if not value:
                    result.errors.append(f"Function {func.name} missing @{field}")
    
    # @function: _validate_errors
    # @purpose: "Validate error definitions"
    # @input: metadata: FileMetadata, result: ValidationResult
    # @side_effects: ["Update result.errors"]
    # @private: true
    def _validate_errors(self, metadata: FileMetadata, result: 'ValidationResult') -> None:
        """@purpose: Validate errors"""
        
        for error in metadata.errors:
            if not error.code:
                result.errors.append(f"Error {error.name} missing @code")
            
            if not error.severity:
                result.errors.append(f"Error {error.name} missing @severity")
    
    # @function: _calculate_score
    # @purpose: "Calculate validation score"
    # @input: result: ValidationResult
    # @output: float
    # @private: true
    def _calculate_score(self, result: 'ValidationResult') -> float:
        """@purpose: Calculate validation score"""
        
        if result.valid:
            return 1.0
        
        # Penalize for each error
        penalty = len(result.errors) * 0.1
        return max(0.0, 1.0 - penalty)

# @schema: ValidationResult
# @ai_readable: true
@dataclass
class ValidationResult:
    """@purpose: Validation result structure"""
    
    # @field: file
    # @type: str
    file: str
    
    # @field: valid
    # @type: bool
    valid: bool = False
    
    # @field: score
    # @type: float
    score: float = 0.0
    
    # @field: errors
    # @type: List[str]
    errors: List[str] = None
    
    # @field: warnings
    # @type: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
