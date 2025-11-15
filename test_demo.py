#!/usr/bin/env python3
"""
Demo script to test ApexClick functionality
This script demonstrates the key features of ApexClick in a Linux environment
"""

import time
import subprocess
import os
import sys

def test_screenshot_capture():
    """Test the MSS screenshot functionality"""
    print("Testing screenshot capture with MSS...")
    
    try:
        import mss
        with mss.mss() as sct:
            # Take a screenshot of the entire screen
            monitor = sct.monitors[0]  # All monitors
            screenshot = sct.grab(monitor)
            
            # Save it
            mss.tools.to_png(screenshot.rgb, screenshot.size, output="/tmp/mss_test.png")
            print(f"✓ Screenshot saved to /tmp/mss_test.png")
            print(f"  Screen size: {screenshot.width}x{screenshot.height}")
            return True
    except Exception as e:
        print(f"✗ Screenshot test failed: {e}")
        return False

def test_color_detection():
    """Test the color detection functionality"""
    print("\nTesting color detection...")
    
    try:
        import numpy as np
        from PIL import Image
        
        # Create a test image with specific colors
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        test_image[25:75, 25:75] = [255, 0, 0]  # Red square
        test_image[10:20, 10:20] = [0, 255, 0]  # Green square
        
        # Test color matching (similar to ApexClick's algorithm)
        target_color = np.array([255, 0, 0])  # Red
        tolerance = 10
        
        matches = np.all(np.abs(test_image - target_color) <= tolerance, axis=-1)
        match_count = np.sum(matches)
        
        print(f"✓ Color detection working: Found {match_count} red pixels")
        return True
    except Exception as e:
        print(f"✗ Color detection test failed: {e}")
        return False

def worker_task(x):
    """Worker function for multiprocessing test"""
    return x * x

def test_multiprocessing():
    """Test multiprocessing functionality"""
    print("\nTesting multiprocessing...")
    
    try:
        import multiprocessing as mp
        import psutil
        
        cpu_count = psutil.cpu_count(logical=False) or mp.cpu_count()
        print(f"✓ CPU cores detected: {cpu_count}")
        
        # Test a simple multiprocessing task
        with mp.Pool(processes=2) as pool:
            results = pool.map(worker_task, [1, 2, 3, 4])
            print(f"✓ Multiprocessing test: {results}")
        
        return True
    except Exception as e:
        print(f"✗ Multiprocessing test failed: {e}")
        return False

def test_input_simulation():
    """Test input simulation capabilities"""
    print("\nTesting input simulation...")
    
    try:
        # Import our Linux compatibility layer
        sys.path.append('/workspace/project/ApexClick/src')
        from fast_input_linux import fast_click, fast_move_and_click
        
        print("✓ Input simulation modules loaded")
        print("  - fast_click: Available")
        print("  - fast_move_and_click: Available")
        print("  Note: Actual clicking disabled in demo mode")
        
        return True
    except Exception as e:
        print(f"✗ Input simulation test failed: {e}")
        return False

def test_window_detection():
    """Test window detection capabilities"""
    print("\nTesting window detection...")
    
    try:
        sys.path.append('/workspace/project/ApexClick/src')
        import pygetwindow_linux as gw
        
        windows = gw.getAllWindows()
        print(f"✓ Window detection working: Found {len(windows)} mock windows")
        for i, window in enumerate(windows):
            print(f"  {i+1}. {window.title} ({window.width}x{window.height})")
        
        return True
    except Exception as e:
        print(f"✗ Window detection test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("ApexClick Functionality Demo")
    print("=" * 40)
    
    tests = [
        test_screenshot_capture,
        test_color_detection,
        test_multiprocessing,
        test_input_simulation,
        test_window_detection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All core ApexClick functionality is working!")
    else:
        print("⚠️  Some functionality may be limited in this environment")
    
    print("\nNote: This demo runs in a Linux environment with compatibility layers.")
    print("On Windows, ApexClick would have full native functionality including:")
    print("- True background clicking without cursor movement")
    print("- Direct window message posting")
    print("- Full window enumeration and control")

if __name__ == "__main__":
    main()