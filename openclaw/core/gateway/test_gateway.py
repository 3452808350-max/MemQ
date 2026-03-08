# @file: test_gateway.py
# @module: openclaw.core.gateway.test_gateway
# @purpose: "Unit tests for gateway modules"
# @ai_maintained: true
# @version: "1.0.0"

import pytest
import asyncio
from dss_modules.gateway import (
    OutputGateway,
    MCPGateway,
    GatewayConfig
)

# ============ Output Gateway Tests ============

# @test: test_gateway_config
# @purpose: "Test gateway configuration"
def test_gateway_config():
    """@purpose: Test config"""
    
    config = GatewayConfig(
        max_tokens=4000,
        compression_ratio=0.5,
        filter_keywords=["debug", "trace"],
        extract_top_n=10
    )
    
    assert config.max_tokens == 4000
    assert config.compression_ratio == 0.5
    assert "debug" in config.filter_keywords
    assert config.extract_top_n == 10

# @test: test_gateway_init
# @purpose: "Test gateway initialization"
def test_gateway_init():
    """@purpose: Test init"""
    
    gateway = OutputGateway()
    
    assert gateway.config.max_tokens == 4000
    assert gateway.config.compression_ratio == 0.5

# @test: test_gateway_filter
# @purpose: "Test gateway filtering"
def test_gateway_filter():
    """@purpose: Test filter"""
    
    gateway = OutputGateway(
        GatewayConfig(filter_keywords=["debug", "trace"])
    )
    
    text = """
    Normal line 1
    Debug: This is debug info
    Normal line 2
    Trace: This is trace info
    Normal line 3
    """
    
    filtered = gateway._filter(text)
    
    assert "Debug:" not in filtered
    assert "Trace:" not in filtered
    assert "Normal line" in filtered

# @test: test_gateway_compress
# @purpose: "Test gateway compression"
@pytest.mark.asyncio
async def test_gateway_compress():
    """@purpose: Test compress"""
    
    gateway = OutputGateway(
        GatewayConfig(max_tokens=10, compression_ratio=0.5)
    )
    
    text = " ".join([f"word{i}" for i in range(20)])
    
    compressed = await gateway._compress(text)
    
    assert len(compressed.split()) <= 5  # 10 * 0.5
    assert "[compressed]" in compressed

# @test: test_gateway_extract
# @purpose: "Test gateway extraction"
def test_gateway_extract():
    """@purpose: Test extract"""
    
    gateway = OutputGateway(
        GatewayConfig(extract_top_n=3)
    )
    
    lines = [f"line{i}" for i in range(10)]
    text = "\n".join(lines)
    
    extracted = gateway._extract_key_info(text)
    
    # Should have first 3 + last 3 + truncation marker
    assert "line0" in extracted
    assert "line9" in extracted
    assert "[content truncated]" in extracted

# @test: test_gateway_process
# @purpose: "Test gateway processing"
@pytest.mark.asyncio
async def test_gateway_process():
    """@purpose: Test process"""
    
    gateway = OutputGateway(
        GatewayConfig(
            max_tokens=20,
            filter_keywords=["debug"],
            extract_top_n=5
        )
    )
    
    text = """
    Normal line 1
    Debug: debug info
    Normal line 2
    Normal line 3
    """ * 10  # Make it long
    
    processed = await gateway.process(text)
    
    assert "Debug:" not in processed
    assert len(processed.split()) <= 20

# @test: test_gateway_stats
# @purpose: "Test gateway statistics"
def test_gateway_stats():
    """@purpose: Test stats"""
    
    gateway = OutputGateway()
    
    original = "word1 word2 word3 word4 word5"
    processed = "word1 word2"
    
    stats = gateway.get_stats(original, processed)
    
    assert stats['original_tokens'] == 5
    assert stats['processed_tokens'] == 2
    assert float(stats['compression_ratio'].rstrip('%')) < 100
    assert stats['tokens_saved'] == 3

# ============ MCP Gateway Tests ============

# @test: test_mcp_gateway_init
# @purpose: "Test MCP gateway initialization"
def test_mcp_gateway_init():
    """@purpose: Test MCP init"""
    
    gateway = MCPGateway()
    
    assert isinstance(gateway, OutputGateway)

# @test: test_mcp_gateway_process
# @purpose: "Test MCP gateway processing"
@pytest.mark.asyncio
async def test_mcp_gateway_process():
    """@purpose: Test MCP process"""
    
    gateway = MCPGateway()
    
    tool_output = "Tool output data"
    tool_name = "test_tool"
    
    processed = await gateway.process(tool_output, tool_name)
    
    assert "[Tool: test_tool]" in processed
    assert "Tool output data" in processed

# @test: test_mcp_gateway_format
# @purpose: "Test MCP gateway formatting"
def test_mcp_gateway_format():
    """@purpose: Test format"""
    
    gateway = MCPGateway()
    
    text = "Tool output"
    
    # Test Claude format
    claude_format = gateway.format_for_model(text, "claude-3")
    assert "<tool_output>" in claude_format
    assert "</tool_output>" in claude_format
    
    # Test GPT format
    gpt_format = gateway.format_for_model(text, "gpt-4")
    assert "Tool Output:" in gpt_format
    assert "```" in gpt_format

# @test: test_gateway_batch_process
# @purpose: "Test batch processing"
@pytest.mark.asyncio
async def test_gateway_batch_process():
    """@purpose: Test batch"""
    
    gateway = OutputGateway()
    
    outputs = [
        "Output 1 with lots of words " * 10,
        "Output 2 with lots of words " * 10,
        "Output 3 with lots of words " * 10
    ]
    
    processed = await gateway.process_batch(outputs)
    
    assert len(processed) == 3
    assert all(len(p) < len(o) for p, o in zip(processed, outputs))

# ============ Integration Tests ============

# @test: test_gateway_end_to_end
# @purpose: "Test end-to-end gateway processing"
@pytest.mark.asyncio
async def test_gateway_end_to_end():
    """@purpose: Test end-to-end"""
    
    gateway = MCPGateway(
        GatewayConfig(
            max_tokens=50,
            compression_ratio=0.5,
            filter_keywords=["DEBUG", "TRACE"],
            extract_top_n=5
        )
    )
    
    # Simulate tool output
    tool_output = """
    DEBUG: Starting process
    Result line 1
    Result line 2
    Result line 3
    Result line 4
    Result line 5
    Result line 6
    Result line 7
    Result line 8
    Result line 9
    Result line 10
    TRACE: Ending process
    """
    
    processed = await gateway.process(tool_output, "search_tool")
    
    # Verify filtering
    assert "DEBUG:" not in processed
    assert "TRACE:" not in processed
    
    # Verify compression
    assert len(processed.split()) <= 50
    
    # Verify tool name
    assert "[Tool: search_tool]" in processed

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
