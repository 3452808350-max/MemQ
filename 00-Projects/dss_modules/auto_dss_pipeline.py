#!/usr/bin/env python3
"""
DSS 自动管道 - 每日预测 + 验证 + 通知

定时任务配置 (crontab):
    # 工作日早上 6:00 执行预测
    0 6 * * 1-5 cd /path/to/dss_modules && python3 auto_dss_pipeline.py --mode predict

    # 工作日早上 7:00 执行验证
    0 7 * * 1-5 cd /path/to/dss_modules && python3 auto_dss_pipeline.py --mode validate

或者使用 OpenClaw Cron:
    openclaw cron add --name "DSS Daily" --schedule "0 6 * * 1-5" --command "..."
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 自动加载 .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())


def run_prediction():
    """运行 DSS 预测"""
    print("=" * 60)
    print(f"DSS 每日预测 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # TODO: 集成你的 DSS 预测代码
    # 这里是一个示例框架

    try:
        # 1. 加载模型
        print("\n[1/3] 加载 DSS 模型...")
        # model = load_dss_model()

        # 2. 获取今日数据
        print("[2/3] 获取市场数据...")
        # data = fetch_today_data()

        # 3. 执行预测
        print("[3/3] 执行预测...")
        # predictions = model.predict(data)
        # save_predictions(predictions)

        print("\n✓ 预测完成")

        # 发送通知
        from telegram_notifier import send_simple_notification
        send_simple_notification(
            "DSS 每日预测完成",
            f"预测任务已成功执行\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n请查看预测结果。"
        )

        return True

    except Exception as e:
        print(f"\n✗ 预测失败: {e}")

        # 发送错误通知
        from telegram_notifier import send_simple_notification
        send_simple_notification(
            "⚠️ DSS 预测失败",
            f"预测任务执行失败\n错误: {str(e)}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        return False


def run_validation(data_path: str = None):
    """运行因子验证"""
    print("=" * 60)
    print(f"DSS 因子验证 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 自动查找昨天的数据文件
    if data_path is None:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        data_path = f"./data/dss_data_{yesterday}.csv"

    if not Path(data_path).exists():
        print(f"✗ 数据文件不存在: {data_path}")

        # 发送错误通知
        from telegram_notifier import send_simple_notification
        send_simple_notification(
            "⚠️ DSS 验证失败",
            f"找不到数据文件: {data_path}\n请检查数据路径。"
        )
        return False

    try:
        from validate_dss_factors import validate_dss_factors

        report, files = validate_dss_factors(
            data_path=data_path,
            output_dir='./reports',
            ic_ir_threshold=0.3,
            pathway_threshold=0.7,
            export_formats=['json', 'markdown']
        )

        # 发送 Telegram 通知
        from telegram_notifier import send_validation_report

        md_report = None
        for f in files:
            if f.endswith('.md'):
                md_report = f
                break

        if md_report:
            send_validation_report(
                report_path=md_report,
                summary=f"通过: {report.passed_factors}/{report.total_factors} ({report.passed_factors/report.total_factors*100:.1f}%)"
            )

        print("\n✓ 验证完成")
        return True

    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()

        # 发送错误通知
        from telegram_notifier import send_simple_notification
        send_simple_notification(
            "⚠️ DSS 验证失败",
            f"验证任务执行失败\n错误: {str(e)}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        return False


def main():
    parser = argparse.ArgumentParser(description='DSS 自动管道')
    parser.add_argument('--mode', type=str, required=True,
                       choices=['predict', 'validate', 'full'],
                       help='运行模式: predict=预测, validate=验证, full=完整流程')
    parser.add_argument('--data-path', type=str, default=None,
                       help='验证模式下的数据文件路径')

    args = parser.parse_args()

    if args.mode == 'predict':
        success = run_prediction()
    elif args.mode == 'validate':
        success = run_validation(args.data_path)
    elif args.mode == 'full':
        success = run_prediction() and run_validation(args.data_path)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
