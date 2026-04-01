# @file: output_gateway.py
# @module: openclaw.core.gateway.output_gateway
# @purpose: "Output gateway for MCP data compression"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio

# @schema: GatewayConfig
# @ai_readable: true
@dataclass
class GatewayConfig:
    """@purpose: Gateway configuration"""
    
    # @field: max_tokens
    # @type: int
    # @default: 4000
    max_tokens: int = 4000
    
    # @field: compression_ratio
    # @type: float
    # @default: 0.5
    compression_ratio: float = 0.5
    
    # @field: filter_keywords
    # @type: List[str]
    filter_keywords: List[str] = None
    
    # @field: extract_top_n
    # @type: int
    # @default: 10
    extract_top_n: int = 10

# @class: OutputGateway
# @purpose: "Output gateway for MCP"
# @ai_testable: true
class OutputGateway:
    """
    @summary: Output gateway
    
    @features:
      - Data filtering
      - Token compression
      - Key information extraction
      - Batch processing
    """
    
    # @attribute: config
    # @type: GatewayConfig
    config: GatewayConfig
    
    # @constructor
    def __init__(self, config: GatewayConfig = None):
        """@purpose: Initialize gateway"""
        
        self.config = config or GatewayConfig()
    
    # @function: process
    # @purpose: "Process tool output before MCP"
    # @input: tool_output: str
    # @output: str
    # @async: true
    # @ai_testable: true
    async def process(self, tool_output: str) -> str:
        """
        @summary: Process output
        
        @steps:
          1. Filter irrelevant content
          2. Compress to token limit
          3. Extract key information
          4. Return compressed output
        """
        
        # @step: 1
        filtered = self._filter(tool_output)
        
        # @step: 2
        compressed = await self._compress(filtered)
        
        # @step: 3
        extracted = self._extract_key_info(compressed)
        
        # @step: 4
        return extracted
    
    # @function: _filter
    # @purpose: "Filter irrelevant content"
    # @input: text: str
    # @output: str
    # @private: true
    def _filter(self, text: str) -> str:
        """
        @purpose: Filter content
        
        @filters:
          - Empty lines
          - Filter keywords
          - Debug information
        """
        
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Skip filter keywords
            if self.config.filter_keywords:
                skip = False
                for keyword in self.config.filter_keywords:
                    if keyword.lower() in line.lower():
                        skip = True
                        break
                
                if skip:
                    continue
            
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    # @function: _compress
    # @purpose: "Compress text to token limit"
    # @input: text: str
    # @output: str
    # @private: true
    # @async: true
    async def _compress(self, text: str) -> str:
        """
        @purpose: Compress text
        
        @strategies:
          - Truncation
          - LLM-based compression
          - Extractive summarization
        """
        
        # Simple token counting (approximate)
        tokens = text.split()
        
        if len(tokens) <= self.config.max_tokens:
            return text
        
        # Truncation strategy
        compression_tokens = int(self.config.max_tokens * self.config.compression_ratio)
        
        compressed_tokens = tokens[:compression_tokens]
        
        return ' '.join(compressed_tokens) + '... [compressed]'
    
    # @function: _extract_key_info
    # @purpose: "Extract key information"
    # @input: text: str
    # @output: str
    # @private: true
    def _extract_key_info(self, text: str) -> str:
        """
        @purpose: Extract key info
        
        @strategies:
          - First N lines
          - Last N lines
          - NLP-based extraction
        """
        
        lines = text.split('\n')
        
        if len(lines) <= self.config.extract_top_n * 2:
            return text
        
        # Extract first N lines + last N lines
        top_lines = lines[:self.config.extract_top_n]
        bottom_lines = lines[-self.config.extract_top_n:]
        
        extracted = '\n'.join(top_lines + ['... [content truncated] ...'] + bottom_lines)
        
        return extracted
    
    # @function: process_batch
    # @purpose: "Process multiple outputs"
    # @input: outputs: List[str]
    # @output: List[str]
    # @async: true
    # @ai_testable: true
    async def process_batch(self, outputs: List[str]) -> List[str]:
        """
        @summary: Batch process
        
        @steps:
          1. Create tasks
          2. Execute concurrently
          3. Return results
        """
        
        # @step: 1
        tasks = [self.process(output) for output in outputs]
        
        # @step: 2-3
        return await asyncio.gather(*tasks)
    
    # @function: get_stats
    # @purpose: "Get gateway statistics"
    # @input: original: str, processed: str
    # @output: Dict[str, any]
    # @ai_testable: true
    def get_stats(self, original: str, processed: str) -> Dict[str, any]:
        """@purpose: Get statistics"""
        
        original_tokens = len(original.split())
        processed_tokens = len(processed.split())
        
        compression_ratio = processed_tokens / max(original_tokens, 1)
        
        return {
            "original_tokens": original_tokens,
            "processed_tokens": processed_tokens,
            "compression_ratio": f"{compression_ratio:.2%}",
            "tokens_saved": original_tokens - processed_tokens
        }

# @class: MCPGateway
# @purpose: "Specialized gateway for MCP protocol"
# @ai_testable: true
class MCPGateway(OutputGateway):
    """
    @summary: MCP gateway
    
    @features:
      - MCP-specific filtering
      - Tool output optimization
      - Model-friendly formatting
    """
    
    # @function: process
    # @purpose: "Process for MCP"
    # @input: tool_output: str, tool_name: str
    # @output: str
    # @async: true
    # @ai_testable: true
    async def process(
        self,
        tool_output: str,
        tool_name: str = None
    ) -> str:
        """
        @summary: Process for MCP
        
        @steps:
          1. Add tool context
          2. Filter and compress
          3. Format for model
        """
        
        # @step: 1
        if tool_name:
            header = f"[Tool: {tool_name}]\n"
        else:
            header = ""
        
        # @step: 2
        processed = await super().process(tool_output)
        
        # @step: 3
        return header + processed
    
    # @function: format_for_model
    # @purpose: "Format output for specific model"
    # @input: text: str, model: str
    # @output: str
    # @ai_testable: true
    def format_for_model(self, text: str, model: str) -> str:
        """@purpose: Format for model"""
        
        # Model-specific formatting
        if 'claude' in model.lower():
            return f"<tool_output>\n{text}\n</tool_output>"
        elif 'gpt' in model.lower():
            return f"Tool Output:\n```\n{text}\n```"
        else:
            return text
