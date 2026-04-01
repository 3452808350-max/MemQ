#!/usr/bin/env python3
"""
Kimi + MemQ 持久化记忆Agent

结合Kimi CLI和MemQ实现带记忆的智能Agent
- 使用Kimi额度进行推理
- 使用MemQ进行记忆持久化
- 可被OpenClaw subagent调用

使用方式:
    from kimi_memq_agent import KimiMemQAgent
    
    agent = KimiMemQAgent()
    
    # 带记忆的对话
    response = agent.chat("分析茅台的技术面")
    
    # 记忆会自动保存和检索
"""
import sys
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

# MemQ路径
sys.path.insert(0, '/home/kyj/.openclaw/workspace/memq')

from kimi_runner import run_kimi_task


@dataclass
class MemoryContext:
    """记忆上下文"""
    relevant_memories: List[Dict] = field(default_factory=list)
    recent_conversations: List[Dict] = field(default_factory=list)
    user_preferences: Dict = field(default_factory=dict)
    dss_knowledge: List[Dict] = field(default_factory=list)


class KimiMemQAgent:
    """
    Kimi + MemQ 持久化记忆Agent
    
    特点:
    1. 使用Kimi CLI额度（不是百炼API）
    2. 自动检索相关记忆注入提示词
    3. 自动保存重要信息到MemQ
    4. 读取MEMORY.md等文件作为长期记忆
    """
    
    def __init__(
        self,
        workspace: str = "/home/kyj/.openclaw/workspace",
        memq_dir: str = "/home/kyj/.openclaw/workspace/memq",
        agent_file: str = "/home/kyj/.openclaw/workspace/kimi-dss-agent/dss-agent.yaml"
    ):
        self.workspace = workspace
        self.memq_dir = memq_dir
        self.agent_file = agent_file
        
        # 记忆文件路径
        self.memory_md = os.path.join(workspace, "MEMORY.md")
        self.user_md = os.path.join(workspace, "USER.md")
        self.soul_md = os.path.join(workspace, "SOUL.md")
        
        # 初始化MemQ（如果可用）
        self.memq = None
        self._init_memq()
        
        # 对话历史缓存
        self._conversation_cache: List[Dict] = []
        
    def _init_memq(self):
        """初始化MemQ"""
        try:
            from plugins.memq_pro import MemQPro
            self.memq = MemQPro(data_dir=self.memq_dir)
            print("✅ MemQ已加载")
        except Exception as e:
            print(f"⚠️ MemQ加载失败: {e}，将使用文件记忆")
    
    def load_memory_md(self) -> str:
        """加载MEMORY.md长期记忆"""
        if os.path.exists(self.memory_md):
            with open(self.memory_md, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def load_user_context(self) -> str:
        """加载用户上下文"""
        context_parts = []
        
        if os.path.exists(self.user_md):
            with open(self.user_md, 'r', encoding='utf-8') as f:
                context_parts.append(f"用户信息:\n{f.read()}")
        
        if os.path.exists(self.soul_md):
            with open(self.soul_md, 'r', encoding='utf-8') as f:
                context_parts.append(f"助手人格:\n{f.read()}")
        
        return "\n\n".join(context_parts)
    
    def search_memories(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索相关记忆"""
        memories = []
        
        # 1. 从MemQ搜索
        if self.memq:
            try:
                results = self.memq.search(query, top_k=top_k)
                memories.extend(results)
            except Exception as e:
                print(f"MemQ搜索失败: {e}")
        
        # 2. 从MEMORY.md关键词匹配
        memory_content = self.load_memory_md()
        if memory_content and query.lower() in memory_content.lower():
            # 简单的段落匹配
            paragraphs = memory_content.split('\n\n')
            for p in paragraphs:
                if query.lower() in p.lower():
                    memories.append({
                        'content': p[:500],
                        'source': 'MEMORY.md',
                        'score': 0.8
                    })
        
        return memories[:top_k]
    
    def save_memory(self, content: str, category: str = "conversation"):
        """保存记忆"""
        timestamp = datetime.now().isoformat()
        
        # 保存到MemQ
        if self.memq:
            try:
                memory_id = f"{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.memq.add(memory_id, content, metadata={
                    'category': category,
                    'timestamp': timestamp
                })
            except Exception as e:
                print(f"MemQ保存失败: {e}")
        
        # 同时保存到对话缓存
        self._conversation_cache.append({
            'content': content,
            'category': category,
            'timestamp': timestamp
        })
    
    def build_context_prompt(self, user_input: str) -> str:
        """构建带记忆上下文的提示词"""
        context_parts = []
        
        # 1. 加载长期记忆
        long_term_memory = self.load_memory_md()
        if long_term_memory:
            context_parts.append(f"""## 长期记忆 (MEMORY.md)

{long_term_memory[:2000]}
""")
        
        # 2. 加载用户上下文
        user_context = self.load_user_context()
        if user_context:
            context_parts.append(f"""## 上下文

{user_context}
""")
        
        # 3. 搜索相关记忆
        relevant_memories = self.search_memories(user_input, top_k=3)
        if relevant_memories:
            memory_text = "\n".join([
                f"- {m.get('content', m.get('text', ''))[:200]}"
                for m in relevant_memories
            ])
            context_parts.append(f"""## 相关记忆

{memory_text}
""")
        
        # 4. 最近对话
        if self._conversation_cache:
            recent = self._conversation_cache[-3:]
            recent_text = "\n".join([
                f"[{c['timestamp']}] {c['content'][:100]}"
                for c in recent
            ])
            context_parts.append(f"""## 最近对话

{recent_text}
""")
        
        # 5. 构建完整提示词
        context = "\n\n".join(context_parts)
        
        full_prompt = f"""你是一个有持久记忆的AI助手。

{context}

---

用户问题: {user_input}

请基于以上记忆和上下文回答问题。如果是DSS选股相关的分析，使用已定义的模块进行。
"""
        
        return full_prompt
    
    def chat(
        self,
        user_input: str,
        timeout: int = 120,
        save_memory: bool = True
    ) -> Dict[str, Any]:
        """
        带记忆的对话
        
        Args:
            user_input: 用户输入
            timeout: 超时时间
            save_memory: 是否保存到记忆
            
        Returns:
            {
                'success': bool,
                'response': str,
                'relevant_memories': list,
                'token_usage': dict
            }
        """
        # 构建带记忆的提示词
        prompt = self.build_context_prompt(user_input)
        
        # 调用Kimi
        result = run_kimi_task(prompt, timeout=timeout)
        
        if result['success']:
            # 保存对话到记忆
            if save_memory:
                self.save_memory(
                    f"用户: {user_input}\n助手: {result['output'][:500]}",
                    category="conversation"
                )
        
        return {
            'success': result['success'],
            'response': result['output'],
            'relevant_memories': self.search_memories(user_input, top_k=3),
            'token_usage': result['token_usage'],
            'error': result.get('error')
        }
    
    def analyze_stock(self, symbol: str, timeout: int = 180) -> Dict[str, Any]:
        """
        分析股票（使用DSS模块）
        
        Args:
            symbol: 股票代码 (如 sh.600519)
            timeout: 超时时间
            
        Returns:
            分析结果
        """
        prompt = f"""请分析股票 {symbol}：

1. 使用DSS模块获取数据:
```python
import sys
sys.path.insert(0, '{self.workspace}')
from dss_v4 import ImprovedStockPicker

picker = ImprovedStockPicker(use_denoise=True, use_news_sentiment=True)
result = picker.analyze_stock('{symbol}')
print(result)
```

2. 解释技术评分、情绪评分的含义
3. 给出投资建议和风险提示
"""
        
        return self.chat(prompt, timeout=timeout)
    
    def learn(self, content: str, category: str = "knowledge"):
        """
        学习新知识并保存到记忆
        
        Args:
            content: 知识内容
            category: 知识类别
        """
        self.save_memory(content, category=category)
        return f"已学习并保存: {content[:100]}..."
    
    def recall(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        回忆相关记忆
        
        Args:
            query: 查询
            top_k: 返回数量
            
        Returns:
            相关记忆列表
        """
        return self.search_memories(query, top_k=top_k)


# OpenClaw subagent接口
def kimi_memq_subagent(
    task: str,
    timeout: int = 120,
    save_memory: bool = True
) -> Dict[str, Any]:
    """
    OpenClaw subagent接口
    
    用法:
        from kimi_memq_agent import kimi_memq_subagent
        result = kimi_memq_subagent("分析茅台技术面")
    """
    agent = KimiMemQAgent()
    return agent.chat(task, timeout=timeout, save_memory=save_memory)


def kimi_analyze_stock(symbol: str) -> Dict[str, Any]:
    """
    股票分析快捷接口
    """
    agent = KimiMemQAgent()
    return agent.analyze_stock(symbol)


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kimi + MemQ 持久化记忆Agent")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--analyze", "-a", help="分析股票 (代码)")
    parser.add_argument("--learn", "-l", help="学习新知识")
    parser.add_argument("--recall", "-r", help="回忆记忆")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    
    args = parser.parse_args()
    
    agent = KimiMemQAgent()
    
    if args.analyze:
        print(f"📊 分析股票: {args.analyze}")
        result = agent.analyze_stock(args.analyze)
        print(result['response'])
    
    elif args.learn:
        print(agent.learn(args.learn))
    
    elif args.recall:
        memories = agent.recall(args.recall)
        for m in memories:
            print(f"- {m.get('content', m.get('text', ''))[:100]}")
    
    elif args.interactive:
        print("Kimi + MemQ 交互模式 (输入 'quit' 退出)")
        print("-" * 50)
        while True:
            try:
                user_input = input("\n你: ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                result = agent.chat(user_input)
                print(f"\nKimi: {result['response']}")
                
            except KeyboardInterrupt:
                break
        
        print("\n再见!")
    
    elif args.task:
        result = agent.chat(args.task)
        print(result['response'])
    
    else:
        parser.print_help()