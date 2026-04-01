# Debian Server 智能代理管理（Clash-CLI 自动开关）

> **任务**: 配置 clash-cli 自动开关，优化数据流量  
> **服务器**: Debian Server (106.53.186.90)  
> **日期**: 2026-03-03

---

## 🎯 任务说明

**请在 Debian Server 上配置智能代理管理系统：**

1. ✅ **安装 clash-cli** - Clash 命令行管理工具
2. ✅ **自动开关策略** - 根据目标地址自动开关代理
3. ✅ **定时任务** - 闲时自动开启，忙时自动关闭
4. ✅ **流量监控** - 统计代理使用情况和节省流量
5. ✅ **Kimi API 集成** - 特定 API 自动走代理

---

## 🚀 快速配置

### 步骤 1: 检查现有配置

```bash
#!/bin/bash
echo "🔍 检查现有代理配置..."

# 检查 clash
if command -v clash &> /dev/null; then
    echo "✅ Clash 已安装"
    clash -v
else
    echo "❌ Clash 未安装"
fi

# 检查 clash-cli
if command -v clash-cli &> /dev/null; then
    echo "✅ clash-cli 已安装"
else
    echo "❌ clash-cli 未安装"
fi

# 检查当前代理状态
echo ""
echo "当前代理状态:"
curl -s --connect-timeout 3 https://www.google.com > /dev/null 2>&1 && echo "代理：开启" || echo "代理：关闭"
```

---

### 步骤 2: 安装 clash-cli

```bash
#!/bin/bash
set -e

echo "📦 安装 clash-cli..."

# 下载 clash-cli
cd /tmp
wget https://github.com/Dreamacro/clash/releases/download/premium/clash-linux-amd64-latest.gz
gunzip clash-linux-amd64-latest.gz
mv clash-linux-amd64-latest /usr/local/bin/clash
chmod +x /usr/local/bin/clash

# 创建配置目录
mkdir -p /etc/clash
mkdir -p ~/.config/clash

# 创建基础配置
cat > /etc/clash/config.yaml << 'EOF'
port: 7890
socks-port: 7891
allow-lan: false
mode: rule
log-level: info

external-controller: 127.0.0.1:9090

proxies:
  # 在这里配置你的代理节点
  - name: "Auto"
    type: selector
    proxies:
      - "DIRECT"
      - "Proxy"

proxy-groups:
  - name: "Proxy"
    type: select
    proxies:
      - "DIRECT"
      - "Auto"

rules:
  # 国内网站直连
  - DOMAIN-SUFFIX,cn,DIRECT
  - DOMAIN-SUFFIX,aliyun.com,DIRECT
  - DOMAIN-SUFFIX,tencent.com,DIRECT
  - DOMAIN-SUFFIX,baidu.com,DIRECT
  - DOMAIN-SUFFIX,qq.com,DIRECT
  
  # AI API 走代理
  - DOMAIN-SUFFIX,minimaxi.com,Proxy
  - DOMAIN-SUFFIX,openai.com,Proxy
  - DOMAIN-SUFFIX,anthropic.com,Proxy
  
  # GitHub 走代理
  - DOMAIN-SUFFIX,github.com,Proxy
  - DOMAIN-SUFFIX,githubusercontent.com,Proxy
  
  # 其他走代理
  - MATCH,Proxy
EOF

# 创建 systemd 服务
cat > /etc/systemd/system/clash.service << 'EOF'
[Unit]
Description=Clash Proxy Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/clash -d /etc/clash -f /etc/clash/config.yaml
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable clash

echo "✅ Clash 安装完成"
```

---

### 步骤 3: 创建 clash-cli 管理脚本

```bash
#!/bin/bash
# clash-manager.sh - Clash 智能管理

CLASH_CONFIG="/etc/clash/config.yaml"
CLASH_API="http://127.0.0.1:9090"
LOG_FILE="/var/log/clash-manager.log"

# 开关代理
toggle_proxy() {
    local mode="$1"
    
    if [ "$mode" == "on" ]; then
        echo "开启代理..."
        curl -X PUT "$CLASH_API/configs" \
            -H "Content-Type: application/json" \
            -d '{"mode": "rule"}'
        echo "✅ 代理已开启" | tee -a $LOG_FILE
    elif [ "$mode" == "off" ]; then
        echo "关闭代理..."
        curl -X PUT "$CLASH_API/configs" \
            -H "Content-Type: application/json" \
            -d '{"mode": "direct"}'
        echo "✅ 代理已关闭（直连模式）" | tee -a $LOG_FILE
    elif [ "$mode" == "smart" ]; then
        echo "智能模式..."
        curl -X PUT "$CLASH_API/configs" \
            -H "Content-Type: application/json" \
            -d '{"mode": "rule"}'
        echo "✅ 智能模式已开启（规则路由）" | tee -a $LOG_FILE
    fi
}

# 显示状态
show_status() {
    echo "📊 Clash 状态:"
    systemctl status clash --no-pager | grep -E "Active|Loaded"
    
    echo ""
    echo "当前模式:"
    curl -s "$CLASH_API/configs" | jq -r '.mode'
    
    echo ""
    echo "流量统计:"
    curl -s "$CLASH_API/traffic/total" | jq '.'
}

# 定时任务 - 闲时开启，忙时关闭
schedule_proxy() {
    echo "配置定时任务..."
    
    # 闲时开启（00:00-08:00）
    (crontab -l 2>/dev/null; echo "0 0 * * * /usr/local/bin/clash-manager.sh on") | crontab -
    
    # 忙时关闭（08:00-00:00）
    (crontab -l 2>/dev/null; echo "0 8 * * * /usr/local/bin/clash-manager.sh off") | crontab -
    
    echo "✅ 定时任务已配置"
}

# 主函数
case "$1" in
    on)
        toggle_proxy "on"
        ;;
    off)
        toggle_proxy "off"
        ;;
    smart)
        toggle_proxy "smart"
        ;;
    status)
        show_status
        ;;
    schedule)
        schedule_proxy
        ;;
    *)
        echo "用法：$0 {on|off|smart|status|schedule}"
        echo ""
        echo "  on      - 开启代理"
        echo "  off     - 关闭代理（直连）"
        echo "  smart   - 智能模式（规则路由）"
        echo "  status  - 显示状态"
        echo "  schedule- 配置定时任务"
        exit 1
        ;;
esac
```

---

### 步骤 4: 配置 Kimi API 自动代理

```bash
#!/bin/bash
# 配置 Kimi CLI 自动代理

echo "🔧 配置 Kimi CLI 自动代理..."

# 创建 Kimi CLI 代理包装脚本
cat > /usr/local/bin/kimi-proxy << 'EOF'
#!/bin/bash
# kimi-proxy - Kimi CLI 智能代理

TARGET="$1"

# 判断是否需要代理
case "$TARGET" in
    *minimaxi.com*|*openai.com*|*anthropic.com*|*github.com*)
        # 需要代理
        export http_proxy="http://127.0.0.1:7890"
        export https_proxy="http://127.0.0.1:7890"
        echo "🔌 使用代理访问：$TARGET"
        ;;
    *aliyun.com*|*tencent.com*|*baidu.com*|*163.com*|*.cn)
        # 直连
        unset http_proxy https_proxy
        echo "🔌 直连访问：$TARGET"
        ;;
    *)
        # 默认智能模式
        export http_proxy="http://127.0.0.1:7890"
        export https_proxy="http://127.0.0.1:7890"
        export no_proxy="localhost,127.0.0.1,.cn,.aliyun.com,.tencent.com"
        echo "🔌 智能模式：$TARGET"
        ;;
esac

# 执行 kimi-cli
kimi-cli "$@"

# 清理环境变量
unset http_proxy https_proxy no_proxy
EOF

chmod +x /usr/local/bin/kimi-proxy

echo "✅ Kimi CLI 代理包装已配置"
echo "使用：kimi-proxy '你的问题'"
```

---

### 步骤 5: 流量监控和报告

```bash
#!/bin/bash
# clash-traffic-monitor.sh - 流量监控

CLASH_API="http://127.0.0.1:9090"
LOG_DIR="/var/log/clash"

mkdir -p $LOG_DIR

echo "📊 Clash 流量统计"
echo "================"
echo ""

# 实时流量
echo "实时流量:"
curl -s "$CLASH_API/traffic/total" | jq '.'

echo ""
echo "连接数:"
curl -s "$CLASH_API/connections" | jq '.connections | length'

echo ""
echo "代理规则命中:"
curl -s "$CLASH_API/rules" | jq '.rules[] | select(.hits > 0) | {pattern: .pattern, hits: .hits}' | head -20

# 每日统计
echo ""
echo "今日流量日志：$LOG_DIR/traffic-$(date +%Y-%m-%d).log"
```

---

### 步骤 6: 一键安装脚本

```bash
#!/bin/bash
# auto_setup_clash.sh - 一键安装 clash 智能管理

set -e

echo "🚀 开始配置 Debian Server 智能代理..."
echo "时间：$(date)"
echo ""

# 步骤 1: 检查
echo "📋 步骤 1: 检查现有配置"
bash -c 'echo "检查中..."'
echo ""

# 步骤 2: 安装 clash
echo "📦 步骤 2: 安装 Clash"
bash -c '
cd /tmp
if [ ! -f clash-linux-amd64-latest.gz ]; then
    wget -q https://github.com/Dreamacro/clash/releases/download/premium/clash-linux-amd64-latest.gz
fi
gunzip clash-linux-amd64-latest.gz
mv clash-linux-amd64-latest /usr/local/bin/clash
chmod +x /usr/local/bin/clash
echo "✅ Clash 已安装"
'
echo ""

# 步骤 3: 配置
echo "🔧 步骤 3: 创建配置文件"
mkdir -p /etc/clash ~/.config/clash

# 步骤 4: 管理脚本
echo "📝 步骤 4: 创建管理脚本"
# (复制上面的 clash-manager.sh)

# 步骤 5: Kimi 集成
echo "🔌 步骤 5: 配置 Kimi CLI 代理"
# (复制上面的 kimi-proxy)

# 步骤 6: 监控
echo "📊 步骤 6: 配置流量监控"
# (复制上面的 traffic-monitor.sh)

# 步骤 7: 测试
echo "🧪 步骤 7: 测试"
systemctl start clash
systemctl status clash --no-pager | grep Active

echo ""
echo "========================================"
echo "✅ 配置完成！"
echo "========================================"
echo ""
echo "使用命令:"
echo "  clash-manager.sh smart   - 智能模式"
echo "  clash-manager.sh status  - 查看状态"
echo "  kimi-proxy \"问题\"        - 使用代理调用 Kimi"
echo ""
```

---

## 📋 给 Debian Server AI 的指令

**通过 SSH 发送以下指令：**

```bash
# 1. SSH 连接到 Debian Server
ssh root@106.53.186.90

# 2. 创建配置脚本
cat > /tmp/setup_smart_proxy.sh << 'SCRIPT'
#!/bin/bash
# (粘贴上面的一键安装脚本内容)
SCRIPT

# 3. 执行配置
chmod +x /tmp/setup_smart_proxy.sh
/tmp/setup_smart_proxy.sh

# 4. 验证
clash-manager.sh status
```

---

## 🎯 预期效果

### 自动开关策略

| 时间 | 模式 | 说明 |
|------|------|------|
| **00:00-08:00** | 代理开启 | 闲时，大流量任务 |
| **08:00-00:00** | 代理关闭 | 忙时，节省流量 |
| **Kimi API** | 智能路由 | 国内直连，国外代理 |

### 流量优化

| 类型 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| Kimi API（国内） | 100% 代理 | 100% 直连 | ~50% |
| GitHub | 100% 代理 | 100% 代理 | - |
| 定时任务 | 手动 | 自动闲时 | ~30% |
| **总节省** | - | - | **~40%** |

---

## ✅ 完成后报告

配置完成后，请提供：

1. **Clash 服务状态** - 运行/停止
2. **当前代理模式** - rule/direct
3. **Kimi CLI 测试** - 能否正常调用
4. **流量统计** - 初始数据
5. **任何错误**

---

*配置指南版本：v1.0*  
*创建时间：2026-03-03*  
*适用于：Debian Server (106.53.186.90)*
