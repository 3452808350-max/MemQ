#!/usr/bin/env python3
import paramiko
import sys

hostname = '192.168.4.147'
port = 3410
username = 'rootKYJ'
password = 'Kyj 1145141919810.'  # EXACT: Space and period

print(f"Connecting to {hostname}:{port}...")
print(f"Username: {username}")
print(f"Password: '{password}' (length: {len(password)})")

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Attempting connection...")
    client.connect(hostname, port=port, username=username, password=password, timeout=10)
    
    print("✅ SSH CONNECTION SUCCESSFUL!")
    print("")
    print("=" * 60)
    print("BASIC HARDWARE INFORMATION")
    print("=" * 60)
    print("")
    
    # 1. System info
    stdin, stdout, stderr = client.exec_command('uname -a')
    print("1. SYSTEM:")
    print(f"   {stdout.read().decode().strip()}")
    print("")
    
    # 2. CPU info
    stdin, stdout, stderr = client.exec_command('lscpu 2>/dev/null || cat /proc/cpuinfo | grep -E "model name|processor" | head -5')
    print("2. CPU INFORMATION:")
    cpu_info = stdout.read().decode().strip().split('\n')
    for line in cpu_info[:5]:
        print(f"   {line}")
    print("")
    
    # 3. Memory info
    stdin, stdout, stderr = client.exec_command('free -h')
    print("3. MEMORY:")
    mem_lines = stdout.read().decode().strip().split('\n')
    for line in mem_lines:
        print(f"   {line}")
    print("")
    
    # 4. Disk info
    stdin, stdout, stderr = client.exec_command('df -h 2>/dev/null | head -15')
    print("4. DISK USAGE:")
    disk_lines = stdout.read().decode().strip().split('\n')
    for line in disk_lines:
        print(f"   {line}")
    print("")
    
    # 5. OS version
    stdin, stdout, stderr = client.exec_command('cat /etc/os-release 2>/dev/null || cat /etc/issue 2>/dev/null || echo "OS info not available"')
    print("5. OPERATING SYSTEM:")
    os_info = stdout.read().decode().strip().split('\n')
    for line in os_info[:10]:
        print(f"   {line}")
    print("")
    
    # 6. Uptime
    stdin, stdout, stderr = client.exec_command('uptime')
    print("6. UPTIME:")
    print(f"   {stdout.read().decode().strip()}")
    print("")
    
    # 7. Load average
    stdin, stdout, stderr = client.exec_command('cat /proc/loadavg 2>/dev/null')
    print("7. LOAD AVERAGE:")
    load = stdout.read().decode().strip()
    if load:
        print(f"   {load}")
    else:
        print("   Not available")
    print("")
    
    # 8. Network interfaces
    stdin, stdout, stderr = client.exec_command('ip addr show 2>/dev/null || ifconfig 2>/dev/null || echo "Network info not available"')
    print("8. NETWORK INTERFACES (first 10 lines):")
    net_lines = stdout.read().decode().strip().split('\n')[:10]
    for line in net_lines:
        print(f"   {line}")
    print("")
    
    # 9. NAS-specific: Running services
    stdin, stdout, stderr = client.exec_command('ps aux | head -10')
    print("9. RUNNING PROCESSES (top 10):")
    proc_lines = stdout.read().decode().strip().split('\n')
    for line in proc_lines:
        print(f"   {line}")
    print("")
    
    # 10. Hardware temperature (if available)
    stdin, stdout, stderr = client.exec_command('sensors 2>/dev/null || echo "Temperature sensors not available"')
    print("10. TEMPERATURE:")
    temp_lines = stdout.read().decode().strip().split('\n')[:5]
    for line in temp_lines:
        print(f"   {line}")
    print("")
    
    # 11. Additional: Storage devices
    stdin, stdout, stderr = client.exec_command('lsblk 2>/dev/null || echo "lsblk not available"')
    print("11. STORAGE DEVICES:")
    storage = stdout.read().decode().strip()
    if storage and "not available" not in storage:
        print(storage[:300] + "..." if len(storage) > 300 else storage)
    else:
        print("   Storage device info not available")
    print("")
    
    print("=" * 60)
    print("CONNECTION SUCCESSFUL - ALL INFORMATION RETRIEVED!")
    print("=" * 60)
    
    client.close()
    
except paramiko.AuthenticationException:
    print("❌ AUTHENTICATION FAILED!")
    print("Double-check:")
    print(f"   Username: '{username}'")
    print(f"   Password: '{password}'")
    print(f"   Port: {port}")
except paramiko.SSHException as e:
    print(f"❌ SSH ERROR: {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()