#!/bin/bash
# DSS 验证 + 邮件发送脚本
# 用法: ./run_dss_with_email.sh /path/to/dss_data.csv

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 检查参数
if [ $# -eq 0 ]; then
    echo "用法: $0 <数据文件路径>"
    exit 1
fi

DATA_PATH=$1
DATE=$(date +%Y%m%d)
REPORT_DIR="./reports"

echo "========================================"
echo "DSS 因子验证 + 邮件发送"
echo "日期: $DATE"
echo "数据: $DATA_PATH"
echo "========================================"

# 运行验证并发送邮件
python3 validate_dss_factors.py \
    --data-path "$DATA_PATH" \
    --output "$REPORT_DIR" \
    --email \
    --formats markdown csv

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ 完成! 报告已生成并发送"
else
    echo ""
    echo "✗ 验证失败"
    exit 1
fi
