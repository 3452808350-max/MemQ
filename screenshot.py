#!/usr/bin/env python3
import os
import sys
from PIL import ImageGrab

try:
    # Take screenshot
    screenshot = ImageGrab.grab()
    
    # Save to file
    output_path = "/home/kyj/.openclaw/workspace/screenshot.png"
    screenshot.save(output_path)
    
    # Check file size
    file_size = os.path.getsize(output_path)
    print(f"Screenshot saved to: {output_path}")
    print(f"File size: {file_size} bytes")
    print(f"Dimensions: {screenshot.size}")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Try installing: pip install pillow")
except Exception as e:
    print(f"Error taking screenshot: {e}")
    import traceback
    traceback.print_exc()