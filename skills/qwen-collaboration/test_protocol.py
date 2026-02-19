#!/usr/bin/env python3
"""
Qwen协作协议测试
测试Kaguya和Qwen之间的高效通信
"""

import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace/skills/qwen-collaboration')

from protocol import QwenProtocol

def test_protocol():
    """测试协议功能"""
    print("🧪 Qwen协作协议测试")
    print("=" * 60)
    
    protocol = QwenProtocol()
    
    # 测试1: 金融分析协议
    print("\n1. 金融分析协议测试")
    print("-" * 40)
    
    finance_task = protocol.create_finance_task(
        symbol="AAPL",
        indicators=["RSI", "MACD", "MA20", "Bollinger", "Volume"],
        timeframe="1d",
        urgency="high"
    )
    
    print(f"任务ID: {finance_task['task_id']}")
    print(f"任务类型: {finance_task['type']}")
    print(f"格式化任务:\n{protocol.format_task_for_qwen(finance_task)}")
    
    # 模拟Qwen响应
    qwen_finance_response = """[F-结果] F-001
综合评分: 8.2/10
趋势判断: 温和偏多
关键信号: 价格>MA20, MACD金叉, RSI中性偏多, 成交量配合"""
    
    parsed_finance = protocol.parse_qwen_response(qwen_finance_response, finance_task['task_id'])
    print(f"\n解析响应: {parsed_finance}")
    
    # 测试2: 论文分析协议
    print("\n\n2. 论文分析协议测试")
    print("-" * 40)
    
    paper_task = protocol.create_paper_task(
        title="StockMixer: MLP-based Stock Market Prediction with Multi-scale Mixing",
        abstract="We propose StockMixer, a novel MLP-based architecture for stock market prediction...",
        focus_areas=["架构创新", "性能优势", "计算效率"]
    )
    
    print(f"任务ID: {paper_task['task_id']}")
    print(f"任务类型: {paper_task['type']}")
    print(f"格式化任务:\n{protocol.format_task_for_qwen(paper_task)}")
    
    # 模拟Qwen响应
    qwen_paper_response = """[P-摘要] P-001
创新点: MLP基础架构; 多尺度混合模块
技术细节: 使用MLP替代传统RNN/Transformer，通过多尺度模块捕捉不同时间模式
实用价值: 58.7%方向准确率，计算效率更高"""
    
    parsed_paper = protocol.parse_qwen_response(qwen_paper_response, paper_task['task_id'])
    print(f"\n解析响应: {parsed_paper}")
    
    # 测试3: 代码开发协议
    print("\n\n3. 代码开发协议测试")
    print("-" * 40)
    
    code_task = protocol.create_code_task(
        description="实现Walk Forward验证框架",
        inputs={"features": "DataFrame", "target": "Series", "train_days": "int"},
        outputs={"predictions": "array", "metrics": "dict"},
        constraints=["使用XGBoost", "支持滚动窗口", "包含评估指标"]
    )
    
    print(f"任务ID: {code_task['task_id']}")
    print(f"任务类型: {code_task['type']}")
    print(f"格式化任务:\n{protocol.format_task_for_qwen(code_task)}")
    
    # 模拟Qwen响应
    qwen_code_response = """[C-完成] C-001
代码文件: walk_forward_validator.py
测试结果: 通过所有测试用例，方向准确率55.2%
使用说明: 导入WalkForwardValidator类，调用rolling_validate方法"""
    
    parsed_code = protocol.parse_qwen_response(qwen_code_response, code_task['task_id'])
    print(f"\n解析响应: {parsed_code}")
    
    # 总结
    print("\n" + "=" * 60)
    print("✅ 协议测试完成")
    print(f"生成任务数: {protocol.task_counter}")
    print("协议功能正常，可以开始实际协作")

if __name__ == "__main__":
    test_protocol()