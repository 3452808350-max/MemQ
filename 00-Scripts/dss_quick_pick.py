"""
DSS 快速选股 - 生成每日推荐 (直接使用 baostock)
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# 精选 20 只股票快速分析
STOCKS = {
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    'sh.601398': ('工商银行', '银行'),
    'sh.601318': ('中国平安', '保险'),
    'sz.002594': ('比亚迪', '新能源车'),
    'sz.300750': ('宁德时代', '电池'),
    'sh.603986': ('兆易创新', '芯片'),
    'sz.002415': ('海康威视', '安防'),
    'sh.601012': ('隆基绿能', '光伏'),
    'sh.600036': ('招商银行', '银行'),
    'sh.600276': ('恒瑞医药', '医药'),
    'sz.000333': ('美的集团', '家电'),
    'sh.601857': ('中国石油', '能源'),
    'sh.600570': ('恒生电子', '软件'),
    'sz.300033': ('同花顺', '软件'),
    'sh.688981': ('中芯国际', '芯片'),
    'sh.601766': ('中国中车', '高铁'),
    'sz.002352': ('顺丰控股', '快递'),
    'sh.600900': ('长江电力', '电力'),
    'sh.601668': ('中国建筑', '基建'),
}

def get_stock_data_baostock(code, days=60):
    """直接从 baostock 获取数据"""
    try:
        lg = bs.login()
        if lg.error_code != '0':
            bs.logout()
            return None
        
        start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=start_date,
            frequency="d"
        )
        
        data_list = []
        while rs.error_code == '0' and rs.next():
            data_list.append(rs.get_row_data())
        
        bs.logout()
        
        if not data_list:
            return None
        
        df = pd.DataFrame(data_list, columns=['date','open','high','low','close','volume'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df.dropna().tail(days)
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return None

def add_technical_indicators(df):
    """添加技术指标"""
    df = df.copy()
    
    # MA
    df['MA5'] = df['close'].rolling(5).mean()
    df['MA20'] = df['close'].rolling(20).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 成交量均线
    df['volume_MA20'] = df['volume'].rolling(20).mean()
    
    return df

def analyze_stock(symbol):
    """分析单只股票"""
    try:
        df = get_stock_data_baostock(symbol, 60)
        if df is None or len(df) < 40:
            return None
        
        df = add_technical_indicators(df)
        df = df.dropna()
        if len(df) < 20:
            return None
        
        latest = df.iloc[-1]
        
        # 技术信号评分
        score = 0
        
        # RSI
        rsi = latest.get('RSI', 50)
        if rsi < 30:
            score += 20
        elif rsi > 70:
            score -= 20
        elif rsi < 40:
            score += 10
        elif rsi > 60:
            score -= 10
        
        # MACD
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_signal', 0)
        if macd > macd_signal:
            score += 15
        else:
            score -= 15
        
        # 均线
        ma5 = latest.get('MA5', 0)
        ma20 = latest.get('MA20', 0)
        if ma5 > ma20:
            score += 10
        else:
            score -= 10
        
        # 成交量
        vol_ma = latest.get('volume_MA20', 0)
        volume = latest.get('volume', 0)
        if vol_ma > 0 and volume > vol_ma * 1.2:
            score += 10
        elif vol_ma > 0 and volume > vol_ma:
            score += 5
        
        # 近期动量
        close = latest['close']
        close_5d_ago = df.iloc[-5]['close'] if len(df) >= 5 else close
        momentum = (close - close_5d_ago) / close_5d_ago
        if momentum > 0.05:
            score += 15
        elif momentum > 0:
            score += 5
        elif momentum < -0.05:
            score -= 15
        else:
            score -= 5
        
        return {
            'close': float(close),
            'score': score,
            'rsi': float(rsi) if rsi else 50.0,
            'macd': '金叉' if macd > macd_signal else '死叉',
            'momentum': f'{momentum*100:+.1f}%',
            'volume_ratio': f'{volume/vol_ma:.2f}x' if vol_ma > 0 else 'N/A',
        }
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def pick_stocks():
    """选股"""
    print("正在分析股票...")
    
    results = []
    for code, (name, industry) in STOCKS.items():
        print(f"  {name}...", end=" ", flush=True)
        info = analyze_stock(code)
        if info:
            info['code'] = code
            info['name'] = name
            info['industry'] = industry
            results.append(info)
            print(f"✓ {info['score']:+d}")
        else:
            print("✗")
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def generate_report():
    """生成报告"""
    today = datetime.now().strftime("%Y年%m月%d日")
    results = pick_stocks()
    
    if not results:
        return "⚠️ 无法获取足够数据"
    
    best = results[0]
    top5 = results[:5]
    
    # 分类
    tech = [r for r in results if r['industry'] in ['芯片', '软件', '电池', '新能源车', '光伏', '安防']]
    traditional = [r for r in results if r['industry'] not in ['芯片', '软件', '电池', '新能源车', '光伏', '安防']]
    
    content = f"""
══════════════════════════════════════════════════════════
           📊 DSS 每日投资建议
           {today}
══════════════════════════════════════════════════════════

🏆 今日首选

   {best['name']} ({best['code']})
   行业：{best['industry']}
   现价：¥{best['close']:.2f}
   
   综合评分：{best['score']:+d}
   RSI: {best['rsi']:.1f} | MACD: {best['macd']}
   5 日动量：{best['momentum']}
   成交量：{best['volume_ratio']}

──────────────────────────────────────────────────────────
📈 Top 5 推荐

"""
    for i, r in enumerate(top5, 1):
        content += f"   {i}. {r['name']:10s} {r['industry']:6s}  评分:{r['score']:+3d}  动量:{r['momentum']}\n"
    
    content += f"""
──────────────────────────────────────────────────────────
📊 行业对比

"""
    if tech:
        content += f"   科技股最佳：{tech[0]['name']} ({tech[0]['score']:+d})\n"
    if traditional:
        content += f"   传统股最佳：{traditional[0]['name']} ({traditional[0]['score']:+d})\n"
    
    content += f"""
──────────────────────────────────────────────────────────
💡 策略建议

"""
    if best['score'] > 30:
        content += "   ✅ 强烈关注 - 技术面积极，动量良好\n"
    elif best['score'] > 10:
        content += "   👍 适度关注 - 有一定机会\n"
    elif best['score'] > 0:
        content += "   ⚠️ 观望为主 - 信号中性\n"
    else:
        content += "   🛡️ 防御策略 - 市场偏弱\n"
    
    content += f"""
⚠️ 免责声明：AI 生成内容仅供参考，不构成投资建议。
   投资有风险，决策需谨慎。

══════════════════════════════════════════════════════════
"""
    return content

if __name__ == "__main__":
    print(generate_report())
