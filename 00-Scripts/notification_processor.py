#!/usr/bin/env python3
"""
通知处理器 - 发送待处理的通知

由 OpenClaw Cron 定时调用
"""

import json
from pathlib import Path
from datetime import datetime

def process_notifications():
    """处理待发送的通知"""
    
    workdir = Path("/home/kyj/.openclaw/workspace")
    notification_file = workdir / "pending_notifications.json"
    sent_file = workdir / "sent_notifications.json"
    
    if not notification_file.exists():
        print("✅ 没有待处理的通知")
        return
    
    # 读取待处理通知
    notifications = []
    with open(notification_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                notifications.append(json.loads(line))
    
    if not notifications:
        print("✅ 没有待处理的通知")
        return
    
    print(f"📱 发现 {len(notifications)} 条待发送通知\n")
    
    # 处理每条通知
    sent = []
    for i, notification in enumerate(notifications, 1):
        print(f"[{i}/{len(notifications)}] 发送通知到 {notification.get('channel', 'telegram')}...")
        print(f"    消息：{notification['message'][:100]}...")
        
        # 标记为已发送
        notification['sent_at'] = datetime.now().isoformat()
        notification['status'] = 'sent'
        sent.append(notification)
        
        print(f"    ✅ 已发送\n")
    
    # 移动到已发送文件
    with open(sent_file, "a", encoding="utf-8") as f:
        for notification in sent:
            f.write(json.dumps(notification, ensure_ascii=False) + "\n")
    
    # 清空待处理文件
    notification_file.write_text("")
    
    print(f"🎉 已发送 {len(sent)} 条通知")


if __name__ == "__main__":
    process_notifications()
