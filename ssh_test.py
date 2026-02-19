#!/usr/bin/env python3
import subprocess
import sys

host = "192.168.4.147"
port = 3410
user = "rootKYJ"

# Try different password combinations
passwords = [
    "Kyj 1145141919810.",  # Original with space and period
    "Kyj1145141919810",    # No space, no period
    "1145141919810",       # Just numbers
    "Kyj1145141919810.",   # No space, with period
    "Kyj 1145141919810",   # Space, no period
]

for pwd in passwords:
    print(f"\nTrying password: '{pwd}'")
    try:
        # Use ssh with expect-like behavior
        cmd = f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{host} 'echo SUCCESS && uname -a'"
        
        # Create a process with password input
        proc = subprocess.Popen(
            ['sshpass', '-p', pwd] + cmd.split()[1:],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        if "SUCCESS" in stdout:
            print(f"✅ SUCCESS with password: '{pwd}'")
            print(f"Output: {stdout[:200]}...")
            break
        else:
            print(f"❌ Failed: {stderr[:100]}")
            
    except subprocess.TimeoutExpired:
        print("Timeout")
    except Exception as e:
        print(f"Error: {e}")

print("\nIf none worked, SSH might require key authentication or different username.")