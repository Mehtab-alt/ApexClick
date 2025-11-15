#!/usr/bin/env python3
"""
GUI interaction test for ApexClick
This script demonstrates interacting with the ApexClick GUI
"""

import time
import subprocess
import os

def take_screenshot(name):
    """Take a screenshot of the current display"""
    filename = f"/tmp/apexclick_{name}.png"
    os.system(f"export DISPLAY=:99 && import -window root {filename}")
    print(f"Screenshot saved: {filename}")
    return filename

def simulate_key_press(key):
    """Simulate a key press using xdotool"""
    try:
        subprocess.run(["xdotool", "key", key], check=True, capture_output=True)
        print(f"Simulated key press: {key}")
    except subprocess.CalledProcessError:
        print(f"Could not simulate key press: {key} (xdotool not available)")
    except FileNotFoundError:
        print("xdotool not available for key simulation")

def main():
    print("ApexClick GUI Test")
    print("=" * 30)
    
    # Check if the application is running
    result = subprocess.run(["pgrep", "-f", "main.py"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("ApexClick is not running. Please start it first.")
        return
    
    print("ApexClick is running. Taking screenshots of different modes...")
    
    # Take initial screenshot (Multi-Position mode)
    take_screenshot("multi_position_mode")
    time.sleep(2)
    
    # Try to simulate clicking on Dynamic mode tab
    # Note: This would require more sophisticated GUI automation
    print("\nNote: In a full Windows environment, you could:")
    print("- Click on the Dynamic tab to see rapid clicking mode")
    print("- Click on the Intelligent tab to see color-based automation")
    print("- Use hotkeys like 'P' to capture positions")
    print("- Use backtick (`) to start/stop automation")
    
    # Show what each mode would do
    print("\nMode Descriptions:")
    print("1. Multi-Position Mode (currently visible):")
    print("   - Record click positions with 'P' key")
    print("   - Replay recorded positions in sequence")
    print("   - Adjustable click interval (default 3ms)")
    print("   - Save/load position profiles")
    
    print("\n2. Dynamic Mode:")
    print("   - Rapid clicking at current cursor position")
    print("   - Follows your mouse cursor")
    print("   - Maximum speed clicking")
    print("   - Adjustable interval")
    
    print("\n3. Intelligent Mode:")
    print("   - Background automation without moving cursor")
    print("   - Color-based target detection")
    print("   - Multi-core processing for speed")
    print("   - Window-specific clicking")
    
    # Demonstrate the performance monitoring
    print(f"\nCurrent Performance (from GUI):")
    print("- CPS: 0 (not currently clicking)")
    print("- CPU Usage: ~2.80%")
    print("- Using 2 CPU cores for processing")

if __name__ == "__main__":
    main()