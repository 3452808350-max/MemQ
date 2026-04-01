#!/usr/bin/env python3
"""发送 DSS 反向验证报告"""

import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from email_system import KaguyaEmailReporter

# 读取验证结果
validation_file = Path("/home/kyj/.openclaw/workspace/data/predictions/validation_2026-02-26.json")
with open(validation_file, "r", encoding="utf-8") as f:
    validation = json.load(f)

# 生成报告
reporter = KaguyaEmailReporter()

subject = f"📊 DSS 反向验证报告 - 预测日期 {validation['prediction_date']}"

# 纯文本版本
text_report = f"""
DSS 反向验证报告
═══════════════════════════════════════════════════════════

预测日期：{validation['prediction_date']}
验证日期：{validation['validation_date']}

📈 验证结果
───────────────────────────────────────────────────────────
• 预测上涨股票数：{validation['predicted_count']} 只
• 实际上涨（正确）：{validation['correct']} 只
• 实际下跌（错误）：{validation['wrong']} 只
• 准确率：{validation['accuracy']:.1f}%

📋 详细明细
───────────────────────────────────────────────────────────
"""

# 按涨跌幅排序
details_sorted = sorted(validation['details'], key=lambda x: x['change_pct'], reverse=True)
for d in details_sorted:
    status = "✅" if d['correct'] else "❌"
    text_report += f"{status} {d['name']:10s} ({d['code']:12s})  预测:{d['pred_score']:+3d}  实际:{d['change_pct']:+.2f}%\n"

text_report += f"""
═══════════════════════════════════════════════════════════
报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

# HTML 版本
html_report = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        .summary {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
        .metric-label {{ font-size: 14px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        .correct {{ color: #27ae60; }}
        .wrong {{ color: #e74c3c; }}
        .footer {{ margin-top: 30px; color: #7f8c8d; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>📊 DSS 反向验证报告</h1>
    
    <div class="summary">
        <h2>验证概览</h2>
        <p><strong>预测日期:</strong> {validation['prediction_date']} | <strong>验证日期:</strong> {validation['validation_date']}</p>
        
        <div class="metric">
            <div class="metric-value">{validation['predicted_count']}</div>
            <div class="metric-label">预测股票数</div>
        </div>
        <div class="metric">
            <div class="metric-value" style="color: #27ae60;">{validation['correct']}</div>
            <div class="metric-label">正确 ✅</div>
        </div>
        <div class="metric">
            <div class="metric-value" style="color: #e74c3c;">{validation['wrong']}</div>
            <div class="metric-label">错误 ❌</div>
        </div>
        <div class="metric">
            <div class="metric-value">{validation['accuracy']:.1f}%</div>
            <div class="metric-label">准确率</div>
        </div>
    </div>
    
    <h2>📋 详细明细</h2>
    <table>
        <tr>
            <th>状态</th>
            <th>股票名称</th>
            <th>代码</th>
            <th>预测分数</th>
            <th>实际涨跌幅</th>
        </tr>
"""

for d in details_sorted:
    status_class = "correct" if d['correct'] else "wrong"
    status_icon = "✅" if d['correct'] else "❌"
    html_report += f"""
        <tr>
            <td class="{status_class}">{status_icon}</td>
            <td>{d['name']}</td>
            <td>{d['code']}</td>
            <td>{d['pred_score']:+d}</td>
            <td class="{status_class}">{d['change_pct']:+.2f}%</td>
        </tr>
"""

html_report += f"""
    </table>
    
    <div class="footer">
        <p>报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>DSS 选股系统 v2.0 | Kaguya AI Assistant</p>
    </div>
</body>
</html>
"""

# 发送邮件
print("发送 DSS 反向验证报告...")
reporter.send_report(subject, text_report, html_report)
print("\n报告发送完成!")
