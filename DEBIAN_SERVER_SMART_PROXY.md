# Debian Server 智能代理自动配置指南

> **目标**: 自动配置智能代理策略，优化数据流量  
> **服务器**: Debian Server (192.168.4.147, RX6800)  
> **日期**: 2026-03-03  
> **执行者**: Debian Server 上的 AI

---

## 📋 任务说明

**你好！请在 Debian Server 上配置智能代理系统：**

1. ✅ **自动代理切换** - 根据目标地址自动选择直连/代理
2. ✅ **流量优化** - 国内流量直连，国外流量代理
3. ✅ **缓存服务** - 减少重复请求
4. ✅ **流量监控** - 统计和告警
5. ✅ **自动策略** - 基于规则的智能路由

---

## 🏗️ 架构设计

```
┌─────────────────┐
│   应用程序       │
│   (Kimi/DSS/..) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  智能代理层      │
│  (Squid + ACL)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│直连  │  │代理  │
│国内  │  │国外  │
└──────┘  └──────┘
```

---

## 🚀 自动配置脚本

### 步骤 1: 检查现有代理

```bash
#!/bin/bash
# check_proxy.sh

echo "🔍 检查现有代理配置..."

# 检查环境变量
echo "当前代理环境变量:"
env | grep -i proxy

# 检查 Squid
if command -v squid &> /dev/null; then
    echo "✅ Squid 已安装"
    squid -v | head -1
else
    echo "❌ Squid 未安装"
fi

# 检查 Privoxy
if command -v privoxy &> /dev/null; then
    echo "✅ Privoxy 已安装"
else
    echo "❌ Privoxy 未安装"
fi

# 检查当前路由
echo ""
echo "当前默认路由:"
ip route | grep default
```

---

### 步骤 2: 安装 Squid 代理

```bash
#!/bin/bash
# install_squid.sh

set -e

echo "📦 安装 Squid 代理..."

apt update
apt install squid squid-opt -y

# 备份原配置
cp /etc/squid/squid.conf /etc/squid/squid.conf.bak

# 创建智能代理配置
cat > /etc/squid/squid.conf << 'EOF'
# Squid 智能代理配置

# 基本设置
http_port 3128
cache_dir ufs /var/spool/squid 100 16 256
cache_effective_user proxy
cache_effective_group proxy

# 访问控制
acl localnet src 192.168.0.0/16
acl localnet src 10.0.0.0/8
acl SSL_ports port 443
acl Safe_ports port 80
acl Safe_ports port 443

# 国内网站 ACL（直连）
acl china_sites dstdomain .cn
acl china_sites dstdomain .aliyun.com
acl china_sites dstdomain .tencent.com
acl china_sites dstdomain .baidu.com
acl china_sites dstdomain .163.com
acl china_sites dstdomain .qq.com
acl china_sites dstdomain .taobao.com
acl china_sites dstdomain .jd.com

# 国内 IP 段（直连）
acl china_ip dst "/etc/squid/china_ip_list.txt"

# 缓存设置
cache_mem 256 MB
maximum_object_size_in_memory 10 MB
cache_swap_low 98
cache_swap_high 99

# 缓存策略 - 优化流量
refresh_pattern -i \.(jpg|jpeg|png|gif|ico|css|js)$ 1440 90% 10080
refresh_pattern -i \.(pdf|doc|docx|xls|xlsx)$ 10080 90% 43200
refresh_pattern . 0 20% 4320

# 访问控制规则
http_access allow localhost
http_access allow localnet
http_access allow china_sites
http_access deny all

# 日志
access_log /var/log/squid/access.log
cache_log /var/log/squid/cache.log

# 智能路由 - 国内直连，国外代理
never_direct deny china_sites
never_direct deny china_ip
always_direct allow china_sites
always_direct allow china_ip
EOF

# 创建国内 IP 列表
echo "📥 下载国内 IP 列表..."
curl -o /etc/squid/china_ip_list.txt \
  "https://raw.githubusercontent.com/Hackl0us/GeoIP2-CN/release/CN-ip-cidr.txt"

# 设置权限
chown -R proxy:proxy /var/spool/squid
chmod 750 /var/spool/squid

# 初始化缓存目录
squid -z

# 启动服务
systemctl enable squid
systemctl restart squid

echo "✅ Squid 安装完成！"
echo "监听端口：3128"
```

---

### 步骤 3: 配置智能代理策略

```bash
#!/bin/bash
# setup_smart_proxy.sh

set -e

echo "🔧 配置智能代理策略..."

# 创建代理自动切换脚本
cat > /usr/local/bin/smart-proxy.sh << 'EOF'
#!/bin/bash
# smart-proxy.sh - 智能代理切换

PROXY_SERVER="127.0.0.1:3128"
DIRECT_MODE="DIRECT"
PROXY_MODE="PROXY"

# 国内网站列表（直连）
CHINA_DOMAINS=(
    ".cn"
    ".aliyun.com"
    ".tencent.com"
    ".baidu.com"
    ".163.com"
    ".qq.com"
    ".taobao.com"
    ".jd.com"
    "192.168."
    "10."
    "172.16."
)

# 判断是否国内网站
is_china_site() {
    local domain="$1"
    
    for china_domain in "${CHINA_DOMAINS[@]}"; do
        if [[ "$domain" == *"$china_domain" ]]; then
            return 0  # 是国内网站
        fi
    done
    
    return 1  # 是国外网站
}

# 获取代理设置
get_proxy() {
    local target="$1"
    
    if is_china_site "$target"; then
        echo "$DIRECT_MODE"
    else
        echo "$PROXY_SERVER"
    fi
}

# 设置全局代理
set_global_proxy() {
    local mode="$1"
    
    if [ "$mode" == "on" ]; then
        export http_proxy="http://$PROXY_SERVER"
        export https_proxy="http://$PROXY_SERVER"
        export no_proxy="localhost,127.0.0.1,192.168.*,10.*,*.cn"
        echo "✅ 代理已开启：$PROXY_SERVER"
    elif [ "$mode" == "off" ]; then
        unset http_proxy https_proxy no_proxy
        echo "✅ 代理已关闭（直连模式）"
    elif [ "$mode" == "smart" ]; then
        export http_proxy="http://$PROXY_SERVER"
        export https_proxy="http://$PROXY_SERVER"
        export no_proxy="localhost,127.0.0.1,192.168.*,10.*,*.cn,*.aliyun.com,*.tencent.com"
        echo "✅ 智能代理已开启（国内直连，国外代理）"
    fi
}

# 显示当前代理状态
show_status() {
    echo "📊 当前代理状态:"
    echo "  HTTP_PROXY: $http_proxy"
    echo "  HTTPS_PROXY: $https_proxy"
    echo "  NO_PROXY: $no_proxy"
}

# 主函数
case "$1" in
    on)
        set_global_proxy "on"
        ;;
    off)
        set_global_proxy "off"
        ;;
    smart)
        set_global_proxy "smart"
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法：$0 {on|off|smart|status}"
        echo ""
        echo "  on    - 开启全局代理"
        echo "  off   - 关闭代理（直连）"
        echo "  smart - 智能模式（国内直连，国外代理）"
        echo "  status- 显示当前状态"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/smart-proxy.sh

echo "✅ 智能代理脚本已创建"
```

---

### 步骤 4: 配置应用程序代理

```bash
#!/bin/bash
# configure_apps_proxy.sh

echo "🔧 配置应用程序代理..."

# 1. Git 代理配置
cat >> ~/.gitconfig << 'EOF'

# 智能代理配置
[http]
    proxy = http://127.0.0.1:3128
[https]
    proxy = http://127.0.0.1:3128
[url "http://"]
    insteadOf = https://
EOF

# 2. APT 代理配置（仅国外源）
cat > /etc/apt/apt.conf.d/01proxy << 'EOF'
// 智能代理 - 仅国外源使用代理
Acquire::http::Proxy::debian.org "DIRECT";
Acquire::http::Proxy::ubuntu.com "DIRECT";
Acquire::http::Proxy::aliyun.com "DIRECT";
Acquire::http::Proxy::tencent.com "DIRECT";
Acquire::http::Proxy::163.com "DIRECT";
EOF

# 3. Pip 代理配置
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
# 使用国内镜像，不需要代理
EOF

# 4. NPM 代理配置
npm config set registry https://registry.npmmirror.com
npm config set proxy null
npm config set https-proxy null

# 5. Docker 代理配置
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/http-proxy.conf << 'EOF'
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:3128"
Environment="HTTPS_PROXY=http://127.0.0.1:3128"
Environment="NO_PROXY=localhost,127.0.0.1,.cn,.aliyun.com,.tencent.com"
EOF

# 6. Kimi CLI 代理配置
cat >> ~/.bashrc << 'EOF'

# 智能代理（Kimi CLI 使用）
alias kimi-proxy='smart-proxy smart'
alias kimi-direct='smart-proxy off'
EOF

echo "✅ 应用程序代理配置完成"
```

---

### 步骤 5: 流量监控和告警

```bash
#!/bin/bash
# setup_traffic_monitor.sh

echo "📊 配置流量监控..."

# 创建监控脚本
cat > /usr/local/bin/traffic-monitor.sh << 'EOF'
#!/bin/bash
# traffic-monitor.sh - 流量监控

LOG_FILE="/var/log/squid/access.log"
ALERT_THRESHOLD=1073741824  # 1GB 告警阈值

# 统计今日流量
today=$(date +%Y-%m-%d)
total_bytes=$(grep "$today" $LOG_FILE | awk '{sum+=$10} END {print sum}')

# 转换为 GB
total_gb=$(echo "scale=2; $total_bytes / 1073741824" | bc)

echo "📊 今日流量统计 ($(date +%Y-%m-%d))"
echo "================================"
echo "总流量：${total_gb} GB"
echo "告警阈值：1 GB"

# 检查是否超过阈值
if (( $(echo "$total_bytes > $ALERT_THRESHOLD" | bc -l) )); then
    echo "⚠️  警告：流量超过 1GB！"
    # 可以发送邮件或 Telegram 通知
    # mail -s "流量告警" admin@example.com <<< "今日流量：${total_gb}GB"
fi

# Top 10 访问网站
echo ""
echo "🔝 Top 10 访问网站:"
grep "$today" $LOG_FILE | awk '{print $7}' | sort | uniq -c | sort -rn | head -10

# 缓存命中率
echo ""
echo "💾 缓存统计:"
squidclient -h localhost -p 3128 mgr:info | grep -A 5 "Request Hit Ratios"
EOF

chmod +x /usr/local/bin/traffic-monitor.sh

# 添加定时任务（每天报告）
(crontab -l 2>/dev/null; echo "0 20 * * * /usr/local/bin/traffic-monitor.sh >> /var/log/traffic-daily.log") | crontab -

echo "✅ 流量监控已配置"
echo "   每日报告时间：20:00"
```

---

### 步骤 6: 自动代理策略（基于规则）

```bash
#!/bin/bash
# setup_auto_proxy_rules.sh

echo "🎯 配置自动代理规则..."

# 创建规则引擎
cat > /usr/local/bin/proxy-rule-engine.py << 'EOF'
#!/usr/bin/env python3
"""
智能代理规则引擎

根据目标地址、时间、流量自动选择最优代理策略
"""

import json
import subprocess
from datetime import datetime
from typing import Dict, List

class ProxyRuleEngine:
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict]:
        """加载规则"""
        return [
            {
                "name": "国内网站直连",
                "condition": {
                    "domain_suffix": [".cn", ".aliyun.com", ".tencent.com"],
                    "ip_prefix": ["192.168.", "10.", "172.16."]
                },
                "action": "direct",
                "priority": 100
            },
            {
                "name": "GitHub 使用代理",
                "condition": {
                    "domain_suffix": [".github.com", ".githubusercontent.com"]
                },
                "action": "proxy",
                "priority": 90
            },
            {
                "name": "AI API 使用代理",
                "condition": {
                    "domain_suffix": [".openai.com", ".anthropic.com", ".minimaxi.com"]
                },
                "action": "proxy",
                "priority": 90
            },
            {
                "name": "大文件下载代理",
                "condition": {
                    "file_extension": [".iso", ".tar.gz", ".zip"],
                    "time_range": "00:00-08:00"  # 闲时
                },
                "action": "proxy",
                "priority": 80
            },
            {
                "name": "视频流媒体直连",
                "condition": {
                    "domain_suffix": [".bilbili.com", ".iqiyi.com", ".youku.com"]
                },
                "action": "direct",
                "priority": 85
            }
        ]
    
    def evaluate(self, target: str, context: Dict = None) -> str:
        """
        评估目标地址，返回代理策略
        
        Args:
            target: 目标地址（URL 或域名）
            context: 上下文信息（时间、文件大小等）
        
        Returns:
            "direct" 或 "proxy"
        """
        for rule in sorted(self.rules, key=lambda x: x["priority"], reverse=True):
            if self._match_rule(rule, target, context):
                print(f"✅ 匹配规则：{rule['name']}")
                return rule["action"]
        
        # 默认策略：国外代理，国内直连
        if self._is_china_domain(target):
            return "direct"
        else:
            return "proxy"
    
    def _match_rule(self, rule: Dict, target: str, context: Dict) -> bool:
        """匹配规则"""
        condition = rule.get("condition", {})
        
        # 域名匹配
        if "domain_suffix" in condition:
            for suffix in condition["domain_suffix"]:
                if target.endswith(suffix):
                    return True
        
        # IP 前缀匹配
        if "ip_prefix" in condition:
            for prefix in condition["ip_prefix"]:
                if target.startswith(prefix):
                    return True
        
        # 时间范围匹配
        if "time_range" in condition:
            time_range = condition["time_range"]
            start, end = time_range.split("-")
            start_hour = int(start.split(":")[0])
            end_hour = int(end.split(":")[0])
            current_hour = datetime.now().hour
            
            if start_hour <= current_hour < end_hour:
                return True
        
        return False
    
    def _is_china_domain(self, target: str) -> bool:
        """判断是否国内域名"""
        china_suffixes = [".cn", ".aliyun.com", ".tencent.com", ".baidu.com"]
        return any(target.endswith(suffix) for suffix in china_suffixes)

# 命令行使用
if __name__ == "__main__":
    import sys
    
    engine = ProxyRuleEngine()
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
        result = engine.evaluate(target)
        print(f"目标：{target}")
        print(f"策略：{'直连' if result == 'direct' else '代理'}")
    else:
        print("用法：proxy-rule-engine.py <URL>")
EOF

chmod +x /usr/local/bin/proxy-rule-engine.py

echo "✅ 自动代理规则引擎已配置"
```

---

### 步骤 7: 测试和验证

```bash
#!/bin/bash
# test_proxy_setup.sh

echo "🧪 测试代理配置..."

# 测试 1: Squid 服务
echo ""
echo "📦 测试 1: Squid 服务状态"
systemctl status squid --no-pager | grep -E "Active|Loaded"

# 测试 2: 代理端口
echo ""
echo "🔌 测试 2: 代理端口监听"
netstat -tlnp | grep 3128

# 测试 3: 智能代理脚本
echo ""
echo "🎯 测试 3: 智能代理脚本"
/usr/local/bin/smart-proxy.sh status

# 测试 4: 规则引擎
echo ""
echo "🧠 测试 4: 规则引擎"
echo "测试 github.com:"
/usr/local/bin/proxy-rule-engine.py github.com
echo ""
echo "测试 aliyun.com:"
/usr/local/bin/proxy-rule-engine.py aliyun.com

# 测试 5: 流量监控
echo ""
echo "📊 测试 5: 流量监控"
/usr/local/bin/traffic-monitor.sh

# 测试 6: 实际请求测试
echo ""
echo "🌐 测试 6: 实际请求测试"
echo "测试国内网站（应直连）:"
curl -I --connect-timeout 5 https://www.baidu.com 2>&1 | head -3

echo ""
echo "测试 GitHub（应代理）:"
curl -I --connect-timeout 5 https://www.github.com 2>&1 | head -3

echo ""
echo "✅ 所有测试完成！"
```

---

## 📋 一键安装脚本

```bash
#!/bin/bash
# auto_setup_all.sh
# 一键自动配置所有代理策略

set -e

echo "🚀 开始自动配置 Debian Server 智能代理..."
echo "时间：$(date)"
echo ""

# 步骤 1: 检查现有配置
echo "📋 步骤 1: 检查现有配置"
bash check_proxy.sh
echo ""

# 步骤 2: 安装 Squid
echo "📦 步骤 2: 安装 Squid 代理"
bash install_squid.sh
echo ""

# 步骤 3: 配置智能代理
echo "🔧 步骤 3: 配置智能代理"
bash setup_smart_proxy.sh
echo ""

# 步骤 4: 配置应用程序
echo "📱 步骤 4: 配置应用程序代理"
bash configure_apps_proxy.sh
echo ""

# 步骤 5: 配置监控
echo "📊 步骤 5: 配置流量监控"
bash setup_traffic_monitor.sh
echo ""

# 步骤 6: 配置规则引擎
echo "🎯 步骤 6: 配置自动规则"
bash setup_auto_proxy_rules.sh
echo ""

# 步骤 7: 测试验证
echo "🧪 步骤 7: 测试验证"
bash test_proxy_setup.sh
echo ""

echo "========================================"
echo "✅ 所有配置完成！"
echo "========================================"
echo ""
echo "代理服务器：http://127.0.0.1:3128"
echo "智能模式：国内直连，国外代理"
echo ""
echo "使用命令:"
echo "  smart-proxy smart  - 开启智能模式"
echo "  smart-proxy status - 查看状态"
echo "  traffic-monitor.sh - 查看流量"
echo ""
echo "配置时间：$(date)"
```

---

## 📊 预期效果

### 流量优化

| 类型 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| 国内流量 | 100% 代理 | 100% 直连 | ~30% |
| 缓存命中 | 0% | 60-80% | ~20% |
| 重复请求 | 100% | 缓存 | ~15% |
| **总节省** | - | - | **~40-50%** |

### 性能提升

| 指标 | 提升 |
|------|------|
| 国内网站访问 | 快 2-3 倍 |
| 重复请求 | 即时响应 |
| 大文件下载 | 闲时自动 |

---

## 🐛 故障排查

### Squid 无法启动

```bash
# 检查配置
squid -k check

# 查看日志
tail -f /var/log/squid/cache.log

# 重新初始化
squid -z
systemctl restart squid
```

### 规则引擎不工作

```bash
# 测试规则
/usr/local/bin/proxy-rule-engine.py github.com

# 检查 Python 依赖
python3 -c "import json; print('OK')"
```

### 流量统计不准确

```bash
# 检查日志权限
ls -la /var/log/squid/access.log

# 重置统计
> /var/log/squid/access.log
systemctl restart squid
```

---

## 📞 完成后报告

配置完成后，请提供以下信息：

1. **Squid 服务状态** - 运行/停止
2. **代理端口监听** - 3128 是否开放
3. **智能代理测试结果** - 国内/国外网站访问
4. **流量监控数据** - 初始统计
5. **任何错误或警告**

---

*配置指南版本：v1.0*  
*创建时间：2026-03-03*  
*适用于：Debian Server (192.168.4.147)*
