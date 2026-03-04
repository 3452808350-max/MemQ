# Context 压缩与临时记忆机制

> **功能**: 话题转换时自动总结压缩上下文  
> **存储路径**: `/home/kyj/.openclaw/workspace/temp_memory/`  
> **日期**: 2026-03-03

---

## 🏗️ 机制设计

### 工作流程

```
检测话题转换
    ↓
总结当前对话要点
    ↓
压缩关键信息
    ↓
保存到临时记忆文件
    ↓
载入到新话题 context
    ↓
继续新话题讨论
```

---

## 📁 文件结构

```
/home/kyj/.openclaw/workspace/temp_memory/
├── context_index.json          # 索引文件（记录所有临时记忆）
├── 2026-03-03_14-30_IELTS.md   # 按时间 + 话题命名
├── 2026-03-03_15-00_Fara.md
├── 2026-03-03_16-15_DSS.md
└── ...
```

---

## 📝 临时记忆文件格式

```markdown
# Temp Memory: [话题名称]

**时间**: 2026-03-03 14:30-15:00  
**持续时间**: 30 分钟  
**相关话题**: [标签 1, 标签 2, ...]

---

## 📋 核心讨论

### 主要问题
[用户提出的核心问题]

### 关键结论
[达成的结论/决定]

### 待办事项
- [ ] 未完成的任务
- [ ] 需要后续跟进的

---

## 🎯 重要信息

### 用户偏好
- [发现的偏好]

### 技术细节
- [关键配置/参数]

### 决策记录
- [做出的决定]

---

## 🔗 相关文件

- `/path/to/file1.md`
- `/path/to/file2.py`

---

## 💡 上下文摘要

[200-300 字的对话摘要，包含关键信息]

---

*创建时间：2026-03-03 14:30*  
*话题转换触发：[新话题名称]*
```

---

## 🤖 实现脚本

### 1. 话题检测模块

```python
#!/usr/bin/env python3
"""
topic_detector.py - 检测话题转换

使用语义相似度判断是否发生话题转换
"""
import numpy as np
from datetime import datetime
from typing import List, Tuple, Optional
import json
import os

# 临时记忆目录
TEMP_MEMORY_DIR = "/home/kyj/.openclaw/workspace/temp_memory"
os.makedirs(TEMP_MEMORY_DIR, exist_ok=True)

# 话题转换阈值（余弦相似度低于此值认为转换话题）
TOPIC_CHANGE_THRESHOLD = 0.6

class TopicDetector:
    def __init__(self):
        self.current_topic = None
        self.conversation_history = []
        
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        # 实际使用可以用 TF-IDF 或词向量
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 
                     'I', 'you', 'we', 'they', 'it', 'this', 'that'}
        
        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return keywords[:20]  # 限制数量
    
    def calculate_similarity(self, keywords1: List[str], 
                           keywords2: List[str]) -> float:
        """计算关键词相似度（Jaccard 相似度）"""
        set1, set2 = set(keywords1), set(keywords2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0
    
    def detect_topic_change(self, new_message: str) -> bool:
        """检测是否发生话题转换"""
        if not self.conversation_history:
            return False
        
        # 提取当前消息关键词
        new_keywords = self.extract_keywords(new_message)
        
        # 提取最近对话的关键词
        recent_history = ' '.join(self.conversation_history[-10:])
        old_keywords = self.extract_keywords(recent_history)
        
        # 计算相似度
        similarity = self.calculate_similarity(new_keywords, old_keywords)
        
        # 判断是否转换话题
        is_change = similarity < TOPIC_CHANGE_THRESHOLD
        
        if is_change:
            print(f"🔄 检测到话题转换！(相似度：{similarity:.2f})")
        else:
            print(f"💬 同一话题继续 (相似度：{similarity:.2f})")
        
        return is_change
    
    def add_to_history(self, message: str):
        """添加到对话历史"""
        self.conversation_history.append(message)
        # 限制历史长度
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-50:]

# 使用示例
if __name__ == "__main__":
    detector = TopicDetector()
    
    # 模拟对话
    messages = [
        "我想配置 Fara-7B 在 Homelab 上",
        "需要安装 ROCm 驱动吗？",
        "RX6800 的 GPU 怎么配置？",
        "对了，雅思作文怎么写开头？",  # 话题转换！
    ]
    
    for msg in messages:
        if detector.detect_topic_change(msg):
            print("→ 触发上下文压缩保存")
        detector.add_to_history(msg)
```

---

### 2. 上下文压缩模块

```python
#!/usr/bin/env python3
"""
context_compressor.py - 压缩对话上下文

使用 LLM 总结对话要点
"""
import requests
import json
from datetime import datetime
from typing import Dict, List

class ContextCompressor:
    def __init__(self):
        self.kimi_api_url = "http://localhost:5000/chat"
        
    def compress_conversation(self, 
                            conversation: List[Dict], 
                            max_length: int = 500) -> str:
        """
        压缩对话上下文
        
        Args:
            conversation: 对话历史 [(role, content), ...]
            max_length: 最大字数
        
        Returns:
            压缩后的摘要
        """
        # 构建总结提示
        prompt = self._build_summary_prompt(conversation)
        
        # 调用 Kimi API
        try:
            response = requests.post(
                self.kimi_api_url,
                json={
                    "prompt": prompt,
                    "session": "context-compression"
                },
                timeout=60
            )
            
            if response.json().get('success'):
                summary = response.json().get('response', '')
                return summary[:max_length]
        except Exception as e:
            print(f"⚠️  压缩失败：{e}")
            return self._fallback_summary(conversation)
        
        return ""
    
    def _build_summary_prompt(self, conversation: List[Dict]) -> str:
        """构建总结提示"""
        conv_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation[-20:]  # 最近 20 条
        ])
        
        prompt = f"""请总结以下对话的核心内容，包括：

1. 讨论的主要话题
2. 达成的结论或决定
3. 未完成的任务或待办事项
4. 重要的技术细节（配置、参数等）
5. 用户的偏好或需求

对话内容：
{conv_text}

请用简洁的中文总结，300 字以内。格式清晰，使用列表。
"""
        return prompt
    
    def _fallback_summary(self, conversation: List[Dict]) -> str:
        """备用总结方案（如果 API 失败）"""
        # 简单提取关键句
        key_points = []
        for msg in conversation[-10:]:
            if msg['role'] == 'user' and len(msg['content']) > 20:
                key_points.append(f"- {msg['content'][:100]}")
        
        return "\n".join(key_points)

# 使用示例
if __name__ == "__main__":
    compressor = ContextCompressor()
    
    # 模拟对话
    conversation = [
        {"role": "user", "content": "我想配置 Fara-7B"},
        {"role": "assistant", "content": "好的，需要以下步骤..."},
        # ... 更多对话
    ]
    
    summary = compressor.compress_conversation(conversation)
    print("📝 对话摘要:")
    print(summary)
```

---

### 3. 临时记忆管理模块

```python
#!/usr/bin/env python3
"""
temp_memory_manager.py - 临时记忆管理

保存、加载、索引临时记忆文件
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

TEMP_MEMORY_DIR = "/home/kyj/.openclaw/workspace/temp_memory"
INDEX_FILE = os.path.join(TEMP_MEMORY_DIR, "context_index.json")

class TempMemoryManager:
    def __init__(self):
        os.makedirs(TEMP_MEMORY_DIR, exist_ok=True)
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """加载索引文件"""
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"memories": []}
    
    def _save_index(self):
        """保存索引文件"""
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def save_memory(self, 
                   topic: str, 
                   summary: str, 
                   metadata: Dict = None) -> str:
        """
        保存临时记忆
        
        Args:
            topic: 话题名称
            summary: 对话摘要
            metadata: 元数据（标签、相关文件等）
        
        Returns:
            文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_topic = topic.replace(" ", "_").replace("/", "_")[:30]
        filename = f"{timestamp}_{safe_topic}.md"
        filepath = os.path.join(TEMP_MEMORY_DIR, filename)
        
        # 生成内容
        content = self._generate_markdown(topic, summary, metadata)
        
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新索引
        self.index["memories"].append({
            "filename": filename,
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "filepath": filepath,
            "summary_preview": summary[:200]
        })
        self._save_index()
        
        print(f"✅ 临时记忆已保存：{filepath}")
        return filepath
    
    def _generate_markdown(self, 
                          topic: str, 
                          summary: str, 
                          metadata: Dict = None) -> str:
        """生成 Markdown 格式内容"""
        if metadata is None:
            metadata = {}
        
        content = f"""# Temp Memory: {topic}

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**话题**: {topic}  
**标签**: {', '.join(metadata.get('tags', ['未分类']))}

---

## 📝 对话摘要

{summary}

---

## 🎯 关键信息

### 用户偏好
{metadata.get('preferences', '- 无')}

### 技术细节
{metadata.get('technical_details', '- 无')}

### 待办事项
{chr(10).join('- ' + item for item in metadata.get('todos', ['无']))}

---

## 🔗 相关文件

{chr(10).join('- ' + f for f in metadata.get('related_files', ['无']))}

---

*创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*触发：话题转换*
"""
        return content
    
    def load_recent_memories(self, 
                             limit: int = 5, 
                             topic: str = None) -> List[Dict]:
        """
        加载最近的临时记忆
        
        Args:
            limit: 数量限制
            topic: 话题过滤（可选）
        
        Returns:
            记忆列表
        """
        memories = self.index["memories"]
        
        # 按时间排序
        memories_sorted = sorted(
            memories, 
            key=lambda x: x["timestamp"], 
            reverse=True
        )
        
        # 过滤话题
        if topic:
            memories_filtered = [
                m for m in memories_sorted 
                if topic.lower() in m["topic"].lower()
            ]
        else:
            memories_filtered = memories_sorted
        
        return memories_filtered[:limit]
    
    def search_memories(self, keywords: str) -> List[Dict]:
        """搜索临时记忆"""
        results = []
        for memory in self.index["memories"]:
            if (keywords.lower() in memory["topic"].lower() or 
                keywords.lower() in memory["summary_preview"].lower()):
                results.append(memory)
        return results
    
    def get_memory_content(self, filename: str) -> str:
        """读取记忆文件内容"""
        filepath = os.path.join(TEMP_MEMORY_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return "文件不存在"

# 使用示例
if __name__ == "__main__":
    manager = TempMemoryManager()
    
    # 保存记忆
    manager.save_memory(
        topic="Fara-7B 配置",
        summary="讨论了在 Homelab (RX6800) 上配置 Fara-7B 的步骤，包括 ROCm 安装、vLLM 配置、Systemd 服务创建等。",
        metadata={
            "tags": ["AI", "Fara-7B", "Homelab", "配置"],
            "technical_details": "- 端口 5001\n- RX6800 GPU\n- ROCm 6.0",
            "todos": ["测试 Fara 服务", "配置 OpenClaw 集成"],
            "related_files": ["/home/fara/fara_service.json"]
        }
    )
    
    # 加载最近记忆
    recent = manager.load_recent_memories(limit=3)
    print(f"📚 最近 {len(recent)} 条记忆")
    
    # 搜索记忆
    results = manager.search_memories("Fara")
    print(f"🔍 找到 {len(results)} 条相关记忆")
```

---

### 4. 主集成模块

```python
#!/usr/bin/env python3
"""
context_manager.py - 上下文管理主模块

整合话题检测、压缩、保存功能
"""
from topic_detector import TopicDetector
from context_compressor import ContextCompressor
from temp_memory_manager import TempMemoryManager
from typing import List, Dict

class ContextManager:
    def __init__(self):
        self.detector = TopicDetector()
        self.compressor = ContextCompressor()
        self.memory_manager = TempMemoryManager()
        self.current_topic = None
        self.conversation_buffer = []
        
    def process_message(self, 
                       role: str, 
                       content: str) -> Dict:
        """
        处理新消息
        
        Args:
            role: 'user' 或 'assistant'
            content: 消息内容
        
        Returns:
            处理结果（是否触发保存等）
        """
        result = {
            "topic_changed": False,
            "saved_memory": False,
            "memory_path": None
        }
        
        # 检测话题转换
        if role == 'user' and self.detector.detect_topic_change(content):
            # 触发保存
            if self.conversation_buffer:
                self._save_current_context()
                result["topic_changed"] = True
                result["saved_memory"] = True
        
        # 添加到历史
        self.detector.add_to_history(content)
        self.conversation_buffer.append({
            "role": role,
            "content": content,
            "timestamp": __import__('time').time()
        })
        
        return result
    
    def _save_current_context(self):
        """保存当前上下文"""
        if not self.conversation_buffer:
            return
        
        # 压缩对话
        summary = self.compressor.compress_conversation(
            self.conversation_buffer
        )
        
        # 提取元数据
        metadata = self._extract_metadata()
        
        # 保存
        topic = self._identify_current_topic()
        filepath = self.memory_manager.save_memory(
            topic=topic,
            summary=summary,
            metadata=metadata
        )
        
        # 清空缓冲
        self.conversation_buffer = []
        
        print(f"💾 上下文已保存：{filepath}")
    
    def _identify_current_topic(self) -> str:
        """识别当前话题"""
        if not self.conversation_buffer:
            return "未命名对话"
        
        # 简单提取第一个用户消息的关键词
        first_msg = self.conversation_buffer[0]
        if first_msg["role"] == "user":
            # 取前 20 个字作为话题
            return first_msg["content"][:30]
        
        return "对话记录"
    
    def _extract_metadata(self) -> Dict:
        """提取元数据"""
        # 可以从对话中提取文件路径、配置等
        metadata = {
            "tags": [],
            "technical_details": [],
            "todos": [],
            "related_files": []
        }
        
        # 简单提取文件路径
        for msg in self.conversation_buffer:
            content = msg["content"]
            if "/home/" in content or "/opt/" in content:
                # 提取路径
                import re
                paths = re.findall(r'/[\w/.-]+', content)
                metadata["related_files"].extend(paths[:5])
        
        return metadata
    
    def load_relevant_context(self, 
                            keywords: str = None, 
                            limit: int = 3) -> str:
        """
        加载相关上下文
        
        Args:
            keywords: 搜索关键词
            limit: 返回数量
        
        Returns:
            格式化的上下文文本
        """
        if keywords:
            memories = self.memory_manager.search_memories(keywords)
        else:
            memories = self.memory_manager.load_recent_memories(limit)
        
        if not memories:
            return "没有找到相关记忆"
        
        # 格式化输出
        output = "📚 相关记忆:\n\n"
        for mem in memories:
            output += f"**{mem['topic']}** ({mem['timestamp'][:10]})\n"
            output += f"{mem['summary_preview']}...\n\n"
        
        return output

# 使用示例
if __name__ == "__main__":
    manager = ContextManager()
    
    # 模拟对话流程
    messages = [
        ("user", "我想配置 Fara-7B 在 Homelab 上"),
        ("assistant", "好的，需要以下步骤..."),
        ("user", "RX6800 需要特殊配置吗？"),
        ("assistant", "需要设置 HSA_OVERRIDE_GFX_VERSION..."),
        ("user", "对了，雅思作文怎么写？"),  # 话题转换！
    ]
    
    for role, content in messages:
        result = manager.process_message(role, content)
        
        if result["topic_changed"]:
            print("🔄 话题转换！")
            # 可以载入相关记忆
            relevant = manager.load_relevant_context("雅思")
            print(relevant)
```

---

## 🔧 系统集成

### 在 OpenClaw 中集成

创建 OpenClaw Skill：

```markdown
# Context Memory Skill

## 功能
- 自动检测话题转换
- 压缩保存对话上下文
- 载入相关历史记忆

## 触发条件
- 用户消息与最近对话相似度 < 0.6
- 用户明确说"换个话题"、"对了"等

## 保存路径
`/home/kyj/.openclaw/workspace/temp_memory/`

## 使用命令
- `/save-context` - 手动保存当前上下文
- `/load-memory [关键词]` - 加载相关记忆
- `/list-memories` - 列出所有临时记忆
```

---

## 📋 配置文件

### config.json

```json
{
  "context_manager": {
    "enabled": true,
    "topic_change_threshold": 0.6,
    "max_history_length": 100,
    "compress_after_messages": 10,
    "save_path": "/home/kyj/.openclaw/workspace/temp_memory/",
    "auto_save_on_topic_change": true,
    "load_relevant_on_new_topic": true
  }
}
```

---

## ✅ 使用示例

### 场景 1: 自动检测话题转换

```
用户：我想配置 Fara-7B
AI:  好的，需要以下步骤...
用户：RX6800 怎么配置？
AI:  需要设置 HSA_OVERRIDE_GFX_VERSION...
用户：对了，雅思作文怎么写？
🔄 检测到话题转换！
💾 自动保存"Fara-7B 配置"上下文
📚 载入"雅思写作"相关记忆
```

### 场景 2: 手动保存

```
用户：/save-context
✅ 当前上下文已保存：temp_memory/2026-03-03_16-30_DSS 分析.md
```

### 场景 3: 搜索历史

```
用户：/load-memory Fara
📚 找到 2 条相关记忆：
1. Fara-7B 配置 (2026-03-03)
   讨论了 Homelab 配置步骤...
2. Fara 测试 (2026-03-02)
   测试了网页搜索功能...
```

---

## 🐛 故障排查

### 话题检测不准确

```python
# 调整阈值
TOPIC_CHANGE_THRESHOLD = 0.5  # 更敏感
TOPIC_CHANGE_THRESHOLD = 0.7  # 更迟钝
```

### 压缩质量差

```python
# 改进总结提示
prompt = """请详细总结以下对话，包括：
1. 所有技术细节
2. 所有配置参数
3. 所有待办事项
...
"""
```

### 文件保存失败

```bash
# 检查目录权限
ls -la /home/kyj/.openclaw/workspace/temp_memory/
chmod 755 /home/kyj/.openclaw/workspace/temp_memory/
```

---

## 📊 性能优化

### 异步保存

```python
import asyncio

async def save_context_async():
    """异步保存，不阻塞对话"""
    await loop.run_in_executor(None, self._save_current_context)
```

### 批量压缩

```python
# 累积 10 条消息后压缩
if len(self.conversation_buffer) % 10 == 0:
    self._compress_and_save()
```

---

*机制设计完成时间：2026-03-03*  
*实施状态：待部署*
