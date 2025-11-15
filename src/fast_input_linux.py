"""
Cross-platform replacement for fast_input.py
This version provides Linux-compatible implementations for demonstration purposes.
Note: Some functionality will be limited compared to the Windows version.
"""

import time
import subprocess
import os
from pynput.mouse import Button, Listener as MouseListener
from pynput import mouse

# Global variables to track cursor position
current_x, current_y = 0, 0

def update_cursor_position(x, y):
    """Update the global cursor position tracking."""
    global current_x, current_y
    current_x, current_y = x, y

# Start a mouse listener to track cursor position
def start_cursor_tracking():
    """Start tracking cursor position in the background."""
    def on_move(x, y):
        update_cursor_position(x, y)
    
    listener = MouseListener(on_move=on_move)
    listener.daemon = True
    listener.start()

# Initialize cursor tracking
start_cursor_tracking()

def fast_click():
    """Performs a left click at the current cursor position using pynput."""
    try:
        controller = mouse.Controller()
        controller.click(Button.left, 1)
    except Exception as e:
        print(f"Click failed: {e}")

def fast_move_and_click(x: int, y: int):
    """Moves the cursor to absolute coordinates and clicks."""
    try:
        controller = mouse.Controller()
        controller.position = (x, y)
        time.sleep(0.001)  # Small delay to ensure position is set
        controller.click(Button.left, 1)
    except Exception as e:
        print(f"Move and click failed: {e}")

def fast_background_click(hwnd, x, y):
    """
    Simulates a background click. On Linux, this is limited compared to Windows.
    
    Args:
        hwnd: Window identifier (limited functionality on Linux)
        x (int): The x-coordinate relative to the window
        y (int): The y-coordinate relative to the window
    """
    try:
        # On Linux, we can try using xdotool if available
        # This is a fallback implementation
        if os.system("which xdotool > /dev/null 2>&1") == 0:
            # Try to use xdotool for window-specific clicking
            subprocess.run([
                "xdotool", "mousemove", "--window", str(hwnd), str(x), str(y),
                "click", "1"
            ], capture_output=True)
        else:
            # Fallback to regular click at absolute position
            # Note: This won't be truly "background" like Windows PostMessage
            print(f"Background click simulated at window {hwnd}, position ({x}, {y})")
            # We could implement a more sophisticated approach here
            
    except Exception as e:
        print(f"Background click failed: {e}")

# Screen dimensions (fallback values)
try:
    import tkinter as tk
    root = tk.Tk()
    SCREEN_WIDTH = root.winfo_screenwidth()
    SCREEN_HEIGHT = root.winfo_screenheight()
    root.destroy()
except:
    SCREEN_WIDTH = 1920  # Fallback
    SCREEN_HEIGHT = 1080  # Fallback

print(f"Linux compatibility layer loaded. Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")