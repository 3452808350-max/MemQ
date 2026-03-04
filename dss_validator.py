#!/usr/bin/env python3
"""
DSS 反向验证模块
- 保存每日预测
- 3个工作日后验证准确率
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# 存储目录
PREDICTION_DIR = Path("/home/kyj/.openclaw/workspace/data/predictions")
PREDICTION_DIR.mkdir(parents=True, exist_ok=True)

def save_prediction(results):
    """保存当日预测结果"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 只保存预测上涨的股票 (score > 0)
    predicted_up = [
        {
            "code": r["code"],
            "name": r["name"],
            "industry": r["industry"],
            "close": r["close"],
            "score": r["score"]
        }
        for r in results if r["score"] > 0
    ]
    
    prediction_data = {
        "date": today,
        "predicted_up_count": len(predicted_up),
        "predicted_up": predicted_up,
        "all_stocks": results
    }
    
    file_path = PREDICTION_DIR / f"prediction_{today}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(prediction_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 预测已保存: {file_path}")
    return file_path

def get_trading_dates(days=10):
    """获取最近的工作日日期（排除周末）"""
    import baostock as bs
    
    dates = []
    current = datetime.now()
    
    # 登录获取交易日
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        return []
    
    try:
        # 获取最近20天的交易日
        rs = bs.query_trade_dates(
            start_date=(current - timedelta(days=30)).strftime('%Y-%m-%d'),
            end_date=current.strftime('%Y-%m-%d')
        )
        
        while rs.next():
            row = rs.get_row_data()
            if row and len(row) >= 2 and row[1] == '1':  # is_trading_day
                dates.append(row[0])
    finally:
        bs.logout()
    
    return dates[-days:]

VALIDATION_DAYS = 5  # 验证周期改为5个工作日

def validate_predictions():
    """验证N个工作日前的预测（默认5天）"""
    import baostock as bs
    
    trading_dates = get_trading_dates(30)
    
    # 需要至少 VALIDATION_DAYS + 1 个交易日
    if len(trading_dates) < VALIDATION_DAYS + 2:
        print(f"数据不足，需要至少{VALIDATION_DAYS + 2}个交易日")
        return None
    
    # N个工作日前的日期
    target_date = trading_dates[-VALIDATION_DAYS]  # 5 working days ago
    prediction_file = PREDICTION_DIR / f"prediction_{target_date}.json"
    
    if not prediction_file.exists():
        print(f"找不到预测文件: {prediction_file}")
        return None
    
    # 读取预测
    with open(prediction_file, "r", encoding="utf-8") as f:
        prediction = json.load(f)
    
    predicted_stocks = prediction.get("predicted_up", [])
    
    if not predicted_stocks:
        print("当日没有预测上涨的股票")
        return None
    
    print(f"\n{'='*60}")
    print(f"📊 DSS 反向验证报告 - 预测日期: {target_date}")
    print(f"{'='*60}")
    
    # 登录获取实际数据
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        return None
    
    try:
        # 获取今日收盘价和3日前收盘价
        latest_date = trading_dates[-1]  # 今日
        prev_date = trading_dates[-4]    # 3天前
        
        correct = 0
        wrong = 0
        details = []
        
        for stock in predicted_stocks:
            code = stock["code"]
            name = stock["name"]
            pred_score = stock["score"]
            
            # 获取历史数据
            rs = bs.query_history_k_data_plus(
                code, "date,close",
                start_date=prev_date,
                end_date=latest_date,
                frequency="d"
            )
            
            prices = []
            while rs.next():
                row = rs.get_row_data()
                if row[1]:  # close price
                    prices.append(float(row[1]))
            
            if len(prices) >= 2:
                old_price = prices[0]
                new_price = prices[-1]
                change_pct = (new_price - old_price) / old_price * 100
                
                # 预测正确: 实际上涨
                if change_pct > 0:
                    correct += 1
                    status = "✅"
                else:
                    wrong += 1
                    status = "❌"
                
                details.append({
                    "name": name,
                    "code": code,
                    "old_price": old_price,
                    "new_price": new_price,
                    "change_pct": change_pct,
                    "pred_score": pred_score,
                    "correct": change_pct > 0
                })
        
        # 计算准确率
        total = correct + wrong
        accuracy = (correct / total * 100) if total > 0 else 0
        
        print(f"\n📈 预测结果验证:")
        print(f"   预测上涨: {len(predicted_stocks)}只")
        print(f"   实际上涨: {correct}只")
        print(f"   实际下跌: {wrong}只")
        print(f"   准确率: {accuracy:.1f}%")
        
        print(f"\n📋 详细明细:")
        for d in sorted(details, key=lambda x: x["change_pct"], reverse=True):
            status = "✅" if d["correct"] else "❌"
            print(f"   {status} {d['name']:8s} 预测:{d['pred_score']:+3d} 实际:{d['change_pct']:+.2f}%")
        
        # 保存验证结果
        validation_result = {
            "prediction_date": target_date,
            "validation_date": latest_date,
            "predicted_count": len(predicted_stocks),
            "correct": correct,
            "wrong": wrong,
            "accuracy": accuracy,
            "details": details
        }
        
        result_file = PREDICTION_DIR / f"validation_{target_date}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(validation_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ 验证结果已保存: {result_file}")
        return validation_result
        
    finally:
        bs.logout()

def get_accuracy_trend(days=30):
    """获取准确率趋势"""
    import glob
    
    validation_files = sorted(PREDICTION_DIR.glob("validation_*.json"))
    validation_files = validation_files[-days:]
    
    if not validation_files:
        return None
    
    accuracies = []
    for f in validation_files:
        with open(f, "r") as fp:
            data = json.load(fp)
            accuracies.append({
                "date": data["prediction_date"],
                "accuracy": data["accuracy"]
            })
    
    return accuracies

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "validate":
            validate_predictions()
        elif sys.argv[1] == "trend":
            trend = get_accuracy_trend()
            if trend:
                print("\n📈 准确率趋势 (最近):")
                for t in trend[-10:]:
                    print(f"   {t['date']}: {t['accuracy']:.1f}%")
    else:
        print("用法:")
        print("  python dss_validator.py validate  - 验证3日前预测")
        print("  python dss_validator.py trend      - 查看准确率趋势")
