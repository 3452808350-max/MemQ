"""
真实基本面数据获取模块 v3
使用东方财富接口获取实时数据
"""
import requests

def get_stock_realtime(symbol):
    """
    使用东方财富接口获取实时数据
    """
    # 转换代码: sh.600519 -> 1.600519, sz.000333 -> 0.000333
    if symbol.startswith('sh'):
        code = f"1.{symbol.replace('sh.', '')}"
    elif symbol.startswith('sz'):
        code = f"0.{symbol.replace('sz.', '')}"
    else:
        return None
    
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fltt": "2",
        "fields": "f43,f58,f162,f167,f170",
        "secid": code,
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if data.get('data'):
            f = data['data']
            return {
                'name': f.get('f58', ''),
                'code': symbol,
                'close': f.get('f43', 0),
                'pe': f.get('f162', 0),
                'pb': f.get('f167', 0),
                'change_pct': f.get('f170', 0),
            }
    except Exception as e:
        print(f"获取失败 {symbol}: {e}")
        return None

if __name__ == "__main__":
    stocks = ['sh.600519', 'sz.000333', 'sh.601111', 'sh.600048', 'sz.002304', 'sz.300024']
    
    print("=== 真实基本面数据 ===")
    for s in stocks:
        data = get_stock_realtime(s)
        if data:
            print(f"{s} {data['name']:8s} 价:{data['close']:7.2f} PE:{data['pe']:6.1f} PB:{data['pb']:4.1f} 涨跌:{data['change_pct']:+5.2f}%")
        else:
            print(f"{s}: 获取失败")
