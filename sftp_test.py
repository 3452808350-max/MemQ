#!/usr/bin/env python3
import paramiko
import sys

hostname = '192.168.4.147'
port = 3410
username = 'rootKYJ'
password = 'Kyj1145141919810'  # No space, no period

print(f"Testing SFTP connection to {hostname}:{port}...")
print(f"Username: {username}")
print(f"Password: {password}")

try:
    # Create transport
    transport = paramiko.Transport((hostname, port))
    
    print("Attempting authentication...")
    transport.connect(username=username, password=password)
    
    print("✅ Authentication successful!")
    
    # Create SFTP client
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    print("\n=== Listing root directory ===")
    files = sftp.listdir('.')
    for file in files[:10]:  # Show first 10 files
        print(f"  {file}")
    
    print(f"\nTotal files in root: {len(files)}")
    
    # Get some system info if possible
    print("\n=== Trying to get system info ===")
    try:
        # Try to read some system files
        with sftp.open('/proc/version', 'r') as f:
            version = f.read(200).decode('utf-8', errors='ignore')
            print(f"Kernel version: {version[:100]}...")
    except:
        print("Could not read /proc/version")
    
    try:
        with sftp.open('/etc/os-release', 'r') as f:
            os_info = f.read(500).decode('utf-8', errors='ignore')
            print(f"\nOS Info:\n{os_info[:200]}...")
    except:
        print("Could not read /etc/os-release")
    
    # Check disk space
    print("\n=== Checking disk usage ===")
    try:
        stdin, stdout, stderr = transport.open_session()
        stdout.channel.exec_command('df -h')
        output = stdout.read().decode('utf-8', errors='ignore')
        print(output[:500])
    except:
        print("Could not execute remote command")
    
    sftp.close()
    transport.close()
    
except paramiko.AuthenticationException:
    print("❌ Authentication failed!")
    print("Possible issues:")
    print("1. Wrong username/password")
    print("2. SSH key authentication required")
    print("3. Account disabled or locked")
except paramiko.SSHException as e:
    print(f"❌ SSH error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()