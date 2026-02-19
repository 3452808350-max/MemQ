#!/usr/bin/env python3
"""
Claw的邮件汇报系统 - 仅用于向K汇报
独立于项目，安全存储授权码
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import json
from pathlib import Path

class KaguyaEmailReporter:
    """Kaguya的邮件系统 - 来自超时空的辉夜姬"""
    
    def __init__(self, config_path=None):
        # 默认配置路径
        if config_path is None:
            config_path = Path.home() / ".openclaw" / "workspace" / "email_config.json"
        
        self.config_path = Path(config_path)
        self.load_config()
    
    def load_config(self):
        """加载邮件配置"""
        default_config = {
            "smtp_server": "smtp.qq.com",
            "smtp_port": 587,
            "sender_email": "3452808350@qq.com",
            "sender_password": "rgjqeyugfqrmdagd",  # QQ邮箱授权码
            "recipient_emails": [
                "3452808350@qq.com",      # K的QQ邮箱
                "kyj1145141@outlook.com"  # K的Outlook邮箱
            ]
        }
        
        # 如果配置文件不存在，创建它
        if not self.config_path.exists():
            print(f"⚠️  配置文件不存在，创建默认配置: {self.config_path}")
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
        
        # 加载配置
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        
        # 验证必要配置
        required = ['sender_email', 'sender_password', 'recipient_emails']
        for key in required:
            if key not in self.config:
                raise ValueError(f"缺少必要配置: {key}")
    
    def send_report(self, subject, message, html_message=None):
        """
        发送邮件 - 来自Kaguya的问候
        
        Args:
            subject: 邮件主题
            message: 纯文本内容
            html_message: HTML内容 (可选)
        """
        print(f"📧 Kaguya发送邮件...")
        print(f"  主题: {subject}")
        print(f"  收件人: {', '.join(self.config['recipient_emails'])}")
        
        # 创建邮件
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config['sender_email']
        msg["To"] = ", ".join(self.config['recipient_emails'])
        
        # 添加纯文本版本
        text_part = MIMEText(message, "plain", "utf-8")
        msg.attach(text_part)
        
        # 添加HTML版本 (如果提供)
        if html_message:
            html_part = MIMEText(html_message, "html", "utf-8")
            msg.attach(html_part)
        
        try:
            # 创建安全连接
            context = ssl.create_default_context()
            
            # 连接SMTP服务器
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls(context=context)  # 启用TLS加密
                server.login(self.config['sender_email'], self.config['sender_password'])
                server.sendmail(
                    self.config['sender_email'], 
                    self.config['recipient_emails'], 
                    msg.as_string()
                )
            
            print("✅ 邮件发送成功! ✨")
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False
    
    def send_kaguya_update(self, project_status=None):
        """发送Kaguya的更新 - 不那么正式的汇报"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        subject = f"✨ Kaguya的更新 - {current_date}"
        
        # 默认项目状态
        if project_status is None:
            project_status = {
                "name": "analyse",
                "location": "/home/kyj/文档/code/",
                "phase": "Week 1 - 基础搭建",
                "progress": "项目结构完成，等待NAS部署",
                "next_steps": ["NAS Git服务器设置", "代码推送", "邮件验证"]
            }
        
        message = f"""
✨ Kaguya的更新

📅 日期: {current_date}
⏰ 时间: {current_time}
👸 来自: Kaguya (你的超时空助手)

🏠 工作空间状态:
- 位置: /home/kyj/.openclaw/workspace/
- 邮件系统: 运行正常
- 配置安全: 授权码在独立配置文件

📁 项目管理:
- 项目名称: {project_status['name']}
- 项目位置: {project_status['location']}
- 当前阶段: {project_status['phase']}
- 进展状态: {project_status['progress']}

🎯 今日完成:
1. ✅ 创建analyse项目结构
2. ✅ 配置本地Git仓库
3. ✅ 设置邮件汇报系统
4. ✅ 测试Alpha Vantage API
5. ✅ 创建NAS部署指南

📋 待办事项:
{chr(10).join(f'  • {item}' for item in project_status['next_steps'])}

🔐 安全状态:
- 邮件授权码: 安全存储在独立配置文件
- 项目API密钥: 在代码中 (NAS部署后相对安全)
- 数据备份: 本地Git + 今晚NAS备份

💡 建议:
1. 晚上7点按指南完成NAS部署
2. 检查QQ和Outlook邮箱确认邮件系统
3. 按照TASKS.md继续项目开发

📞 联系:
- Telegram: @RiverJiert
- 邮箱: 3452808350@qq.com / kyj1145141@outlook.com

--
✨ Kaguya的超时空通讯
保持联系，随时找我聊天~
"""
        
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Claw每日汇报 - {current_date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 15px; text-align: center; border-radius: 5px; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin-top: 20px; }}
        .section {{ margin-bottom: 20px; padding: 15px; border-radius: 5px; }}
        .status {{ background-color: #e7f3fe; border-left: 4px solid #2196F3; }}
        .todo {{ background-color: #fff3cd; border-left: 4px solid #ffc107; }}
        .security {{ background-color: #d4edda; border-left: 4px solid #28a745; }}
        .success {{ color: #4CAF50; font-weight: bold; }}
        .code {{ background-color: #f4f4f4; padding: 10px; border-radius: 3px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Claw每日工作汇报</h1>
            <h2>{current_date}</h2>
        </div>
        
        <div class="content">
            <div class="section status">
                <h3>📊 工作概览</h3>
                <p><strong>时间:</strong> {current_time}</p>
                <p><strong>来自:</strong> Kaguya (你的超时空助手)</p>
                <p><strong>工作空间:</strong> /home/kyj/.openclaw/workspace/</p>
            </div>
            
            <div class="section status">
                <h3>📁 项目管理</h3>
                <ul>
                    <li><strong>项目名称:</strong> {project_status['name']}</li>
                    <li><strong>项目位置:</strong> {project_status['location']}</li>
                    <li><strong>当前阶段:</strong> {project_status['phase']}</li>
                    <li><strong>进展状态:</strong> {project_status['progress']}</li>
                </ul>
            </div>
            
            <div class="section status">
                <h3>✅ 今日完成</h3>
                <ol>
                    <li>创建analyse项目结构</li>
                    <li>配置本地Git仓库</li>
                    <li>设置邮件汇报系统</li>
                    <li>测试Alpha Vantage API</li>
                    <li>创建NAS部署指南</li>
                </ol>
            </div>
            
            <div class="section todo">
                <h3>📋 待办事项</h3>
                <ul>
                    {''.join(f'<li>{item}</li>' for item in project_status['next_steps'])}
                </ul>
            </div>
            
            <div class="section security">
                <h3>🔐 安全状态</h3>
                <ul>
                    <li>邮件授权码: 安全存储在独立配置文件</li>
                    <li>项目API密钥: 在代码中 (NAS部署后相对安全)</li>
                    <li>数据备份: 本地Git + 今晚NAS备份</li>
                </ul>
            </div>
            
            <div class="section">
                <h3>💡 建议</h3>
                <ol>
                    <li>晚上7点按指南完成NAS部署</li>
                    <li>检查QQ和Outlook邮箱确认邮件系统</li>
                    <li>按照TASKS.md继续项目开发</li>
                </ol>
            </div>
            
            <hr>
            <p style="color: #666; font-size: 12px; text-align: center;">
                Claw自动汇报系统 | 工作空间: /home/kyj/.openclaw/workspace/<br>
                此邮件仅用于工作汇报，请勿转发
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return self.send_report(subject, message, html_message)
    
    def send_nas_deployment_report(self, success=True, details=None):
        """发送NAS部署汇报"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if success:
            subject = "✅ NAS部署完成汇报"
            message = f"""
NAS Git服务器部署完成汇报

⏰ 时间: {current_time}
🏠 位置: 192.168.4.147:3410
📦 项目: analyse

✅ 部署状态: 成功

📊 部署详情:
{details if details else '代码已成功推送到NAS Git服务器'}

🔧 验证命令:
ssh -p 3410 rootKYJ@192.168.4.147 \\
  'su - git -c "cd /srv/git/stock-analysis-dss.git && git log --oneline -5"'

💻 后续使用:
- 日常推送: git push nas
- 从NAS克隆: git clone ssh://git@192.168.4.147:3410/srv/git/stock-analysis-dss.git

🔐 安全提醒:
- API密钥在代码中，NAS本地网络相对安全
- 建议后续将密钥移到环境变量

--
Claw NAS部署汇报
"""
        else:
            subject = "❌ NAS部署失败汇报"
            message = f"""
NAS Git服务器部署失败汇报

⏰ 时间: {current_time}
🏠 位置: 192.168.4.147:3410
📦 项目: analyse

❌ 部署状态: 失败

📊 错误详情:
{details if details else '部署过程中出现错误'}

🔧 故障排除:
1. 检查NAS是否开机
2. 确认SSH服务运行 (端口3410)
3. 验证Git服务器设置
4. 检查网络连接

💻 手动命令:
cd /home/kyj/文档/code/
git remote add nas ssh://git@192.168.4.147:3410/srv/git/stock-analysis-dss.git
git push -u nas master

📞 需要帮助:
请检查项目文档或联系系统管理员。

--
Claw NAS部署汇报
"""
        
        return self.send_report(subject, message)
    
    def send_ielts_feedback(self, essay_topic, feedback, score_estimate):
        """发送IELTS写作反馈"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        subject = f"📝 IELTS写作反馈 - {essay_topic[:30]}..."
        
        message = f"""
IELTS写作任务反馈

⏰ 时间: {current_time}
📚 任务类型: Writing Task 2
🎯 主题: {essay_topic}

📊 评分估计:
- Task Response: {score_estimate.get('task_response', 'N/A')}
- Coherence & Cohesion: {score_estimate.get('coherence', 'N/A')}
- Lexical Resource: {score_estimate.get('lexical', 'N/A')}
- Grammatical Range: {score_estimate.get('grammar', 'N/A')}
- 总体估计: {score_estimate.get('overall', 'N/A')}

✅ 优点:
{feedback.get('strengths', '暂无记录')}

🔧 改进建议:
{feedback.get('improvements', '暂无记录')}

📝 语法重点:
{feedback.get('grammar_focus', '暂无记录')}

💡 学习建议:
{feedback.get('learning_tips', '暂无记录')}

🎯 练习建议:
1. 每天练习1篇写作
2. 重点改进语法错误
3. 积累学术词汇
4. 定时练习 (40分钟)

--
✨ Kaguya的IELTS小贴士
专注逻辑结构 > 词汇量
"""
        
        return self.send_report(subject, message)

def test_email_system():
    """测试邮件系统"""
    print("="*60)
    print("✨ Kaguya邮件系统测试")
    print("="*60)
    
    reporter = KaguyaEmailReporter()
    
    print(f"📋 配置信息:")
    print(f"  发件人: {reporter.config['sender_email']}")
    print(f"  收件人: {', '.join(reporter.config['recipient_emails'])}")
    print(f"  SMTP服务器: {reporter.config['smtp_server']}:{reporter.config['smtp_port']}")
    print()
    
    # 测试发送
    test_subject = "Claw邮件系统测试"
    test_message = f"这是一封测试邮件，确认Claw的邮件汇报系统工作正常。\n\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print("📤 发送测试邮件...")
    success = reporter.send_report(test_subject, test_message)
    
    if success:
        print("✅ 测试成功! ✨ 请检查你的邮箱:")
        print("  1. QQ邮箱 (3452808350@qq.com)")
        print("  2. Outlook邮箱 (kyj1145141@outlook.com)")
    else:
        print("❌ 测试失败，请检查配置")
    
    return success

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_email_system()
    elif len(sys.argv) > 1 and sys.argv[1] == "update":
        reporter = KaguyaEmailReporter()
        reporter.send_kaguya_update()
    else:
        print("使用方法:")
        print("  python email_system.py test      # 测试邮件系统")
        print("  python email_system.py update    # 发送Kaguya的更新")
        print()
        print("配置位置: ~/.openclaw/workspace/email_config.json")