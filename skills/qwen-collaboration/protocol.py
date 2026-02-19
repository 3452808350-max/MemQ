#!/usr/bin/env python3
"""
Qwen协作协议实现
Kaguya和Qwen之间的高效通信协议
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

class QwenProtocol:
    """Qwen协作协议核心类"""
    
    def __init__(self):
        self.task_counter = {
            'F': 0,  # 金融分析
            'P': 0,  # 论文理解
            'C': 0,  # 代码开发
            'R': 0,  # 研究报告
            'A': 0   # 算法优化
        }
    
    def generate_task_id(self, task_type: str) -> str:
        """生成任务ID"""
        if task_type not in self.task_counter:
            task_type = 'F'  # 默认金融分析
        
        self.task_counter[task_type] += 1
        return f"{task_type}-{self.task_counter[task_type]:03d}"
    
    def create_finance_task(self, symbol: str, indicators: list, 
                           timeframe: str = "1d", urgency: str = "medium") -> Dict:
        """创建金融分析任务"""
        task_id = self.generate_task_id('F')
        
        return {
            "protocol": "Qwen-Collab-v1",
            "task_id": task_id,
            "type": "finance_analysis",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "symbol": symbol,
                "timeframe": timeframe,
                "indicators": indicators,
                "urgency": urgency
            },
            "expected_output": {
                "format": "analysis_report",
                "sections": ["summary", "signals", "risks", "recommendation"]
            }
        }
    
    def create_paper_task(self, title: str, abstract: str, 
                         focus_areas: list) -> Dict:
        """创建论文理解任务"""
        task_id = self.generate_task_id('P')
        
        return {
            "protocol": "Qwen-Collab-v1",
            "task_id": task_id,
            "type": "paper_analysis",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "title": title,
                "abstract": abstract,
                "focus_areas": focus_areas
            },
            "expected_output": {
                "format": "technical_summary",
                "sections": ["innovations", "comparison", "significance"]
            }
        }
    
    def create_code_task(self, description: str, inputs: Dict,
                        outputs: Dict, constraints: list) -> Dict:
        """创建代码开发任务"""
        task_id = self.generate_task_id('C')
        
        return {
            "protocol": "Qwen-Collab-v1",
            "task_id": task_id,
            "type": "code_development",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "description": description,
                "inputs": inputs,
                "outputs": outputs,
                "constraints": constraints
            },
            "expected_output": {
                "format": "code_file",
                "requirements": ["runnable", "commented", "tested"]
            }
        }
    
    def format_task_for_qwen(self, task: Dict) -> str:
        """将任务格式化为Qwen可理解的文本"""
        task_type = task["type"]
        
        if task_type == "finance_analysis":
            data = task["data"]
            return f"""[F-分析] {data['symbol']} {data['timeframe']}
指标: {', '.join(data['indicators'])}
紧急度: {data['urgency']}
任务ID: {task['task_id']}"""
        
        elif task_type == "paper_analysis":
            data = task["data"]
            return f"""[P-精读] {data['title']}
摘要: {data['abstract'][:200]}...
重点: {', '.join(data['focus_areas'])}
任务ID: {task['task_id']}"""
        
        elif task_type == "code_development":
            data = task["data"]
            return f"""[C-开发] {data['description']}
输入: {json.dumps(data['inputs'], ensure_ascii=False)}
输出: {json.dumps(data['outputs'], ensure_ascii=False)}
约束: {', '.join(data['constraints'])}
任务ID: {task['task_id']}"""
        
        else:
            return json.dumps(task, ensure_ascii=False, indent=2)
    
    def parse_qwen_response(self, response: str, task_id: str) -> Dict:
        """解析Qwen的响应"""
        lines = response.strip().split('\n')
        
        # 尝试提取协议标记
        if response.startswith('[F-结果]'):
            return self._parse_finance_response(response, task_id)
        elif response.startswith('[P-摘要]'):
            return self._parse_paper_response(response, task_id)
        elif response.startswith('[C-完成]'):
            return self._parse_code_response(response, task_id)
        else:
            # 通用解析
            return {
                "task_id": task_id,
                "raw_response": response,
                "parsed_at": datetime.now().isoformat()
            }
    
    def _parse_finance_response(self, response: str, task_id: str) -> Dict:
        """解析金融分析响应"""
        lines = response.split('\n')
        result = {
            "task_id": task_id,
            "type": "finance_result",
            "parsed_at": datetime.now().isoformat()
        }
        
        for line in lines:
            if '综合评分:' in line:
                result['score'] = line.split(':', 1)[1].strip()
            elif '趋势判断:' in line:
                result['trend'] = line.split(':', 1)[1].strip()
            elif '关键信号:' in line:
                result['signals'] = line.split(':', 1)[1].strip().split(', ')
        
        return result
    
    def _parse_paper_response(self, response: str, task_id: str) -> Dict:
        """解析论文分析响应"""
        lines = response.split('\n')
        result = {
            "task_id": task_id,
            "type": "paper_result",
            "parsed_at": datetime.now().isoformat()
        }
        
        for line in lines:
            if '创新点:' in line:
                result['innovations'] = line.split(':', 1)[1].strip().split('; ')
            elif '技术细节:' in line:
                result['technical_details'] = line.split(':', 1)[1].strip()
            elif '实用价值:' in line:
                result['practical_value'] = line.split(':', 1)[1].strip()
        
        return result
    
    def _parse_code_response(self, response: str, task_id: str) -> Dict:
        """解析代码开发响应"""
        lines = response.split('\n')
        result = {
            "task_id": task_id,
            "type": "code_result",
            "parsed_at": datetime.now().isoformat()
        }
        
        for line in lines:
            if '代码文件:' in line:
                result['code_file'] = line.split(':', 1)[1].strip()
            elif '测试结果:' in line:
                result['test_results'] = line.split(':', 1)[1].strip()
            elif '使用说明:' in line:
                result['usage'] = line.split(':', 1)[1].strip()
        
        return result


# 使用示例
if __name__ == "__main__":
    protocol = QwenProtocol()
    
    # 示例1: 金融分析任务
    finance_task = protocol.create_finance_task(
        symbol="AAPL",
        indicators=["RSI", "MACD", "MA20", "Volume"],
        timeframe="1d",
        urgency="high"
    )
    
    print("金融分析任务:")
    print(json.dumps(finance_task, indent=2, ensure_ascii=False))
    print("\n格式化后:")
    print(protocol.format_task_for_qwen(finance_task))
    
    print("\n" + "="*60 + "\n")
    
    # 示例2: 论文分析任务
    paper_task = protocol.create_paper_task(
        title="StockMixer: MLP-based Stock Market Prediction",
        abstract="We propose StockMixer, a novel MLP-based architecture...",
        focus_areas=["架构创新", "性能对比", "实用价值"]
    )
    
    print("论文分析任务:")
    print(json.dumps(paper_task, indent=2, ensure_ascii=False))
    print("\n格式化后:")
    print(protocol.format_task_for_qwen(paper_task))
    
    print("\n" + "="*60 + "\n")
    
    # 示例3: 模拟Qwen响应
    qwen_response = """[F-结果] F-001
综合评分: 8.5/10
趋势判断: 温和多头
关键信号: 价格>MA20, MACD金叉, 成交量放大"""
    
    parsed = protocol.parse_qwen_response(qwen_response, "F-001")
    print("解析Qwen响应:")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))