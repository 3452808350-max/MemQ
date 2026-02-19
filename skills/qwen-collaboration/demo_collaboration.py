#!/usr/bin/env python3
"""
Kaguya-Qwen协作演示
展示如何使用协议进行高效协作
"""

import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace/skills/qwen-collaboration')

from protocol import QwenProtocol

class KaguyaQwenCollaborator:
    """Kaguya和Qwen的协作管理器"""
    
    def __init__(self):
        self.protocol = QwenProtocol()
        self.task_history = []
    
    def send_to_qwen(self, task_type: str, **kwargs):
        """发送任务给Qwen"""
        if task_type == "finance":
            task = self.protocol.create_finance_task(**kwargs)
        elif task_type == "paper":
            task = self.protocol.create_paper_task(**kwargs)
        elif task_type == "code":
            task = self.protocol.create_code_task(**kwargs)
        else:
            raise ValueError(f"未知任务类型: {task_type}")
        
        formatted_task = self.protocol.format_task_for_qwen(task)
        self.task_history.append({
            "task": task,
            "sent_at": task["timestamp"],
            "status": "sent"
        })
        
        return formatted_task, task["task_id"]
    
    def receive_from_qwen(self, response: str, task_id: str):
        """接收Qwen的响应"""
        parsed = self.protocol.parse_qwen_response(response, task_id)
        
        # 更新任务历史
        for task_record in self.task_history:
            if task_record["task"]["task_id"] == task_id:
                task_record["response"] = parsed
                task_record["status"] = "completed"
                task_record["completed_at"] = parsed["parsed_at"]
                break
        
        return parsed
    
    def generate_report(self):
        """生成协作报告"""
        report = {
            "total_tasks": len(self.task_history),
            "completed_tasks": len([t for t in self.task_history if t.get("status") == "completed"]),
            "pending_tasks": len([t for t in self.task_history if t.get("status") == "sent"]),
            "task_breakdown": {}
        }
        
        # 统计任务类型
        for task_record in self.task_history:
            task_type = task_record["task"]["type"]
            if task_type not in report["task_breakdown"]:
                report["task_breakdown"][task_type] = 0
            report["task_breakdown"][task_type] += 1
        
        return report


def demo_real_world_scenario():
    """演示真实世界协作场景"""
    print("🚀 Kaguya-Qwen 真实协作演示")
    print("=" * 60)
    
    collaborator = KaguyaQwenCollaborator()
    
    # 场景1: DSS系统改进任务
    print("\n📈 场景1: DSS系统改进")
    print("-" * 40)
    
    # Kaguya发送金融分析任务
    task1, task1_id = collaborator.send_to_qwen(
        task_type="finance",
        symbol="AAPL,GOOGL,MSFT",
        indicators=["RSI", "MACD", "MA20", "Volume", "Bollinger"],
        timeframe="1d",
        urgency="high"
    )
    
    print(f"Kaguya → Qwen:")
    print(task1)
    
    # 模拟Qwen响应
    qwen_response1 = """[F-结果] F-001
综合评分: 8.5/10
趋势判断: 分化明显
关键信号: 
- AAPL: 温和多头，RSI 62.5，建议持有
- GOOGL: 中性偏空，面临阻力，建议观望
- MSFT: 强势多头，突破关键位，建议加仓"""
    
    result1 = collaborator.receive_from_qwen(qwen_response1, task1_id)
    print(f"\nQwen → Kaguya:")
    print(f"任务完成: {task1_id}")
    print(f"趋势判断: {result1.get('trend', 'N/A')}")
    print(f"关键信号: {result1.get('signals', [])}")
    
    # 场景2: 论文学习任务
    print("\n\n📚 场景2: 论文精读学习")
    print("-" * 40)
    
    task2, task2_id = collaborator.send_to_qwen(
        task_type="paper",
        title="MASTER: Multi-Agent Spatio-Temporal Ensemble for Stock Prediction",
        abstract="We propose MASTER, a multi-agent framework that combines spatial and temporal information...",
        focus_areas=["多智能体架构", "时空特征融合", "实际应用价值"]
    )
    
    print(f"Kaguya → Qwen:")
    print(task2)
    
    # 模拟Qwen响应
    qwen_response2 = """[P-摘要] P-001
创新点: 多智能体协同; 时空特征融合; 集成学习框架
技术细节: 使用多个智能体分别处理不同时间尺度和市场维度数据，通过注意力机制融合
实用价值: 在A股市场达到59.2%方向准确率，适合高频交易场景"""
    
    result2 = collaborator.receive_from_qwen(qwen_response2, task2_id)
    print(f"\nQwen → Kaguya:")
    print(f"任务完成: {task2_id}")
    print(f"创新点: {result2.get('innovations', [])}")
    print(f"实用价值: {result2.get('practical_value', 'N/A')}")
    
    # 场景3: 代码优化任务
    print("\n\n💻 场景3: 代码优化实现")
    print("-" * 40)
    
    task3, task3_id = collaborator.send_to_qwen(
        task_type="code",
        description="优化DSS v2.0的Walk Forward验证性能",
        inputs={
            "data": "DataFrame with features",
            "model": "XGBoost/RandomForest config",
            "window_params": "train/val/test days"
        },
        outputs={
            "predictions": "numpy array",
            "metrics": "dict with accuracy, sharpe, etc",
            "execution_time": "seconds"
        },
        constraints=["支持并行计算", "内存优化", "结果可复现", "添加性能监控"]
    )
    
    print(f"Kaguya → Qwen:")
    print(task3)
    
    # 模拟Qwen响应
    qwen_response3 = """[C-完成] C-001
代码文件: dss_v2_optimized.py
测试结果: 性能提升42%，内存使用减少35%，准确率保持55.1%
使用说明: 
1. 使用ParallelWalkForward类替代原版
2. 支持多进程并行验证
3. 添加了内存监控和性能日志
4. 结果完全可复现"""
    
    result3 = collaborator.receive_from_qwen(qwen_response3, task3_id)
    print(f"\nQwen → Kaguya:")
    print(f"任务完成: {task3_id}")
    print(f"代码文件: {result3.get('code_file', 'N/A')}")
    print(f"测试结果: {result3.get('test_results', 'N/A')}")
    
    # 生成协作报告
    print("\n" + "=" * 60)
    print("📊 协作报告")
    print("=" * 60)
    
    report = collaborator.generate_report()
    print(f"总任务数: {report['total_tasks']}")
    print(f"已完成: {report['completed_tasks']}")
    print(f"进行中: {report['pending_tasks']}")
    print(f"任务分布: {report['task_breakdown']}")
    
    print("\n✅ 演示完成!")
    print("协议使Kaguya和Qwen的协作效率大幅提升")


if __name__ == "__main__":
    demo_real_world_scenario()