#!/usr/bin/env python3
import paramiko

hostname = '192.168.4.147'
port = 3410
password = 'Kyj 1145141919810.'

# Try different username combinations
usernames = ['rootKYJ', 'root', 'admin', 'Administrator', 'fnos', 'feiniu']

for username in usernames:
    print(f"\nTrying username: '{username}'")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, timeout=5)
        
        print(f"✅ SUCCESS with username: '{username}'!")
        
        # Get basic info
        stdin, stdout, stderr = client.exec_command('uname -a && echo "---" && hostname')
        print(f"System: {stdout.read().decode().strip()}")
        
        client.close()
        break
        
    except paramiko.AuthenticationException:
        print(f"❌ Authentication failed for '{username}'")
    except Exception as e:
        print(f"Error: {e}")

print("\nIf all failed, possible issues:")
print("1. SSH service not running on port 3410")
print("2. Password is incorrect")
print("3. SSH configured for key authentication only")
print("4. User account disabled")
print("5. Firewall blocking connection")