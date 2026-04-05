"""
邮件发送模块 - 用于发送 DSS 验证报告

需要配置环境变量或 .env 文件:
    SMTP_HOST: SMTP服务器地址 (默认: smtp.qq.com)
    SMTP_PORT: SMTP端口 (默认: 587)
    SMTP_USER: 邮箱地址
    SMTP_PASS: 邮箱密码或授权码
    EMAIL_TO: 收件人地址 (多个用逗号分隔)
"""
import os
import smtplib
from pathlib import Path

# 自动加载 .env 文件
def load_env_file():
    """加载 .env 文件到环境变量"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime


def send_report_email(report_path: str,
                     subject: str = None,
                     body: str = None,
                     attachments: list = None):
    """
    发送报告邮件

    支持的邮箱:
    - Gmail: smtp.gmail.com:587 (需要应用专用密码)
    - QQ邮箱: smtp.qq.com:587 (需要授权码)
    - 163邮箱: smtp.163.com:25 (需要授权码)
    - Outlook: smtp.office365.com:587
    - 企业微信: smtp.exmail.qq.com:465 (SSL)

    Args:
        report_path: 报告文件路径 (markdown格式)
        subject: 邮件主题 (默认自动生成)
        body: 邮件正文 (默认读取报告内容)
        attachments: 附件列表

    Returns:
        bool: 是否发送成功
    """
    # 读取配置
    smtp_host = os.getenv('SMTP_HOST', 'smtp.qq.com')  # 默认QQ邮箱
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    email_to = os.getenv('EMAIL_TO')
    
    if not smtp_user or not smtp_pass:
        print("✗ 邮件配置缺失: 请设置 SMTP_USER 和 SMTP_PASS 环境变量")
        return False
    
    if not email_to:
        print("✗ 收件人配置缺失: 请设置 EMAIL_TO 环境变量")
        return False
    
    # 读取报告内容
    report_path = Path(report_path)
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
    else:
        report_content = "报告文件未找到"
    
    # 构建邮件
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email_to
    
    # 主题
    if subject is None:
        today = datetime.now().strftime('%Y-%m-%d')
        msg['Subject'] = f"DSS 因子验证报告 - {today}"
    else:
        msg['Subject'] = subject
    
    # 正文
    if body is None:
        # 提取关键信息
        summary = extract_summary(report_content)
        body = f"""DSS 因子验证报告

{summary}

详细报告请查看附件。

---
发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 添加 HTML 版本 (Markdown 转简单 HTML)
    html_body = markdown_to_html(report_content)
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # 添加附件
    if attachments is None:
        attachments = []
    
    # 自动添加报告文件
    if report_path.exists() and str(report_path) not in attachments:
        attachments.append(str(report_path))
    
    for attachment_path in attachments:
        attachment_path = Path(attachment_path)
        if not attachment_path.exists():
            continue
            
        # 猜测文件类型
        ctype, encoding = mimetypes.guess_type(str(attachment_path))
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        
        maintype, subtype = ctype.split('/', 1)
        
        with open(attachment_path, 'rb') as f:
            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=attachment_path.name
            )
            msg.attach(attachment)
    
    # 发送邮件
    try:
        # 根据端口选择连接方式
        use_ssl = smtp_port == 465

        if use_ssl:
            # SSL 连接 (企业微信等)
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            # STARTTLS 连接 (QQ、Gmail等)
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()

        server.login(smtp_user, smtp_pass)

        recipients = [e.strip() for e in email_to.split(',')]
        server.sendmail(smtp_user, recipients, msg.as_string())
        server.quit()

        print(f"✓ 邮件发送成功: {', '.join(recipients)}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ 认证失败: {e}")
        print("  提示: QQ邮箱需要使用授权码而非登录密码")
        print("  获取授权码: QQ邮箱设置 -> 账户 -> 开启SMTP服务 -> 生成授权码")
        return False
    except Exception as e:
        print(f"✗ 邮件发送失败: {e}")
        return False


def extract_summary(report_content: str) -> str:
    """从报告中提取摘要"""
    lines = report_content.split('\n')
    summary_lines = []
    
    for line in lines[:50]:  # 只看前50行
        if line.startswith('- 总因子数') or line.startswith('- 通过') or \
           line.startswith('- 未通过') or line.startswith('- 通过率'):
            summary_lines.append(line.strip('- '))
    
    return '\n'.join(summary_lines) if summary_lines else "请查看详细报告"


def markdown_to_html(markdown_text: str) -> str:
    """简单 Markdown 转 HTML"""
    html = markdown_text
    
    # 标题
    html = html.replace('# ', '<h1>').replace('\n# ', '</p>\n<h1>')
    html = html.replace('## ', '<h2>').replace('\n## ', '</p>\n<h2>')
    html = html.replace('### ', '<h3>').replace('\n### ', '</p>\n<h3>')
    
    # 粗体
    html = html.replace('**', '<b>', 1).replace('**', '</b>', 1)
    
    # 换行
    html = html.replace('\n', '<br>\n')
    
    # 表格简单处理
    lines = html.split('\n')
    result = []
    in_table = False
    
    for line in lines:
        if '|' in line and not in_table:
            in_table = True
            result.append('<table border="1" cellpadding="5">')
        elif '|' not in line and in_table:
            in_table = False
            result.append('</table>')
        
        if in_table and '|' in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells and not all(c in '-|' for c in line):
                row = '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'
                result.append(row)
        else:
            result.append(line)
    
    if in_table:
        result.append('</table>')
    
    return '<html><body>' + '\n'.join(result) + '</body></html>'


def test_email_config():
    """测试邮件配置"""
    print("邮件配置检查:")
    print(f"  SMTP_HOST: {os.getenv('SMTP_HOST', 'smtp.qq.com')}")
    print(f"  SMTP_PORT: {os.getenv('SMTP_PORT', '587')}")
    print(f"  SMTP_USER: {os.getenv('SMTP_USER', '未设置')}")
    print(f"  SMTP_PASS: {'已设置' if os.getenv('SMTP_PASS') else '未设置'}")
    print(f"  EMAIL_TO: {os.getenv('EMAIL_TO', '未设置')}")
    print()
    print("常用邮箱配置:")
    print("  QQ邮箱: SMTP_HOST=smtp.qq.com, SMTP_PORT=587")
    print("  Gmail:  SMTP_HOST=smtp.gmail.com, SMTP_PORT=587")
    print("  163:    SMTP_HOST=smtp.163.com, SMTP_PORT=25")
    print("  企业微信: SMTP_HOST=smtp.exmail.qq.com, SMTP_PORT=465")


if __name__ == '__main__':
    test_email_config()
