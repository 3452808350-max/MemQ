# OpenClaw AI-First 代码规范

> **版本**: 1.0.0  
> **创建时间**: 2026-03-06  
> **理念**: Code Written for Machines, Not Humans

---

## 📜 核心原则

### 原则 1: 结构化优先 (Structured First)

**传统代码**:
```python
# 人类可读但结构松散
def process(data):
    result = []
    for item in data:
        if item.get('type') == 'a':
            result.append(transform_a(item))
        elif item.get('type') == 'b':
            result.append(transform_b(item))
    return result
```

**AI 优先代码**:
```python
# @module: data_processor
# @purpose: "Process data items based on type classification"
# @pattern: "Type-based dispatch with explicit transformation rules"

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# @schema: ItemType
class ItemType(str, Enum):
    """@ai_readable: Explicit type enumeration"""
    TYPE_A = "a"
    TYPE_B = "b"

# @schema: TransformRule
@dataclass
class TransformRule:
    """@ai_readable: Explicit transformation rule structure"""
    item_type: ItemType
    transformer: callable
    output_schema: Dict[str, type]

# @registry: TRANSFORM_RULES
TRANSFORM_RULES: Dict[ItemType, TransformRule] = {
    ItemType.TYPE_A: TransformRule(ItemType.TYPE_A, transform_a, {"result": str}),
    ItemType.TYPE_B: TransformRule(ItemType.TYPE_B, transform_b, {"result": int}),
}

# @function: process
# @purpose: "Process data items using registered transformation rules"
# @pattern: "Data-driven dispatch"
# @input: List[Dict[str, Any]]
# @output: List[Dict[str, Any]]
# @side_effects: None (pure function)
def process(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """@ai_summary: Dispatch each item to its transformer based on type"""
    result: List[Dict[str, Any]] = []
    
    for item in data:
        item_type = ItemType(item.get('type'))
        rule = TRANSFORM_RULES.get(item_type)
        
        if rule:
            transformed = rule.transformer(item)
            result.append(transformed)
        else:
            # @ai_readable: Explicit error handling
            raise ValueError(f"Unknown item type: {item_type}")
    
    return result
```

---

### 原则 2: 显式优先 (Explicit First)

**传统代码**:
```python
# 隐式行为，AI 难理解
class MemoryManager:
    def __init__(self, config):
        self.config = config
        self._cache = {}
        self._init_db()  # 隐式副作用
    
    def _init_db(self):
        # AI 不知道什么时候会调用
        pass
```

**AI 优先代码**:
```python
# @module: memory_manager
# @purpose: "Manage AI long-term memory with explicit lifecycle"
# @lifecycle: ["initialize", "store", "retrieve", "cleanup"]

from typing import Optional, Dict
from dataclasses import dataclass, field

# @schema: MemoryManagerConfig
@dataclass
class MemoryManagerConfig:
    """@ai_readable: Explicit configuration structure"""
    database_path: str
    cache_size: int = 1000
    auto_initialize: bool = False

# @class: MemoryManager
# @state: ["initialized", "running", "stopped"]
# @dependencies: ["config", "database_connection"]
class MemoryManager:
    """@ai_summary: Memory manager with explicit lifecycle management"""
    
    # @attribute: state
    # @type: str
    # @values: ["initialized", "running", "stopped"]
    state: str = "initialized"
    
    # @attribute: config
    # @type: MemoryManagerConfig
    config: MemoryManagerConfig
    
    # @attribute: db_connection
    # @type: Optional[DatabaseConnection]
    # @nullable: true
    db_connection: Optional[DatabaseConnection] = None
    
    # @constructor
    # @side_effects: None (explicit initialization required)
    def __init__(self, config: MemoryManagerConfig):
        """@ai_summary: Create manager without side effects"""
        self.config = config
        self.state = "initialized"
    
    # @method: initialize
    # @purpose: "Initialize database connection explicitly"
    # @side_effects: ["Create database connection"]
    # @precondition: state == "initialized"
    # @postcondition: state == "running"
    def initialize(self) -> None:
        """@ai_summary: Explicit initialization with clear pre/post conditions"""
        if self.state != "initialized":
            raise RuntimeError(f"Cannot initialize from state: {self.state}")
        
        self.db_connection = DatabaseConnection(self.config.database_path)
        self.state = "running"
    
    # @method: store
    # @purpose: "Store memory to database"
    # @side_effects: ["Database write"]
    # @precondition: state == "running"
    # @postcondition: Memory stored or error raised
    def store(self, text: str, category: str) -> str:
        """@ai_summary: Store memory with explicit precondition check"""
        if self.state != "running":
            raise RuntimeError("Manager not initialized. Call initialize() first.")
        
        return self.db_connection.store(text, category)
```

---

### 原则 3: 数据驱动优先 (Data-Driven First)

**传统代码**:
```python
# 流程驱动，AI 难理解逻辑
def validate_agent(agent):
    if not agent.name:
        return False
    if not agent.model:
        return False
    if agent.model not in ['minimax', 'qwen', 'kimi']:
        return False
    if agent.memory_limit < 100:
        return False
    return True
```

**AI 优先代码**:
```python
# @module: agent_validator
# @purpose: "Validate agent configuration using declarative rules"
# @pattern: "Data-driven validation with schema"

from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

# @schema: ValidationRule
@dataclass
class ValidationRule:
    """@ai_readable: Explicit validation rule structure"""
    field: str
    rule_type: str  # "required", "enum", "range", "pattern"
    params: Dict[str, Any]
    error_message: str

# @schema: ValidationResult
@dataclass
class ValidationResult:
    """@ai_readable: Explicit validation result structure"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

# @registry: AGENT_VALIDATION_RULES
# @purpose: "Declarative validation rules for agent configuration"
AGENT_VALIDATION_RULES: List[ValidationRule] = [
    ValidationRule(
        field="name",
        rule_type="required",
        params={"min_length": 1, "max_length": 64},
        error_message="Agent name is required (1-64 characters)"
    ),
    ValidationRule(
        field="model",
        rule_type="enum",
        params={"values": ["minimax", "qwen", "kimi"]},
        error_message="Model must be one of: minimax, qwen, kimi"
    ),
    ValidationRule(
        field="memory_limit",
        rule_type="range",
        params={"min": 100, "max": 10000},
        error_message="Memory limit must be between 100 and 10000"
    ),
]

# @function: validate_agent
# @purpose: "Validate agent config using declarative rules"
# @pattern: "Data-driven validation"
# @input: Dict[str, Any]
# @output: ValidationResult
# @side_effects: None (pure function)
def validate_agent(config: Dict[str, Any]) -> ValidationResult:
    """@ai_summary: Validate using registered declarative rules"""
    result = ValidationResult(valid=True)
    
    for rule in AGENT_VALIDATION_RULES:
        value = config.get(rule.field)
        
        if rule.rule_type == "required":
            if value is None or value == "":
                result.valid = False
                result.errors.append(rule.error_message)
        
        elif rule.rule_type == "enum":
            if value not in rule.params["values"]:
                result.valid = False
                result.errors.append(rule.error_message)
        
        elif rule.rule_type == "range":
            if not (rule.params["min"] <= value <= rule.params["max"]):
                result.valid = False
                result.errors.append(rule.error_message)
    
    return result
```

---

### 原则 4: 可推理优先 (Reasoning-Friendly)

**传统代码**:
```python
# AI 不知道为什么要这样写
def calculate_score(user):
    score = 0
    if user.age > 18:
        score += 10
    if user.premium:
        score += 20
    if user.active_days > 30:
        score += 30
    return score
```

**AI 优先代码**:
```python
# @module: score_calculator
# @purpose: "Calculate user score based on explicit scoring rules"
# @reasoning: "Each rule has explicit weight and condition"

from typing import List, Dict, Any
from dataclasses import dataclass

# @schema: ScoringRule
@dataclass
class ScoringRule:
    """@ai_readable: Explicit scoring rule with weight and condition"""
    rule_id: str
    description: str  # @ai_context: Why this rule exists
    condition: callable
    weight: int  # Score weight
    category: str  # For grouping rules

# @registry: SCORING_RULES
# @purpose: "Explicit scoring rules with clear reasoning"
SCORING_RULES: List[ScoringRule] = [
    ScoringRule(
        rule_id="age_adult",
        description="Adult users get base score (business requirement)",
        condition=lambda user: user.age > 18,
        weight=10,
        category="demographics"
    ),
    ScoringRule(
        rule_id="premium_user",
        description="Premium users contribute more to platform",
        condition=lambda user: user.premium,
        weight=20,
        category="subscription"
    ),
    ScoringRule(
        rule_id="active_user",
        description="Active users are more valuable (30+ days)",
        condition=lambda user: user.active_days > 30,
        weight=30,
        category="engagement"
    ),
]

# @function: calculate_score
# @purpose: "Calculate user score using explicit scoring rules"
# @reasoning: "Sum of all matching rule weights"
# @input: User object
# @output: int (total score)
# @side_effects: None (pure function)
def calculate_score(user: User) -> int:
    """
    @ai_summary: Calculate score by summing weights of matching rules
    
    @ai_reasoning: |
      For each scoring rule:
      1. Evaluate condition against user
      2. If condition matches, add rule weight to score
      3. Return total score
    
    @ai_example: |
      User(age=25, premium=True, active_days=45)
      → age_adult matches: +10
      → premium_user matches: +20
      → active_user matches: +30
      → Total: 60
    """
    total_score: int = 0
    
    for rule in SCORING_RULES:
        if rule.condition(user):
            total_score += rule.weight
    
    return total_score
```

---

### 原则 5: 短小函数优先 (Short Function First)

**传统代码**:
```python
# 长函数，AI 难以在有限上下文中理解
def process_request(request):
    # 50+ 行代码...
    # AI 需要记住太多上下文
    pass
```

**AI 优先代码**:
```python
# @module: request_processor
# @purpose: "Process requests using composable small functions"
# @pattern: "Function composition with clear boundaries"

from typing import Dict, Any, Tuple

# @function: validate_request
# @purpose: "Validate request structure"
# @input: Dict[str, Any]
# @output: Tuple[bool, Optional[str]]
# @side_effects: None
# @max_lines: 20
def validate_request(request: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """@ai_summary: Validate request with explicit error message"""
    if not request.get('type'):
        return False, "Missing request type"
    if not request.get('data'):
        return False, "Missing request data"
    return True, None

# @function: authorize_request
# @purpose: "Check request authorization"
# @input: Dict[str, Any]
# @output: bool
# @side_effects: None
# @max_lines: 20
def authorize_request(request: Dict[str, Any]) -> bool:
    """@ai_summary: Check authorization token"""
    token = request.get('token')
    return token and token.startswith('valid_')

# @function: process_request
# @purpose: "Process request using composable validation"
# @pattern: "Early return with small functions"
# @input: Dict[str, Any]
# @output: Dict[str, Any]
# @side_effects: ["Log processing"]
# @max_lines: 20
def process_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    @ai_summary: Process request with explicit validation steps
    
    @ai_flow: |
      1. Validate request structure
      2. Check authorization
      3. Process based on type
      4. Return result
    """
    # Step 1: Validate
    valid, error = validate_request(request)
    if not valid:
        return {"success": False, "error": error}
    
    # Step 2: Authorize
    if not authorize_request(request):
        return {"success": False, "error": "Unauthorized"}
    
    # Step 3: Process
    result = process_by_type(request['type'], request['data'])
    
    # Step 4: Return
    return {"success": True, "result": result}
```

---

## 📊 AI-First 代码检查清单

### 结构检查

- [ ] 函数长度 < 20 行
- [ ] 模块长度 < 500 行
- [ ] 单一职责原则
- [ ] 显式依赖注入
- [ ] 无隐式副作用

### 命名检查

- [ ] 变量名语义清晰
- [ ] 函数名表达意图
- [ ] 类名表达职责
- [ ] 无缩写和隐喻
- [ ] 使用枚举代替魔法值

### 类型检查

- [ ] 完整类型注解
- [ ] 使用 dataclass
- [ ] 使用 TypedDict
- [ ] 显式 Optional
- [ ] 显式 Union 类型

### 文档检查

- [ ] @module 元数据
- [ ] @purpose 说明
- [ ] @input/@output 类型
- [ ] @side_effects 声明
- [ ] @ai_summary 注释

### 逻辑检查

- [ ] 显式条件判断
- [ ] 显式错误处理
- [ ] 显式状态管理
- [ ] 数据驱动逻辑
- [ ] 无复杂继承

---

## 🎯 实施计划

### Phase 1: 规范定义 (1 周)

- [ ] 完成 AI-First 代码规范文档
- [ ] 创建代码模板
- [ ] 创建检查清单
- [ ] 创建示例代码库

### Phase 2: 工具支持 (1 周)

- [ ] 创建 lint 规则
- [ ] 创建代码生成器
- [ ] 创建文档生成器
- [ ] 创建验证工具

### Phase 3: 试点模块 (2 周)

- [ ] 选择 Memory Manager 模块
- [ ] 完全 AI-First 重构
- [ ] 验证 AI 理解效果
- [ ] 收集反馈改进

### Phase 4: 全面推广 (4 周)

- [ ] 核心模块重构
- [ ] 文档更新
- [ ] 培训材料
- [ ] 持续改进

---

## 📚 参考资源

### 论文

1. Stanford - Agentic Programming
2. Anthropic - Context Engineering
3. GitHub - LLM Code Readability Study
4. OpenAI - Model Behavior Consistency

### 工具

1. ESLint AI rules
2. Pylint AI plugins
3. Code formatter for AI
4. Documentation generator

---

*规范版本：1.0.0*  
*创建时间：2026-03-06*  
*状态：草案*  
*下一步：讨论和修改*
