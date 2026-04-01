# @file: plugin.py
# @module: openclaw.core.plugin.plugin
# @purpose: "Define AI-First Plugin system"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# @enum: PluginState
# @ai_readable: true
class PluginState(str, Enum):
    """
    @value: UNLOADED - Plugin not loaded
    @value: LOADING - Plugin is loading
    @value: ACTIVE - Plugin is active
    @value: ERROR - Plugin has error
    """
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"

# @schema: PluginMetadata
# @ai_readable: true
@dataclass
class PluginMetadata:
    """@purpose: Plugin metadata structure"""
    
    # @field: name
    # @type: str
    # @required: true
    name: str
    
    # @field: version
    # @type: str
    # @required: true
    version: str
    
    # @field: description
    # @type: str
    # @required: true
    description: str
    
    # @field: author
    # @type: str
    # @default: "Unknown"
    author: str = "Unknown"
    
    # @field: dependencies
    # @type: List[str]
    # @default: []
    dependencies: List[str] = field(default_factory=list)
    
    # @field: capabilities
    # @type: List[str]
    # @default: []
    capabilities: List[str] = field(default_factory=list)

# @class: Plugin
# @purpose: "AI-First Plugin base class"
# @ai_testable: true
class Plugin:
    """
    @summary: Base class for all plugins
    
    @features:
      - Explicit metadata
      - Lifecycle management
      - Capability declaration
      - AI-discoverable
    """
    
    # @attribute: metadata
    # @type: PluginMetadata
    metadata: PluginMetadata
    
    # @attribute: state
    # @type: PluginState
    state: PluginState = PluginState.UNLOADED
    
    # @attribute: config
    # @type: Dict[str, Any]
    config: Dict[str, Any] = field(default_factory=dict)
    
    # @function: initialize
    # @purpose: "Initialize plugin"
    # @side_effects: ["Set state to ACTIVE"]
    # @async: true
    # @ai_testable: true
    async def initialize(self) -> None:
        """@purpose: Initialize plugin"""
        
        self.state = PluginState.LOADING
        
        try:
            await self._initialize()
            self.state = PluginState.ACTIVE
        except Exception as e:
            self.state = PluginState.ERROR
            raise
    
    # @function: _initialize
    # @purpose: "Plugin-specific initialization"
    # @side_effects: ["Plugin-specific"]
    # @async: true
    # @protected: true
    # @ai_testable: true
    async def _initialize(self) -> None:
        """@purpose: Override in subclass"""
        pass
    
    # @function: shutdown
    # @purpose: "Shutdown plugin"
    # @side_effects: ["Set state to UNLOADED"]
    # @async: true
    # @ai_testable: true
    async def shutdown(self) -> None:
        """@purpose: Shutdown plugin"""
        
        try:
            await self._shutdown()
        finally:
            self.state = PluginState.UNLOADED
    
    # @function: _shutdown
    # @purpose: "Plugin-specific shutdown"
    # @side_effects: ["Plugin-specific"]
    # @async: true
    # @protected: true
    # @ai_testable: true
    async def _shutdown(self) -> None:
        """@purpose: Override in subclass"""
        pass
    
    # @function: get_capabilities
    # @purpose: "Get plugin capabilities"
    # @output: List[Dict[str, Any]]
    # @ai_testable: true
    def get_capabilities(self) -> List[Dict[str, Any]]:
        """@purpose: Get capabilities"""
        
        return [
            {"name": cap, "enabled": True}
            for cap in self.metadata.capabilities
        ]

# @class: PluginRegistry
# @purpose: "Manage plugin lifecycle"
# @ai_testable: true
class PluginRegistry:
    """
    @summary: Plugin registry and lifecycle manager
    
    @features:
      - Plugin discovery
      - Lifecycle management
      - Dependency resolution
      - AI-discoverable
    """
    
    # @attribute: plugins
    # @type: Dict[str, Plugin]
    plugins: Dict[str, Plugin]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize registry"""
        self.plugins = {}
    
    # @function: register
    # @purpose: "Register plugin"
    # @input: plugin: Plugin
    # @side_effects: ["Add to registry"]
    # @ai_testable: true
    def register(self, plugin: Plugin) -> None:
        """@purpose: Register plugin"""
        
        self.plugins[plugin.metadata.name] = plugin
    
    # @function: unregister
    # @purpose: "Unregister plugin"
    # @input: name: str
    # @side_effects: ["Remove from registry"]
    # @ai_testable: true
    def unregister(self, name: str) -> None:
        """@purpose: Unregister plugin"""
        
        if name in self.plugins:
            del self.plugins[name]
    
    # @function: get_plugin
    # @purpose: "Get plugin by name"
    # @input: name: str
    # @output: Optional[Plugin]
    # @ai_testable: true
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """@purpose: Get plugin"""
        
        return self.plugins.get(name)
    
    # @function: list_plugins
    # @purpose: "List all plugins"
    # @output: List[PluginMetadata]
    # @ai_testable: true
    def list_plugins(self) -> List[PluginMetadata]:
        """@purpose: List plugins"""
        
        return [
            plugin.metadata
            for plugin in self.plugins.values()
        ]
    
    # @function: initialize_all
    # @purpose: "Initialize all plugins"
    # @side_effects: ["Initialize all plugins"]
    # @async: true
    # @ai_testable: true
    async def initialize_all(self) -> None:
        """@purpose: Initialize all"""
        
        for plugin in self.plugins.values():
            await plugin.initialize()
    
    # @function: shutdown_all
    # @purpose: "Shutdown all plugins"
    # @side_effects: ["Shutdown all plugins"]
    # @async: true
    # @ai_testable: true
    async def shutdown_all(self) -> None:
        """@purpose: Shutdown all"""
        
        for plugin in reversed(list(self.plugins.values())):
            await plugin.shutdown()
