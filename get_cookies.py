#!/usr/bin/env python3
import sqlite3
import os
import json

cookie_db = "/home/kyj/snap/firefox/common/.mozilla/firefox/5v4fhvdo.default/cookies.sqlite"

if not os.path.exists(cookie_db):
    print("Cookie database not found")
    exit(1)

try:
    conn = sqlite3.connect(cookie_db)
    cursor = conn.cursor()
    
    # Query for DeepSeek cookies
    cursor.execute("""
        SELECT host, name, value, path, expiry, lastAccessed
        FROM moz_cookies 
        WHERE host LIKE '%deepseek%' OR host LIKE '%platform.deepseek%'
        ORDER BY lastAccessed DESC
    """)
    
    cookies = cursor.fetchall()
    
    print(f"Found {len(cookies)} DeepSeek cookies:")
    print("-" * 80)
    
    for i, (host, name, value, path, expiry, lastAccessed) in enumerate(cookies, 1):
        print(f"{i}. Host: {host}")
        print(f"   Name: {name}")
        print(f"   Value: {value[:50]}..." if len(value) > 50 else f"   Value: {value}")
        print(f"   Path: {path}")
        print(f"   Last Accessed: {lastAccessed}")
        print()
    
    conn.close()
    
    # Also try to create a curl cookie jar
    if cookies:
        print("\n=== Curl Cookie Jar Format ===")
        with open("cookies.txt", "w") as f:
            for host, name, value, path, expiry, lastAccessed in cookies:
                # Convert to Netscape cookie format for curl
                f.write(f"{host}\tTRUE\t{path}\tFALSE\t{expiry}\t{name}\t{value}\n")
        print("Cookies saved to cookies.txt")
        
except Exception as e:
    print(f"Error reading cookies: {e}")
    import traceback
    traceback.print_exc()