"""
Telegram 通知模块 - 用于发送 DSS 验证报告

需要配置环境变量或 .env 文件:
    TELEGRAM_BOT_TOKEN: Telegram Bot Token
    TELEGRAM_CHAT_ID: 接收消息的 Chat ID
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

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


def send_telegram_message(message: str, parse_mode: str = 'Markdown') -> bool:
    """
    发送 Telegram 消息

    Args:
        message: 消息内容
        parse_mode: 解析模式 (Markdown 或 HTML)

    Returns:
        bool: 是否发送成功
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token:
        print("✗ Telegram Bot Token 未设置")
        print("  请设置 TELEGRAM_BOT_TOKEN 环境变量")
        return False

    if not chat_id:
        print("✗ Telegram Chat ID 未设置")
        print("  请设置 TELEGRAM_CHAT_ID 环境变量")
        return False

    try:
        import urllib.request
        import urllib.parse

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }

        headers = {'Content-Type': 'application/json'}
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                print(f"✓ Telegram 消息发送成功")
                return True
            else:
                print(f"✗ Telegram API 错误: {result.get('description')}")
                return False

    except Exception as e:
        print(f"✗ 发送失败: {e}")
        return False


def send_validation_report(report_path: str, summary: Optional[str] = None) -> bool:
    """
    发送验证报告到 Telegram

    Args:
        report_path: 报告文件路径
        summary: 可选的摘要信息

    Returns:
        bool: 是否发送成功
    """
    report_path = Path(report_path)

    # 读取报告内容
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()
    else:
        report_content = "报告文件未找到"

    # 提取关键信息
    key_info = extract_key_info(report_content)

    # 构建消息
    today = datetime.now().strftime('%Y-%m-%d')
    message = f"""📊 *DSS 因子验证报告 - {today}*

{key_info}

"""

    if summary:
        message += f"\n📝 *摘要*\n{summary}\n"

    message += f"\n📁 完整报告: `{report_path}`"

    return send_telegram_message(message)


def extract_key_info(report_content: str) -> str:
    """从报告中提取关键信息"""
    lines = report_content.split('\n')
    info_lines = []

    for line in lines[:100]:
        line = line.strip()
        # 提取摘要部分
        if line.startswith('- ') and any(k in line for k in ['总因子数', '通过', '未通过', '通过率']):
            emoji = '✅' if '通过' in line and '未' not in line else '📊'
            info_lines.append(f"{emoji} {line[2:]}")
        # 提取因子表格
        elif '|' in line and any(k in line.lower() for k in ['factor', 'ir', '稳定性', '状态']):
            if '---' not in line:
                info_lines.append(line)

    if info_lines:
        return '\n'.join(info_lines[:20])  # 限制行数
    else:
        return "📄 详细报告已生成"


def send_simple_notification(title: str, message: str) -> bool:
    """
    发送简单通知

    Args:
        title: 通知标题
        message: 通知内容

    Returns:
        bool: 是否发送成功
    """
    emoji_map = {
        '成功': '✅',
        '失败': '❌',
        '错误': '⚠️',
        '警告': '⚠️',
        '完成': '✅',
        '开始': '🚀',
        '报告': '📊',
    }

    emoji = 'ℹ️'
    for key, e in emoji_map.items():
        if key in title:
            emoji = e
            break

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    text = f"""{emoji} *{title}*

{message}

🕐 {now}"""

    return send_telegram_message(text)


def test_telegram_config():
    """测试 Telegram 配置"""
    print("Telegram 配置检查:")
    print(f"  TELEGRAM_BOT_TOKEN: {'已设置' if os.getenv('TELEGRAM_BOT_TOKEN') else '未设置'}")
    print(f"  TELEGRAM_CHAT_ID: {os.getenv('TELEGRAM_CHAT_ID', '未设置')}")
    print()

    if os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'):
        print("正在发送测试消息...")
        result = send_simple_notification(
            "DSS 系统测试",
            "这是来自 DSS 因子验证系统的测试消息。\n\n如果收到这条消息，说明 Telegram 通知配置正确！"
        )
        if result:
            print("\n✓ 测试消息发送成功！")
        else:
            print("\n✗ 测试消息发送失败")
    else:
        print("请先在 .env 文件中配置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
        print()
        print("配置步骤:")
        print("  1. 找 @BotFather 创建 Bot，获取 Token")
        print("  2. 给 Bot 发送一条消息")
        print("  3. 访问 https://api.telegram.org/bot<TOKEN>/getUpdates 获取 Chat ID")
        print("  4. 将 Token 和 Chat ID 填入 .env 文件")


if __name__ == '__main__':
    test_telegram_config()
