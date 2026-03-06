# @file: parser.py
# @module: openclaw.tools.parser
# @purpose: "Parse AI-optimized code format and extract metadata"
# @ai_maintained: true
# @version: "1.0.0"
# @test_coverage: 0.95

import re
import ast
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

# @schema: FunctionMetadata
# @ai_readable: true
@dataclass
class FunctionMetadata:
    """@purpose: Function metadata structure"""
    name: str
    purpose: str = ""
    input: str = ""
    output: str = ""
    side_effects: List[str] = field(default_factory=list)
    raises: List[str] = field(default_factory=list)
    async_: bool = False
    private: bool = False
    ai_testable: bool = False

# @schema: ClassMetadata
# @ai_readable: true
@dataclass
class ClassMetadata:
    """@purpose: Class metadata structure"""
    name: str
    purpose: str = ""
    dependencies: List[str] = field(default_factory=list)
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    methods: List[FunctionMetadata] = field(default_factory=list)

# @schema: SchemaMetadata
# @ai_readable: true
@dataclass
class SchemaMetadata:
    """@purpose: Schema metadata structure"""
    name: str
    purpose: str = ""
    fields: List[Dict[str, Any]] = field(default_factory=list)
    ai_readable: bool = False

# @schema: ErrorMetadata
# @ai_readable: true
@dataclass
class ErrorMetadata:
    """@purpose: Error metadata structure"""
    name: str
    code: str = ""
    severity: str = "error"
    ai_fixable: bool = False
    fix_suggestion: str = ""

# @schema: FileMetadata
# @ai_readable: true
@dataclass
class FileMetadata:
    """@purpose: File-level metadata structure"""
    file: str = ""
    module: str = ""
    purpose: str = ""
    ai_maintained: bool = False
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    test_coverage: float = 0.0
    schemas: List[SchemaMetadata] = field(default_factory=list)
    classes: List[ClassMetadata] = field(default_factory=list)
    functions: List[FunctionMetadata] = field(default_factory=list)
    errors: List[ErrorMetadata] = field(default_factory=list)

# @class: AICodeParser
# @purpose: "Parse AI-optimized code and extract metadata"
# @ai_testable: true
class AICodeParser:
    """
    @summary: Parse AI-optimized code format
    
    @features:
      - Extract file-level metadata
      - Extract schema definitions
      - Extract function signatures
      - Extract error definitions
      - Generate AI-readable structure
    """
    
    # @attribute: metadata_patterns
    # @type: Dict[str, re.Pattern]
    _metadata_patterns: Dict[str, re.Pattern]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize parser with regex patterns"""
        
        self._metadata_patterns = {
            'file': re.compile(r'#\s*@file:\s*(.+)'),
            'module': re.compile(r'#\s*@module:\s*(.+)'),
            'purpose': re.compile(r'#\s*@purpose:\s*"([^"]+)"'),
            'ai_maintained': re.compile(r'#\s*@ai_maintained:\s*(true|false)'),
            'version': re.compile(r'#\s*@version:\s*"([^"]+)"'),
            'dependencies': re.compile(r'#\s*@dependencies:\s*\[(.+)\]'),
            'test_coverage': re.compile(r'#\s*@test_coverage:\s*([\d.]+)'),
            'schema': re.compile(r'#\s*@schema:\s*(\w+)'),
            'function': re.compile(r'#\s*@function:\s*(\w+)'),
            'class': re.compile(r'#\s*@class:\s*(\w+)'),
            'error': re.compile(r'#\s*@error:\s*(\w+)'),
            'input': re.compile(r'#\s*@input:\s*(.+)'),
            'output': re.compile(r'#\s*@output:\s*(.+)'),
            'side_effects': re.compile(r'#\s*@side_effects:\s*\[(.+)\]'),
            'raises': re.compile(r'#\s*@raises:\s*(.+)'),
            'async': re.compile(r'#\s*@async:\s*(true|false)'),
            'private': re.compile(r'#\s*@private:\s*(true|false)'),
            'ai_testable': re.compile(r'#\s*@ai_testable:\s*(true|false)'),
            'code': re.compile(r'#\s*@code:\s*"([^"]+)"'),
            'severity': re.compile(r'#\s*@severity:\s*"([^"]+)"'),
            'ai_fixable': re.compile(r'#\s*@ai_fixable:\s*(true|false)'),
            'fix_suggestion': re.compile(r'#\s*@fix_suggestion:\s*"([^"]+)"'),
        }
    
    # @function: parse_file
    # @purpose: "Parse Python file and extract AI metadata"
    # @input: file_path: str
    # @output: FileMetadata
    # @raises: FileNotFoundError
    # @ai_testable: true
    def parse_file(self, file_path: str) -> FileMetadata:
        """
        @summary: Parse Python file and extract metadata
        
        @steps:
          1. Read file content
          2. Extract file-level metadata
          3. Extract schemas
          4. Extract classes
          5. Extract functions
          6. Extract errors
          7. Return FileMetadata
        """
        
        # @step: 1
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # @step: 2
        metadata = FileMetadata()
        metadata.file = path.name
        self._extract_file_metadata(content, metadata)
        
        # @step: 3
        self._extract_schemas(content, metadata)
        
        # @step: 4
        self._extract_classes(content, metadata)
        
        # @step: 5
        self._extract_functions(content, metadata)
        
        # @step: 6
        self._extract_errors(content, metadata)
        
        # @step: 7
        return metadata
    
    # @function: parse_directory
    # @purpose: "Parse all Python files in directory"
    # @input: dir_path: str, pattern: str
    # @output: List[FileMetadata]
    # @ai_testable: true
    def parse_directory(self, dir_path: str, pattern: str = "*.py") -> List[FileMetadata]:
        """@purpose: Parse directory of Python files"""
        
        path = Path(dir_path)
        files = list(path.glob(pattern))
        
        metadata_list = []
        for file in files:
            if file.name.startswith('_'):
                continue
            
            try:
                metadata = self.parse_file(str(file))
                metadata_list.append(metadata)
            except Exception as e:
                print(f"Error parsing {file}: {e}")
        
        return metadata_list
    
    # @function: _extract_file_metadata
    # @purpose: "Extract file-level metadata"
    # @input: content: str, metadata: FileMetadata
    # @side_effects: ["Update metadata object"]
    # @private: true
    def _extract_file_metadata(self, content: str, metadata: FileMetadata) -> None:
        """@purpose: Extract file-level metadata"""
        
        metadata.module = self._extract_match(self._metadata_patterns['module'], content)
        metadata.purpose = self._extract_match(self._metadata_patterns['purpose'], content)
        metadata.ai_maintained = self._extract_match(self._metadata_patterns['ai_maintained'], content) == 'true'
        metadata.version = self._extract_match(self._metadata_patterns['version'], content) or '1.0.0'
        metadata.test_coverage = float(self._extract_match(self._metadata_patterns['test_coverage'], content) or '0.0')
        
        deps_str = self._extract_match(self._metadata_patterns['dependencies'], content)
        if deps_str:
            metadata.dependencies = [d.strip().strip('"') for d in deps_str.split(',')]
    
    # @function: _extract_schemas
    # @purpose: "Extract schema definitions"
    # @input: content: str, metadata: FileMetadata
    # @side_effects: ["Update metadata.schemas"]
    # @private: true
    def _extract_schemas(self, content: str, metadata: FileMetadata) -> None:
        """@purpose: Extract schema definitions"""
        
        schema_matches = re.finditer(r'#\s*@schema:\s*(\w+)\s*\n#.*?@ai_readable:\s*(true|false)\s*\n@dataclass\s*\nclass\s+(\w+):', content, re.MULTILINE)
        
        for match in schema_matches:
            schema = SchemaMetadata(
                name=match.group(1),
                ai_readable=match.group(2) == 'true'
            )
            
            # Extract purpose
            purpose_match = re.search(r'#\s*@purpose:\s*"([^"]+)"', match.group(0))
            if purpose_match:
                schema.purpose = purpose_match.group(1)
            
            metadata.schemas.append(schema)
    
    # @function: _extract_classes
    # @purpose: "Extract class definitions"
    # @input: content: str, metadata: FileMetadata
    # @side_effects: ["Update metadata.classes"]
    # @private: true
    def _extract_classes(self, content: str, metadata: FileMetadata) -> None:
        """@purpose: Extract class definitions"""
        
        class_matches = re.finditer(r'#\s*@class:\s*(\w+)\s*\n#.*?@purpose:\s*"([^"]+)"\s*\n#.*?@dependencies:\s*\[(.+)\]\s*\nclass\s+(\w+):', content, re.MULTILINE)
        
        for match in class_matches:
            cls = ClassMetadata(
                name=match.group(1),
                purpose=match.group(2),
                dependencies=[d.strip().strip('"') for d in match.group(3).split(',')]
            )
            
            metadata.classes.append(cls)
    
    # @function: _extract_functions
    # @purpose: "Extract function definitions"
    # @input: content: str, metadata: FileMetadata
    # @side_effects: ["Update metadata.functions"]
    # @private: true
    def _extract_functions(self, content: str, metadata: FileMetadata) -> None:
        """@purpose: Extract function definitions"""
        
        func_pattern = r'#\s*@function:\s*(\w+)\s*\n(.*?)\ndef\s+(\w+)\('
        func_matches = re.finditer(func_pattern, content, re.DOTALL)
        
        for match in func_matches:
            func_meta = match.group(0)
            
            func = FunctionMetadata(
                name=match.group(1),
                purpose=self._extract_match(self._metadata_patterns['purpose'], func_meta),
                input=self._extract_match(self._metadata_patterns['input'], func_meta),
                output=self._extract_match(self._metadata_patterns['output'], func_meta),
                async_=self._extract_match(self._metadata_patterns['async'], func_meta) == 'true',
                ai_testable=self._extract_match(self._metadata_patterns['ai_testable'], func_meta) == 'true'
            )
            
            metadata.functions.append(func)
    
    # @function: _extract_errors
    # @purpose: "Extract error definitions"
    # @input: content: str, metadata: FileMetadata
    # @side_effects: ["Update metadata.errors"]
    # @private: true
    def _extract_errors(self, content: str, metadata: FileMetadata) -> None:
        """@purpose: Extract error definitions"""
        
        error_pattern = r'#\s*@error:\s*(\w+)\s*\n#.*?@code:\s*"([^"]+)"\s*\n#.*?@severity:\s*"([^"]+)"\s*\n#.*?@ai_fixable:\s*(true|false)\s*\n#.*?@fix_suggestion:\s*"([^"]+)"\s*\nclass\s+(\w+)'
        error_matches = re.finditer(error_pattern, content, re.MULTILINE)
        
        for match in error_matches:
            error = ErrorMetadata(
                name=match.group(1),
                code=match.group(2),
                severity=match.group(3),
                ai_fixable=match.group(4) == 'true',
                fix_suggestion=match.group(5)
            )
            
            metadata.errors.append(error)
    
    # @function: _extract_match
    # @purpose: "Extract regex match result"
    # @input: pattern: re.Pattern, content: str
    # @output: Optional[str]
    # @private: true
    def _extract_match(self, pattern: re.Pattern, content: str) -> Optional[str]:
        """@purpose: Extract regex match"""
        
        match = pattern.search(content)
        return match.group(1) if match else None
    
    # @function: generate_summary
    # @purpose: "Generate AI-readable summary"
    # @input: metadata: FileMetadata
    # @output: str
    # @ai_testable: true
    def generate_summary(self, metadata: FileMetadata) -> str:
        """
        @summary: Generate AI-readable summary
        
        @output:
          Markdown formatted summary of file metadata
        """
        
        summary = f"# {metadata.module}\n\n"
        summary += f"**Purpose**: {metadata.purpose}\n\n"
        
        if metadata.schemas:
            summary += "## Schemas\n\n"
            for schema in metadata.schemas:
                summary += f"### {schema.name}\n{schema.purpose}\n\n"
        
        if metadata.classes:
            summary += "## Classes\n\n"
            for cls in metadata.classes:
                summary += f"### {cls.name}\n{cls.purpose}\n\n"
        
        if metadata.functions:
            summary += "## Functions\n\n"
            for func in metadata.functions:
                summary += f"### {func.name}\n{func.purpose}\n\n"
        
        return summary
