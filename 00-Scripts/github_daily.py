#!/usr/bin/env python3
"""
GitHub 每日热门项目推荐
- 高星项目（新增 stars 最多）
- 高增长率项目（star growth rate 最高）
"""

import requests
import json
from datetime import datetime, timedelta

# GitHub API (无需 token 也可用，但有 token 限额更高)
GITHUB_API = "https://api.github.com"

def fetch_trending_repos(limit=10):
    """获取 trending 项目（按近期 stars 排序）"""
    
    # 搜索最近 7 天创建的高星项目
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    queries = [
        {
            'name': '🔥 本周热门（高星）',
            'q': f'stars:>500 created:>={week_ago}',
            'sort': 'stars',
            'order': 'desc'
        },
        {
            'name': '📈 高增长率（新星）',
            'q': f'stars:>100 created:>={week_ago}',
            'sort': 'stars',
            'order': 'desc'
        },
        {
            'name': '⭐ 总体热门',
            'q': 'stars:>5000',
            'sort': 'stars',
            'order': 'desc'
        }
    ]
    
    results = []
    
    for query in queries:
        try:
            url = f"{GITHUB_API}/search/repositories"
            params = {
                'q': query['q'],
                'sort': query['sort'],
                'order': query['order'],
                'per_page': limit
            }
            
            headers = {'Accept': 'application/vnd.github.v3+json'}
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                repos = data.get('items', [])[:5]  # 每类取 5 个
                
                results.append({
                    'category': query['name'],
                    'repos': [format_repo(r) for r in repos]
                })
            else:
                print(f"API 错误：{response.status_code}")
                print(response.text[:200])
                
        except Exception as e:
            print(f"查询失败 {query['name']}: {e}")
    
    return results

def format_repo(repo):
    """格式化项目信息"""
    return {
        'name': repo['full_name'],
        'stars': repo['stargazers_count'],
        'forks': repo['forks_count'],
        'desc': (repo['description'] or '无描述')[:100],
        'url': repo['html_url'],
        'language': repo['language'] or 'Unknown',
        'created': repo['created_at'][:10]
    }

def format_message(results):
    """格式化输出消息"""
    lines = [f"🐙 **GitHub 每日推荐** - {datetime.now().strftime('%Y-%m-%d')}\n"]
    
    for category in results:
        lines.append(f"\n{category['category']}")
        lines.append("─" * 40)
        
        for repo in category['repos']:
            lines.append(f"\n📦 [{repo['name']}]({repo['url']})")
            lines.append(f"   ⭐ {repo['stars']:,} | 🍴 {repo['forks']:,} | 💻 {repo['language']}")
            lines.append(f"   _{repo['desc']}_")
    
    lines.append("\n\n💡 提示：点击项目链接查看详情")
    
    return "\n".join(lines)

def send_email(subject, html_content, to_email):
    """通过 SMTP 发送邮件（使用现有的 email_config.json 配置）"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import json
    import os
    
    # 读取现有邮箱配置
    config_path = '/home/kyj/.openclaw/workspace/email_config.json'
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"⚠️ 无法读取邮箱配置：{e}")
        return False
    
    smtp_server = config.get('smtp_server', 'smtp.qq.com')
    smtp_port = config.get('smtp_port', 587)
    smtp_user = config.get('sender_email', '')
    smtp_pass = config.get('sender_password', '')
    
    if not smtp_user or not smtp_pass:
        print("⚠️ 邮箱配置不完整，跳过邮件发送")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email
        
        # HTML 版本
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 连接服务器
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        
        print(f"✅ 邮件已发送至 {to_email}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

def format_email_html(results):
    """格式化 HTML 邮件"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; }}
            .header {{ background: linear-gradient(135deg, #24292e 0%, #0366d6 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .repo {{ border-left: 4px solid #0366d6; padding: 15px; margin: 15px 0; background: #f6f8fa; border-radius: 4px; }}
            .repo-name {{ font-weight: bold; color: #0366d6; font-size: 16px; }}
            .repo-meta {{ color: #586069; font-size: 14px; margin: 5px 0; }}
            .repo-desc {{ color: #24292e; font-style: italic; margin-top: 8px; }}
            .category {{ margin-top: 30px; }}
            .category-title {{ font-size: 18px; font-weight: bold; color: #24292e; border-bottom: 2px solid #0366d6; padding-bottom: 10px; }}
            .footer {{ text-align: center; color: #586069; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e1e4e8; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="margin: 0;">🐙 GitHub 每日推荐</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">{date_str}</p>
        </div>
    """
    
    for category in results:
        html += f"""
        <div class="category">
            <div class="category-title">{category['category']}</div>
        """
        
        for repo in category['repos']:
            html += f"""
            <div class="repo">
                <div class="repo-name">
                    <a href="{repo['url']}" style="text-decoration: none; color: #0366d6;">{repo['name']}</a>
                </div>
                <div class="repo-meta">
                    ⭐ {repo['stars']:,} stars | 🍴 {repo['forks']:,} forks | 💻 {repo['language']}
                </div>
                <div class="repo-desc">{repo['desc']}</div>
            </div>
            """
        
        html += "</div>"
    
    html += """
        <div class="footer">
            <p>由 OpenClaw 自动生成 • 祝你编码愉快！</p>
        </div>
    </body>
    </html>
    """
    
    return html

def main(send_to_telegram=False, send_to_email=False, email_address=None):
    print("🚀 开始获取 GitHub 热门项目...")
    
    results = fetch_trending_repos()
    
    if results:
        # Markdown 格式（Telegram）
        message_md = format_message(results)
        print("\n" + message_md[:500] + "...\n")
        
        # HTML 格式（邮件）
        message_html = format_email_html(results)
        
        # 保存结果
        with open('/home/kyj/.openclaw/workspace/github_daily_output.md', 'w') as f:
            f.write(message_md)
        
        print(f"✅ 已获取 {sum(len(c['repos']) for c in results)} 个项目推荐")
        
        # 发送到 Telegram
        if send_to_telegram:
            import subprocess
            cmd = ['openclaw', 'message', 'send', '--target', 'telegram:8278708856', '--message', message_md]
            try:
                subprocess.run(cmd, timeout=30)
                print("✅ 已发送到 Telegram")
            except Exception as e:
                print(f"⚠️ Telegram 发送失败：{e}")
        
        # 发送邮件
        if send_to_email and email_address:
            send_email(
                subject=f"🐙 GitHub 每日推荐 - {datetime.now().strftime('%Y-%m-%d')}",
                html_content=message_html,
                to_email=email_address
            )
        
        return message_md
    else:
        print("❌ 获取失败")
        return None

if __name__ == "__main__":
    import sys
    send_telegram = '--telegram' in sys.argv
    send_email_flag = '--email' in sys.argv
    
    # 获取邮箱地址（从参数或环境变量）
    email_addr = None
    for i, arg in enumerate(sys.argv):
        if arg == '--email' and i + 1 < len(sys.argv):
            email_addr = sys.argv[i + 1]
            break
    
    if not email_addr:
        import os
        email_addr = os.getenv('OUTLOOK_EMAIL')
    
    main(send_to_telegram=send_telegram, send_to_email=send_email_flag, email_address=email_addr)
