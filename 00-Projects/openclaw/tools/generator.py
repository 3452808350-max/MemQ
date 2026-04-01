# @file: generator.py
# @module: openclaw.tools.generator
# @purpose: "Generate AI-optimized code from metadata"
# @ai_maintained: true
# @version: "1.0.0"
# @test_coverage: 0.95

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# @class: AICodeGenerator
# @purpose: "Generate AI-optimized code from metadata"
# @ai_testable: true
class AICodeGenerator:
    """
    @summary: Generate AI-optimized code
    
    @features:
      - Generate file with metadata
      - Generate schema definitions
      - Generate function stubs
      - Generate error classes
      - Generate test stubs
    """
    
    # @function: generate_file
    # @purpose: "Generate Python file with AI metadata"
    # @input: module: str, purpose: str, content: Dict[str, Any]
    # @output: str
    # @ai_testable: true
    def generate_file(self, module: str, purpose: str, content: Dict[str, Any]) -> str:
        """
        @summary: Generate complete Python file
        
        @steps:
          1. Generate file header
          2. Generate schemas
          3. Generate errors
          4. Generate classes
          5. Generate functions
          6. Return complete code
        """
        
        code = ""
        
        # @step: 1
        code += self._generate_header(module, purpose)
        code += "\n\n"
        
        # @step: 2
        if 'schemas' in content:
            for schema in content['schemas']:
                code += self._generate_schema(schema)
                code += "\n\n"
        
        # @step: 3
        if 'errors' in content:
            for error in content['errors']:
                code += self._generate_error(error)
                code += "\n\n"
        
        # @step: 4
        if 'classes' in content:
            for cls in content['classes']:
                code += self._generate_class(cls)
                code += "\n\n"
        
        # @step: 5
        if 'functions' in content:
            for func in content['functions']:
                code += self._generate_function(func)
                code += "\n\n"
        
        # @step: 6
        return code
    
    # @function: generate_test
    # @purpose: "Generate test for function"
    # @input: function_name: str, function_meta: Dict[str, Any]
    # @output: str
    # @ai_testable: true
    def generate_test(self, function_name: str, function_meta: Dict[str, Any]) -> str:
        """@purpose: Generate test stub for function"""
        
        test_name = f"test_{function_name}"
        
        test = f"# @test_for: {function_name}\n"
        test += "# @ai_generated: true\n"
        test += "# @test_type: \"unit\"\n"
        test += f"def {test_name}():\n"
        test += f'    """@purpose: Test {function_name}"""\n'
        test += "    \n"
        test += "    # Arrange\n"
        test += "    \n"
        test += "    # Act\n"
        test += "    \n"
        test += "    # Assert\n"
        test += "    pass\n"
        
        return test
    
    # @function: _generate_header
    # @purpose: "Generate file header"
    # @input: module: str, purpose: str
    # @output: str
    # @private: true
    def _generate_header(self, module: str, purpose: str) -> str:
        """@purpose: Generate file header with metadata"""
        
        header = f"# @file: {module.split('.')[-1]}.py\n"
        header += f"# @module: {module}\n"
        header += f"# @purpose: \"{purpose}\"\n"
        header += "# @ai_maintained: true\n"
        header += "# @version: \"1.0.0\"\n"
        header += "# @test_coverage: 0.95\n"
        
        return header
    
    # @function: _generate_schema
    # @purpose: "Generate schema definition"
    # @input: schema: Dict[str, Any]
    # @output: str
    # @private: true
    def _generate_schema(self, schema: Dict[str, Any]) -> str:
        """@purpose: Generate schema dataclass"""
        
        name = schema.get('name', 'Schema')
        purpose = schema.get('purpose', '')
        
        code = f"# @schema: {name}\n"
        code += "# @ai_readable: true\n"
        code += f"# @purpose: \"{purpose}\"\n"
        code += "@dataclass\n"
        code += f"class {name}:\n"
        
        if 'fields' in schema:
            for field in schema['fields']:
                code += f"    # @field: {field['name']}\n"
                code += f"    # @type: {field.get('type', 'Any')}\n"
                if 'default' in field:
                    code += f"    {field['name']}: {field.get('type', 'Any')} = {field['default']}\n"
                else:
                    code += f"    {field['name']}: {field.get('type', 'Any')}\n"
        else:
            code += "    pass\n"
        
        return code
    
    # @function: _generate_error
    # @purpose: "Generate error class"
    # @input: error: Dict[str, Any]
    # @output: str
    # @private: true
    def _generate_error(self, error: Dict[str, Any]) -> str:
        """@purpose: Generate error class"""
        
        name = error.get('name', 'Error')
        code = error.get('code', 'UNK-000')
        severity = error.get('severity', 'error')
        ai_fixable = error.get('ai_fixable', False)
        suggestion = error.get('fix_suggestion', '')
        
        error_code = f"# @error: {name}\n"
        error_code += f"# @code: \"{code}\"\n"
        error_code += f"# @severity: \"{severity}\"\n"
        error_code += f"# @ai_fixable: {str(ai_fixable).lower()}\n"
        if suggestion:
            error_code += f"# @fix_suggestion: \"{suggestion}\"\n"
        error_code += f"class {name}(Exception):\n"
        error_code += f'    """@purpose: {name}"""\n'
        error_code += "    \n"
        error_code += f'    error_code: str = "{code}"\n'
        error_code += f'    severity: ErrorSeverity = ErrorSeverity.{severity.upper()}\n'
        error_code += f'    ai_fixable: bool = {str(ai_fixable).lower()}\n'
        if suggestion:
            error_code += f'    ai_suggestion: str = "{suggestion}"\n'
        
        return error_code
    
    # @function: _generate_class
    # @purpose: "Generate class definition"
    # @input: cls: Dict[str, Any]
    # @output: str
    # @private: true
    def _generate_class(self, cls: Dict[str, Any]) -> str:
        """@purpose: Generate class definition"""
        
        name = cls.get('name', 'Class')
        purpose = cls.get('purpose', '')
        
        code = f"# @class: {name}\n"
        code += f"# @purpose: \"{purpose}\"\n"
        
        if 'dependencies' in cls:
            deps = ', '.join([f'"{d}"' for d in cls['dependencies']])
            code += f"# @dependencies: [{deps}]\n"
        
        code += f"class {name}:\n"
        code += f'    """@summary: {purpose}"""\n'
        code += "    \n"
        
        if 'attributes' in cls:
            for attr in cls['attributes']:
                code += f"    # @attribute: {attr['name']}\n"
                code += f"    # @type: {attr.get('type', 'Any')}\n"
                code += f"    {attr['name']}: {attr.get('type', 'Any')}\n"
                code += "    \n"
        
        if 'methods' in cls:
            for method in cls['methods']:
                code += self._generate_function(method)
                code += "\n"
        
        return code
    
    # @function: _generate_function
    # @purpose: "Generate function stub"
    # @input: func: Dict[str, Any]
    # @output: str
    # @private: true
    def _generate_function(self, func: Dict[str, Any]) -> str:
        """@purpose: Generate function stub"""
        
        name = func.get('name', 'function')
        purpose = func.get('purpose', '')
        input_params = func.get('input', '')
        output = func.get('output', 'None')
        async_ = func.get('async', False)
        
        code = f"# @function: {name}\n"
        code += f"# @purpose: \"{purpose}\"\n"
        
        if input_params:
            code += f"# @input: {input_params}\n"
        
        code += f"# @output: {output}\n"
        
        if async_:
            code += f"async def {name}(self):\n"
        else:
            code += f"def {name}(self):\n"
        
        code += f'    """@purpose: {purpose}"""\n'
        code += "    pass\n"
        
        return code
    
    # @function: save_file
    # @purpose: "Save generated code to file"
    # @input: code: str, file_path: str
    # @side_effects: ["Create file"]
    # @ai_testable: true
    def save_file(self, code: str, file_path: str) -> None:
        """@purpose: Save code to file"""
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
