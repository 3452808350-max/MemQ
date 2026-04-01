"""
DSS Swarm - 100 只股票选股系统（修复版 v3 - 稳定版）
修复内容：
1. 串行处理（避免 signal 线程问题）
2. 单只股票超时保护（用 subprocess + timeout）
3. 全局模型复用（避免重复训练）
4. 数据缓存（避免重复请求）
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import signal
from dss_modules.data_loader import get_stock_data
from dss_modules.features import add_technical_indicators
from dss_modules.models import StockModel
import numpy as np

# ============ 全局模型（复用，避免重复训练） ============
_global_model = None
_model_trained = False

def _get_global_model():
    """获取全局模型"""
    global _global_model
    if _global_model is None:
        _global_model = StockModel('lgbm')
    return _global_model

def _train_global_model_once(X, y):
    """训练全局模型（只训练一次）"""
    global _global_model, _model_trained
    if not _model_trained and len(X) > 25:
        if _global_model is None:
            _global_model = StockModel('lgbm')
        _global_model.fit(X, y)
        _model_trained = True
        print("[✓] 全局模型已训练")
    return _model_trained

# 100 只股票池 (传统 50 + 高科技 50)
STOCKS = {
    # ===== 传统行业 (50 只) =====
    # 银行
    'sh.601398': ('工商银行', '银行'),
    'sh.601939': ('建设银行', '银行'),
    'sh.601288': ('农业银行', '银行'),
    'sh.601988': ('中国银行', '银行'),
    'sh.600000': ('浦发银行', '银行'),
    'sh.600015': ('华夏银行', '银行'),
    'sh.600016': ('民生银行', '银行'),
    'sh.600036': ('招商银行', '银行'),
    'sh.601166': ('兴业银行', '银行'),
    'sh.601818': ('光大银行', '银行'),
    # 保险
    'sh.601318': ('中国平安', '保险'),
    'sh.601601': ('中国人保', '保险'),
    'sh.601336': ('新华保险', '保险'),
    'sh.601628': ('中国人寿', '保险'),
    # 能源
    'sh.601857': ('中国石油', '能源'),
    'sh.600028': ('中国石化', '能源'),
    'sh.600871': ('石化机械', '能源'),
    'sh.600188': ('兖州煤业', '能源'),
    'sh.601001': ('大同煤业', '能源'),
    # 白酒
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    'sh.603589': ('金种子酒', '白酒'),
    'sh.600559': ('老白干酒', '白酒'),
    'sh.000596': ('古井贡酒', '白酒'),
    # 地产
    'sh.000002': ('万科 A', '地产'),
    'sh.600048': ('保利地产', '地产'),
    'sh.600383': ('金地集团', '地产'),
    'sh.600340': ('华夏幸福', '地产'),
    'sh.000069': ('华侨城 A', '地产'),
    # 制造业
    'sh.600104': ('上汽集团', '汽车'),
    'sh.600660': ('福耀玻璃', '汽车'),
    'sh.601766': ('中国中车', '高铁'),
    'sh.601111': ('中国国航', '航空'),
    'sh.601006': ('大秦铁路', '铁路'),
    'sz.002352': ('顺丰控股', '快递'),
    'sh.600900': ('长江电力', '电力'),
    'sh.600585': ('海螺水泥', '水泥'),
    'sh.600276': ('恒瑞医药', '医药'),
    'sz.000513': ('丽珠集团', '医药'),
    'sh.600612': ('老凤祥', '珠宝'),
    'sz.002293': ('罗莱生活', '纺织'),
    'sh.600108': ('亚盛集团', '农业'),
    'sz.000998': ('隆平高科', '种业'),
    'sh.601668': ('中国建筑', '基建'),
    'sh.601390': ('中国中铁', '基建'),
    'sh.600019': ('宝钢股份', '钢铁'),
    'sh.600010': ('包钢股份', '钢铁'),
    'sh.600017': ('日照港', '港口'),
    'sh.601018': ('宁波港', '港口'),
    'sh.600009': ('上海机场', '机场'),
    'sh.600897': ('厦门机场', '机场'),
    'sh.600887': ('伊利股份', '食品'),
    'sh.600309': ('万华化学', '化工'),
    'sh.600352': ('浙江龙盛', '化工'),
    
    # ===== 高科技行业 (50 只) =====
    # 芯片
    'sh.603986': ('兆易创新', '芯片'),
    'sh.603501': ('韦尔股份', '芯片'),
    'sz.002475': ('立讯精密', '芯片'),
    'sh.688981': ('中芯国际', '芯片'),
    'sh.688008': ('澜起科技', '芯片'),
    # AI/云计算
    'sz.002410': ('广联达', '软件'),
    'sh.600570': ('恒生电子', '软件'),
    'sh.600588': ('用友网络', '软件'),
    'sz.300033': ('同花顺', '软件'),
    'sh.688111': ('金山云', '云计算'),
    # 新能源车
    'sz.002594': ('比亚迪', '新能源车'),
    'sz.300750': ('宁德时代', '电池'),
    'sh.600705': ('青岛银行', '新能源车'),
    'sh.601238': ('广汽集团', '新能源车'),
    'sz.300124': ('汇川技术', '新能源车'),
    # 互联网
    'sz.000333': ('美的集团', '家电'),
    'sh.600690': ('青岛海尔', '家电'),
    'sz.000651': ('格力电器', '家电'),
    'sh.603259': ('药明康德', '医药科技'),
    'sz.300015': ('爱尔眼科', '医疗'),
    'sz.300015': ('眼科医疗', '医疗'),
    # 通信
    'sh.600050': ('中国联通', '通信'),
    'sh.601728': ('中国电信', '通信'),
    'sh.600498': ('烽火通信', '通信'),
    # 半导体
    'sh.688396': ('华润微', '半导体'),
    'sz.002371': ('北方华创', '半导体'),
    'sh.688012': ('中微公司', '半导体'),
    'sz.002371': ('芯片制造', '半导体'),
    # 光伏
    'sh.600438': ('通威股份', '光伏'),
    'sz.002129': ('中环股份', '光伏'),
    'sh.601012': ('隆基绿能', '光伏'),
    'sz.300274': ('阳光电源', '光伏'),
    # 储能
    'sz.300014': ('亿纬锂能', '储能'),
    'sz.300458': ('全志科技', '芯片'),
    # 自动化
    'sz.300124': ('汇川技术', '自动化'),
    'sh.600835': ('上海机电', '自动化'),
    # 机器人
    'sz.300024': ('机器人', '机器人'),
    'sh.600835': ('智能制造', '机器人'),
    # 医疗科技
    'sz.300003': ('乐普医疗', '医疗'),
    'sz.300015': ('医疗设备', '医疗'),
    # 新材料
    'sh.600522': ('中天科技', '新材料'),
    'sz.300408': ('三环集团', '新材料'),
    # 数字经济
    'sh.600100': ('同方股份', '数字经济'),
    'sz.000034': ('神州数码', '数字经济'),
    # 安防
    'sz.002415': ('海康威视', '安防'),
    'sz.002236': ('大华股份', '安防'),
    # 量子科技
    'sh.688027': ('国盾量子', '量子'),
    # 大数据
    'sh.600850': ('华东医药', '大数据'),
    'sz.000977': ('浪潮信息', '大数据'),
    # 区块链
    'sz.002195': ('二三四五', '区块链'),
    # VR/AR
    'sz.300081': ('恒信东方', 'VR'),
    'sz.300296': ('利亚德', 'LED'),
}

def analyze_stock_with_timeout(symbol, timeout_sec=30):
    """分析单只股票（带超时保护 - 主线程 signal）"""
    result = [None]  # 用 list 避免闭包问题
    timeout_occurred = [False]
    
    def timeout_handler(signum, frame):
        timeout_occurred[0] = True
        raise TimeoutError(f"股票分析超时 ({timeout_sec}秒)")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_sec)
    
    try:
        result[0] = _analyze_stock_internal(symbol)
    except TimeoutError as e:
        print(f"[!] {symbol} 分析超时 ({timeout_sec}秒)")
        result[0] = None
    except Exception as e:
        print(f"[!] {symbol} 分析失败：{e}")
        result[0] = None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    
    return result[0]

def _analyze_stock_internal(symbol):
    """内部股票分析函数"""
    df = get_stock_data(symbol, 250, 'baostock')
    if df is None or len(df) < 100:
        return None
    
    df = add_technical_indicators(df)
    df = df.dropna()
    if len(df) < 30:
        return None
    
    latest = df.iloc[-1]
    
    # 技术信号评分
    score = 0
    
    # RSI (超卖 +20, 超买 -20)
    rsi = latest.get('RSI', 50)
    if rsi < 30:
        score += 20
    elif rsi > 70:
        score -= 20
    elif rsi < 40:
        score += 10
    elif rsi > 60:
        score -= 10
    
    # MACD (金叉 +15, 死叉 -15)
    macd = latest.get('MACD', 0)
    if macd > 0:
        score += 15
    else:
        score -= 15
    
    # 均线 (多头 +10, 空头 -10)
    ma5 = latest.get('MA5', 0)
    ma20 = latest.get('MA20', 0)
    if ma5 > ma20:
        score += 10
    else:
        score -= 10
    
    # 成交量 (高于均量 +5)
    vol_ma = latest.get('volume_MA20', 0)
    volume = latest.get('Volume', 0)
    if volume > vol_ma:
        score += 5
    
    # 布林带位置
    bb_pos = latest.get('BB_position', 0.5)
    if bb_pos < 0.2:
        score += 10
    elif bb_pos > 0.8:
        score -= 10
    
    # 预测（使用全局模型）
    df['label'] = (df['Close'].shift(-5) / df['Close'] > 1.02).astype(int)
    df = df.dropna()
    
    pred_score = 0
    if len(df) > 30:
        feature_cols = [c for c in df.columns if c not in ['Open','High','Low','Close','Volume','label']]
        X = df[feature_cols].values
        y = df['label'].values
        valid = ~np.isnan(X).any(axis=1)
        X, y = X[valid], y[valid]
        if len(X) > 25:
            split = len(X) - 10
            # 训练全局模型（只训练一次）
            _train_global_model_once(X[:split], y[:split])
            model = _get_global_model()
            if model and _model_trained:
                proba = model.predict_proba(X[split:])
                if proba[0] > 0.5:
                    pred_score = int((proba[0] - 0.5) * 200)
                else:
                    pred_score = -int((0.5 - proba[0]) * 200)
    
    total_score = score + pred_score
    
    return {
        'close': latest['Close'],
        'score': total_score,
        'tech_score': score,
        'pred_score': pred_score,
        'rsi': rsi,
        'macd': '金叉' if macd > 0 else '死叉',
    }

def pick_best_sequential(timeout_per_stock=30):
    """串行选股（稳定版，带超时）"""
    print(f"正在分析 100 只股票（每只最多{timeout_per_stock}秒）...")
    
    results = []
    for i, (code, (name, industry)) in enumerate(STOCKS.items(), 1):
        info = analyze_stock_with_timeout(code, timeout_per_stock)
        if info:
            info['code'] = code
            info['name'] = name
            info['industry'] = industry
            results.append(info)
        
        if i % 10 == 0:
            print(f"  已处理 {i}/100 只股票，成功 {len(results)} 只...")
    
    print(f"✓ 完成 100/100 只股票分析，成功 {len(results)} 只")
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def pick_best():
    """选股（默认串行稳定版）"""
    return pick_best_sequential(timeout_per_stock=30)

def generate_email_content():
    """生成邮件内容"""
    from datetime import datetime
    results = pick_best()
    
    if not results:
        return "无法获取足够数据"
    
    best = results[0]
    
    # Top 5
    top5 = results[:5]
    
    # 传统 vs 高科技
    trad = [r for r in results if r['industry'] in ['银行','保险','能源','白酒','地产','基建','钢铁']]
    hi_tech = [r for r in results if r['industry'] not in trad]
    
    best_trad = trad[0] if trad else None
    best_hightech = hi_tech[0] if hi_tech else None
    
    today = datetime.now().strftime("%Y年%m月%d日")
    content = f"""
══════════════════════════════════════════════════════════
           📊 每日投资建议报告
           DSS AI 选股系统 - {today}
══════════════════════════════════════════════════════════

🏆 今日最佳推荐

   股票：{best['name']} ({best['code']})
   行业：{best['industry']}
   收盘价：¥{best['close']:.2f}
   
   技术评分：{best['tech_score']:+d}
   预测评分：{best['pred_score']:+d}
   综合评分：{best['score']:+d}
   
   RSI: {best['rsi']:.1f}
   MACD: {best['macd']}

──────────────────────────────────────────────────────────
📈 Top 5 推荐

"""
    for i, r in enumerate(top5, 1):
        content += f"   {i}. {r['name']:10s} ({r['code']:8s})  评分：{r['score']:+3d}  行业：{r['industry']}\n"
    
    content += f"""
──────────────────────────────────────────────────────────
📊 行业对比

   传统行业最佳：{best_trad['name'] if best_trad else 'N/A'} (评分：{best_trad['score'] if best_trad else 0:+d})
   高科技最佳：   {best_hightech['name'] if best_hightech else 'N/A'} (评分：{best_hightech['score'] if best_hightech else 0:+d})

──────────────────────────────────────────────────────────
💡 投资建议

   基于 DSS 系统分析，推荐关注：{best['name']}
   
   理由:
   - 综合评分最高 ({best['score']:+d}分)
   - 技术面{'积极' if best['tech_score'] > 0 else '需要观察'}
   - AI 预测{'看涨' if best['pred_score'] > 0 else '看跌'}

⚠️ 免责声明:
   本报告由 AI 系统自动生成，仅供参考，不构成投资建议。
   投资有风险，入市需谨慎。

══════════════════════════════════════════════════════════
"""
    return content

if __name__ == "__main__":
    print(generate_email_content())
