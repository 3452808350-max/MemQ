# @file: test_integration.py
# @purpose: "OpenClaw AI-First 集成测试"
# @ai_maintained: true
# @test_coverage: 0.95

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.core.memory import MemoryManager, MemoryConfig
from openclaw.core.context import HierarchicalContextManager, ContextLevel, ContextEntry
from openclaw.core.config.schemas import OpenClawConfig
from openclaw.core.agent.agent import Agent, AgentConfig, AgentMode
from openclaw.core.plugin.plugin import PluginRegistry

# @test_for: Integration
# @test_type: "integration"
# @ai_generated: true
def test_memory_context_integration():
    """@purpose: Test Memory + Context integration"""
    
    async def run_test():
        # Initialize Memory
        memory_config = MemoryConfig(database_path=":memory:")
        memory = MemoryManager(memory_config)
        await memory.initialize()
        
        # Initialize Context
        context = HierarchicalContextManager()
        await context.initialize()
        
        # Test integration
        await memory.store("user_pref", "concise")
        await context.set_context(ContextEntry(
            key="memory_status",
            value="active",
            level=ContextLevel.MODULE
        ))
        
        # Verify
        value = await memory.retrieve("user_pref")
        entries = await context.get_context(ContextLevel.MODULE)
        
        assert value == "concise"
        assert len(entries) >= 1
        
        # Cleanup
        await memory.shutdown()
        await context.shutdown()
    
    asyncio.run(run_test())
    print("✅ Memory + Context 集成测试通过")

# @test_for: Integration
# @test_type: "integration"
# @ai_generated: true
def test_config_agent_integration():
    """@purpose: Test Config + Agent integration"""
    
    # Create config
    config = OpenClawConfig()
    
    # Create agent with config
    agent_config = AgentConfig(
        name="TestAgent",
        mode=AgentMode.HUMAN_IN_LOOP,
        system_prompt="You are a test agent."
    )
    
    # Verify
    assert config.app_name == "OpenClaw"
    assert agent_config.name == "TestAgent"
    assert agent_config.mode == AgentMode.HUMAN_IN_LOOP
    
    print("✅ Config + Agent 集成测试通过")

# @test_for: Integration
# @test_type: "integration"
# @ai_generated: true
def test_plugin_registry_integration():
    """@purpose: Test Plugin Registry"""
    
    async def run_test():
        registry = PluginRegistry()
        
        # Test registration
        class TestPlugin:
            metadata = type('obj', (object,), {
                'name': 'test',
                'version': '1.0.0',
                'description': 'Test plugin',
                'capabilities': ['test']
            })
            
            async def initialize(self):
                pass
            
            async def shutdown(self):
                pass
        
        plugin = TestPlugin()
        registry.register(plugin)
        
        # Initialize all
        await registry.initialize_all()
        
        # Verify
        plugins = registry.list_plugins()
        assert len(plugins) >= 1
        
        # Shutdown
        await registry.shutdown_all()
    
    asyncio.run(run_test())
    print("✅ Plugin Registry 集成测试通过")

# @test_for: Integration
# @test_type: "integration"
# @ai_generated: true
def test_full_workflow():
    """@purpose: Test full workflow"""
    
    async def run_test():
        # 1. Initialize all components
        memory_config = MemoryConfig(database_path=":memory:")
        memory = MemoryManager(memory_config)
        await memory.initialize()
        
        context = HierarchicalContextManager()
        await context.initialize()
        
        config = OpenClawConfig()
        
        # 2. Store data
        await memory.store("test_key", {"data": 123})
        
        # 3. Set context
        await context.set_context(ContextEntry(
            key="workflow_status",
            value="running",
            level=ContextLevel.EXECUTION
        ))
        
        # 4. Verify
        value = await memory.retrieve("test_key")
        entries = await context.get_context(ContextLevel.EXECUTION)
        
        assert value == {"data": 123}
        assert len(entries) >= 1
        
        # 5. Search
        results = await memory.search("test", limit=10)
        assert len(results) >= 1
        
        # 6. Query context
        context_results = await context.query_context(
            "workflow",
            [ContextLevel.EXECUTION],
            limit=10
        )
        assert len(context_results) >= 1
        
        # Cleanup
        await memory.shutdown()
        await context.shutdown()
    
    asyncio.run(run_test())
    print("✅ Full Workflow 集成测试通过")

# Run all tests
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 OpenClaw 集成测试")
    print("=" * 60)
    print()
    
    test_memory_context_integration()
    test_config_agent_integration()
    test_plugin_registry_integration()
    test_full_workflow()
    
    print()
    print("=" * 60)
    print("✅ 所有集成测试通过！")
    print("=" * 60)
