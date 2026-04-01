"""
电脑控制工具箱 (System Control Toolkit)
让AI能够操作这台电脑的"手脚"
"""
import os
import subprocess
import psutil
import json
from datetime import datetime

# ============ 1. 系统监控 ============

def get_system_stats():
    """获取系统状态 (CPU/内存/磁盘/进程)"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 内存
        memory = psutil.virtual_memory()
        
        # 磁盘
        disk = psutil.disk_usage('/')
        
        # 进程 (按内存排序 top 10)
        processes = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    'pid': p.info['pid'],
                    'name': p.info['name'],
                    'cpu': p.info['cpu_percent'] or 0,
                    'memory': p.info['memory_percent'] or 0
                })
            except:
                pass
        
        processes.sort(key=lambda x: x['memory'], reverse=True)
        top_processes = processes[:10]
        
        return {
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count
            },
            'memory': {
                'total_gb': round(memory.total / (1024**3), 1),
                'used_gb': round(memory.used / (1024**3), 1),
                'available_gb': round(memory.available / (1024**3), 1),
                'percent': memory.percent
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 1),
                'used_gb': round(disk.used / (1024**3), 1),
                'free_gb': round(disk.free / (1024**3), 1),
                'percent': disk.percent
            },
            'top_processes': top_processes
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def get_system_info():
    """获取系统基本信息"""
    return {
        'hostname': os.uname().nodename,
        'os': f"{os.uname().sysname} {os.uname().release}",
        'arch': os.uname().machine,
        'python_version': os.sys.version,
        'home': os.path.expanduser('~'),
        'cwd': os.getcwd(),
        'uptime_seconds': psutil.boot_time() and (datetime.now().timestamp() - psutil.boot_time())
    }


# ============ 2. 进程管理 ============

def list_processes(pattern=None, limit=20):
    """列出进程"""
    processes = []
    for p in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'create_time']):
        try:
            info = p.info
            if pattern is None or pattern.lower() in info['name'].lower():
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'status': info['status'],
                    'cpu': round(info['cpu_percent'] or 0, 1),
                    'memory': round(info['memory_percent'] or 0, 1)
                })
        except:
            pass
    
    # 按CPU排序
    processes.sort(key=lambda x: x['cpu'], reverse=True)
    return processes[:limit]


def kill_process(pid):
    """终止进程"""
    try:
        p = psutil.Process(pid)
        p.terminate()
        return {'status': 'ok', 'message': f'进程 {pid} 已终止'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ============ 3. 文件操作增强 ============

def get_directory_tree(path, max_depth=2):
    """获取目录树"""
    def walk_dir(current_path, current_depth):
        if current_depth > max_depth:
            return []
        
        items = []
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                rel_path = os.path.relpath(item_path, path)
                
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'type': 'directory',
                        'children': walk_dir(item_path, current_depth + 1) if current_depth < max_depth else []
                    })
                else:
                    size = os.path.getsize(item_path)
                    items.append({
                        'name': item,
                        'type': 'file',
                        'size': size
                    })
        except PermissionError:
            pass
        
        return items
    
    return {
        'path': path,
        'tree': walk_dir(path, 0)
    }


# ============ 4. 网络状态 ============

def get_network_stats():
    """获取网络状态"""
    stats = psutil.net_io_counters()
    return {
        'bytes_sent': stats.bytes_sent,
        'bytes_recv': stats.bytes_recv,
        'packets_sent': stats.packets_sent,
        'packets_recv': stats.packets_recv,
        'errin': stats.errin,
        'errout': stats.errout
    }


def get_connections():
    """获取网络连接"""
    connections = []
    for conn in psutil.net_connections(kind='inet'):
        if conn.status:
            connections.append({
                'family': 'IPv4' if conn.family == 2 else 'IPv6',
                'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else '',
                'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else '',
                'status': conn.status,
                'pid': conn.pid
            })
    return connections[:50]


# ============ 5. 用户会话 ============

def get_login_users():
    """获取登录用户"""
    users = []
    for user in psutil.users():
        users.append({
            'name': user.name,
            'terminal': user.terminal,
            'host': user.host,
            'started': datetime.fromtimestamp(user.started).isoformat()
        })
    return users


# ============ 6. 服务管理 (systemd) ============

def list_services():
    """列出服务"""
    try:
        result = subprocess.run(['systemctl', 'list-units', '--type=service', '--all', '--no-pager'], 
                              capture_output=True, text=True, timeout=10)
        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题
        
        services = []
        for line in lines[:30]:
            parts = line.split()
            if len(parts) >= 4:
                services.append({
                    'name': parts[0],
                    'load': parts[1],
                    'active': parts[2],
                    'sub': parts[3]
                })
        return services
    except Exception as e:
        return {'error': str(e)}


# ============ 7. 截屏 (需要DISPLAY) ============

def screenshot(filename=None):
    """截取屏幕 - 需要图形界面"""
    if not os.environ.get('DISPLAY'):
        return {
            'status': 'error', 
            'message': '无图形界面 (DISPLAY未设置)', 
            'hint': '这是无头服务器，无法截屏'
        }
    
    # 尝试使用pyscreenshot
    try:
        import pyscreenshot as ImageGrab
        if filename is None:
            filename = f"/tmp/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        img = ImageGrab.grab()
        img.save(filename)
        return {'status': 'ok', 'filename': filename}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ============ 8. 鼠标/键盘控制 (需要DISPLAY) ============

def mouse_move(x, y):
    """移动鼠标 - 需要图形界面"""
    if not os.environ.get('DISPLAY'):
        return {'status': 'error', 'message': '无图形界面'}
    
    try:
        import pyautogui
        pyautogui.moveTo(x, y)
        return {'status': 'ok', 'message': f'移动到 ({x}, {y})'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def mouse_click(x=None, y=None, button='left'):
    """点击鼠标 - 需要图形界面"""
    if not os.environ.get('DISPLAY'):
        return {'status': 'error', 'message': '无图形界面'}
    
    try:
        import pyautogui
        if x and y:
            pyautogui.click(x, y, button=button)
        else:
            pyautogui.click(button=button)
        return {'status': 'ok', 'message': f'点击 {button}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def keyboard_type(text):
    """输入文本 - 需要图形界面"""
    if not os.environ.get('DISPLAY'):
        return {'status': 'error', 'message': '无图形界面'}
    
    try:
        import pyautogui
        pyautogui.write(text)
        return {'status': 'ok', 'message': f'输入: {text}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def keyboard_hotkey(*keys):
    """发送快捷键 - 需要图形界面"""
    if not os.environ.get('DISPLAY'):
        return {'status': 'error', 'message': '无图形界面'}
    
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
        return {'status': 'ok', 'message': f'快捷键: {"+".join(keys)}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ============ 9. 应用控制 ============

# 允许的安全应用列表
SAFE_APPS = {
    'browser': ['xdg-open', 'https://'],
    'files': ['nautilus', ''],
    'terminal': ['gnome-terminal', ''],
    'code': ['code', ''],
}

def open_app(app_name):
    """打开应用 - 安全版本
    
    ⚠️ 只允许预定义的安全应用
    """
    try:
        # 检查是否在允许列表中
        if app_name.lower() not in SAFE_APPS:
            return {'status': 'error', 'message': f'应用 "{app_name}" 不在允许列表中'}
        
        cmd, _ = SAFE_APPS[app_name.lower()]
        # ✅ 使用 shell=False 安全调用
        subprocess.Popen([cmd], shell=False)
        return {'status': 'ok', 'message': f'启动: {app_name}'}
    except FileNotFoundError:
        return {'status': 'error', 'message': f'应用未找到: {app_name}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def run_command(cmd):
    """运行命令并返回输出 - 安全版本
    
    ⚠️ 只允许安全的命令列表，禁止 shell 注入
    """
    # 允许的安全命令白名单
    SAFE_COMMANDS = ['ls', 'cat', 'grep', 'find', 'df', 'du', 'top', 'ps', 'date']
    
    try:
        # 检查命令是否在白名单中
        cmd_base = cmd.split()[0] if isinstance(cmd, str) else cmd[0]
        if cmd_base not in SAFE_COMMANDS:
            return {'status': 'error', 'message': f'命令 "{cmd_base}" 不在允许列表中'}
        
        # ✅ 使用 shell=False 安全调用，参数列表形式
        if isinstance(cmd, str):
            cmd = cmd.split()
        
        result = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=30)
        return {
            'status': 'ok',
            'returncode': result.returncode,
            'stdout': result.stdout[:5000],
            'stderr': result.stderr[:1000]
        }
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': '命令超时'}
    except FileNotFoundError:
        return {'status': 'error', 'message': f'命令未找到: {cmd_base}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ============ 主函数 - 测试 ============

if __name__ == "__main__":
    print("=" * 50)
    print("系统控制工具箱 - 测试")
    print("=" * 50)
    
    # 测试系统状态
    print("\n[1] 系统状态")
    stats = get_system_stats()
    print(f"CPU: {stats['cpu']['percent']}%")
    print(f"内存: {stats['memory']['used_gb']}GB / {stats['memory']['total_gb']}GB")
    
    # 测试系统信息
    print("\n[2] 系统信息")
    info = get_system_info()
    print(f"主机名: {info['hostname']}")
    print(f"系统: {info['os']}")
    
    # 测试进程列表
    print("\n[3] Top进程")
    procs = list_processes(limit=5)
    for p in procs:
        print(f"  {p['name']}: CPU {p['cpu']}%, MEM {p['memory']}%")
    
    # 测试网络
    print("\n[4] 网络状态")
    net = get_network_stats()
    print(f"发送: {net['bytes_sent']/1024/1024:.1f} MB")
    print(f"接收: {net['bytes_recv']/1024/1024:.1f} MB")
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
